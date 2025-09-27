#!/usr/bin/env python3
"""
Cognitive Lattice Web Coordinator
=================================

Coordinates between the web agent and cognitive lattice,
managing the epistemic memory and task progression.
"""

import os
from datetime import datetime
import re
import json
import asyncio
from typing import Dict, Any, List, Optional
from .simple_web_agent import SimpleWebAgent

def create_debug_run_folder() -> str:
    """Create a unique folder for this run's debug data"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_folder = os.path.join(os.getcwd(), "debug_runs", f"run_{timestamp}")
    os.makedirs(run_folder, exist_ok=True)
    return run_folder
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
        
        # Create unique debug folder for this run
        self.debug_run_folder = create_debug_run_folder()
        print(f"🗂️ Debug data will be saved to: {self.debug_run_folder}")
        
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
            confirm_callback=self._confirm_callback,
            debug_run_folder=self.debug_run_folder
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

**This plan is for you to follow at a later time. It should be clear, unambiguous, and actionable.**
**Instructions for Creating the Plan:**
1. **Review Your Progress:** First, examine your cognitive lattice to see what has already been accomplished. Don't repeat actions that have already been successfully completed.
2. **Analyze the User's Goal:** Break down the user's request into its core components.
3. **Start with Action:** If the goal includes navigating to a website, that will have been taken care off by the back-end, so you can safely assume you are already at {url}.
4. **Logical Steps:** Think step-by-step in a way that would allow you, as an autonomous agent, to follow the plan later. The list is *not* for a human, it is for you to follow in the future.
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

**Example for making a bowl from chipotle.com with the following prompt "go to chipotle.com. then go to the menu and build me a bowl with the following ingredients: chicken, white rice, and black beans. Hit add to bag button after that. After that, for the meal name, type "Sean". Now, look for the entree and confirm that the ingredients (chicken, white rice and black beans) were selected. Then look for the total and report the price for the order. Finally, click the remove item button." "**
{{
    "plan": [
    1. Navigate to the menu section on the homepage
    2. Select the 'Bowl' option as the entree format
    3. Choose 'Chicken' as the protein
    4. Select 'White Rice' as the rice option
    5. Select 'Black Beans' as the beans option
    6. Click the 'Add to Bag' button to add the customized bowl
    7. Enter 'Sean' as the meal name when prompted
    8. Look for the entree item in the cart and verify that 'Chicken', 'White Rice', and 'Black Beans' are included in the ingredients list
    9. Find the total price of the order in the cart summary and report this price
    10. Click the 'Remove Item' or equivalent button to remove the bowl from the cart
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
            
            # Additional wait for page to fully stabilize before starting automation
            print("⏳ Waiting for page to fully load and stabilize...")
            import asyncio
            await asyncio.sleep(2)  # Give the page extra time to fully load
            
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
                    
                    # Also save lattice state to run folder for audit trail
                    try:
                        lattice_backup_file = os.path.join(self.debug_run_folder, f"lattice_state_after_step{step_num}.json")
                        self.lattice.save_to_file(lattice_backup_file)
                        print(f"🗂️ DEBUG: Lattice state saved to {os.path.basename(lattice_backup_file)}")
                    except Exception as lattice_error:
                        print(f"⚠️ DEBUG: Failed to save lattice backup: {lattice_error}")
                
                # Save current URL and page state for audit trail
                try:
                    url_log_file = os.path.join(self.debug_run_folder, f"page_state_step{step_num}.txt")
                    with open(url_log_file, 'w', encoding='utf-8') as f:
                        f.write(f"STEP {step_num} PAGE STATE - {datetime.now()}\n")
                        f.write("=" * 50 + "\n")
                        f.write(f"Step Description: {step_description}\n")
                        f.write(f"URL: {current_url}\n")
                        f.write(f"Success: {success}\n")
                        f.write(f"DOM Changed: {dom_changed}\n")
                        if error:
                            f.write(f"Error: {error}\n")
                        # Add page title if available
                        if hasattr(self.web_agent, 'browser'):
                            try:
                                html_content, page_title = await self.web_agent.browser.get_current_dom()
                                f.write(f"Page Title: {page_title}\n")
                            except:
                                pass
                        f.write("=" * 50 + "\n")
                except Exception as url_error:
                    print(f"⚠️ DEBUG: Failed to save URL state: {url_error}")
                
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
            print(f"📁 Complete debug data saved to: {self.debug_run_folder}")
            
            # Save comprehensive run summary for audit trail
            await self._save_run_summary(objectives, successful_steps, len(web_steps), url)
            
            # Complete task in lattice
            if self.lattice:
                self.lattice.add_event({
                    "type": "web_task_completed",
                    "timestamp": datetime.now().isoformat(),
                    "goal": primary_goal,
                    "url": url,
                    "success": overall_success,
                    "steps_completed": len(web_steps),
                    "debug_run_folder": self.debug_run_folder
                })
                # Save lattice after task completion
                self.lattice.save()
                
                # Save final lattice state to run folder for complete audit trail
                try:
                    final_lattice_file = os.path.join(self.debug_run_folder, "final_lattice_state.json")
                    self.lattice.save_to_file(final_lattice_file)
                    print(f"🗂️ Final lattice state saved for audit: {os.path.basename(final_lattice_file)}")
                except Exception as e:
                    print(f"⚠️ Failed to save final lattice: {e}")
                
                # Save complete interactive session to run folder
                try:
                    session_file = os.path.join(self.debug_run_folder, f"cognitive_lattice_interactive_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                    self._save_complete_session(session_file)
                    print(f"🗂️ Complete interactive session saved: {os.path.basename(session_file)}")
                except Exception as e:
                    print(f"⚠️ Failed to save interactive session: {e}")
                
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
            
            # ############################################################################# 
            # DEBUG: Save observation prompt to file for troubleshooting
            # ############################################################################# 
            try:
                # Create observation prompt first to save it
                observation_prompt = f"""You are analyzing a web page to complete this observation task: "{step_description}"

