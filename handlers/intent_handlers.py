"""
Intent-based query handlers - Separate handlers for different types of user interactions
Extracted from main.py for better modularity and testability
"""

import os
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from external_api_client import ExternalAPIClient


class BaseHandler:
    """Base class for all intent handlers"""
    
    def __init__(self, session_manager, advanced_rag=None, tool_manager=None):
        self.session_manager = session_manager
        self.advanced_rag = advanced_rag
        self.tool_manager = tool_manager
    
    def handle(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle the user query and return results"""
        raise NotImplementedError("Subclasses must implement handle method")


class ChatHandler(BaseHandler):
    """Handles simple conversational queries"""
    
    def handle(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        print(f"💬 [Simple Chat]: Routing to external API for conversational response...")
        
        if self.advanced_rag and hasattr(self.advanced_rag, 'external_client'):
            try:
                # Direct API call for simple chat - no chunking, no RAG
                chat_response = self.advanced_rag.external_client.query_external_api(user_query)
                print(f"✅ Chat response received")
                print(f"\n💬 Response: {chat_response}")
                
                # Log the chat response as an event
                self.session_manager.lattice.add_event({
                    "type": "chat_response",
                    "timestamp": datetime.now().isoformat(),
                    "query": user_query,
                    "response": chat_response,
                    "status": "completed"
                })
                
                return {
                    "status": "success",
                    "response": chat_response,
                    "type": "chat"
                }
                
            except Exception as e:
                print(f"❌ Chat API call failed: {e}")
                fallback_response = "I'm here to chat, but I'm having trouble connecting to my chat system right now."
                print(f"💬 Fallback: {fallback_response}")
                
                self.session_manager.lattice.add_event({
                    "type": "chat_response",
                    "timestamp": datetime.now().isoformat(),
                    "query": user_query,
                    "response": fallback_response,
                    "status": "error",
                    "error": str(e)
                })
                
                return {
                    "status": "error",
                    "response": fallback_response,
                    "error": str(e),
                    "type": "chat"
                }
        else:
            fallback_response = "I'm here to chat! (External API not available)"
            print(f"💬 [Chatbot]: {fallback_response}")
            
            self.session_manager.lattice.add_event({
                "type": "chat_response",
                "timestamp": datetime.now().isoformat(),
                "query": user_query,
                "response": fallback_response,
                "status": "completed"
            })
            
            return {
                "status": "success",
                "response": fallback_response,
                "type": "chat"
            }


class QueryHandler(BaseHandler):
    """Handles simple direct queries"""
    
    def handle(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        print(f"❓ [Simple Query]: Routing directly to external API...")
        
        if self.advanced_rag and hasattr(self.advanced_rag, 'external_client'):
            try:
                # Direct API call for simple questions - no chunking, no RAG
                query_response = self.advanced_rag.external_client.query_external_api(user_query)
                print(f"✅ Query response received")
                print(f"\n💡 Response: {query_response}")
                
                # Log the query response as an event
                self.session_manager.lattice.add_event({
                    "type": "query_response",
                    "timestamp": datetime.now().isoformat(),
                    "query": user_query,
                    "response": query_response,
                    "status": "completed"
                })
                
                return {
                    "status": "success",
                    "response": query_response,
                    "type": "query"
                }
                
            except Exception as e:
                print(f"❌ Query API call failed: {e}")
                fallback_response = "I'd be happy to help answer that, but I'm having trouble connecting right now."
                print(f"💡 Fallback: {fallback_response}")
                
                self.session_manager.lattice.add_event({
                    "type": "query_response",
                    "timestamp": datetime.now().isoformat(),
                    "query": user_query,
                    "response": fallback_response,
                    "status": "error",
                    "error": str(e)
                })
                
                return {
                    "status": "error",
                    "response": fallback_response,
                    "error": str(e),
                    "type": "query"
                }
        else:
            fallback_response = "I'd be happy to help answer that! (External API not available)"
            print(f"💡 [Query]: {fallback_response}")
            
            self.session_manager.lattice.add_event({
                "type": "query_response",
                "timestamp": datetime.now().isoformat(),
                "query": user_query,
                "response": fallback_response,
                "status": "completed"
            })
            
            return {
                "status": "success",
                "response": fallback_response,
                "type": "query"
            }


class AnalysisHandler(BaseHandler):
    """Handles document analysis and RAG-based queries"""
    
    def handle(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        print(f"📊 [Document Analysis]: Using advanced RAG system...")
        
        if not self.advanced_rag:
            return {
                "status": "error",
                "response": "Advanced RAG system not available for analysis queries.",
                "type": "analysis"
            }
        
        try:
            # Use the enhanced query method with fresh API call
            print(f"🌐 Making fresh API call for new analysis...")
            result = self.advanced_rag.enhanced_query(
                user_query,
                max_chunks=5,  # More chunks for better context
                enable_external_enhancement=True,
                safety_threshold=0.7
            )
            
            # Save and display results
            self._save_query_results(user_query, result)
            self._display_analysis_results(user_query, result)
            
            return {
                "status": "success",
                "result": result,
                "type": "analysis"
            }
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            traceback.print_exc()
            return {
                "status": "error",
                "response": str(e),
                "type": "analysis"
            }
    
    def _save_query_results(self, user_query: str, result: Dict[str, Any]):
        """Save interactive query results to session file"""
        # Determine session file
        session_results_file = getattr(self, 'session_results_file', None)
        if not session_results_file:
            query_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_results_file = f"interactive_session_{query_timestamp}.json"
            self.session_results_file = session_results_file
        
        # Clean the results for JSON serialization
        def clean_for_json(obj):
            """Recursively clean objects for JSON serialization"""
            if isinstance(obj, dict):
                cleaned = {}
                for key, value in obj.items():
                    if key in ['embedding', 'embeddings']:
                        cleaned[key] = f"<embedding_array_length_{len(value) if hasattr(value, '__len__') else 'unknown'}>"
                    else:
                        cleaned[key] = clean_for_json(value)
                return cleaned
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif hasattr(obj, 'tolist'):
                return f"<numpy_array_shape_{obj.shape}>"
            elif hasattr(obj, '__dict__'):
                return str(obj)
            else:
                return obj
        
        # Load existing session data
        session_data = {"queries": []}
        if hasattr(self, 'session_results_file') and os.path.exists(self.session_results_file):
            try:
                with open(self.session_results_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                if "queries" not in session_data:
                    session_data["queries"] = []
            except Exception as load_err:
                print(f"⚠️ Could not load existing session file: {load_err}")
                session_data = {"queries": []}
        
        # Format the current query result
        query_result = {
            "query": user_query,
            "timestamp": datetime.now().isoformat(),
            "query_type": "interactive_analysis",
            "chunks_found": len(result['local_results']['results']),
            "local_results": result['local_results'],
            "external_analysis": result.get('external_analysis'),
            "audit_results": result.get('audit_results'),
            "safety_status": result.get('safety_status', 'unknown')
        }
        
        # Clean and save
        cleaned_query_result = clean_for_json(query_result)
        
        if not result.get('reused_analysis'):
            session_data["queries"].append(cleaned_query_result)
            session_data["session_start"] = session_data.get("session_start", datetime.now().isoformat())
            session_data["last_updated"] = datetime.now().isoformat()
            session_data["total_queries"] = len(session_data["queries"])
            
            try:
                with open(session_results_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
                print(f"💾 Query results saved to session: {session_results_file} ({session_data['total_queries']} queries)")
            except Exception as save_error:
                print(f"⚠️ Could not save query results: {save_error}")
    
    def _display_analysis_results(self, user_query: str, result: Dict[str, Any]):
        """Display analysis results in user-friendly format"""
        print(f"\n" + "="*60)
        print(f"📝 ANALYSIS RESULTS FOR: '{user_query}'")
        print(f"="*60)
        
        local_results = result.get('local_results', {})
        if local_results and local_results.get('results'):
            print(f"📊 Found {len(local_results['results'])} relevant chunks")
        
        if result.get('reused_analysis'):
            print(f"♻️ Used previous analysis (saved ~6000 tokens)")
        
        # Extract and format the analysis from external_analysis
        if result.get('external_analysis'):
            print(f"\n🔍 DETAILED ANALYSIS:")
            enhanced_answer = result['external_analysis'].get('enhanced_answer', '')
            if enhanced_answer and isinstance(enhanced_answer, str) and len(enhanced_answer) > 0:
                print(enhanced_answer)
            else:
                print("Analysis completed but no detailed response available.")
        
        # Show source chunk previews
        if local_results and local_results.get('results'):
            print(f"\n📚 SOURCE CHUNKS:")
            for i, chunk in enumerate(local_results['results'][:3], 1):  # Show top 3
                preview = chunk.get('content', '')[:200] + "..." if len(chunk.get('content', '')) > 200 else chunk.get('content', '')
                print(f"   {i}. {preview}")
        
        # Show audit results
        if result.get('audit_results'):
            audit = result['audit_results']
            print(f"\n🛡️ AUDIT RESULTS:")
            print(f"   📋 Audit passed: {'✅' if audit.get('audit_passed') else '❌'}")
            if audit.get('safety_audit'):
                risk_level = audit['safety_audit'].get('risk_level', 'unknown')
                print(f"   ⚠️ Risk level: {risk_level}")
        
        print(f"\n" + "="*60)


class TaskHandler(BaseHandler):
    """Handles structured task planning and execution"""
    
    def handle(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        print(f"🧩 [Task Planner]: Routing to structured task handler.")
        
        # Check for active task
        current_task = self.session_manager.lattice.get_active_task()
        
        if current_task:
            return self._handle_existing_task(user_query, current_task, context)
        else:
            return self._handle_new_task(user_query, context)
    
    def _handle_existing_task(self, user_query: str, current_task: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle input for an existing active task"""
        print(f"📋 Continuing existing task: {current_task.get('task_title', 'Untitled Task')}")
        
        task_plan = current_task.get("task_plan", [])
        completed_steps = current_task.get("completed_steps", [])
        
        # Handle "continue/next" action - advance to next step
        action = context.get('action', 'step_input') if context else 'step_input'
        
        if action == "continue":
            current_step_index = len(completed_steps)
            if current_step_index < len(task_plan):
                # Mark current step as completed and move to next
                if completed_steps:
                    self.session_manager.lattice.mark_step_completed(len(completed_steps))
                    self.session_manager.lattice.save()
                    print(f"💾 Step {len(completed_steps)} marked completed and saved")
                
                next_step_index = current_step_index + 1
                next_step = task_plan[current_step_index] if current_step_index < len(task_plan) else None
                
                if next_step:
                    print(f"⏭️ Moving to step {next_step_index}/{len(task_plan)}: {next_step}")
                    return {
                        "status": "continue",
                        "current_step": next_step_index,
                        "step_description": next_step,
                        "message": f"Step {next_step_index}: {next_step}"
                    }
                else:
                    # Task completed
                    self.session_manager.lattice.complete_current_task()
                    return {
                        "status": "completed",
                        "message": "🎉 Task completed successfully!"
                    }
            else:
                return {
                    "status": "completed",
                    "message": "All steps completed. Task finished!"
                }
        else:
            # Normal step processing
            current_step_index = len(completed_steps) + 1
            step_description = task_plan[current_step_index - 1] if current_step_index <= len(task_plan) else f"Step {current_step_index}"
            
            # Execute step with tool detection
            result = self._execute_step(user_query, step_description, current_step_index)
            
            # Update lattice
            self.session_manager.lattice.execute_step(current_step_index, user_query, result["result"])
            
            # Explicitly save the lattice after step execution
            self.session_manager.lattice.save()
            print(f"💾 Step {current_step_index} saved to lattice")
            
            return result
    
    def _handle_new_task(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle creation of a new structured task"""
        print(f"🚀 Initiating new structured task planning...")
        
        if not self.advanced_rag or not hasattr(self.advanced_rag, 'external_client'):
            return {
                "status": "error",
                "message": "External API not available for task planning."
            }
        
        try:
            # Create task plan using external API
            print(f"📋 Asking external API to create a plan for: '{user_query}'")
            plan_response = self.advanced_rag.external_client.create_task_plan(user_query)
            
            if plan_response.get("success") and plan_response.get("plan"):
                task_plan = plan_response["plan"]
                print(f"📋 Task plan created with {len(task_plan)} steps:")
                for i, step in enumerate(task_plan, 1):
                    print(f"   {i}. {step}")
                
                # Create new task in lattice
                task_data = self.session_manager.lattice.create_new_task(user_query, task_plan)
                
                # Explicitly save the lattice after task creation
                self.session_manager.lattice.save()
                print(f"💾 Task saved to lattice: {self.session_manager.lattice.session_file}")
                
                # Start with first step
                first_step = task_plan[0] if task_plan else "No steps defined"
                print(f"🎯 Ready to execute step 1: {first_step}")
                
                return {
                    "status": "created",
                    "task_data": task_data,
                    "current_step": 1,
                    "step_description": first_step,
                    "total_steps": len(task_plan),
                    "message": f"Task created with {len(task_plan)} steps. Ready for step 1."
                }
            else:
                return {
                    "status": "error",
                    "message": f"Task planning failed: {plan_response.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            print(f"❌ Task planning failed: {e}")
            return {
                "status": "error",
                "message": f"Task planning failed: {str(e)}"
            }
    
    def _execute_step(self, user_input: str, step_description: str, step_number: int) -> Dict[str, Any]:
        """Execute a single task step with tool detection"""
        print(f"🎯 Executing step {step_number}: {step_description}")
        
        # Use tool manager if available
        if self.tool_manager:
            print(f"🧠 Asking LLM to select tools for: '{user_input}'")
            
            # Get tool selection from LLM
            selected_tool = self.tool_manager._llm_tool_selection(
                user_input, 
                step_description, 
                list(self.tool_manager.available_tools.keys())
            )
            
            if selected_tool:
                print(f"🎯 LLM selected tool: {selected_tool}")
                
                # Extract parameters for the tool using the tool manager's parameter extraction
                tool_calls = self.tool_manager.detect_tool_needs(user_input, {
                    "step_description": step_description,
                    "step_number": step_number
                })
                
                if tool_calls and len(tool_calls) > 0:
                    print(f"🔧 Tools detected: {', '.join([r.get('tool_name', 'unknown') for r in tool_calls])}")
                    
                    # Execute each detected tool
                    executed_results = []
                    for tool_call in tool_calls:
                        tool_name = tool_call.get('tool_name')
                        parameters = tool_call.get('parameters', {})
                        
                        print(f"🔧 Executing {tool_name} with parameters: {parameters}")
                        
                        # Actually execute the tool
                        execution_result = self.tool_manager.execute_tool(tool_name, parameters)
                        executed_results.append(execution_result)
                        
                        # Update recent_tool_results for context in future steps
                        if execution_result.get('status') == 'success':
                            self.tool_manager.recent_tool_results[tool_name] = execution_result.get('result', {})
                    
                    print(f"🔧 Tools executed successfully: {', '.join([r.get('tool_name', 'unknown') for r in executed_results])}")
                    return {
                        "status": "success",
                        "result": self._format_tool_results(executed_results),
                        "tools_used": [r.get('tool_name', selected_tool) for r in executed_results],
                        "step_number": step_number
                    }
                else:
                    print(f"🔧 Tool selected but no parameters extracted - falling back to external API")
        
        # Fallback to external API if no tools or tool execution failed
        if self.advanced_rag and hasattr(self.advanced_rag, 'external_client'):
            try:
                api_result = self.advanced_rag.external_client.query_external_api(
                    f"For the task step '{step_description}', the user provided: '{user_input}'. Please provide a helpful response."
                )
                
                return {
                    "status": "success",
                    "result": api_result,
                    "step_number": step_number,
                    "source": "external_api"
                }
                
            except Exception as e:
                return {
                    "status": "error",
                    "result": f"Step execution failed: {str(e)}",
                    "step_number": step_number
                }
        
        return {
            "status": "error",
            "result": "No execution method available",
            "step_number": step_number
        }
    
    def _format_tool_results(self, tool_results: List[Dict[str, Any]]) -> str:
        """Format tool results for display"""
        if not tool_results:
            return "No tool results available"
        
        formatted_results = []
        for tool_result in tool_results:
            tool_name = tool_result.get('tool_name', 'Unknown')
            result_data = tool_result.get('result', {})
            
            if isinstance(result_data, dict):
                formatted_results.append(f"🔧 **{tool_name.upper()} RESULTS:**\n{json.dumps(result_data, indent=2)}")
            else:
                formatted_results.append(f"🔧 **{tool_name.upper()} RESULTS:**\n{str(result_data)}")
        
        return "\n\n".join(formatted_results)


class IntentRouter:
    """Routes user queries to appropriate handlers based on intent"""
    
    def __init__(self, session_manager, advanced_rag=None, tool_manager=None):
        self.handlers = {
            "chat": ChatHandler(session_manager, advanced_rag, tool_manager),
            "query": QueryHandler(session_manager, advanced_rag, tool_manager),
            "analysis": AnalysisHandler(session_manager, advanced_rag, tool_manager),
            "task": TaskHandler(session_manager, advanced_rag, tool_manager)
        }
    
    def route_query(self, user_query: str, intent: str, action: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Route query to appropriate handler"""
        
        # Determine handler based on intent and action
        handler_key = self._determine_handler(intent, action)
        
        if handler_key in self.handlers:
            handler_context = context or {}
            handler_context.update({"intent": intent, "action": action})
            
            return self.handlers[handler_key].handle(user_query, handler_context)
        else:
            return {
                "status": "error",
                "message": f"No handler available for intent '{intent}' and action '{action}'",
                "type": "error"
            }
    
    def _determine_handler(self, intent: str, action: str = None) -> str:
        """Determine which handler to use based on intent and action"""
        
        # Chat intents
        if intent in ["chat", "simple", "conversation"]:
            return "chat"
        
        # Simple query intents
        elif intent == "query" and action in ["query", "question", "ask", "simple_question_answering"]:
            return "query"
        
        # Analysis intents
        elif (intent in ["analysis", "summarize", "broad"] or 
              (intent == "specific" and action in ["analyze", "summarize", "extract", "review"]) or
              (intent == "query" and action in ["extract", "analyze", "review"])):
            return "analysis"
        
        # Task intents
        elif (intent in ["task", "structured_task", "plan", "planner"] or
              (intent == "query" and action in ["plan", "planning", "step_by_step", "itinerary"])):
            return "task"
        
        # Default to query for unknown intents
        else:
            return "query"
