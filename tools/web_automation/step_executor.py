
"""
Single-step executor: turns a PageContext + goal into a CommandBatch via LLM,
executes it through BrowserController, and returns Evidence. Keeps concerns small:
- No Playwright primitives here (delegated to BrowserController)
- No lattice writes here (the orchestrator does logging + lattice updates)
- No DOM parsing here (dom_processor already built PageContext)

You can swap the LLM client as long as it exposes `await client.query_json(prompt: str) -> dict`.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import json
from datetime import datetime

from .models import PageContext, CommandBatch, Command, Evidence

# Optional: import prompt_builder if present; fall back to local minimal builder
try:
    from .prompt_builder import build_reasoning_prompt
except Exception:  # pragma: no cover
    def build_reasoning_prompt(goal: str, ctx: PageContext, recent_actions: Optional[List[Dict[str, Any]]] = None) -> str:
        recent_actions = recent_actions or []
        skeleton = (ctx.skeleton or "")[:4000]
        # compact candidates
        candidates = []
        for el in ctx.interactive[:30]:
            candidates.append({
                "tag": el.tag,
                "text": el.text,
                "score": round(getattr(el, "score", 0.0), 3),
                "selectors": (el.selectors or [])[:3],
            })
        lines: List[str] = []
        lines.append("System:\n"
                     "You are a web-navigation planner. Given a goal, a DOM skeleton, and ranked candidates, "
                     "return 1-3 JSON commands that advance the goal. Prefer provided selectors.")
        lines.append("--- Goal ---\n" + goal.strip())
        lines.append(f"--- Page ---\nURL: {ctx.url}\nTitle: {ctx.title}\nSignature: {ctx.signature}")
        lines.append("--- DOM Skeleton (truncated) ---\n" + skeleton)
        lines.append("--- Ranked Candidates ---")
        for i, c in enumerate(candidates, 1):
            sels = ", ".join(c["selectors"]) if c["selectors"] else ""
            text = c["text"] or ""
            lines.append(f"{i}. <{c['tag']}> score={c['score']} text=\"{text}\" selectors=[{sels}]")
        if recent_actions:
            lines.append("--- Recent Actions ---")
            for a in recent_actions[-5:]:
                lines.append(f"- {a}")
        lines.append("--- Respond ---\n"
                     "Return JSON: {\"commands\":[], \"confidence\":0..1, \"rationale\":str}. Limit to 1–3 commands.")
        return "\n\n".join(lines)


@dataclass
class StepOutcome:
    batch: CommandBatch
    evidence: Evidence
    confidence: float
    rationale: str
    breadcrumb: str = ""  # Plain English note about what was accomplished


class StepExecutor:
    """Reason over the current page, produce a plan (CommandBatch), execute, return Evidence."""

    def __init__(self, browser_controller, llm_client, safety_manager=None, logger=None):
        self.browser = browser_controller
        self.llm = llm_client
        self.safety = safety_manager
        self.logger = logger

    async def reason_and_act(
        self,
        goal: str,
        ctx: PageContext,
        mode: str = "autonomous",
        recent_actions: Optional[List[Dict[str, Any]]] = None,
        breadcrumbs: Optional[List[str]] = None,
    ) -> StepOutcome:
        """
        1) Build prompt from PageContext with progressive candidate disclosure
        2) Ask LLM for next 1–3 commands (JSON)
        3) If LLM says "NONE", increase candidates and retry
        4) Safety pre-check (if provided)
        5) Execute batch via BrowserController
        6) Return Evidence (+ confidence/rationale)
        """
        
        # Progressive candidate disclosure: start with 10, expand if needed
        max_passes = 5  # Up to 50 candidates (5 x 10)
        raw_response = None  # Initialize for the loop
        
        for pass_number in range(1, max_passes + 1):
            print(f"🔍 Candidate pass {pass_number} (showing top {pass_number * 10} candidates)")
            
            # 1) Build prompt with current pass number
            prompt = build_reasoning_prompt(goal, ctx, recent_actions or [], breadcrumbs or [], pass_number)
            
            # ############################################################################# 
            # DEBUG: Save prompt to file for troubleshooting
            # ############################################################################# 
            # TODO: REMOVE OR COMMENT OUT ALL DEBUG CODE BELOW BEFORE PRODUCTION
            # ############################################################################# 
            try:
                import os
                debug_dir = os.path.join(os.getcwd(), "debug_prompts")
                os.makedirs(debug_dir, exist_ok=True)
                
                from datetime import datetime
                # Create unique filename with step info and microsecond precision
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                step_info = getattr(ctx, 'step_number', getattr(ctx, 'step', 'unknown'))
                total_info = getattr(ctx, 'total_steps', 'unknown')
                debug_file = os.path.join(debug_dir, f"web_prompt_step{step_info}of{total_info}_pass{pass_number}_{timestamp}.txt")
                
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write("################################################################################\n")
                    f.write(f"FULL PROMPT SENT TO EXTERNAL API - {datetime.now()}\n")
                    f.write("################################################################################\n")
                    f.write(f"Step: {step_info} of {total_info}\n")
                    f.write(f"Pass: {pass_number} (candidates: {pass_number * 10})\n")
                    f.write(f"Goal: {goal}\n")
                    f.write(f"URL: {ctx.url}\n")
                    f.write(f"Page Title: {ctx.title}\n")
                    f.write(f"Page Signature: {ctx.signature}\n")
                    f.write(f"Overall Goal: {getattr(ctx, 'overall_goal', 'not specified')}\n")
                    f.write("=" * 80 + "\n")
                    f.write("FULL PROMPT CONTENT:\n")
                    f.write("=" * 80 + "\n")
                    f.write(prompt)
                    f.write("\n" + "=" * 80 + "\n")
                    f.write(f"Prompt length: {len(prompt)} characters\n")
                    f.write("################################################################################\n")
                
                print(f"🐛 DEBUG: Prompt saved to {os.path.abspath(debug_file)}")
            except Exception as debug_error:
                print(f"⚠️ DEBUG: Failed to save prompt: {debug_error}")
            # ############################################################################# 
            
            # 2) Ask LLM
            try:
                raw_response = self.llm.query_external_api(prompt)
                
                # Check if LLM said "NONE" (no suitable candidates)
                if '"no_match"' in raw_response and '"NONE"' in raw_response:
                    print(f"🔄 Pass {pass_number}: LLM found no suitable candidates, expanding to pass {pass_number + 1}")
                    if pass_number == max_passes:
                        print(f"⚠️ Reached maximum passes ({max_passes}), proceeding with best effort")
                        # Continue with the "NONE" response to handle gracefully
                        break
                    continue  # Try next pass with more candidates
                
                # LLM found a candidate, proceed with execution
                print(f"✅ Pass {pass_number}: LLM selected a candidate")
                break
                
            except Exception as llm_error:
                print(f"❌ Pass {pass_number}: LLM query failed: {llm_error}")
                if pass_number == max_passes:
                    raise  # Re-raise on final pass
                continue  # Try next pass
        
        # Continue with normal execution flow using the final raw_response
        # Handle case where all passes failed
        if raw_response is None:
            raw_response = '{"commands": [{"type": "noop"}], "confidence": 0.1, "rationale": "All candidate passes failed"}'
        
        # ############################################################################# 
        # DEBUG: Save LLM response to file for troubleshooting
        # ############################################################################# 
        # TODO: REMOVE OR COMMENT OUT THIS DEBUG CODE LATER
        # ############################################################################# 
        try:
            # Use same timestamp and step info for matching prompt/response pairs
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            step_info = getattr(ctx, 'step_number', getattr(ctx, 'step', 'unknown'))
            total_info = getattr(ctx, 'total_steps', 'unknown')
            debug_file = os.path.join(debug_dir, f"web_response_step{step_info}of{total_info}_{timestamp}.txt")
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write("################################################################################\n")
                f.write(f"FULL RESPONSE FROM EXTERNAL API - {datetime.now()}\n")
                f.write("################################################################################\n")
                f.write(f"Step: {step_info} of {total_info}\n")
                f.write(f"Goal: {goal}\n")
                f.write(f"URL: {ctx.url}\n")
                f.write(f"Overall Goal: {getattr(ctx, 'overall_goal', 'not specified')}\n")
                f.write("=" * 80 + "\n")
                f.write("RAW LLM RESPONSE CONTENT:\n")
                f.write("=" * 80 + "\n")
                f.write(raw_response)
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"Response length: {len(raw_response)} characters\n")
                f.write("################################################################################\n")
            
            print(f"🐛 DEBUG: Response saved to {os.path.abspath(debug_file)}")
        except Exception as debug_error:
            print(f"⚠️ DEBUG: Failed to save response: {debug_error}")
            # ############################################################################# 
            # END DEBUG CODE - REMOVE BEFORE PRODUCTION
            # ############################################################################# 
        
        print(f"🤖 LLM Raw Response: {raw_response[:200]}...")  # Debug output
        
        # Try to extract JSON from response (in case there's extra text)
        try:
            json_start = raw_response.find('{')
            json_end = raw_response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = raw_response[json_start:json_end]
                raw = json.loads(json_str)
            else:
                # No JSON found, create fallback
                raw = {
                    "commands": [{"type": "noop"}], 
                    "confidence": 0.3, 
                    "rationale": f"Could not parse JSON from response: {raw_response[:100]}..."
                }
                
        except (AttributeError, json.JSONDecodeError, Exception) as e:
            # Fallback if API doesn't return valid JSON
            print(f"❌ JSON parsing failed: {e}")
            raw = {
                "commands": [{"type": "noop"}], 
                "confidence": 0.1, 
                "rationale": f"API error: {str(e)}"
            }
        
        commands, confidence, rationale, breadcrumb = self._parse_llm_json(raw)
        batch = CommandBatch(commands=commands)

        # Safety pre-check (optional)
        if self.safety is not None:
            decision = self.safety.requires_human_confirmation(
                command_batch=batch,
                ctx=ctx,
                mode=mode,
                confidence=confidence,
            )
            if getattr(decision, "require_confirmation", False):
                # Return a no-op Evidence; orchestrator can pause & ask user
                empty_ev = Evidence(
                    success=False,
                    dom_after_sig=ctx.signature,
                    regions_after=[],
                    findings={"pause_reasons": getattr(decision, "reasons", [])},
                    used_selector=None,
                    fallback_used=False,
                    timing_ms=0,
                    errors=[],
                )
                return StepOutcome(batch=batch, evidence=empty_ev, confidence=confidence, rationale=rationale, breadcrumb=breadcrumb)

        # 4) Execute batch with fallback logic
        evidence = await self._execute_with_fallbacks(batch, goal, ctx, recent_actions)

        # Log decision/result if logger provided
        if self.logger is not None:
            try:
                self.logger.log_decision(ctx, batch, mode, rationale, confidence)
                self.logger.log_result(ctx, batch, evidence)
            except Exception:
                pass

        return StepOutcome(batch=batch, evidence=evidence, confidence=confidence, rationale=rationale, breadcrumb=breadcrumb)

    async def _execute_with_fallbacks(
        self, 
        initial_batch: CommandBatch, 
        goal: str, 
        ctx: PageContext, 
        recent_actions: Optional[List[Dict[str, Any]]] = None
    ) -> Evidence:
        """
        Execute commands with fallback logic:
        1. Try initial batch (ranked interactive elements)
        2. If fails, retry with full DOM skeleton
        3. If still fails, retry with DOM diff context
        """
        # First attempt: Execute original batch
        evidence = await self.browser.execute_action_batch(initial_batch)
        
        # Check if we should try fallbacks:
        # 1. If there are errors (selectors not found, etc.)
        # 2. If interaction commands executed but DOM didn't change (suspicious)
        # 3. If success is False
        should_fallback = (
            len(evidence.errors) > 0 or 
            not evidence.success or
            (len(initial_batch.commands) > 0 and 
             any(cmd.type in ['click', 'type'] for cmd in initial_batch.commands) and
             not evidence.success)
        )
        
        # If successful, return immediately
        if not should_fallback:
            return evidence
            
        print(f"🔄 First attempt needs fallback. Success: {evidence.success}, Errors: {len(evidence.errors)}")
        print(f"🔄 Error details: {evidence.errors}")
        
        # Second attempt: Use full DOM skeleton for richer context
        try:
            fallback_batch = await self._create_fallback_batch_with_full_dom(goal, ctx, recent_actions)
            if fallback_batch and len(fallback_batch.commands) > 0:
                print("🔄 Attempting fallback with full DOM skeleton...")
                fallback_evidence = await self.browser.execute_action_batch(fallback_batch)
                fallback_evidence.fallback_used = True
                
                # If this worked, return it
                if fallback_evidence.success or len(fallback_evidence.errors) == 0:
                    print("✅ Fallback with full DOM succeeded!")
                    return fallback_evidence
                    
                print(f"🔄 Full DOM fallback also failed with {len(fallback_evidence.errors)} errors.")
        except Exception as e:
            print(f"⚠️ Failed to create full DOM fallback: {e}")
        
        # Third attempt: Use DOM diff if available
        try:
            diff_batch = await self._create_fallback_batch_with_dom_diff(goal, ctx, recent_actions)
            if diff_batch and len(diff_batch.commands) > 0:
                print("🔄 Attempting fallback with DOM diff...")
                diff_evidence = await self.browser.execute_action_batch(diff_batch)
                diff_evidence.fallback_used = True
                
                # If this worked, return it
                if diff_evidence.success or len(diff_evidence.errors) == 0:
                    print("✅ DOM diff fallback succeeded!")
                    return diff_evidence
                    
                print(f"🔄 DOM diff fallback also failed with {len(diff_evidence.errors)} errors.")
        except Exception as e:
            print(f"⚠️ Failed to create DOM diff fallback: {e}")
        
        # All fallbacks failed, return the original evidence with fallback attempted flag
        print("❌ All fallback attempts failed, returning original evidence")
        evidence.fallback_used = True
        return evidence

    async def _create_fallback_batch_with_full_dom(
        self, 
        goal: str, 
        ctx: PageContext, 
        recent_actions: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[CommandBatch]:
        """Create a new command batch using full DOM skeleton instead of ranked elements."""
        try:
            # Import dom_processor to get full skeleton
            from . import dom_processor as dp
            from utils.dom_skeleton import create_dom_skeleton
            
            # Get current DOM for full skeleton
            raw_dom, title = await self.browser.get_current_dom()
            compressed = dp.compress_dom(raw_dom, goal)
            full_skeleton = create_dom_skeleton(compressed)
            
            # Build a richer prompt with full DOM skeleton
            fallback_prompt = self._build_fallback_prompt_with_full_dom(goal, ctx, full_skeleton, recent_actions)
            
            # Query LLM with richer context
            raw_response = self.llm.query_external_api(fallback_prompt)
            
            # Debug: Save fallback prompt and response
            try:
                import os
                debug_dir = os.path.join(os.getcwd(), "debug_prompts")
                os.makedirs(debug_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                step_info = getattr(ctx, 'step_number', 'unknown')
                
                # Save fallback prompt
                prompt_file = os.path.join(debug_dir, f"fallback_prompt_step{step_info}_{timestamp}.txt")
                with open(prompt_file, 'w', encoding='utf-8') as f:
                    f.write("FALLBACK PROMPT WITH FULL DOM SKELETON\n")
                    f.write("=" * 50 + "\n")
                    f.write(fallback_prompt)
                
                # Save fallback response  
                response_file = os.path.join(debug_dir, f"fallback_response_step{step_info}_{timestamp}.txt")
                with open(response_file, 'w', encoding='utf-8') as f:
                    f.write("FALLBACK RESPONSE\n")
                    f.write("=" * 50 + "\n")
                    f.write(str(raw_response))
                
                print(f"🐛 DEBUG: Fallback prompt saved to {prompt_file}")
                print(f"🐛 DEBUG: Fallback response saved to {response_file}")
            except Exception as debug_error:
                print(f"⚠️ DEBUG: Failed to save fallback debug files: {debug_error}")
            
            commands, confidence, rationale, breadcrumb = self._parse_llm_json(raw_response)
            
            print(f"🔍 FALLBACK DEBUG: Parsed {len(commands)} commands from LLM response")
            for i, cmd in enumerate(commands):
                print(f"  Command {i+1}: {cmd.type} selector='{cmd.selector}' text='{cmd.text}'")
            
            return CommandBatch(commands=commands)
            
        except Exception as e:
            print(f"⚠️ Error creating full DOM fallback: {e}")
            return None

    async def _create_fallback_batch_with_dom_diff(
        self, 
        goal: str, 
        ctx: PageContext, 
        recent_actions: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[CommandBatch]:
        """Create a new command batch using DOM diff to show only what changed."""
        try:
            # This would require implementing DOM diff logic
            # For now, return None - we can implement this later if needed
            return None
            
        except Exception as e:
            print(f"⚠️ Error creating DOM diff fallback: {e}")
            return None

    def _build_fallback_prompt_with_full_dom(
        self, 
        goal: str, 
        ctx: PageContext, 
        full_skeleton: str, 
        recent_actions: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Build a prompt using the full DOM skeleton instead of ranked interactive elements."""
        recent_actions = recent_actions or []
        
        lines = []
        lines.append("System:")
        lines.append("FALLBACK MODE: The initial ranked elements failed to provide working selectors.")
        lines.append("You are a web-navigation expert. The full DOM skeleton is provided below.")
        lines.append("Analyze the ENTIRE skeleton and choose ANY selector that will advance the goal.")
        lines.append("You can use ANY element you see - buttons, divs, spans, inputs, links, etc.")
        lines.append("Return 1-3 JSON commands with the EXACT selectors you identify in the DOM.")
        lines.append("")
        
        lines.append(f"--- Goal ---")
        lines.append(goal.strip())
        lines.append("")
        
        lines.append(f"--- Page Info ---")
        lines.append(f"URL: {ctx.url}")
        lines.append(f"Title: {ctx.title}")
        lines.append(f"Current Step: {getattr(ctx, 'step_number', 'unknown')} of {getattr(ctx, 'total_steps', 'unknown')}")
        lines.append("")
        
        lines.append("--- FULL DOM SKELETON ---")
        lines.append("INSTRUCTIONS: Look through this ENTIRE skeleton for ANY element that could help achieve the goal.")
        lines.append("Focus on: input fields, buttons, clickable divs, forms, links, etc.")
        lines.append("")
        lines.append(full_skeleton)
        lines.append("")
        
        if recent_actions:
            lines.append("--- Recent Actions That Failed ---")
            for action in recent_actions[-3:]:  # Show last 3 failed actions
                lines.append(f"- {action}")
            lines.append("")
        
        lines.append("--- Required Response Format ---")
        lines.append("Return JSON with 'commands' array. Each command needs:")
        lines.append("- type: 'click', 'type', 'press', or 'navigate'")
        lines.append("- selector: CSS selector you found in the DOM above")
        lines.append("- text: (for type commands) what to type")
        lines.append("- key: (for press commands) key to press")
        lines.append("- url: (for navigate commands) URL to go to")
        lines.append("")
        lines.append("CRITICAL: Use EXACT selectors from the DOM skeleton above.")
        lines.append("Example: {'commands': [{'type': 'click', 'selector': '#specific-button-id'}]}")
        
        return "\n".join(lines)

    # -----------------
    # Helpers
    # -----------------
    def _parse_llm_json(self, obj: Any) -> Tuple[List[Command], float, str, str]:
        """Leniently coerce the LLM response to (commands, confidence, rationale, breadcrumb)."""
        # If the LLM returned a string, try json.loads
        if isinstance(obj, str):
            # First, try to extract JSON from markdown code blocks
            import re
            markdown_json_match = re.search(r'```json\s*(\{.*?\})\s*```', obj, re.DOTALL)
            if markdown_json_match:
                json_str = markdown_json_match.group(1)
                try:
                    obj = json.loads(json_str)
                except Exception:
                    obj = {}
            else:
                # Try direct JSON parsing
                try:
                    obj = json.loads(obj)
                except Exception:
                    obj = {}
        if not isinstance(obj, dict):
            obj = {}

        cmd_list = []
        for item in obj.get("commands", []) or []:
            if not isinstance(item, dict):
                continue
            t = (item.get("type") or "").strip().lower()
            
            # Handle press commands (for Enter key, etc.)
            if t == "press":
                key_value = item.get("key", "").strip()
                if key_value:
                    cmd = Command(
                        type="press",
                        key=key_value,
                        selector=None,
                        text=None,
                        url=None,
                        enter=None
                    )
                    cmd_list.append(cmd)
                continue
            
            # Check against actual ActionType values
            if t not in {"navigate", "wait_for", "click", "type", "select", "press"}:
                continue
                
            # Handle the 'key' parameter from LLM - map it to appropriate fields
            key_value = item.get("key")
            enter_value = None
            
            # If key is "Enter" or "Return", set enter=True for type commands
            if key_value and key_value.lower() in ["enter", "return"] and t == "type":
                enter_value = True
            
            cmd = Command(
                type=t,
                selector=item.get("selector"),
                text=item.get("text"),
                url=item.get("url"),
                enter=enter_value
            )
            cmd_list.append(cmd)
            
            # Auto-add Enter after type commands in search-like fields
            if t == "type" and self._looks_like_search_field(item):
                enter_cmd = Command(
                    type="press",
                    key="Enter",
                    selector=None,
                    text=None,
                    url=None,
                    enter=None
                )
                cmd_list.append(enter_cmd)

        # Default to a no-op if empty
        if not cmd_list:
            cmd_list = [Command(type="noop")]

        conf = obj.get("confidence")
        try:
            confidence = float(conf) if conf is not None else 0.5
        except Exception:
            confidence = 0.5

        rationale = obj.get("rationale") or ""
        breadcrumb = obj.get("breadcrumb") or ""
        return cmd_list[:3], confidence, rationale, breadcrumb

    def _looks_like_search_field(self, command_item: dict) -> bool:
        """Detect if a type command is targeting a search field that would benefit from auto-Enter."""
        selector = (command_item.get("selector", "") or "").lower()
        text = (command_item.get("text", "") or "").lower()
        
        # Check selector for search-related patterns
        search_patterns = [
            "search", "query", "q", "term", "location", "address", 
            "zip", "postal", "find", "lookup", "filter"
        ]
        
        # If selector contains search-related keywords
        for pattern in search_patterns:
            if pattern in selector:
                return True
        
        # Check if it's an input field (most common for search)
        if "input" in selector and any(attr in selector for attr in ["[type=", "[name=", "[id=", "[placeholder="]):
            return True
            
        # Check if the text being typed looks like a search term (short, no spaces suggesting forms)
        if text and len(text.strip()) < 50 and not any(char in text for char in ["@", "password", "email"]):
            return True
            
        return False
