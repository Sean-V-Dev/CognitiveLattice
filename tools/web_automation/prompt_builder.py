from typing import List, Dict, Any
from .models import PageContext, CommandBatch, Command

# Hard caps to keep prompts small and deterministic
MAX_SKELETON_CHARS = 4000
MAX_CANDIDATES = 30
MAX_SEL_PER_CANDIDATE = 3

SYSTEM_INSTRUCTIONS = (
    "You are a web-navigation planner. "
    "Given a goal, a DOM skeleton, and ranked action candidates, return 1-3 JSON commands "
    "that make concrete progress toward the goal. Use only provided selectors if possible. "
    "IMPORTANT: When typing into search fields, input boxes, or forms, always follow the 'type' command "
    "immediately with a 'press' command with 'key': 'Enter' - this is the standard web pattern. "
    "Most sites (Google, YouTube, etc.) expect Enter after typing, not clicking submit buttons. "
    "CLICKING: For elements with text content (buttons, links, spans with role='link'), use 'click' commands. "
    "Prefer the highest-scoring candidates that match your goal. Ignore accessibility/usability helpers unless specifically needed."
)

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "commands": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["click", "type", "press", "navigate"]},
                    "selector": {"type": ["string", "null"]},
                    "text": {"type": ["string", "null"]},
                    "url": {"type": ["string", "null"]},
                    "key": {"type": ["string", "null"]}
                },
                "required": ["type"],
                "additionalProperties": False
            }
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "rationale": {"type": "string"}
    },
    "required": ["commands"],
    "additionalProperties": False
}


def _shape_candidates(ctx: PageContext) -> List[Dict[str, Any]]:
    shaped = []
    for el in ctx.interactive[:MAX_CANDIDATES]:
        shaped.append({
            "tag": el.tag,
            "text": el.text,
            "score": round(getattr(el, "score", 0.0), 3),
            "selectors": el.selectors[:MAX_SEL_PER_CANDIDATE]
        })
    return shaped


def build_reasoning_prompt(goal: str, ctx: PageContext, recent_actions: List[Dict[str, Any]] | None = None) -> str:
    """Assemble a compact, model-friendly planning prompt."""
    recent_actions = recent_actions or []
    skeleton = (ctx.skeleton or "")[:MAX_SKELETON_CHARS]
    candidates = _shape_candidates(ctx)

    lines: List[str] = []
    lines.append("System:\n" + SYSTEM_INSTRUCTIONS)
    lines.append("--- Goal ---\n" + goal.strip())
    lines.append(f"--- Page ---\nURL: {ctx.url}\nTitle: {ctx.title}\nSignature: {ctx.signature}")
    lines.append("--- DOM Skeleton (truncated) ---\n" + skeleton)
    lines.append("--- Ranked Candidates ---")
    for i, c in enumerate(candidates, 1):
        sels = ", ".join(c["selectors"])
        text = c["text"] or ""
        lines.append(f"{i}. <{c['tag']}> score={c['score']} text=\"{text}\" selectors=[{sels}]")
    if recent_actions:
        lines.append("--- Recent Actions ---")
        for a in recent_actions[-5:]:  # last 5 only
            lines.append(f"- {a}")
    # Guidance + schema hint
    lines.append("--- Respond ---\n"
                 "Return ONLY valid JSON with these exact fields:\n"
                 "{\n"
                 '  "commands": [{"type": "type", "selector": "input[name=search]", "text": "45305"}, {"type": "press", "key": "Enter"}],\n'
                 '  "confidence": 0.8,\n'
                 '  "rationale": "typing search term and pressing Enter (standard web pattern)"\n'
                 "}\n"
                 "Use only provided selectors when possible. Prefer high-score candidates.\n"
                 "Limit commands to 1–3. Do not include any text outside the JSON.")
    return "\n\n".join(lines)


def build_verification_prompt(goal: str, ctx_before: PageContext, ctx_after: PageContext, attempted: CommandBatch) -> str:
    """Optional: Ask model to verify whether the attempted commands progressed the goal."""
    lines: List[str] = []
    lines.append("System: You verify progress after actions. Be strict and concise.")
    lines.append("--- Goal ---\n" + goal.strip())
    lines.append(f"--- Before Signature ---\n{ctx_before.signature}")
    lines.append(f"--- After Signature ---\n{ctx_after.signature}")
    lines.append("--- Attempted Commands ---")
    for c in attempted.commands:
        lines.append(f"- {c.type} {c.selector or c.key or c.url or c.text}")
    lines.append("--- Respond ---\n"
                "Say one sentence about progress, then return a JSON: {\"progress\": true|false, \"reason\": str}.")
    return "\n\n".join(lines)
