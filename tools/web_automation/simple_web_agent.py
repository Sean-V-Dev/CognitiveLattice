# =========================
# tools/web_automation/simple_web_agent.py  (orchestrator excerpt)
# =========================
import time
from typing import Optional, Tuple, Dict, Any, List
from .models import ContextPacket, CommandBatch, PageContext
from .lattice_logger import LatticeLogger
#from .planner import Planner  # Future: recipe-based planning
#from .recipe_cache import RecipeCache  # Future: DOM key caching
from .step_executor import StepExecutor
from .safety import SafetyManager
from .dom_processor import create_page_context_sync as create_page_context, page_signature  # DOM processing functions
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
            breadcrumbs = []  # Track plain English progress
            
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
                
            # Add verification requirement for location/search goals
            verification_clause = ""
            if any(k in goal.lower() for k in ["location", "search", "find", "nearest"]):
                verification_clause = (
                    " IMPORTANT: You are NOT done until the chosen location is VERIFIED. "
                    "Verification means a single store detail view is open with address + hours visible "
                    "AND an order affordance (e.g., 'Start order' or pickup/delivery button) is present. "
                    "If not present, click the top result to open its detail and verify."
                )

            # Execute single step through StepExecutor
            outcome = await self.executor.reason_and_act(
                goal=goal + verification_clause,
                ctx=ctx,
                mode="autonomous",
                recent_actions=recent_actions,
                breadcrumbs=breadcrumbs
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
            
            # Add breadcrumb if available
            if hasattr(outcome, 'breadcrumb') and outcome.breadcrumb:
                breadcrumbs.append(f"Step {step_number}: {outcome.breadcrumb}")
                # Keep only last 5 breadcrumbs to avoid prompt bloat
                breadcrumbs = breadcrumbs[-5:]
            
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

    async def execute_single_step(self, step_goal: str, current_url: str = None, 
                                 step_number: int = 1, total_steps: int = 1, 
                                 overall_goal: str = None,
                                 recent_events: List[Dict[str, Any]] = None,
                                 previous_signature: str = None,
                                 lattice_state: Dict[str, Any] = None,
                                 breadcrumbs: List[str] = None) -> Dict[str, Any]:
        """
        Execute a single step of a planned automation sequence.
        Returns step result without looping - designed for step-by-step execution.
        """
        try:
            # Get current DOM and create page context
            raw_dom, title = await self.browser.get_current_dom()
            actual_url = current_url or "about:blank"
            ctx = create_page_context(actual_url, title, raw_dom, step_goal,
                                    step_number=step_number, total_steps=total_steps, 
                                    overall_goal=overall_goal or step_goal,
                                    recent_events=recent_events,
                                    previous_signature=previous_signature,
                                    lattice_state=lattice_state)
            
            # Add step tracking to context (redundant but ensures compatibility)
            ctx.step_number = step_number
            ctx.total_steps = total_steps
            ctx.overall_goal = overall_goal or step_goal
            
            # Context packet for lattice logging  
            context_packet = ContextPacket(
                session_id="web_automation",
                goal=step_goal,
                url=ctx.url,
                step=step_number,
                dom_snapshot=raw_dom[:1000],
                page_sig=ctx.signature,
                regions=[],
                recipes={},
                memory={},
                policy={}
            )
            
            # Add verification requirement for location/search goals
            verification_clause = ""
            if any(k in step_goal.lower() for k in ["location", "search", "find", "nearest"]):
                verification_clause = (
                    " IMPORTANT: You are NOT done until the chosen location is VERIFIED. "
                    "Verification means a single store detail view is open with address + hours visible "
                    "AND an order affordance (e.g., 'Start order' or pickup/delivery button) is present. "
                    "If not present, click the top result to open its detail and verify."
                )

            # Execute single step through StepExecutor
            outcome = await self.executor.reason_and_act(
                goal=step_goal + verification_clause,
                ctx=ctx,
                mode="autonomous",
                recent_actions=[],  # Fresh start for each planned step
                breadcrumbs=breadcrumbs or []
            )
            
            # Log the step
            self.logger.log_decision(context_packet, outcome.batch, "autonomous", outcome.rationale, outcome.confidence)
            self.logger.log_result(context_packet, outcome.batch, outcome.evidence)
            
            # Determine if the step was successful based on DOM changes AND evidence
            dom_changed = outcome.evidence.dom_after_sig != ctx.signature
            evidence_success = outcome.evidence.success
            has_errors = len(outcome.evidence.errors) > 0
            
            # Enhanced step verification: check if goal is truly complete
            step_complete, completion_analysis = await self._verify_step_completion(
                step_goal=step_goal,
                outcome=outcome,
                dom_changed=dom_changed,
                ctx=ctx
            )
            
            # Debug: Log verification analysis
            print(f"🔍 STEP VERIFICATION: Complete={step_complete}")
            print(f"🔍 Analysis: {completion_analysis.get('reason', 'No reason provided')}")
            if 'signals' in completion_analysis:
                signals = completion_analysis['signals']
                print(f"🔍 Signals: affordance={signals.get('has_affordance')}, details={signals.get('has_details')}, selected={signals.get('selected_state')}, url={signals.get('url_selected_like')}")
            
            # Use enhanced completion logic instead of simple DOM check
            success = step_complete and evidence_success and not has_errors
            
            # Log completion analysis for debugging
            print(f"🔍 STEP VERIFICATION: {completion_analysis}")
            
            # Convert evidence to JSON-serializable dict to prevent lattice save issues
            evidence_dict = {
                "success": outcome.evidence.success,
                "dom_after_sig": outcome.evidence.dom_after_sig,
                "dom_before_sig": outcome.evidence.dom_before_sig,
                "regions_after": outcome.evidence.regions_after,
                "findings": outcome.evidence.findings,
                "used_selector": outcome.evidence.used_selector,
                "fallback_used": outcome.evidence.fallback_used,
                "timing_ms": outcome.evidence.timing_ms
            }
            
            # Include verification result for coordinator's logical success check
            verification_result = {
                "complete": step_complete,
                "analysis": completion_analysis
            }
            
            return {
                "success": success,
                "evidence": evidence_dict,
                "dom_changed": dom_changed,
                "final_url": ctx.url,
                "completion_analysis": completion_analysis,  # Add completion analysis to result
                "verification": verification_result,  # Add explicit verification result
                "commands_executed": [
                    {
                        "type": cmd.type,
                        "selector": cmd.selector,
                        "text": cmd.text,
                        "key": cmd.key,
                        "url": cmd.url
                    } for cmd in outcome.batch.commands
                ],
                "step_goal": step_goal,
                "rationale": outcome.rationale,
                "confidence": outcome.confidence,
                "page_signature": outcome.evidence.dom_after_sig,
                "breadcrumb": getattr(outcome, 'breadcrumb', None)  # Include breadcrumb for coordinator
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step_goal": step_goal
            }

    def _is_goal_achieved(self, goal: str, evidence, ctx: PageContext) -> bool:
        """Enhanced goal completion detection with explicit verification requirement."""
        goal_lower = goal.lower()

        # Must have success + a DOM change
        if not evidence.success or evidence.dom_after_sig == ctx.signature:
            return False

        # Prefer explicit verified signal set by _verify_step_completion
        verified = False
        findings = getattr(evidence, "findings", {}) or {}
        if isinstance(findings, dict):
            verified = bool(findings.get("location_verified")) or bool(findings.get("selection_verified"))

        # If the task is a location/search style, require verified selection (not just being on the results page)
        if any(k in goal_lower for k in ["location", "search", "find", "nearest"]):
            if verified:
                return True

            # Fallback: strong heuristics that imply a single, selected location detail view
            skel = (getattr(ctx, "skeleton", "") or "").lower()
            strong_indicators = [
                "start order",           # order affordance appears after a location is selected
                "order pickup",
                "order delivery", 
                "make this my restaurant",
                "set as favorite",
                "selected",              # selected state on the chosen card
                "hours", "phone", "directions"  # detail pane content typically present after selection
            ]
            url_ok = any(seg in (ctx.url or "").lower() for seg in ["/location/", "/store/", "/restaurants/"])
            has_detail_panel = ("address" in skel and ("hours" in skel or "phone" in skel)) or "order" in skel

            return url_ok and has_detail_panel and any(ind in skel for ind in strong_indicators)

        # Generic success fallback (discouraged for this task type)
        return False
        
    async def _verify_step_completion(
        self,
        step_goal: str,
        outcome,
        dom_changed: bool,
        ctx: PageContext,
        wait_ms: int = 1200
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Post-action verifier for 'select location' style goals.
        Returns (is_complete, analysis_dict) and mutates outcome.evidence.findings with 'location_verified'.
        """
        analysis: Dict[str, Any] = {"reason": "", "signals": {}}

        # Small dwell: allow SPA to render detail pane after click
        try:
            if hasattr(self.browser, 'sleep'):
                await self.browser.sleep(wait_ms / 1000.0)
            else:
                import asyncio
                await asyncio.sleep(wait_ms / 1000.0)
        except Exception:
            pass

        # Re-read DOM after dwell (don't rely only on evidence.dom_after_sig)
        try:
            raw_dom_after, _ = await self.browser.get_current_dom()
        except Exception:
            raw_dom_after = getattr(outcome.evidence, "dom_after", None) or ""

        text = (raw_dom_after or "").lower()

        # Heuristic signals that a single location has been verified/selected
        affordances = ["start order", "order pickup", "order delivery", "make this my restaurant", "set as favorite"]
        details_keys = ["hours", "phone", "directions", "get directions"]
        selection_tokens = ["selected", "aria-selected=\"true\"", "is-selected", "card--selected"]

        has_affordance = any(tok in text for tok in affordances)
        has_details = ("address" in text and any(k in text for k in details_keys))
        selected_state = any(tok in text for tok in selection_tokens)

        # URL pattern often changes from /find or /locations (list) -> /location/<slug> (detail)
        url_lower = (ctx.url or "").lower()
        url_selected_like = any(seg in url_lower for seg in ["/location/", "/store/", "/restaurants/"]) \
                            and not any(seg in url_lower for seg in ["/find", "/search", "/locations?"])

        # Compose verdict
        verified = (has_affordance and has_details) or (selected_state and has_details) or (url_selected_like and has_details)

        # Record signals to evidence.findings (so _is_goal_achieved can use them)
        findings = getattr(outcome.evidence, "findings", None)
        if not isinstance(findings, dict):
            findings = {}
            try:
                outcome.evidence.findings = findings  # keep structure consistent with your logger
            except Exception:
                pass

        findings["location_verified"] = bool(verified)
        findings["signals"] = {
            "has_affordance": has_affordance,
            "has_details": has_details,
            "selected_state": selected_state,
            "url_selected_like": url_selected_like
        }

        if verified:
            analysis["reason"] = "Verified by post-selection affordances/details and/or selected-state."
        else:
            analysis["reason"] = "Only on results/listing; no unique selected-location confirmation detected."

        return verified, analysis
        
    def _send_heartbeat(self, step: int, evidence) -> None:
        """Send periodic status updates."""
        now = time.time()
        if now - self._last_heartbeat >= 5.0:  # Every 5 seconds
            status_msg = f"Step {step}: {'✓' if evidence.success else '✗'} {evidence.findings}"
            self.status_callback(status_msg)
            self._last_heartbeat = now

    async def _verify_step_completion(self, step_goal: str, outcome, dom_changed: bool, ctx) -> tuple[bool, dict]:
        """
        Enhanced step verification that checks if the goal is truly complete.
        Returns (is_complete, analysis_details)
        """
        # Get current DOM to analyze completion state
        try:
            current_dom, _ = await self.browser.get_current_dom()
            
            # Basic interaction requirements
            has_interaction = any(cmd.type in ['click', 'type'] for cmd in outcome.batch.commands)
            evidence_success = outcome.evidence.success
            has_errors = len(outcome.evidence.errors) > 0
            
            # If no DOM change on interaction, likely failed
            if has_interaction and not dom_changed and evidence_success:
                print(f"⚠️ VERIFICATION: Interaction without DOM change detected")
                return False, {"reason": "interaction_no_dom_change", "details": "Interaction commands reported success but DOM unchanged"}
            
            # Basic failure conditions
            if has_errors or not evidence_success:
                print(f"⚠️ VERIFICATION: Basic failure - errors: {has_errors}, success: {evidence_success}")
                return False, {"reason": "execution_failed", "details": f"Errors: {outcome.evidence.errors}"}
            
            # Check for common incomplete patterns
            incomplete_signals = self._detect_incomplete_patterns(current_dom, step_goal)
            
            if incomplete_signals:
                print(f"🔄 VERIFICATION: Incomplete patterns detected: {incomplete_signals}")
                return False, {
                    "reason": "goal_incomplete", 
                    "details": f"Detected incomplete patterns: {incomplete_signals}",
                    "suggestion": "Continue with follow-up actions"
                }
            
            # Check for goal-specific completion
            goal_complete = self._check_goal_specific_completion(current_dom, step_goal)
            
            if not goal_complete:
                print(f"🔄 VERIFICATION: Goal not yet achieved: {step_goal}")
                return False, {
                    "reason": "goal_not_achieved",
                    "details": f"Goal '{step_goal}' not yet fully achieved based on current DOM state"
                }
            
            # All checks passed - step is complete
            print(f"✅ VERIFICATION: Step complete - {step_goal}")
            return True, {"reason": "complete", "details": "All completion criteria met"}
            
        except Exception as e:
            print(f"⚠️ Error in step verification: {e}")
            # Fall back to basic logic if verification fails
            basic_success = dom_changed and evidence_success and not has_errors
            return basic_success, {"reason": "verification_error", "details": str(e)}

    def _detect_incomplete_patterns(self, dom: str, goal: str) -> list:
        """Detect common UI patterns that suggest the step isn't complete."""
        import re
        
        signals = []
        dom_lower = dom.lower()
        goal_lower = goal.lower()
        
        # Pattern 1: Modal/popup appeared with action buttons
        modal_patterns = [
            r'<div[^>]*class[^>]*modal[^>]*>',
            r'<div[^>]*class[^>]*popup[^>]*>',
            r'<div[^>]*class[^>]*dialog[^>]*>',
            r'role=["\']dialog["\']'
        ]
        
        for pattern in modal_patterns:
            if re.search(pattern, dom_lower):
                # Check for action buttons in the modal
                action_buttons = re.findall(r'<button[^>]*>(choose|select|confirm|ok|continue|proceed)[^<]*</button>', dom_lower)
                if action_buttons:
                    signals.append(f"modal_with_action_buttons: {action_buttons}")
        
        # Pattern 2: Location selection specific patterns
        if any(word in goal_lower for word in ['location', 'select', 'choose', 'restaurant']):
            # Check for "Choose this location" type buttons
            choose_buttons = re.findall(r'<[^>]*>(choose|select)[^<]*location[^<]*</[^>]*>', dom_lower)
            if choose_buttons:
                signals.append(f"location_choose_buttons: {choose_buttons}")
            
            # Check for location details that appeared but no final selection
            if 'data-qa-restaurant-id' in dom_lower and ('choose' in dom_lower or 'select' in dom_lower):
                signals.append("location_details_without_selection")
        
        # Pattern 3: Form submission patterns
        if any(word in goal_lower for word in ['enter', 'type', 'submit', 'search']):
            # Check for submit buttons that appeared
            submit_buttons = re.findall(r'<button[^>]*type=["\']submit["\'][^>]*>', dom_lower)
            if submit_buttons:
                signals.append("submit_buttons_available")
        
        # Pattern 4: Success messages that indicate completion
        success_patterns = [
            r'success|completed|done|confirmed|selected',
            r'thank you|order placed|reservation made'
        ]
        
        for pattern in success_patterns:
            if re.search(pattern, dom_lower):
                # This suggests completion, so remove incomplete signals
                return []  # Override - step might actually be complete
        
        return signals

    def _check_goal_specific_completion(self, dom: str, goal: str) -> bool:
        """Check if the specific goal has been achieved based on DOM content."""
        import re
        
        dom_lower = dom.lower()
        goal_lower = goal.lower()
        
        # Location selection goals
        if any(word in goal_lower for word in ['select', 'choose']) and 'location' in goal_lower:
            # Look for confirmation that a location was selected
            confirmation_patterns = [
                r'selected location|chosen location|your location',
                r'location confirmed|location set',
                r'delivery to|pickup at',
                r'order from this location'
            ]
            
            for pattern in confirmation_patterns:
                if re.search(pattern, dom_lower):
                    return True
            
            # If we just see location details but no confirmation, not complete
            if 'data-qa-restaurant-id' in dom_lower and not any(re.search(p, dom_lower) for p in confirmation_patterns):
                return False
        
        # Search goals
        if any(word in goal_lower for word in ['search', 'find', 'enter']) and any(word in goal_lower for word in ['location', 'zip', 'address']):
            # Look for search results
            if any(phrase in dom_lower for phrase in ['search results', 'locations found', 'nearby', 'restaurants near']):
                return True
        
        # Default: if DOM changed significantly, assume goal met (fallback)
        return True