#!/usr/bin/env python3
"""
Cognitive Lattice Web Coordinator
=================================

Coordinates between the web agent and cognitive lattice,
managing the epistemic memory and task progression.
"""

from datetime import datetime
import re
import json
import asyncio
from typing import Dict, Any, List, Optional
from .simple_web_agent import SimpleWebAgent
from .browser_controller import BrowserController
from .safety import SafetyManager


class CognitiveLatticeWebCoordinator:
    """
    Coordinates web automation with cognitive lattice integration.
    Manages task creation, progress tracking, and epistemic memory.
    """
    
    def __init__(self, external_client=None, cognitive_lattice=None, enable_stealth=True, use_real_chrome=True):
        self.external_client = external_client
        self.lattice = cognitive_lattice
        
        # Create browser controller with stealth settings and real Chrome
        self.browser = BrowserController(
            profile_name="default",
            headless=not enable_stealth,  # headless opposite of stealth for now
            browser_type="chromium",
            use_real_chrome=use_real_chrome,  # Use real Chrome for bot detection bypass
            chrome_debug_port=9222
        )
        
        # Create safety manager with default policies
        self.safety = SafetyManager()
        
        # Create web agent with all components
        self.web_agent = SimpleWebAgent(
            browser=self.browser,
            lattice=cognitive_lattice,
            llm_client=external_client,
            policy=None,  # Use default safety policies
            status_callback=self._status_callback,
            confirm_callback=self._confirm_callback
        )
    
    async def create_web_automation_plan(self, goal: str, url: str) -> List[str]:
        """
        Create a step-by-step plan for web automation tasks.
        Uses the proven planning approach from the original system.
        """
        print(f"📋 Creating web automation plan for: '{goal}'")
        
        if not self.external_client:
            # Fallback to simple plan if no external client
            return [
                f"Navigate to {url} and dismiss any initial pop-ups",
                f"Complete the task: {goal}"
            ]
        
        # Build cognitive lattice context to avoid redundant steps
        lattice_context = "No previous progress recorded."
        if self.lattice:
            try:
                active_task = self.lattice.get_active_task()
                if active_task:
                    completed_steps = active_task.get("completed_steps", [])
                    task_plan = active_task.get("task_plan", [])
                    lattice_context = f"""
Active Task: {active_task.get('task_title', 'Web Automation')}
Progress: {len(completed_steps)}/{len(task_plan)} steps completed
Completed Steps:
{chr(10).join([f"- {step.get('description', 'Unknown')}" for step in completed_steps]) if completed_steps else "None"}
"""
            except Exception as e:
                lattice_context = f"Error reading lattice: {e}"
        
        # Use the enhanced planning prompt that handles both action and observation steps
        plan_prompt = f"""You are an expert autonomous web agent. Your task is to create a concise, step-by-step plan to achieve the user's high-level goal.

**User's Goal:** "{goal}"
**Target Website:** "{url}"

**Your Current Progress (Cognitive Lattice):**
{lattice_context}

**Instructions for Creating the Plan:**
1. **Review Your Progress:** First, examine your cognitive lattice to see what has already been accomplished. Don't repeat actions that have already been successfully completed.
2. **Analyze the User's Goal:** Break down the user's request into its core components.
3. **Start with Action:** Assume the browser is already on the target website. Focus on actionable steps, not navigation setup.
4. **Logical Steps:** Think step-by-step. What is the most logical sequence of actions a human would take?
5. **Include Both Action and Observation Steps:** Your plan should include:
   - **Action Steps:** Navigate, click, type, select (e.g., "Click the product option", "Enter name as 'John'")
   - **Observation Steps:** Look for elements, verify content, extract information, report findings (e.g., "Look for the item listing and verify details", "Find the total price and report it")
6. **Avoid Redundancy:** Each step should be distinctly different. Don't create steps that would repeat the same action or accomplish something already shown as completed in your lattice.
7. **Describe Goals, Not Technical Details:** Phrase each step as a high-level goal (e.g., "Find the search bar and enter the location") rather than a specific command (e.g., "Click the div with id='search'").
8. **Be Specific:** If the user mentions specific data (like ZIP codes, items, names), include them in the plan steps.
9. **End with Verification:** If the user asks to verify or report something, include that as the final step(s).

**Step Types You Can Use:**
- **Navigation:** "Go to the product section", "Navigate to checkout"
- **Selection:** "Select the desired option", "Choose the preferred item"
- **Input:** "Enter the customer name", "Type the location code"
- **Interaction:** "Click the add to cart button", "Press enter to save"
- **Observation:** "Look for the item listing in the cart", "Find the details list"
- **Verification:** "Confirm that the selected items are listed", "Verify the order was placed correctly"
- **Reporting:** "Report the total price", "Extract and display the subtotal"

**Output Format:**
Return a JSON object with a single key "plan" containing a list of simple, actionable goal strings.

**Example for a location search goal:**
{{
    "plan": [
        "Click on the 'Find Locations' or 'Store Locator' button to access the location search.",
        "Enter the specified location code to search for nearby locations.",
        "Submit the search by pressing Enter or clicking search button.",
        "Select the first available location from the search results."
    ]
}}

**Important: Use your cognitive lattice to avoid creating redundant steps. If your lattice shows you've already entered a ZIP code successfully, don't create another step to enter it again. Let the complexity of the goal and what remains to be accomplished determine the number of steps needed.**
"""

        try:
            print(f"🧠 Creating web automation plan using proven planning prompt...")
            response = self.external_client.query_external_api(plan_prompt)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                plan_json = json.loads(json_match.group(0))
                plan_steps = plan_json.get('plan', [])
                
                if plan_steps:
                    print(f"📋 Created {len(plan_steps)} step plan:")
                    for i, step in enumerate(plan_steps, 1):
                        print(f"   {i}. {step}")
                    return plan_steps
            
            # Fallback to text parsing if JSON fails
            print("⚠️ JSON parsing failed, trying text parsing...")
            lines = response.split('\n')
            steps = []
            for line in lines:
                line = line.strip()
                # Look for numbered steps
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    # Clean up the step text
                    clean_step = re.sub(r'^\d+\.\s*', '', line)  # Remove "1. "
                    clean_step = re.sub(r'^[-•]\s*', '', clean_step)  # Remove "- " or "• "
                    if clean_step:
                        steps.append(clean_step)
            
            if steps:
                print(f"📋 Created {len(steps)} web automation steps (from text parsing):")
                for i, step in enumerate(steps, 1):
                    print(f"   {i}. {step}")
                return steps
                
        except Exception as e:
            print(f"❌ Web automation planning failed: {e}")
        
        # Final fallback plan
        print("⚠️ Using fallback plan")
        return [
            f"Navigate to {url} and dismiss any initial pop-ups",
            f"Complete the task: {goal}"
        ]

    async def execute_web_task(self, url: str, objectives: List[str], max_iterations: int = 10) -> bool:
        """
        Execute a complete web automation task with lattice integration.
        
        Args:
            url: Target URL to navigate to
            objectives: List of objectives to accomplish 
            max_iterations: Maximum number of iterations to attempt
            
        Returns:
            bool: True if task completed successfully, False otherwise
        """
        try:
            # Primary goal is the first objective
            primary_goal = objectives[0] if objectives else "Navigate to website"
            
            # STEP 1: Create detailed web automation plan
            print(f"🚀 Step 1: Creating web automation plan...")
            web_steps = await self.create_web_automation_plan(primary_goal, url)
            
            # STEP 2: Create task in lattice with proper plan
            if self.lattice:
                task_data = self.lattice.create_new_task(
                    query=primary_goal,
                    task_plan=web_steps  # Use the detailed plan instead of generic steps
                )
                # Save lattice after creating new task
                self.lattice.save()
                print(f"[LATTICE] Created web task with {len(web_steps)} steps: {primary_goal}")
            
            # STEP 3: Execute each step of the plan autonomously
            print(f"🚀 Step 2: Executing {len(web_steps)} planned steps...")
            current_url = url
            successful_steps = 0
            breadcrumbs = []  # Track plain English progress across steps
            
            # Initialize browser once for all steps
            await self.web_agent.browser.initialize()
            await self.web_agent.browser.navigate(url)
            
            for step_num, step_description in enumerate(web_steps, 1):
                print(f"\n🎯 Executing Step {step_num}/{len(web_steps)}: {step_description}")
                
                # Gather enhanced context for this step
                recent_events = []
                previous_signature = None
                lattice_state = {}
                
                if self.lattice:
                    # Get recent events from lattice event log (last 5)
                    if hasattr(self.lattice, 'event_log') and self.lattice.event_log:
                        recent_events = self.lattice.event_log[-5:]
                    
                    # Get active task for context
                    active_task = self.lattice.get_active_task()
                    
                    # Build lattice state with planning context
                    lattice_state = {
                        'planned_steps': web_steps,
                        'current_step_index': step_num - 1,
                        'successful_patterns': [],  # Could be populated from previous sessions
                        'session_id': self.lattice.session_id,
                        'active_task': active_task
                    }
                    
                    # Get previous DOM signature for delta detection
                    if recent_events:
                        for event in reversed(recent_events):
                            if isinstance(event, dict) and 'result' in event:
                                result = event['result']
                                if isinstance(result, dict) and 'page_signature' in result:
                                    previous_signature = result['page_signature']
                                    break
                
                # Execute this specific step using enhanced context
                # Check if this is an observation/reporting step
                observation_keywords = ['look for', 'find and report', 'extract', 'verify', 'confirm', 'check', 'report', 'display', 'show', 'observe']
                is_observation_step = any(keyword in step_description.lower() for keyword in observation_keywords)
                
                if is_observation_step:
                    print(f"📊 Detected observation step - using DOM analysis approach")
                    step_result = await self._execute_observation_step(
                        step_description=step_description,
                        current_url=current_url,
                        step_number=step_num,
                        overall_goal=primary_goal,
                        breadcrumbs=breadcrumbs
                    )
                else:
                    print(f"🎯 Detected action step - using web agent approach")
                    step_result = await self.web_agent.execute_single_step(
                        step_goal=step_description, 
                        current_url=current_url,
                        step_number=step_num,
                        total_steps=len(web_steps),
                        overall_goal=primary_goal,
                        recent_events=recent_events,
                        previous_signature=previous_signature,
                        lattice_state=lattice_state,
                        breadcrumbs=breadcrumbs
                    )
                
                # Check step success with enhanced logic
                technical_success = step_result.get("success", False)
                dom_changed = step_result.get("dom_changed", False)
                error = step_result.get("error")
                
                # Check if goal was logically achieved despite technical issues
                logical_success = self._check_logical_success(step_result, step_description)
                
                # Use logical success if available, fall back to technical success
                success = logical_success if logical_success is not None else technical_success
                
                print(f"[WEB AGENT] Step {step_num}: {'✓' if success else '✗'} "
                      f"DOM Changed: {dom_changed} "
                      f"(Technical: {'✓' if technical_success else '✗'}, Logical: {'✓' if logical_success else '?' if logical_success is None else '✗'})"
                      f"{f'Error: {error}' if error else ''}")
                
                # Log step completion to lattice
                if self.lattice:
                    self.lattice.add_event({
                        "type": "web_step_completed",
                        "timestamp": datetime.now().isoformat(),
                        "step_number": step_num,
                        "step_description": step_description,
                        "success": success,
                        "dom_changed": dom_changed,
                        "result": step_result
                    })
                    # Save lattice after each step
                    self.lattice.save()
                
                # Collect breadcrumb from step result
                if step_result and 'breadcrumb' in step_result and step_result['breadcrumb']:
                    breadcrumbs.append(f"Step {step_num}: {step_result['breadcrumb']}")
                    # Keep only last 5 breadcrumbs to avoid prompt bloat
                    breadcrumbs = breadcrumbs[-5:]
                
                # Track successful steps
                if success:
                    successful_steps += 1
                    print(f"   ✅ Step {step_num} completed successfully")
                    
                    # Update current URL for next step
                    current_url = step_result.get("final_url", current_url)
                else:
                    print(f"   ❌ Step {step_num} failed: {error or 'Unknown error'}")
                    
                    # For critical early steps, consider stopping
                    if step_num <= 2 and not dom_changed:
                        print(f"   ⚠️ Early step failed with no DOM changes - this may indicate a critical issue")
                        # Don't break, but be aware this might not work
                
                # Small delay between steps to let page settle
                await asyncio.sleep(1)
            
            # Close browser after all steps
            await self.web_agent.browser.close(save_state=True)
            
            # STEP 4: Determine overall success
            success_rate = successful_steps / len(web_steps) if web_steps else 0
            overall_success = success_rate >= 0.5  # At least 50% of steps successful
            
            print(f"\n🏁 Web automation completed! {successful_steps}/{len(web_steps)} steps successful ({success_rate:.1%})")
            
            # Complete task in lattice
            if self.lattice:
                self.lattice.add_event({
                    "type": "web_task_completed",
                    "timestamp": datetime.now().isoformat(),
                    "goal": primary_goal,
                    "url": url,
                    "success": overall_success,
                    "steps_completed": len(web_steps)
                })
                # Save lattice after task completion
                self.lattice.save()
                
                # Mark task as completed if it was successful
                if overall_success and hasattr(self.lattice, 'complete_current_task'):
                    self.lattice.complete_current_task()
            
            return overall_success
            
        except Exception as e:
            if self.lattice:
                # Add error event instead of calling non-existent complete_task
                self.lattice.add_event({
                    "type": "web_task_error",
                    "timestamp": datetime.now().isoformat(),
                    "goal": primary_goal if 'primary_goal' in locals() else "Unknown",
                    "url": url,
                    "error": str(e),
                    "success": False
                })
                # Save lattice after error
                self.lattice.save()
            
            print(f"❌ Web task execution failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _status_callback(self, message: str) -> None:
        """Handle status updates from the web agent."""
        print(f"[WEB AGENT] {message}")
        if self.lattice:
            event = {
                "type": "web_progress",
                "data": {"message": message},
                "source": "web_automation",
                "timestamp": datetime.now().isoformat()
            }
            self.lattice.add_event(event)
            # Save lattice after status updates (but less frequently)
            # Only save on important status messages to avoid too many writes
            if any(keyword in message.lower() for keyword in ["completed", "failed", "error", "success"]):
                self.lattice.save()
    
    def _confirm_callback(self, reasons: List[str], summary: Dict[str, Any]) -> bool:
        """Handle confirmation requests from safety manager."""
        print(f"[SAFETY] Confirmation required: {reasons}")
        print(f"[SAFETY] Summary: {summary}")
        
        # For now, auto-approve safe actions (can be enhanced for interactive mode)
        # In production, this could prompt the user or apply more sophisticated rules
        risk_level = len(reasons)
        if risk_level <= 2:  # Low risk - auto approve
            print("[SAFETY] Auto-approved (low risk)")
            return True
        else:  # High risk - for now auto-decline, could prompt user
            print("[SAFETY] Auto-declined (high risk)")
            return False
    
    def get_lattice_summary(self) -> Dict[str, Any]:
        """Get summary of lattice state"""
        if not self.lattice:
            return {"status": "No lattice available"}
        
        return self.lattice.get_lattice_summary()
    
    def _check_logical_success(self, step_result: Dict[str, Any], step_description: str) -> Optional[bool]:
        """
        Check if step achieved its logical goal despite technical execution issues.
        Returns: True (logical success), False (logical failure), None (unclear)
        """
        try:
            # Check for explicit verification result first
            verification = step_result.get("verification", {})
            if isinstance(verification, dict):
                if verification.get("complete") is True:
                    print(f"🎯 LOGICAL SUCCESS: Explicit verification passed")
                    return True
                elif verification.get("complete") is False:
                    print(f"🚫 LOGICAL FAILURE: Explicit verification failed")
                    return False
            
            # Check for completion analysis from enhanced verification
            completion_analysis = step_result.get("completion_analysis", {})
            if isinstance(completion_analysis, dict):
                # Look for verification signals
                signals = completion_analysis.get("signals", {})
                if isinstance(signals, dict):
                    has_affordance = signals.get("has_affordance", False)
                    has_details = signals.get("has_details", False)
                    
                    # If we have both affordance and details, it's a logical success
                    if has_affordance and has_details:
                        print(f"🎯 LOGICAL SUCCESS: Found affordance + details signals")
                        return True
            
            # Check evidence findings for location verification
            evidence = step_result.get("evidence", {})
            if isinstance(evidence, dict):
                findings = evidence.get("findings", {})
                if isinstance(findings, dict) and findings.get("location_verified") is True:
                    print(f"🎯 LOGICAL SUCCESS: Location verified flag set")
                    return True
            
            # Check for DOM changes + specific goal patterns
            dom_changed = step_result.get("dom_changed", False)
            if dom_changed:
                # For location selection goals
                if any(keyword in step_description.lower() for keyword in ["select", "location", "restaurant", "store"]):
                    # If DOM changed and it's a selection step, likely succeeded
                    final_url = step_result.get("final_url", "")
                    if any(pattern in final_url.lower() for pattern in ["/location/", "/store/", "/restaurants/"]):
                        print(f"🎯 LOGICAL SUCCESS: Location URL pattern + DOM change")
                        return True
                
                # For search/navigation goals  
                if any(keyword in step_description.lower() for keyword in ["search", "find", "navigate", "go to"]):
                    # If DOM changed on search/nav, likely succeeded
                    print(f"🎯 LOGICAL SUCCESS: Search/nav goal + DOM change")
                    return True
            
            # Check error patterns that might be false negatives
            error = step_result.get("error", "")
            if error and isinstance(error, str):
                # Playwright viewport/timeout issues don't necessarily mean logical failure
                false_negative_patterns = [
                    "element is outside of the viewport",
                    "waiting for element to be visible",
                    "retrying click action",
                    "timeout",
                    "element not stable"
                ]
                if any(pattern in error.lower() for pattern in false_negative_patterns):
                    # If DOM changed despite viewport issues, likely succeeded
                    if dom_changed:
                        print(f"🎯 LOGICAL SUCCESS: DOM changed despite viewport error")
                        return True
            
            return None  # Unable to determine logical success
            
        except Exception as e:
            print(f"⚠️ Error checking logical success: {e}")
            return None

    async def _execute_observation_step(self, step_description: str, current_url: str, 
                                       step_number: int, overall_goal: str, breadcrumbs: List[str]) -> Dict[str, Any]:
        """
        Execute an observation/reporting step that requires DOM analysis rather than clicking.
        
        Args:
            step_description: Natural language description of the observation task
            current_url: Current page URL
            step_number: Current step number
            overall_goal: The high-level goal for context
            breadcrumbs: History of completed steps
            
        Returns:
            Dict with step execution results
        """
        try:
            print(f"📊 Executing observation step: {step_description}")
            
            # Get current page HTML using the browser controller's method
            html_content, page_title = await self.web_agent.browser.get_current_dom()
            
            # Use DOM processor functions to find relevant information
            from .dom_processor import summarize_interactive_elements
            
            # Process DOM to find elements relevant to the observation task
            elements = summarize_interactive_elements(html_content, goal=step_description)
            
            # Create observation prompt for LLM analysis
            observation_prompt = f"""You are analyzing a web page to complete this observation task: "{step_description}"

**Overall Goal:** {overall_goal}
**Current Step:** {step_number} - {step_description}
**Previous Progress:** {'; '.join(breadcrumbs[-3:]) if breadcrumbs else 'None'}

**Current Page Elements:**
{elements}

**Your Task:**
1. Look through the provided page elements to find information relevant to: "{step_description}"
2. Extract the specific information requested
3. Report your findings in a clear, concise format
4. Focus on actionable information that helps complete the overall goal
5. If you cannot find the requested information, explain what you searched for and what you found instead

**Response Format:**
- Start with "OBSERVATION RESULT:" 
- Provide the specific information found (prices, ingredients, availability, etc.)
- If reporting prices, quantities, or other data, format it clearly
- If verifying or confirming something, state clearly whether it was found/confirmed or not
- Include any relevant details that would help with the overall goal: "{overall_goal}"

**Example Good Responses:**
- "OBSERVATION RESULT: Found selected product in cart with specified options and customizations. Total price is $12.99."
- "OBSERVATION RESULT: Confirmed the following items are listed: main product, selected options, chosen add-ons. No additional items found."
- "OBSERVATION RESULT: Unable to find a clear price display. Found 'Add to Cart' button but no visible pricing information on current page."

Please analyze the page elements and provide your observation result:"""

            try:
                # Use the external client for LLM analysis
                response = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.external_client.query_external_api, 
                    observation_prompt
                )
                
                print(f"✅ Observation completed: {response}")
                
                # Create breadcrumb for this observation
                breadcrumb = f"Observed: {response[:100]}..." if len(response) > 100 else f"Observed: {response}"
                
                # Return success result in same format as web agent
                return {
                    "success": True,
                    "dom_changed": False,  # Observation doesn't change DOM
                    "final_url": current_url,
                    "breadcrumb": breadcrumb,
                    "observation_result": response,
                    "verification": {"complete": True},
                    "step_type": "observation"
                }
                
            except Exception as e:
                print(f"❌ Observation LLM analysis failed: {str(e)}")
                return {
                    "success": False,
                    "dom_changed": False,
                    "final_url": current_url,
                    "error": f"Observation analysis error: {str(e)}",
                    "step_type": "observation"
                }
                
        except Exception as e:
            print(f"❌ Observation step failed: {str(e)}")
            return {
                "success": False,
                "dom_changed": False,
                "final_url": current_url,
                "error": f"Observation error: {str(e)}",
                "step_type": "observation"
            }


# Backward-compatible function that maintains existing API
async def execute_cognitive_web_task(goal: str, url: str, external_client=None, cognitive_lattice=None, 
                                    use_real_chrome: bool = True) -> Dict[str, Any]:
    """
    Backward-compatible function for executing cognitive web tasks.
    
    Args:
        goal: The primary objective to accomplish
        url: Target URL to navigate to
        external_client: LLM client for reasoning
        cognitive_lattice: Lattice instance for memory management
        use_real_chrome: Whether to use real Chrome for bot detection bypass (default True)
        
    Returns:
        Dict with status and results
    """
    coordinator = CognitiveLatticeWebCoordinator(
        external_client=external_client,
        cognitive_lattice=cognitive_lattice,
        use_real_chrome=use_real_chrome
    )
    
    # Convert single goal to objectives list for internal API
    success = await coordinator.execute_web_task(url, [goal])
    
    # Return in expected format
    return {
        "success": success,
        "goal": goal,
        "url": url,
        "timestamp": datetime.now().isoformat()
    }

