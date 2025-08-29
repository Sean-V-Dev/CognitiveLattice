
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
    ) -> StepOutcome:
        """
        1) Build prompt from PageContext
        2) Ask LLM for next 1–3 commands (JSON)
        3) Safety pre-check (if provided)
        4) Execute batch via BrowserController
        5) Return Evidence (+ confidence/rationale)
        """
        # 1) Build prompt
        prompt = build_reasoning_prompt(goal, ctx, recent_actions or [])
        
        # DEBUG: Save prompt to file for troubleshooting##############################
        # TODO: REMOVE OR COMMENT OUT THIS DEBUG CODE LATER
        try:
            import os
            debug_dir = os.path.join(os.getcwd(), "debug_prompts")
            os.makedirs(debug_dir, exist_ok=True)
            
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
            debug_file = os.path.join(debug_dir, f"web_prompt_{timestamp}.txt")
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"WEB AUTOMATION PROMPT DEBUG - {timestamp}\n")
                f.write("=" * 80 + "\n")
                f.write(f"Goal: {goal}\n")
                f.write(f"URL: {ctx.url}\n")
                f.write(f"Page Title: {ctx.title}\n")
                f.write(f"Page Signature: {ctx.signature}\n")
                f.write("-" * 40 + "\n")
                f.write("FULL PROMPT SENT TO LLM:\n")
                f.write("-" * 40 + "\n")
                f.write(prompt)
                f.write("\n" + "=" * 80 + "\n")
            
            print(f"🐛 DEBUG: Prompt saved to {debug_file}")
        except Exception as debug_error:
            print(f"⚠️ DEBUG: Failed to save prompt: {debug_error}")
        # END DEBUG CODE###############################

        # 2) Query LLM (expects JSON result)
        try:
            raw_response = self.llm.query_external_api(prompt)
            
            # DEBUG: Save LLM response to file for troubleshooting##########################
            # TODO: REMOVE OR COMMENT OUT THIS DEBUG CODE LATER
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                debug_file = os.path.join(debug_dir, f"web_response_{timestamp}.txt")
                
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write("=" * 80 + "\n")
                    f.write(f"WEB AUTOMATION RESPONSE DEBUG - {timestamp}\n")
                    f.write("=" * 80 + "\n")
                    f.write(f"Goal: {goal}\n")
                    f.write(f"URL: {ctx.url}\n")
                    f.write("-" * 40 + "\n")
                    f.write("RAW LLM RESPONSE:\n")
                    f.write("-" * 40 + "\n")
                    f.write(raw_response)
                    f.write("\n" + "=" * 80 + "\n")
                
                print(f"🐛 DEBUG: Response saved to {debug_file}")
            except Exception as debug_error:
                print(f"⚠️ DEBUG: Failed to save response: {debug_error}")
            # END DEBUG CODE############################
            
            print(f"🤖 LLM Raw Response: {raw_response[:200]}...")  # Debug output
            
            # Try to extract JSON from response (in case there's extra text)
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
        
        commands, confidence, rationale = self._parse_llm_json(raw)
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
                return StepOutcome(batch=batch, evidence=empty_ev, confidence=confidence, rationale=rationale)

        # 4) Execute batch
        evidence = await self.browser.execute_action_batch(batch)

        # Log decision/result if logger provided
        if self.logger is not None:
            try:
                self.logger.log_decision(ctx, batch, mode, rationale, confidence)
                self.logger.log_result(ctx, batch, evidence)
            except Exception:
                pass

        return StepOutcome(batch=batch, evidence=evidence, confidence=confidence, rationale=rationale)

    # -----------------
    # Helpers
    # -----------------
    def _parse_llm_json(self, obj: Any) -> Tuple[List[Command], float, str]:
        """Leniently coerce the LLM response to (commands, confidence, rationale)."""
        # If the LLM returned a string, try json.loads
        if isinstance(obj, str):
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
        return cmd_list[:3], confidence, rationale

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
