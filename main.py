import re
import os
import json
import traceback
from typing import List, Dict, Any
from datetime import datetime
from core.external_api_client import ExternalAPIClient
from core.tool_manager import ToolManager
from core.cognitive_lattice import CognitiveLattice, SessionManager
from core.llama_client import diagnose_user_intent

def main():
    # === Initialize session manager and cognitive lattice === #
    session_manager = SessionManager()
    print(f"🧠 Cognitive Lattice initialized for session: {session_manager.lattice.session_id}")

    # === Initialize Tool Manager === #
    tool_manager = ToolManager()
    print(f"🔧 Tool Manager initialized")

    print("📋 CognitiveLattice Interactive Agent")
    print("=" * 50)
    
    # Initialize external API client
    try:
        external_api = ExternalAPIClient()
        print(f"🌐 External API client initialized")
    except Exception as e:
        print(f"⚠️ Could not initialize External API Client: {e}")
        external_api = None

    # === Interactive User-Driven Analysis ===
    print("\n💬 Starting Interactive Analysis Engine")
    print("=" * 50)
    print("🔔 NOTE: External API calls will ONLY be made when you explicitly request them!")
    print("Enter your request (e.g., 'Help me plan a trip', 'Process my document'), or type 'exit' to quit.")

    while True:
        try:
            user_query = input("\nYour request: ")
            if user_query.lower() in ['exit', 'quit']:
                print("✅ Exiting interactive session.")
                break

            # 1. Check for active task FIRST - this creates a "task lock"
            # Clean up any malformed tasks first
            session_manager.lattice.cleanup_malformed_tasks()
            
            active_task = session_manager.lattice.get_active_task()
            
            # DEBUG: Show task status
            all_tasks = session_manager.lattice.get_nodes("task")
            if all_tasks:
                print(f"🔍 DEBUG: Found {len(all_tasks)} total tasks in lattice")
                for i, task in enumerate(all_tasks):
                    status = task.get("status", "unknown")
                    title = task.get("task_title", task.get("query", "Unknown"))[:50]
                    has_plan = "task_plan" in task and len(task.get("task_plan", [])) > 0
                    completed_count = len(task.get("completed_steps", []))
                    print(f"   Task {i+1}: {title}... (status: {status}, has_plan: {has_plan}, completed: {completed_count})")
            
            if active_task:
                print(f"🔒 ACTIVE TASK FOUND: {active_task.get('task_title', 'Untitled')[:50]}...")
            else:
                print(f"🔓 NO ACTIVE TASK FOUND")
            
            if active_task:
                # TASK LOCK: When a task is active, ALL input is treated as task-related
                task_progress = session_manager.lattice.get_task_progress(active_task)
                print(f"📊 Task Lock Active: {task_progress['completed_steps']}/{task_progress['total_steps']} steps completed")
                
                # Force intent to be "task" - bypass all other intent diagnosis
                intent = "task"
                action = "step_input"
                
                # Only check for explicit continuation keywords
                continue_keywords = ["continue", "next", "proceed", "go ahead", "keep going", "yes", "ok", "okay"]
                if user_query.lower().strip() in continue_keywords:
                    action = "continue"
                    print(f"   - Forced Intent: {intent} (continuation)")
                else:
                    print(f"   - Forced Intent: {intent} (user providing step input)")
                    
            else:
                # No active task, do normal intent detection
                print("🧠 Diagnosing user intent...")
                intent_info = diagnose_user_intent(user_query)
                intent = intent_info.get("intent", "query")
                action = intent_info.get("action", "query")
                
                # Handle nested intent/action structures
                if isinstance(intent, dict):
                    intent = intent.get("type", intent.get("intent", "query"))
                if isinstance(action, dict):
                    action = action.get("type", action.get("action", "query"))
                
                print(f"   - Intent: {intent}, Action: {action}")

            # 2. Add this turn to the cognitive lattice (audit log style)
            if intent == "task" and action == "step_input" and active_task:
                # For step input, we DON'T pre-add to lattice here
                # The task handler will create the updated node with API results
                pass
            else:
                # Add new event for new plan, chat, or query
                lattice_event = {
                    "type": intent,
                    "query": user_query,
                    "action": action,
                    "timestamp": datetime.now().isoformat(),
                    "status": "pending"
                }
                session_manager.lattice.add_event(lattice_event)

            # === Intent-based Routing === #
            if intent in ["chat", "simple", "conversation"]:
                # Simple chat intent: respond conversationally
                print(f"💬 [Simple Chat]: Routing to external API for conversational response...")
                if external_api:
                    try:
                        # Direct API call for simple chat - no chunking, no RAG
                        chat_response = external_api.query_external_api(user_query)
                        print(f"✅ Chat response received")
                        print(f"\n💬 Response: {chat_response}")
                        
                        # Log the chat response as an event
                        session_manager.lattice.add_event({
                            "type": "chat_response",
                            "timestamp": datetime.now().isoformat(),
                            "query": user_query,
                            "response": chat_response,
                            "status": "completed"
                        })
                        
                    except Exception as e:
                        print(f"❌ Chat API call failed: {e}")
                        fallback_response = "I'm here to chat, but I'm having trouble connecting to my chat system right now."
                        print(f"💬 Fallback: {fallback_response}")
                        session_manager.lattice.add_event({
                            "type": "chat_response",
                            "timestamp": datetime.now().isoformat(),
                            "query": user_query,
                            "response": fallback_response,
                            "status": "error",
                            "error": str(e)
                        })
                else:
                    fallback_response = "I'm here to chat! (External API not available)"
                    print(f"💬 [Chatbot]: {fallback_response}")
                    session_manager.lattice.add_event({
                        "type": "chat_response",
                        "timestamp": datetime.now().isoformat(),
                        "query": user_query,
                        "response": fallback_response,
                        "status": "completed"
                    })

            elif intent == "query" and action in ["query", "question", "ask", "simple_question_answering"]:
                # Simple specific query - now handled by tools if applicable
                print(f"❓ [Query]: Checking for tool-enhanced response...")
                
                # Check if tools can handle this query
                tool_enhancement = tool_manager.enhance_llm_response(
                    user_query,
                    context={
                        'external_client': external_api,
                        'session_manager': session_manager
                    }
                )
                
                if tool_enhancement['tools_used']:
                    # Tools handled the query
                    print(f"🔧 Tool detected: {', '.join(tool_enhancement['tools_used'])}")
                    print(tool_enhancement['enhanced_response'])
                    
                    # Log as a tool execution event
                    session_manager.lattice.add_event({
                        "type": "tool_execution",
                        "timestamp": datetime.now().isoformat(),
                        "query": user_query,
                        "tools_used": tool_enhancement['tools_used'],
                        "result": tool_enhancement['enhanced_response'],
                        "status": "completed"
                    })
                    
                    # Save the lattice after tool execution
                    session_manager.lattice.save()
                else:
                    # No tools, fallback to direct API call
                    if external_api:
                        try:
                            query_response = external_api.query_external_api(user_query)
                            print(f"✅ Query response received")
                            print(f"\n💡 Response: {query_response}")
                            
                            # Log the query response as an event
                            session_manager.lattice.add_event({
                                "type": "query_response",
                                "timestamp": datetime.now().isoformat(),
                                "query": user_query,
                                "response": query_response,
                                "status": "completed"
                            })
                            
                            # Save the lattice
                            session_manager.lattice.save()
                            
                        except Exception as e:
                            print(f"❌ Query API call failed: {e}")
                            fallback_response = "I'd be happy to help answer that, but I'm having trouble connecting right now."
                            print(f"💡 Fallback: {fallback_response}")
                            session_manager.lattice.add_event({
                                "type": "query_response",
                                "timestamp": datetime.now().isoformat(),
                                "query": user_query,
                                "response": fallback_response,
                                "status": "error",
                                "error": str(e)
                            })
                            
                            # Save the lattice
                            session_manager.lattice.save()
                    else:
                        fallback_response = "I'd be happy to help answer that! (External API not available)"
                        print(f"💡 [Query]: {fallback_response}")
                        session_manager.lattice.add_event({
                            "type": "query_response",
                            "timestamp": datetime.now().isoformat(),
                            "query": user_query,
                            "response": fallback_response,
                            "status": "completed"
                        })
                        
                        # Save the lattice
                        session_manager.lattice.save()

            elif intent in ["analysis", "summarize", "broad"] or (intent == "specific" and action in ["analyze", "summarize", "extract", "review"]) or (intent == "query" and action in ["extract", "analyze", "review"]):
                # Document analysis queries - now handled by tools
                print(f"📊 [Document Analysis]: Checking for tool-enhanced response...")
                
                # Check if tools can handle this analysis
                tool_enhancement = tool_manager.enhance_llm_response(
                    user_query,
                    context={
                        'external_client': external_api,
                        'session_manager': session_manager
                    }
                )
                
                if tool_enhancement['tools_used']:
                    # Tools handled the analysis
                    print(f"🔧 Tool detected: {', '.join(tool_enhancement['tools_used'])}")
                    print(tool_enhancement['enhanced_response'])
                    
                    # Log as a tool execution event
                    session_manager.lattice.add_event({
                        "type": "tool_execution",
                        "timestamp": datetime.now().isoformat(),
                        "query": user_query,
                        "tools_used": tool_enhancement['tools_used'],
                        "result": tool_enhancement['enhanced_response'],
                        "status": "completed"
                    })
                    
                    # Save the lattice after tool execution
                    session_manager.lattice.save()
                else:
                    # No document processing tools available
                    print("⚠️ Document analysis requires document processing tools to be loaded first.")
                    print("💡 Try: 'Process my document' first, then ask analysis questions.")
                    
                    session_manager.lattice.add_event({
                        "type": "analysis_request",
                        "timestamp": datetime.now().isoformat(),
                        "query": user_query,
                        "response": "Document processing tools required",
                        "status": "requires_tools"
                    })
                    
                    # Save the lattice after adding event
                    session_manager.lattice.save()

            elif intent in ["task", "structured_task", "plan", "planner"] or (intent == "query" and action in ["plan", "planning", "step_by_step", "itinerary"]):
                # This is the master logic for handling all structured tasks.
                print(f"🧩 [Task Planner]: Routing to structured task handler.")
                
                current_task = session_manager.lattice.get_active_task()
                
                # SCENARIO 1: A task is already active. The user is providing input for the current step.
                if current_task:
                    print(f"📋 Continuing existing task: {current_task.get('task_title', 'Untitled Task')}")
                    print(f"🔍 Task details: query='{current_task.get('query', 'N/A')[:30]}...', status='{current_task.get('status', 'N/A')}'")
                    task_plan = current_task.get("task_plan", [])
                    completed_steps = current_task.get("completed_steps", [])
                    print(f"🔍 Task has {len(task_plan)} planned steps and {len(completed_steps)} completed steps")
                    
                    # Handle "continue/next" action - advance to next step
                    if action == "continue":
                        # Mark current step as completed and move to next
                        completed_steps = current_task.get("completed_steps", [])
                        current_step_index = len(completed_steps)
                        
                        # Mark the current in-progress step as fully completed (if it exists)
                        if completed_steps and completed_steps[-1].get("status") == "in_progress":
                            step_number = completed_steps[-1].get("step_number", len(completed_steps))
                            session_manager.lattice.mark_step_completed(step_number)
                            print(f"✅ Step {step_number} marked as completed")
                        
                        # Check if there are more steps
                        task_plan = current_task.get("task_plan", [])
                        if current_step_index < len(task_plan):
                            next_step_description = task_plan[current_step_index]
                            print(f"\n⏭️ Moving to step {current_step_index + 1}/{len(task_plan)}: {next_step_description}")
                            print(f"💡 Provide the information for this step or type 'continue' if no input is needed.")
                            session_manager.lattice.save()
                            continue  # Skip the rest of the task logic, wait for user input on new step
                        else:
                            session_manager.lattice.complete_current_task()
                            print(f"🎉 Task completed! All {len(task_plan)} steps executed.")
                            continue
                    
                    # Normal step processing - find current active step (first incomplete step)
                    current_step_index = 0
                    
                    # Find the first step that hasn't been completed yet
                    for i, step_data in enumerate(completed_steps):
                        if step_data.get("status") == "completed":
                            current_step_index = i + 1
                        else:
                            # Found an in-progress or incomplete step, this is our current step
                            current_step_index = i
                            break
                    
                    # If all existing steps are completed, we're on the next new step
                    if current_step_index >= len(completed_steps):
                        current_step_index = len(completed_steps)
                    
                    # Validate that the task has a proper task plan
                    if not task_plan:
                        print("⚠️ Found task without a valid plan. Marking as completed and starting fresh.")
                        current_task["status"] = "completed"
                        session_manager.lattice.save()
                        # Set current_task to None so we create a new task
                        current_task = None
                    elif current_step_index < len(task_plan):
                        # Process the current step
                        current_step_description = task_plan[current_step_index]
                        print(f"🎯 Executing step {current_step_index + 1}/{len(task_plan)}: {current_step_description}")
                        
                        # Build comprehensive context for external API
                        tool_context = ""
                        if hasattr(tool_manager, 'recent_tool_results') and tool_manager.recent_tool_results:
                            tool_context = "\n\nRECENT TOOL RESULTS AVAILABLE:\n"
                            for tool_name, tool_result in tool_manager.recent_tool_results.items():
                                tool_context += f"\n{tool_name.upper()} RESULTS:\n"
                                
                                # Generic tool result formatting - works for ANY tool
                                if isinstance(tool_result, dict):
                                    # Look for common patterns in tool results
                                    if 'options' in str(tool_result).lower():
                                        # Tool provided options/choices
                                        for key, value in tool_result.items():
                                            if isinstance(value, list) and len(value) > 0:
                                                tool_context += f"{key.replace('_', ' ').title()}:\n"
                                                for i, option in enumerate(value[:5], 1):  # Show max 5 options
                                                    if isinstance(option, dict):
                                                        # Format option details generically
                                                        option_str = ", ".join([f"{k}: {v}" for k, v in option.items() if not k.startswith('_')])
                                                        tool_context += f"  Option {i}: {option_str[:100]}...\n"
                                                    else:
                                                        tool_context += f"  Option {i}: {str(option)[:100]}...\n"
                                    elif 'selected' in str(tool_result).lower():
                                        # Tool made a selection
                                        for key, value in tool_result.items():
                                            if 'selected' in key.lower():
                                                if isinstance(value, dict):
                                                    selection_str = ", ".join([f"{k}: {v}" for k, v in value.items() if not k.startswith('_')])
                                                    tool_context += f"SELECTED: {selection_str[:150]}...\n"
                                                else:
                                                    tool_context += f"SELECTED: {str(value)[:150]}...\n"
                                    else:
                                        # Generic formatting for any other tool result
                                        result_str = str(tool_result)[:300]
                                        tool_context += f"{result_str}...\n"
                                else:
                                    # Non-dict result
                                    tool_context += f"{str(tool_result)[:300]}...\n"
                                    
                            tool_context += "\nNOTE: User may refer to these results by option number (e.g., 'option 2' means the second option above).\n"
                        
                        # Add dynamic task context from cognitive lattice
                        dynamic_context = ""
                        if current_task:
                            # Extract dynamic context from the actual task and session history
                            dynamic_context = "\n\nTASK CONTEXT:\n"
                            dynamic_context += f"- Original Request: {current_task.get('query', 'Unknown')}\n"
                            dynamic_context += f"- Task Type: {current_task.get('task_title', 'Unknown Task')}\n"
                            dynamic_context += f"- Started: {current_task.get('created', 'Unknown')}\n"
                            
                            # Extract key details from session events and completed steps
                            session_events = session_manager.lattice.event_log
                            completed_steps = current_task.get('completed_steps', [])
                            
                            # Look for important contextual information in the session
                            context_details = []
                            for event in session_events[-10:]:  # Look at recent events
                                if event.get('type') == 'tool_execution':
                                    tools_used = event.get('tools_used', [])
                                    if tools_used:
                                        context_details.append(f"Used tools: {', '.join(tools_used)}")
                            
                            # Show what's been accomplished so far
                            if completed_steps:
                                dynamic_context += f"- Progress: {len(completed_steps)} steps completed\n"
                                for step in completed_steps[-3:]:  # Show last 3 steps
                                    step_num = step.get('step_number', '?')
                                    step_desc = step.get('description', 'Unknown step')[:50]
                                    dynamic_context += f"  Step {step_num}: {step_desc}...\n"
                            
                            # Show current tool results/selections if available
                            if hasattr(tool_manager, 'recent_tool_results') and tool_manager.recent_tool_results:
                                dynamic_context += "- Current Selections:\n"
                                for tool_name, result in tool_manager.recent_tool_results.items():
                                    # Generic selection detection - works for ANY tool
                                    if isinstance(result, dict):
                                        for key, value in result.items():
                                            if 'selected' in key.lower() and isinstance(value, dict):
                                                # Extract key details from any selected item
                                                item_details = []
                                                for detail_key, detail_value in value.items():
                                                    if not detail_key.startswith('_') and detail_value:
                                                        item_details.append(f"{detail_key}: {detail_value}")
                                                
                                                if item_details:
                                                    selection_summary = ", ".join(item_details[:3])  # Show first 3 details
                                                    tool_display_name = tool_name.replace('_', ' ').title()
                                                    dynamic_context += f"  ✅ {tool_display_name}: {selection_summary[:100]}...\n"
                        
                        step_execution_prompt = f"""You are helping a user with a step-by-step task plan. Here is the complete context:

ORIGINAL TASK PLAN YOU CREATED:
{chr(10).join([f"{i+1}. {step}" for i, step in enumerate(current_task.get('task_plan', []))])}

CURRENT STEP: You are currently working on Step {current_step_index + 1} of this task plan.
CURRENT STEP DESCRIPTION: "{current_step_description}"

USER INPUT FOR THIS STEP: "{user_query}"

{dynamic_context}{tool_context}

INSTRUCTIONS: 
- The user has provided input specifically for Step {current_step_index + 1}: "{current_step_description}"
- Factor in the user's new input and provide a response that addresses this specific step
- IMPORTANT: Use the TASK CONTEXT above to understand what this task is really about
- If user refers to options by number (e.g., "option 2"), use the tool results context above
- Consider what's already been selected (marked with ✅)
- Do NOT advance to other steps - focus only on completing or updating Step {current_step_index + 1}
- Provide a helpful, actionable response for this current step based on the user's input

COMPLETED STEPS SO FAR:
{chr(10).join([f"Step {step.get('step_number', i+1)}: {step.get('description', 'No description')} - COMPLETED" for i, step in enumerate(completed_steps)]) if completed_steps else "None completed yet"}

Please respond with information relevant to Step {current_step_index + 1} only."""
                        
                        if external_api:
                            try:
                                # 🔧 TOOL-FIRST APPROACH: Check for tools before making external API call
                                tool_enhancement = tool_manager.enhance_llm_response(
                                    user_query,  # Check user input directly for tool needs
                                    context={
                                        'step_number': current_step_index + 1,
                                        'step_description': current_step_description,
                                        'user_input': user_query,
                                        'task_context': current_task,
                                        'external_client': external_api  # Pass LLM for tool selection
                                    }
                                )
                                
                                # If tools were used, skip external API call and use tool results directly
                                if tool_enhancement['tools_used']:
                                    print(f"🔧 Tools detected - using tool results directly (skipping external API)")
                                    final_step_result = tool_enhancement['enhanced_response']
                                else:
                                    # No tools needed, proceed with normal external API call
                                    step_result = external_api.query_external_api(step_execution_prompt)
                                    final_step_result = step_result
                                
                                # Log tool usage if any tools were used
                                if tool_enhancement['tools_used']:
                                    print(f"🔧 Tools used: {', '.join(tool_enhancement['tools_used'])}")
                                    session_manager.lattice.add_event({
                                        "type": "tools_executed",
                                        "timestamp": datetime.now().isoformat(),
                                        "step_number": current_step_index + 1,
                                        "tools_used": tool_enhancement['tools_used'],
                                        "tool_results": tool_enhancement['tool_results']
                                    })
                                
                                # Update the active task state using the new hybrid approach
                                session_manager.lattice.execute_step(
                                    step_number=current_step_index + 1,
                                    user_input=user_query,
                                    result=final_step_result
                                )
                                
                                print(f"🔄 Step {current_step_index + 1} updated:")
                                
                                # Display the result with better formatting
                                if "FLIGHT SEARCH RESULTS FOUND" in final_step_result or "FLIGHT SELECTION CONFIRMED" in final_step_result:
                                    # Show full flight results without truncation
                                    print(f"   📄 Result: {final_step_result}")
                                else:
                                    # For other results, show more characters but still truncate if very long
                                    if len(final_step_result) > 5000:
                                        print(f"   📄 Result: {final_step_result[:5000]}...")
                                    else:
                                        print(f"   📄 Result: {final_step_result}")
                                
                                print(f"\n💡 This step is ready. You can:")
                                print(f"   - Type 'next' or 'continue' to move to the next step")
                                print(f"   - Provide more information to refine this step further")
                                print(f"   - Ask questions about this step")

                                session_manager.lattice.save()

                            except Exception as e:
                                print(f"❌ Step execution failed: {e}")
                                # Log the error event
                                session_manager.lattice.add_event({
                                    "type": "step_error",
                                    "timestamp": datetime.now().isoformat(),
                                    "step_number": current_step_index + 1,
                                    "error": str(e),
                                    "user_input": user_query
                                })
                                session_manager.lattice.save()
                        else:
                            print("⚠️ External API not available for step execution.")
                    else:
                        print("✅ Task is already complete.")
                        current_task["status"] = "completed"
                        session_manager.lattice.save()
                        # Set current_task to None so we create a new task
                        current_task = None

                # SCENARIO 2: No active task. The user is starting a new one.
                if not current_task:
                    print("🚀 Initiating new structured task planning...")
                    if external_api:
                        try:
                            plan_response = external_api.create_task_plan(user_query)
                            
                            if plan_response.get("success"):
                                plan_text = plan_response.get("plan_text", "")
                                task_steps = [step.strip() for step in plan_text.split('\n') if step.strip() and step.strip()[0].isdigit()]
                                task_steps = [re.sub(r'^\d+\.\s*', '', step) for step in task_steps]

                                if task_steps:
                                    # Create the new task using the hybrid approach
                                    new_task = session_manager.lattice.create_new_task(user_query, task_steps)
                                    
                                    print(f"📋 Task plan created with {len(task_steps)} steps:")
                                    for i, step in enumerate(task_steps, 1):
                                        print(f"   {i}. {step}")
                                    
                                    print(f"\n🎯 Ready to execute step 1: {task_steps[0]}")
                                    print(f"💡 Provide the information for this step or type 'continue' if no input is needed.")
                                else:
                                    print("⚠️ Could not parse a valid plan from the external response.")
                                    session_manager.lattice.add_event({
                                        "type": "task_creation_failed",
                                        "timestamp": datetime.now().isoformat(),
                                        "query": user_query,
                                        "error": "Could not parse plan"
                                    })
                                    session_manager.lattice.save()
                            else:
                                print(f"⚠️ API call for planning failed: {plan_response.get('error')}")
                                session_manager.lattice.save()
                        except Exception as e:
                            print(f"❌ Task planning failed: {e}")
                            session_manager.lattice.save()
                    else:
                        print("⚠️ External API not available for task planning.")
                        session_manager.lattice.save()

            else:
                print(f"❓ [System]: Unrecognized intent '{intent}'. Please try rephrasing your request.")
                session_manager.lattice.add_event({
                    "type": "unrecognized_intent",
                    "timestamp": datetime.now().isoformat(),
                    "query": user_query,
                    "intent": intent,
                    "response": f"Unrecognized intent '{intent}'."
                })
                session_manager.lattice.save()

        except KeyboardInterrupt:
            print("\n⚠️ Process interrupted by user. Exiting.")
            break
        except Exception as e:
            print(f"\n❌ An error occurred during interactive analysis: {e}")
            traceback.print_exc()

# Only run if this file is executed directly
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error in main execution: {e}")
        traceback.print_exc()