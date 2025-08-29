# =========================
# tools/web_automation/safety.py
# =========================
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re

# --- Phase heuristics (tune per site as needed) ---
CART_KEYWORDS = ["cart", "bag", "basket", "subtotal", "items"]
CHECKOUT_KEYWORDS = ["checkout", "contact", "delivery", "pickup time", "address"]
PAYMENT_KEYWORDS = ["payment", "card", "google pay", "apple pay", "place order", "cvv", "billing"]

def current_phase(dom_text: str) -> str:
    t = dom_text.lower()
    if any(k in t for k in PAYMENT_KEYWORDS):  return "payment"
    if any(k in t for k in CHECKOUT_KEYWORDS): return "checkout"
    if any(k in t for k in CART_KEYWORDS):     return "cart"
    return "browse"

PAYMENT_RE = re.compile(r"(checkout|payment|pay|purchase|place[-_\s]?order|card|gpay|googlepay|applepay)", re.I)
AUTH_RE    = re.compile(r"(login|log[-_\s]?in|sign[-_\s]?in|auth|authorize|oauth|2fa|mfa|password)", re.I)
DESTRUCTIVE_RE = re.compile(r"(submit|confirm|place|cancel|delete|purchase|checkout)", re.I)

# --- Default policy ---
DEFAULT_POLICY: Dict[str, Any] = {
    "schema_version": "safety.v0.2",
    "confirm_payment": True,       # always confirm on payment/auth
    "min_confidence": 0.70,        # below this → confirm
    "spend_cap": {"amount": 25.00, "currency": "USD"},  # confirm if total exceeds
    "allow_domains": [],           # [] = allow all; if non-empty, others require confirmation
    "deny_domains": [],            # hard block (require confirmation)
    "require_idempotency": True,   # destructive/charge actions need idempotency_key
    "heartbeat_seconds": 60,       # send periodic status update during long safe runs
    # OPTIONAL safety governor if you still want a single number:
    "risk_budget": None,           # e.g., 12 → confirm when cumulative risk exceeds this
    # scoring weights (used only if risk_budget is not None)
    "risk_weights": {"browse": 1, "cart": 2, "checkout": 5, "payment": 10},
}

@dataclass
class SafetyDecision:
    require_confirmation: bool
    reasons: List[str] = field(default_factory=list)
    phase: str = "browse"

class SafetyManager:
    def __init__(self, policy: Optional[Dict[str, Any]] = None):
        p = dict(DEFAULT_POLICY)
        if policy:
            p.update(policy)
        self.policy = p

    # ---- Public: main decision the orchestrator calls ----
    def requires_human_confirmation(
        self,
        *,
        command_batch,                 # CommandBatch
        ctx,                           # ContextPacket
        mode: str,                     # "probe" | "replay"
        confidence: float,
        findings: Optional[Dict[str, Any]] = None,
        dom_text: str = "",
        cumulative_risk: int = 0
    ) -> SafetyDecision:
        reasons: List[str] = []
        phase = current_phase(dom_text)

        # (1) Domain policy
        if self._domain_denied(ctx.url):
            reasons.append("domain_denied")
        elif self._domain_not_allowed(ctx.url):
            reasons.append("domain_not_in_allowlist")

        # (2) Confidence
        if confidence < float(self.policy["min_confidence"]):
            reasons.append(f"low_confidence<{self.policy['min_confidence']}")

        # (3) Critical phases/actions
        if self._batch_contains_auth(command_batch):
            reasons.append("auth_action")
        if phase == "payment" or self._batch_contains_payment(command_batch):
            if self.policy.get("confirm_payment", True):
                reasons.append("payment_action")

        # (4) Spend cap (if we already know price)
        if findings and self._exceeds_spend_cap(findings, self.policy.get("spend_cap", {})):
            reasons.append("spend_cap_exceeded")

        # (5) Idempotency for destructive actions
        if self._batch_is_destructive(command_batch) and self.policy.get("require_idempotency", True):
            if not getattr(command_batch, "idempotency_key", ""):
                reasons.append("missing_idempotency_key")

        # (6) Optional risk budget (if enabled)
        if self.policy.get("risk_budget") is not None:
            budget = int(self.policy["risk_budget"])
            if cumulative_risk > budget:
                reasons.append("risk_budget_exceeded")

        return SafetyDecision(require_confirmation=bool(reasons), reasons=reasons, phase=phase)

    # ---- Helpers for orchestrator heartbeat (every N seconds) ----
    def heartbeat_seconds(self) -> int:
        return int(self.policy.get("heartbeat_seconds", 60))

    def score_phase(self, phase: str) -> int:
        weights = self.policy.get("risk_weights") or {}
        return int(weights.get(phase, 1))

    # ---- Primitive detectors ----------------------------------------------
    def _batch_contains_payment(self, batch) -> bool:
        for c in batch.commands:
            if (c.url and PAYMENT_RE.search(c.url)) or (c.selector and PAYMENT_RE.search(c.selector)):
                return True
        return False

    def _batch_contains_auth(self, batch) -> bool:
        for c in batch.commands:
            if (c.url and AUTH_RE.search(c.url)) or (c.selector and AUTH_RE.search(c.selector)):
                return True
        return False

    def _batch_is_destructive(self, batch) -> bool:
        for c in batch.commands:
            if (c.url and DESTRUCTIVE_RE.search(c.url)) or (c.selector and DESTRUCTIVE_RE.search(c.selector)):
                return True
        return False

    def _domain_denied(self, url: str) -> bool:
        host = (url or "").lower()
        denies = self.policy.get("deny_domains") or []
        return any(d in host for d in denies)

    def _domain_not_allowed(self, url: str) -> bool:
        host = (url or "").lower()
        allows = self.policy.get("allow_domains") or []
        return bool(allows) and not any(a in host for a in allows)

    def _exceeds_spend_cap(self, findings: Dict[str, Any], cap: Dict[str, Any]) -> bool:
        if not cap:
            return False
        try:
            cap_amt = float(cap.get("amount", 0))
            total = findings.get("cart", {}).get("total")
            if hasattr(total, "amount"):        # Money dataclass
                total_amt = float(total.amount)
            elif isinstance(total, dict):
                total_amt = float(total.get("amount", 0))
            else:
                total_amt = float(total or 0)
            return total_amt > cap_amt
        except Exception:
            return False