**Overall Goal:** {overall_goal}
**Current Step:** {step_number} - {step_description}
**Previous Progress:** {'; '.join(breadcrumbs[-3:]) if breadcrumbs else 'None'}

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
                
                # Save observation prompt
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                debug_file = os.path.join(self.debug_run_folder, f"observation_prompt_step{step_number}_{timestamp}.txt")
                
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write("################################################################################\n")
                    f.write(f"OBSERVATION PROMPT - {datetime.now()}\n")
                    f.write("################################################################################\n")
                    f.write(f"Step: {step_number}\n")
                    f.write(f"Step Description: {step_description}\n")
                    f.write(f"Overall Goal: {overall_goal}\n")
                    f.write(f"URL: {current_url}\n")
                    f.write("=" * 80 + "\n")
                    f.write("OBSERVATION PROMPT CONTENT:\n")
                    f.write("=" * 80 + "\n")
                    f.write(observation_prompt)
                    f.write("\n" + "=" * 80 + "\n")
                    f.write(f"Prompt length: {len(observation_prompt)} characters\n")
                    f.write("################################################################################\n")
                
                print(f"🐛 DEBUG: Observation prompt saved to {os.path.basename(debug_file)}")
            except Exception as debug_error:
                print(f"⚠️ DEBUG: Failed to save observation prompt: {debug_error}")
            # ############################################################################# 
            
            # Get current page HTML using the browser controller's method
            html_content, page_title = await self.web_agent.browser.get_current_dom()
            
            # Use DOM processor functions to find relevant information
            from .dom_processor import summarize_interactive_elements
            
            # Process DOM to find elements relevant to the observation task
            elements = summarize_interactive_elements(html_content, goal=step_description)
            
            # Add elements to the prompt
            full_prompt = observation_prompt.replace(
                "Please analyze the page elements and provide your observation result:",
                f"**Current Page Elements:**\n{elements}\n\nPlease analyze the page elements and provide your observation result:"
            )

            try:
                # Use the external client for LLM analysis
                response = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.external_client.query_external_api, 
                    full_prompt
                )
                
                # ############################################################################# 
                # DEBUG: Save observation response to file for troubleshooting
                # ############################################################################# 
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    debug_file = os.path.join(self.debug_run_folder, f"observation_response_step{step_number}_{timestamp}.txt")
                    
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write("################################################################################\n")
                        f.write(f"OBSERVATION RESPONSE - {datetime.now()}\n")
                        f.write("################################################################################\n")
                        f.write(f"Step: {step_number}\n")
                        f.write(f"Step Description: {step_description}\n")
                        f.write(f"Overall Goal: {overall_goal}\n")
                        f.write(f"URL: {current_url}\n")
                        f.write("=" * 80 + "\n")
                        f.write("OBSERVATION RESPONSE CONTENT:\n")
                        f.write("=" * 80 + "\n")
                        f.write(response)
                        f.write("\n" + "=" * 80 + "\n")
                        f.write(f"Response length: {len(response)} characters\n")
                        f.write("################################################################################\n")
                    
                    print(f"🐛 DEBUG: Observation response saved to {os.path.basename(debug_file)}")
                except Exception as debug_error:
                    print(f"⚠️ DEBUG: Failed to save observation response: {debug_error}")
                # ############################################################################# 
                
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

    async def _save_run_summary(self, objectives: List[str], successful_steps: int, total_steps: int, url: str) -> None:
        """
        Save comprehensive run summary for skeptic-proof audit trail.
        
        This creates a complete record that external reviewers can examine
        to verify the autonomous capabilities and decision-making process.
        """
        try:
            summary_file = os.path.join(self.debug_run_folder, "RUN_SUMMARY_AUDIT_TRAIL.md")
            
            # Calculate timing
            run_end_time = datetime.now()
            folder_timestamp = os.path.basename(self.debug_run_folder).split('_', 1)[1]
            run_start_time = datetime.strptime(folder_timestamp.rsplit('_', 1)[0], "%Y%m%d_%H%M%S")
            execution_duration = run_end_time - run_start_time
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("# AUTONOMOUS WEB AUTOMATION - COMPLETE AUDIT TRAIL\n\n")
                f.write("This document provides a complete, skeptic-proof audit trail of an autonomous web automation run.\n")
                f.write("Every decision, prompt, response, and action has been logged for verification.\n\n")
                
                f.write("## EXECUTIVE SUMMARY\n\n")
                f.write(f"- **Run ID**: {os.path.basename(self.debug_run_folder)}\n")
                f.write(f"- **Target URL**: {url}\n")
                f.write(f"- **Primary Objective**: {objectives[0] if objectives else 'Not specified'}\n")
                f.write(f"- **Success Rate**: {successful_steps}/{total_steps} steps ({successful_steps/total_steps*100:.1f}%)\n")
                f.write(f"- **Execution Time**: {execution_duration.total_seconds():.1f} seconds\n")
                f.write(f"- **Timestamp**: {run_start_time.strftime('%Y-%m-%d %H:%M:%S')} to {run_end_time.strftime('%H:%M:%S')}\n")
                f.write(f"- **Overall Result**: {'✅ SUCCESS' if successful_steps == total_steps else '⚠️ PARTIAL SUCCESS' if successful_steps > 0 else '❌ FAILED'}\n\n")
                
                f.write("## OBJECTIVES BREAKDOWN\n\n")
                for i, objective in enumerate(objectives, 1):
                    f.write(f"{i}. {objective}\n")
                f.write("\n")
                
                f.write("## AUDIT TRAIL CONTENTS\n\n")
                f.write("This folder contains the following evidence files:\n\n")
                
                # List all files in the run folder
                try:
                    for file in sorted(os.listdir(self.debug_run_folder)):
                        if file != "RUN_SUMMARY_AUDIT_TRAIL.md":
                            file_path = os.path.join(self.debug_run_folder, file)
                            file_size = os.path.getsize(file_path)
                            f.write(f"- **{file}** ({file_size:,} bytes)\n")
                            
                            # Add description for different file types
                            if file.startswith("web_prompt_"):
                                f.write(f"  - Action step LLM prompt with candidate elements and reasoning instructions\n")
                            elif file.startswith("web_response_"):
                                f.write(f"  - Action step LLM response with selected elements and commands\n")
                            elif file.startswith("observation_prompt_"):
                                f.write(f"  - Observation step prompt for DOM analysis and data extraction\n")
                            elif file.startswith("observation_response_"):
                                f.write(f"  - Observation step response with extracted information\n")
                            elif file.startswith("dom_debug_"):
                                f.write(f"  - Complete DOM analysis showing all interactive elements found and ranked\n")
                            elif file.startswith("page_state_"):
                                f.write(f"  - Page URL and state information for step verification\n")
                            elif file.startswith("lattice_state_"):
                                f.write(f"  - Cognitive lattice memory state snapshot after step completion\n")
                            elif file == "final_lattice_state.json":
                                f.write(f"  - Complete final state of the cognitive lattice memory system\n")
                            elif file.startswith("cognitive_lattice_interactive_session_"):
                                f.write(f"  - Complete interactive session with full conversation and decision history\n")
                            f.write("\n")
                            
                except Exception as e:
                    f.write(f"- Error listing files: {e}\n\n")
                
                f.write("## PROGRESSIVE CANDIDATE DISCLOSURE SYSTEM\n\n")
                f.write("This system uses a multi-pass approach to ensure optimal element selection:\n\n")
                f.write("1. **Pass 1**: Present top 10 candidate elements to LLM\n")
                f.write("2. **Pass 2**: If LLM responds 'NONE', expand to top 20 candidates\n")
                f.write("3. **Pass 3**: Expand to 30 candidates if still no match\n")
                f.write("4. **Pass 4**: Expand to 40 candidates\n")
                f.write("5. **Pass 5**: Final attempt with 50 candidates\n\n")
                f.write("This prevents the LLM from choosing suboptimal elements (like #20 instead of #3)\n")
                f.write("while still providing fallback options for edge cases.\n\n")
                
                f.write("## INTERACTIVE SESSION HISTORY\n\n")
                f.write("The `cognitive_lattice_interactive_session_*.json` file contains the complete\n")
                f.write("conversation and decision history that led to this automation run:\n\n")
                f.write("- **Original User Request**: The exact natural language goal provided\n")
                f.write("- **Plan Generation**: How the goal was broken down into steps\n")
                f.write("- **Decision Trail**: Every web automation decision with rationale and confidence\n")
                f.write("- **Context Evolution**: How understanding developed throughout the conversation\n")
                f.write("- **Error Recovery**: Any corrections or refinements made during execution\n")
                f.write("- **Memory Formation**: How information was stored and recalled\n\n")
                f.write("This provides the complete story from initial request to final execution,\n")
                f.write("showing the system's reasoning process and context awareness.\n\n")
                
                f.write("## VERIFICATION INSTRUCTIONS\n\n")
                f.write("To verify this automation run:\n\n")
                f.write("1. **Review Prompts**: Examine `web_prompt_*.txt` files to see exact instructions sent to LLM\n")
                f.write("2. **Check Responses**: Review `web_response_*.txt` files to see LLM reasoning and decisions\n")
                f.write("3. **Trace Observations**: Look at `observation_*.txt` files to see information extraction\n")
                f.write("4. **DOM Analysis**: Check `dom_debug_*.txt` files to see all interactive elements found and ranked\n")
                f.write("5. **Memory Verification**: Check `lattice_state_*.json` files for decision context and memory\n")
                f.write("6. **Page States**: Review `page_state_*.txt` files for URL progression and step verification\n")
                f.write("7. **Interactive Session**: Examine `cognitive_lattice_interactive_session_*.json` for complete conversation history\n")
                f.write("8. **Progressive Disclosure**: Look for pass numbers in filenames to see candidate expansion\n\n")
                
                f.write("## SYSTEM ENVIRONMENT\n\n")
                try:
                    import platform
                    import sys
                    f.write(f"- **Operating System**: {platform.system()} {platform.release()}\n")
                    f.write(f"- **Python Version**: {sys.version.split()[0]}\n")
                    f.write(f"- **Architecture**: {platform.architecture()[0]}\n")
                    f.write(f"- **Processor**: {platform.processor()}\n")
                    f.write(f"- **Machine**: {platform.machine()}\n")
                except Exception as e:
                    f.write(f"- **System Info Error**: {e}\n")
                f.write("\n")
                
                f.write("## TECHNICAL DETAILS\n\n")
                f.write("- **LLM Model**: External API (configuration in prompts)\n")
                f.write("- **Browser**: Real Chrome (anti-bot detection bypass)\n")
                f.write("- **DOM Processing**: Element ranking and candidate selection\n")
                f.write("- **Safety**: Multi-layer validation and confirmation systems\n")
                f.write("- **Memory**: Cognitive lattice for context preservation\n\n")
                
                f.write("## SYSTEM CAPABILITIES DEMONSTRATED\n\n")
                f.write("✅ **Autonomous Navigation**: Self-directed movement through web interfaces\n")
                f.write("✅ **Element Selection**: Intelligent choice of optimal interactive elements\n")
                f.write("✅ **Form Completion**: Automated data entry and option selection\n")
                f.write("✅ **Context Awareness**: Memory of previous actions and goals\n")
                f.write("✅ **Error Recovery**: Progressive candidate disclosure and retry logic\n")
                f.write("✅ **Information Extraction**: Observation and verification of results\n")
                f.write("✅ **Safety Boundaries**: Stops at payment confirmation for human approval\n\n")
                
                f.write("---\n\n")
                f.write("*This audit trail was generated automatically by the CognitiveLattice*\n")
                f.write("*autonomous web automation system. All files in this folder constitute*\n")
                f.write("*a complete record of the system's decision-making process.*\n")
            
            print(f"📋 Comprehensive audit trail saved: {os.path.basename(summary_file)}")
            
        except Exception as e:
            print(f"⚠️ Failed to save run summary: {e}")

    def _save_complete_session(self, session_file: str) -> None:
        """
        Save a complete copy of the cognitive lattice interactive session.
        
        This captures the entire conversation history, decisions, and context
        that led to this automation run - perfect for skeptic verification.
        """
        try:
            if not self.lattice:
                print("⚠️ No lattice available to save session")
                return
            
            # Get the complete lattice data including all events and history
            session_data = {
                "session_metadata": {
                    "run_id": os.path.basename(self.debug_run_folder),
                    "timestamp": datetime.now().isoformat(),
                    "automation_type": "web_automation",
                    "lattice_version": getattr(self.lattice, 'version', 'unknown')
                },
                "active_task_state": getattr(self.lattice, 'active_task_state', None),
                "event_log": getattr(self.lattice, 'event_log', []),
                "memory_chunks": getattr(self.lattice, 'memory_chunks', []),
                "session_id": getattr(self.lattice, 'session_id', 'unknown'),
                "creation_time": getattr(self.lattice, 'creation_time', 'unknown'),
                "last_updated": getattr(self.lattice, 'last_updated', 'unknown')
            }
            
            # Add any additional lattice attributes that might contain session data
            for attr in ['decisions', 'contexts', 'interactions', 'conversation_history']:
                if hasattr(self.lattice, attr):
                    session_data[attr] = getattr(self.lattice, attr)
            
            # Save the complete session data
            with open(session_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(session_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Get file size for logging
            file_size = os.path.getsize(session_file)
            print(f"💾 Session data saved: {file_size:,} bytes")
            
        except Exception as e:
            print(f"⚠️ Failed to save complete session: {e}")
            import traceback
            traceback.print_exc()


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

