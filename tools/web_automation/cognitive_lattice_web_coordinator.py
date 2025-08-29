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
    
    def __init__(self, external_client=None, cognitive_lattice=None, enable_stealth=True):
        self.external_client = external_client
        self.lattice = cognitive_lattice
        
        # Create browser controller with stealth settings
        self.browser = BrowserController(
            profile_name="default",
            headless=not enable_stealth,  # headless opposite of stealth for now
            browser_type="chromium"
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
        
        # Use the proven planning prompt from the old system
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
5. **Avoid Redundancy:** Each step should be distinctly different. Don't create steps that would repeat the same action or accomplish something already shown as completed in your lattice.
6. **Describe Actions, Not Code:** Phrase each step as a high-level goal (e.g., "Find the search bar and enter the zip code") rather than a specific command (e.g., "Click the div with id='search'").
7. **Be Specific:** If the user mentions specific data (like ZIP codes, items, names), include them in the plan steps.

**Output Format:**
Return a JSON object with a single key "plan" containing a list of simple, actionable goal strings.

**Example for a location search goal:**
{{
    "plan": [
        "Click on the 'Find Locations' or 'Store Locator' button to access the location search.",
        "Enter the zip code {goal.split('45305')[0] + '45305' if '45305' in goal else 'specified location'} to search for nearby locations.",
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
                print(f"[LATTICE] Created web task with {len(web_steps)} steps: {primary_goal}")
            
            # STEP 3: Execute each step of the plan autonomously
            print(f"🚀 Step 2: Executing {len(web_steps)} planned steps...")
            current_url = url
            successful_steps = 0
            
            # Initialize browser once for all steps
            await self.web_agent.browser.initialize()
            await self.web_agent.browser.navigate(url)
            
            for step_num, step_description in enumerate(web_steps, 1):
                print(f"\n🎯 Executing Step {step_num}/{len(web_steps)}: {step_description}")
                
                # Execute this specific step using the new single-step method
                step_result = await self.web_agent.execute_single_step(
                    step_goal=step_description, 
                    current_url=current_url
                )
                
                # Check step success
                success = step_result.get("success", False)
                dom_changed = step_result.get("dom_changed", False)
                error = step_result.get("error")
                
                print(f"[WEB AGENT] Step {step_num}: {'✓' if success else '✗'} "
                      f"DOM Changed: {dom_changed} "
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


# Backward-compatible function that maintains existing API
async def execute_cognitive_web_task(goal: str, url: str, external_client=None, cognitive_lattice=None) -> Dict[str, Any]:
    """
    Backward-compatible function for executing cognitive web tasks.
    
    Args:
        goal: The primary objective to accomplish
        url: Target URL to navigate to
        external_client: LLM client for reasoning
        cognitive_lattice: Lattice instance for memory management
        
    Returns:
        Dict with status and results
    """
    coordinator = CognitiveLatticeWebCoordinator(
        external_client=external_client,
        cognitive_lattice=cognitive_lattice
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

