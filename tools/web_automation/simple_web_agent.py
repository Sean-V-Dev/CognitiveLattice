# =========================
# tools/web_automation/simple_web_agent.py  (orchestrator excerpt)
# =========================
import time
from typing import Optional, Tuple, Dict, Any
from .models import ContextPacket, CommandBatch, PageContext
from .lattice_logger import LatticeLogger
#from .planner import Planner  # Future: recipe-based planning
#from .recipe_cache import RecipeCache  # Future: DOM key caching
from .step_executor import StepExecutor
from .safety import SafetyManager
from .dom_processor import create_page_context, page_signature  # DOM processing functions
from .prompt_builder import build_reasoning_prompt

class SimpleWebAgent:
    def __init__(self, browser, lattice, llm_client, policy=None, status_callback=None, confirm_callback=None):
        self.browser = browser
        self.llm_client = llm_client
        self.logger = LatticeLogger(lattice)
       #self.recipes = RecipeCache()  # Future: recipe-based caching
        #self.planner = Planner(self.recipes)  # Future: intelligent planning
        self.executor = StepExecutor(browser, llm_client, logger=self.logger)
        self.safety = SafetyManager(policy)
        self.status_callback = status_callback or (lambda msg: None)   # heartbeat
        self.confirm_callback = confirm_callback or (lambda reasons, summary: True)

        self._last_heartbeat = 0.0
        self._cumulative_risk = 0

    async def execute_task(self, goal: str, url: str) -> Dict[str, Any]:
        """
        Main orchestrator: Navigate → DOM → LLM Reasoning → Execute → Repeat
        Returns final status and findings.
        """
        try:
            # Initialize browser and navigate
            await self.browser.initialize()
            await self.browser.navigate(url)
            
            max_steps = 10  # Safety limit
            step_number = 0
            recent_actions = []
            
            while step_number < max_steps:
                step_number += 1
                
                # Get current DOM and create page context
                raw_dom, title = await self.browser.get_current_dom()
                ctx = create_page_context(url, title, raw_dom, goal)
                
                # Build context packet for this step (using correct ContextPacket fields)
                context_packet = ContextPacket(
                    session_id="web_automation",  # Simple session identifier
                    goal=goal,
                    url=ctx.url,
                    step=step_number,
                    dom_snapshot=raw_dom[:1000],  # Truncate for memory efficiency
                    page_sig=ctx.signature,
                    regions=[],  # Could populate with visual regions in future
                    recipes={},  # Future: recipe caching
                    memory={},   # Future: user preferences
                    policy={}    # Future: policy configuration
                )
                
                # Execute single step through StepExecutor
                outcome = await self.executor.reason_and_act(
                    goal=goal,
                    ctx=ctx,
                    mode="autonomous",
                    recent_actions=recent_actions
                )
                
                # Log the step using context_packet (has session_id, step, goal)
                self.logger.log_decision(context_packet, outcome.batch, "autonomous", outcome.rationale, outcome.confidence)
                self.logger.log_result(context_packet, outcome.batch, outcome.evidence)
                
                # Add to recent actions for next iteration
                recent_actions.append({
                    "step": step_number,
                    "commands": [{"type": cmd.type, "selector": cmd.selector} for cmd in outcome.batch.commands],
                    "success": outcome.evidence.success
                })
                
                # Check if task completed or needs human intervention
                if not outcome.evidence.success:
                    if "pause_reasons" in outcome.evidence.findings:
                        return {
                            "status": "paused", 
                            "step": step_number,
                            "reasons": outcome.evidence.findings["pause_reasons"],
                            "evidence": outcome.evidence
                        }
                    
                # Check for goal completion (basic heuristic)
                if self._is_goal_achieved(goal, outcome.evidence, ctx):
                    return {
                        "status": "completed",
                        "step": step_number, 
                        "evidence": outcome.evidence,
                        "final_url": ctx.url
                    }
                
                # Heartbeat for long-running tasks
                self._send_heartbeat(step_number, outcome.evidence)
                
            return {
                "status": "max_steps_reached",
                "step": step_number,
                "evidence": outcome.evidence if 'outcome' in locals() else None
            }
            
        finally:
            await self.browser.close(save_state=True)

    async def execute_single_step(self, step_goal: str, current_url: str = None) -> Dict[str, Any]:
        """
        Execute a single step of a planned automation sequence.
        Returns step result without looping - designed for step-by-step execution.
        """
        try:
            # Get current DOM and create page context
            raw_dom, title = await self.browser.get_current_dom()
            actual_url = current_url or "about:blank"
            ctx = create_page_context(actual_url, title, raw_dom, step_goal)
            
            # Context packet for lattice logging  
            context_packet = ContextPacket(
                session_id="web_automation",
                goal=step_goal,
                url=ctx.url,
                step=1,  # Single step
                dom_snapshot=raw_dom[:1000],
                page_sig=ctx.signature,
                regions=[],
                recipes={},
                memory={},
                policy={}
            )
            
            # Execute single step through StepExecutor
            outcome = await self.executor.reason_and_act(
                goal=step_goal,
                ctx=ctx,
                mode="autonomous",
                recent_actions=[]  # Fresh start for each planned step
            )
            
            # Log the step
            self.logger.log_decision(context_packet, outcome.batch, "autonomous", outcome.rationale, outcome.confidence)
            self.logger.log_result(context_packet, outcome.batch, outcome.evidence)
            
            # Determine if the step was successful based on DOM changes or other evidence
            dom_changed = outcome.evidence.dom_after_sig != ctx.signature
            success = outcome.evidence.success or dom_changed
            
            return {
                "success": success,
                "evidence": outcome.evidence,
                "dom_changed": dom_changed,
                "final_url": ctx.url,
                "commands_executed": len(outcome.batch.commands),
                "step_goal": step_goal,
                "rationale": outcome.rationale,
                "confidence": outcome.confidence
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step_goal": step_goal
            }

    def _is_goal_achieved(self, goal: str, evidence, ctx: PageContext) -> bool:
        """Enhanced goal completion detection."""
        goal_lower = goal.lower()
        
        # Check if DOM changed significantly (good sign)
        if not evidence.success or evidence.dom_after_sig == ctx.signature:
            return False
            
        # Location/search specific goals
        if any(word in goal_lower for word in ["location", "search", "find", "nearest"]):
            # Check if we're on a results page or location listing
            current_dom = getattr(ctx, 'skeleton', '') or ''
            location_indicators = [
                "results", "locations", "stores", "address", "miles", "distance",
                "open", "hours", "directions", "map", "latitude", "longitude"
            ]
            if any(indicator in current_dom.lower() for indicator in location_indicators):
                return True
                
        # URL change often indicates successful navigation
        if hasattr(ctx, 'url') and ctx.url:
            if any(word in ctx.url.lower() for word in ["search", "location", "store", "find"]):
                return True
        
        # Fallback to simple completion check
        if "success" in goal_lower or "complete" in goal_lower:
            return evidence.success and evidence.dom_after_sig != ctx.signature
            
        return False
        
    def _send_heartbeat(self, step: int, evidence) -> None:
        """Send periodic status updates."""
        now = time.time()
        if now - self._last_heartbeat >= 5.0:  # Every 5 seconds
            status_msg = f"Step {step}: {'✓' if evidence.success else '✗'} {evidence.findings}"
            self.status_callback(status_msg)
            self._last_heartbeat = now