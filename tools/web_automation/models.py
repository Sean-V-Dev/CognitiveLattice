# tools/web_automation/models.py
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Literal, Any

# ---- Tiny “enums” (type-safe strings) ----
ActionType = Literal["navigate", "wait_for", "click", "type", "select", "press"]
AssertType = Literal["exists", "clickable", "region_changed", "cart_contains", "price_total"]

# ---- Context passed into the planner for this turn/step ----
@dataclass
class ContextPacket:
    """What the planner needs to decide the next action batch."""
    session_id: str                  # your lattice session id
    goal: str                        # high-level user goal ("order chipotle bowl")
    url: str                         # canonical site URL
    step: int                        # which step of the plan we’re on (1,2,3…)
    dom_snapshot: str                # raw/normalized DOM string (or a handle to it)
    page_sig: str                    # page-level signature (for replay vs probe)
    regions: List[Dict[str, Any]]    # region-level signatures/metadata
    recipes: Dict[str, Any] = field(default_factory=dict)   # candidate cached recipe (if any)
    memory: Dict[str, Any] = field(default_factory=dict)    # user prefs (e.g., protein=chicken)
    policy: Dict[str, Any] = field(default_factory=dict)    # autonomy_steps, confirm_payment, etc.

# ---- One atomic browser command (planner -> executor) ----
@dataclass
class Command:
    """One concrete browser action."""
    type: ActionType
    selector: Optional[str] = None   # CSS/XPath/role-text selector (if applicable)
    url: Optional[str] = None        # for navigate
    text: Optional[str] = None       # for type
    key: Optional[str] = None        # for press (e.g., "Enter", "Tab", "Escape")
    enter: Optional[bool] = None     # press Enter after typing?

# ---- A batch of commands with guards (pre/post) ----
@dataclass
class CommandBatch:
    """A small batch of actions with safety checks and pacing."""
    commands: List[Command] = field(default_factory=list)
    preconditions: List[Dict[str, Any]] = field(default_factory=list)   # e.g., [{"assert":"exists","selector":"..."}]
    postconditions: List[Dict[str, Any]] = field(default_factory=list)  # e.g., [{"assert":"region_changed","region":"builder"}]
    idempotency_key: str = ""       # unique key so we don’t double-charge / double-submit
    human_pacing: Dict[str, int] = field(default_factory=lambda: {"min_ms": 120, "max_ms": 480})

# ---- DOM Processing Models ----
@dataclass
class Element:
    """An interactive element extracted from the DOM."""
    tag: str
    text: str
    attrs: Dict[str, str] = field(default_factory=dict)
    selectors: List[str] = field(default_factory=list)  # first is primary
    score: float = 0.0

@dataclass
class PageContext:
    """Complete page context for LLM reasoning."""
    url: str
    title: str
    raw_dom: str
    skeleton: str
    signature: str
    interactive: List[Element] = field(default_factory=list)

# ---- What the executor/verifier reports back after running a batch ----
@dataclass
class Evidence:
    """Outcome of executing a CommandBatch."""
    success: bool
    dom_after_sig: str                              # Page signature after execution
    # Nice to have so Evidence is self-contained (fallback to ctx.page_sig if None):
    dom_before_sig: Optional[str] = None

    regions_after: List[Dict[str, Any]] = field(default_factory=list)   # Updated regions if you compute them
    findings: Dict[str, Any] = field(default_factory=dict)              # Structured results (cart, price, store, etc.)

    used_selector: Optional[str] = None           # Which selector actually worked
    fallback_used: bool = False                   # Did we use backup selectors?

    timing_ms: int = 0                            # How long execution took
    errors: List[str] = field(default_factory=list)  # Non-fatal errors/warnings encountered

    # Optional: store the detailed outcomes of each postcondition assertion
    postcondition_results: List[Dict[str, Any]] = field(default_factory=list)

    # If you ever capture a screenshot or evidence artifacts:
    screenshot_path: Optional[str] = None         # e.g., for debugging/demo (keep as a path, not bytes)

# ---- (Optional) Helper for money so you never parse strings like "$12.97" again ----
@dataclass
class Money:
    amount: float
    currency: str = "USD"
