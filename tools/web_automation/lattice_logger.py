# tools/web_automation/lattice_logger.py
from __future__ import annotations
from typing import Optional, Dict, Any, List
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from .models import ContextPacket, CommandBatch, Evidence

SCHEMA_VERSION = "web_automation.v0.1"

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _serialize(obj: Any) -> Any:
    """Safely convert dataclasses (e.g., Money) to dicts; leave primitives as-is."""
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    return obj

def _redact_text(text: Optional[str]) -> Optional[str]:
    """Avoid leaking PII; store presence/length only."""
    if text is None:
        return None
    return f"<redacted:{len(text)}chars>"

class LatticeLogger:
    """Single interface for all lattice logging from web automation."""

    def __init__(self, cognitive_lattice=None, source: str = "web_automation"):
        self.cognitive_lattice = cognitive_lattice
        self.source = source

    # ---- Decision ---------------------------------------------------------

    def log_decision(
        self,
        ctx: ContextPacket,
        plan: CommandBatch,
        mode: str,                 # "probe" | "replay"
        rationale: str,
        confidence: float
    ) -> Optional[str]:
        if not self.cognitive_lattice:
            return None

        planned_commands = [
            {
                "type": cmd.type,
                "selector": cmd.selector,
                # Do not log raw typed text to avoid PII leakage:
                "text": _redact_text(cmd.text),
                "url": cmd.url,
            }
            for cmd in plan.commands
        ]

        event = {
            "schema_version": SCHEMA_VERSION,
            "session_id": ctx.session_id,
            "step": ctx.step,
            "goal": ctx.goal,
            "site_url": ctx.url,
            "mode": mode,                       # "probe" or "replay"
            "rationale": rationale,
            "confidence": confidence,
            "idempotency_key": plan.idempotency_key,
            "preconditions": plan.preconditions,
            "postconditions": plan.postconditions,
            "human_pacing": plan.human_pacing,
            "dom_signatures": {
                "before": ctx.page_sig,
            },
            "planned_commands": planned_commands,
            "timestamp": _utc_now(),
        }

        event_to_log = {
            "type": "web_decision",
            "data": event,
            "source": self.source,
            "timestamp": _utc_now(),
        }

        return self.cognitive_lattice.add_event(event_to_log)

    # ---- Execution Result -------------------------------------------------

    def log_result(
        self,
        ctx: ContextPacket,
        plan: CommandBatch,
        evidence: Evidence,
        errors: Optional[Dict[str, Any]] = None,
        postcondition_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        if not self.cognitive_lattice:
            return None

        executed_commands = [
            {
                "type": cmd.type,
                "selector": cmd.selector,
                "text": _redact_text(cmd.text),
                "url": cmd.url,
            }
            for cmd in plan.commands
        ]

        event = {
            "schema_version": SCHEMA_VERSION,
            "session_id": ctx.session_id,
            "step": ctx.step,
            "goal": ctx.goal,
            "site_url": ctx.url,
            "success": evidence.success,
            "idempotency_key": plan.idempotency_key,
            "executed_commands": executed_commands,
            "findings": _serialize(evidence.findings),
            "used_selector": evidence.used_selector,
            "fallback_used": evidence.fallback_used,
            "timing_ms": evidence.timing_ms,
            "dom_signatures": {
                "before": ctx.page_sig,
                "after": evidence.dom_after_sig,
                "changed": evidence.dom_after_sig != ctx.page_sig,
            },
            "postcondition_results": postcondition_results or [],
            "errors": errors or {},
            "timestamp": _utc_now(),
        }

        event_to_log = {
            "type": "web_execution_result",
            "data": event,
            "source": self.source,
            "timestamp": _utc_now(),
        }

        return self.cognitive_lattice.add_event(event_to_log)

    # ---- Step Completion ---------------------------------------------------

    def log_step_completion(
        self,
        ctx: ContextPacket,
        step_description: str,
        total_timing_ms: int,
        success: bool
    ) -> Optional[str]:
        if not self.cognitive_lattice:
            return None

        event = {
            "schema_version": SCHEMA_VERSION,
            "session_id": ctx.session_id,
            "step": ctx.step,
            "goal": ctx.goal,
            "site_url": ctx.url,
            "step_description": step_description,
            "success": success,
            "total_timing_ms": total_timing_ms,
            "timestamp": _utc_now(),
        }

        event_to_log = {
            "type": "web_step_completed",
            "data": event,
            "source": self.source,
            "timestamp": _utc_now(),
        }

        return self.cognitive_lattice.add_event(event_to_log)
