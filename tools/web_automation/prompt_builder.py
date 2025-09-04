from typing import List, Dict, Any, Optional
from .models import PageContext, CommandBatch, Command

# Hard caps to keep prompts small and deterministic
MAX_SKELETON_CHARS = 0
MAX_CANDIDATES = 50
MAX_SEL_PER_CANDIDATE = 3

SYSTEM_INSTRUCTIONS = (
    "You are an intelligent web-navigation planner with access to recent memory, state tracking, and breadcrumb context. "
    "Given a goal, DOM skeleton, ranked candidates, and progress history, return 1-3 JSON commands "
    "that make concrete progress toward the goal. "
    
    "CONTEXTUAL AWARENESS: You have access to breadcrumb progress that shows what actions you've already completed. "
    "Use this context to understand where you are in the workflow and what the next logical step should be. "
    "Pay attention to DOM signature changes and success/failure patterns from recent actions. "
    
    "SELECTION POLICY "
    
    "TOP-10 GATE (HARD): "
    "- You MUST choose from the top 10 candidates unless an OVERRIDE is justified. "
    
    "GOAL LEXICON (derive per step): "
    "- Extract target nouns from the goal (things to click/select), plus 2–6 common UI variants. "
    "- Extract verbs and qualifiers (filters, ingredients, dates…). "
    
    "DISQUALIFIERS (reject unless explicitly requested by the goal): "
    "- Marketing/hero/promo copy (e.g., \"limited time\", \"featured\", \"join\", \"rewards\", \"order now\"). "
    "- Group/catering/corporate language (e.g., \"for X–Y people\", \"$ per person\"). "
    "- Prebuilt/lifestyle/celebrity items if the goal is custom building (e.g., \"Lifestyle Bowl\", \"The ___ Bowl\"). "
    
    "PREFERENCES (apply within top-5): "
    "1) GOAL-NOUN FIRST: Prefer candidates whose TEXT or ATTRIBUTES contain a target noun or its variants. "
    "2) SEMANTIC SELECTORS over decorative containers: "
    "   Strong: [data-*], [role], [aria-*], clear text with goal noun. "
    "   Weak: generic containers (hero/top-level-menu/card/paragraph) or empty text. "
    "3) STEP-COST: Prefer the option most likely to land on the next expected state with the fewest steps. "
    "4) DE-LOOP: Do not repeat selectors that recently failed (see breadcrumbs). "
    
    "OVERRIDE (RARE): "
    "- Only if no top-5 candidate matches the goal lexicon nouns OR all such matches are disqualified. "
    "- If you override, include `override_reason` citing ≥2 concrete signals (e.g., \"no noun match in top-5; candidate has data-button + exact noun variant\"). "

    "OUTPUT: "
    "- Return 1–3 JSON commands. Each must include a `why` citing: (a) goal-noun match, (b) semantic selector evidence, (c) disqualifiers avoided. "
    "- Include `override_reason` if outside top-5. "

    "CYCLE PREVENTION: If breadcrumbs or recent actions show you've tried the same element multiple times, "
    "DO NOT repeat that action. Look for alternative approaches: different selectors, waiting for dynamic content, "
    "or navigating to different areas of the page. "
    
    "SEARCH PATTERNS: When looking for search fields, prioritize: input[type=search], input[name*='zip'|'postal'], "
    "input[placeholder*='ZIP'|'location'], [aria-label*='search'|'location'], [role='textbox']. "
    
    "TYPING PROTOCOL: Always follow 'type' with 'press Enter' for search fields and forms. "
    "This is the standard web pattern for Google, YouTube, location search, etc. "
    
    "DYNAMIC CONTENT: If you click a button that should reveal content but don't see expected elements, "
    "the content may be loading. Try different selectors or consider that the click triggered a modal/dropdown. "
    
    "CONSTRAINTS: Avoid login/rewards/marketing unless explicitly needed. Focus on the core goal. "
    "If no relevant elements are visible, click elements that reveal the functionality you need. "
    
    "PROGRESS VERIFICATION: Use DOM signature changes as evidence of successful actions. "
    "If signature unchanged after action, try a different approach. Use your breadcrumb context to avoid repeating unsuccessful strategies."
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
        "rationale": {"type": "string"},
        "breadcrumb": {
            "type": "string", 
            "description": "Plain English note for your future self about what you just accomplished in this step. Be brief but clear enough to understand the progress made."
        }
    },
    "required": ["commands"],
    "additionalProperties": False
}


def _build_recent_state_context(page_context: PageContext) -> str:
    """Build context from recent lattice events and step history."""
    context_parts = []
    
    # Current step tracking
    if hasattr(page_context, 'current_step') and hasattr(page_context, 'total_steps'):
        context_parts.append(f"STEP {page_context.current_step} of {page_context.total_steps}")
    
    # Recent events from lattice (last 3-5 for relevance)
    if hasattr(page_context, 'recent_events') and page_context.recent_events:
        context_parts.append("RECENT ACTIONS:")
        clicked_elements = []  # Track what we've clicked for cycle detection
        
        for i, event in enumerate(page_context.recent_events[-5:], 1):
            # Extract key info from lattice events
            if isinstance(event, dict):
                action_type = event.get('type', 'unknown')
                action_data = event.get('data', {})
                
                # Handle web step events
                if action_type == 'web_step_completed':
                    step_num = action_data.get('step_number', i)
                    step_desc = action_data.get('step_description', 'unknown step')
                    success = action_data.get('success', False)
                    status = "✓" if success else "✗"
                    context_parts.append(f"  {step_num}. {status} {step_desc}")
                    
                    # Extract actual commands executed
                    result = action_data.get('result', {})
                    if isinstance(result, dict):
                        commands = result.get('commands_executed', [])
                        for cmd in commands:
                            if isinstance(cmd, dict):
                                cmd_type = cmd.get('type', 'unknown')
                                selector = cmd.get('selector', '')[:40]  # Truncate long selectors
                                if cmd_type == 'click' and selector:
                                    clicked_elements.append(selector)
                                    context_parts.append(f"       → clicked: {selector}")
                                elif cmd_type == 'type':
                                    text = cmd.get('text', '')[:20]
                                    context_parts.append(f"       → typed: {text} in {selector}")
                
                # Handle direct action events  
                elif action_type == 'action':
                    action_name = action_data.get('action', 'unknown')
                    selector = action_data.get('selector', '')[:40]  # Truncate long selectors
                    if action_name == 'click' and selector:
                        clicked_elements.append(selector)
                    context_parts.append(f"  {i}. {action_name}: {selector}")
                    
                elif action_type == 'navigation':
                    url = action_data.get('url', '')
                    context_parts.append(f"  {i}. Navigate to: {url}")
        
        # Cycle detection warning
        if clicked_elements:
            unique_clicks = set(clicked_elements)
            if len(clicked_elements) > len(unique_clicks):
                context_parts.append("⚠️  CYCLE DETECTED: Same elements clicked multiple times!")
                for selector in unique_clicks:
                    count = clicked_elements.count(selector)
                    if count > 1:
                        context_parts.append(f"    - '{selector}' clicked {count} times - try different approach!")
    
    # Previous DOM signature for change detection
    if hasattr(page_context, 'previous_dom_signature'):
        context_parts.append(f"PREV DOM SIGNATURE: {page_context.previous_dom_signature}")
    
    return "\n".join(context_parts) if context_parts else ""


def _build_affordance_hints(goal: str) -> str:
    """Build goal-specific affordance hints for common web patterns."""
    goal_lower = goal.lower()
    
    hints = []
    
    # Location/ZIP search patterns
    if any(term in goal_lower for term in ['location', 'zip', 'postal', 'address', 'store', 'find']):
        hints.extend([
            "LOCATION SEARCH HINTS:",
            "- Look for: input[type=search], input[name*='zip'], input[placeholder*='ZIP/location']",
            "- ARIA patterns: [aria-label*='search'|'location'|'zip'], [role='textbox']",
            "- Button triggers: 'Find Store', 'Store Locator', 'Locations', 'Find Location'",
            "- Common IDs: #store-locator, #zip-search, #location-input"
        ])
    
    # Search functionality
    if 'search' in goal_lower:
        hints.extend([
            "SEARCH HINTS:",
            "- Primary: input[type=search], input[name*='search']",
            "- Secondary: input[placeholder*='search'], .search-input",
            "- Always press Enter after typing in search fields"
        ])
    
    # Navigation patterns
    if any(term in goal_lower for term in ['menu', 'navigate', 'go to']):
        hints.extend([
            "NAVIGATION HINTS:",
            "- Look for: nav elements, [role='navigation'], .menu, .nav",
            "- Mobile: button[aria-label*='menu'], .hamburger, .menu-toggle"
        ])
    
    return "\n".join(hints) if hints else ""


def _build_delta_verification(page_context: PageContext) -> str:
    """Build verification signals for checking progress."""
    signals = [
        "PROGRESS VERIFICATION:",
        "- DOM signature changes indicate successful actions",
        "- URL changes suggest navigation progress", 
        "- New form elements appearing = successful reveal actions",
        "- If signature unchanged after action, try different approach",
        "- If signature changed but no search field appears, look for modals/dropdowns/dynamic content"
    ]
    
    # Add current signature for comparison
    if hasattr(page_context, 'dom_signature'):
        signals.append(f"- Current DOM signature: {page_context.dom_signature}")
    
    # Add specific cycle detection guidance
    if hasattr(page_context, 'recent_events') and page_context.recent_events:
        # Check for repeated clicks in recent events
        clicked_selectors = []
        for event in page_context.recent_events[-3:]:  # Last 3 events
            if isinstance(event, dict):
                action_data = event.get('data', {})
                if isinstance(action_data, dict):
                    result = action_data.get('result', {})
                    if isinstance(result, dict):
                        commands = result.get('commands_executed', [])
                        for cmd in commands:
                            if isinstance(cmd, dict) and cmd.get('type') == 'click':
                                clicked_selectors.append(cmd.get('selector', ''))
        
        # Add cycle warning
        if clicked_selectors:
            unique_selectors = set(filter(None, clicked_selectors))  # Remove empty strings
            if len(clicked_selectors) > len(unique_selectors):
                signals.append("⚠️ CYCLE WARNING: Avoid clicking elements that were recently clicked")
                signals.append("- Try different selectors or look for alternative interaction patterns")
    
    return "\n".join(signals)


def _build_lattice_guidance(page_context: PageContext) -> str:
    """Build guidance from cognitive lattice for next logical steps."""
    guidance_parts = []
    
    # Check if we have lattice data available
    if hasattr(page_context, 'lattice_state') and page_context.lattice_state:
        lattice_state = page_context.lattice_state
        
        # Expected next steps from planning
        if 'planned_steps' in lattice_state and 'current_step_index' in lattice_state:
            current_idx = lattice_state['current_step_index']
            planned_steps = lattice_state['planned_steps']
            
            if current_idx < len(planned_steps):
                current_plan = planned_steps[current_idx]
                guidance_parts.append(f"LATTICE GUIDANCE: {current_plan}")
            
            # Show next planned step for context
            if current_idx + 1 < len(planned_steps):
                next_plan = planned_steps[current_idx + 1]
                guidance_parts.append(f"NEXT PLANNED: {next_plan}")
        
        # Success patterns from memory
        if 'successful_patterns' in lattice_state:
            patterns = lattice_state['successful_patterns']
            if patterns:
                guidance_parts.append("SUCCESSFUL PATTERNS:")
                for pattern in patterns[-3:]:  # Last 3 successful patterns
                    guidance_parts.append(f"  - {pattern}")
    
    return "\n".join(guidance_parts) if guidance_parts else "LATTICE: No specific guidance available"


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


def build_reasoning_prompt(goal: str, ctx: PageContext, recent_actions: List[Dict[str, Any]] | None = None, breadcrumbs: List[str] | None = None) -> str:
    """Assemble a rich, context-aware planning prompt with lattice integration."""
    recent_actions = recent_actions or []
    breadcrumbs = breadcrumbs or []
    skeleton = (ctx.skeleton or "")[:MAX_SKELETON_CHARS]
    candidates = _shape_candidates(ctx)

    lines: List[str] = []
    lines.append("System:\n" + SYSTEM_INSTRUCTIONS)
    
    # Enhanced goal section with affordance hints
    lines.append("--- Goal ---\n" + goal.strip())
    affordance_hints = _build_affordance_hints(goal)
    if affordance_hints:
        lines.append("--- " + affordance_hints.split(':')[0] + " ---\n" + affordance_hints)
    
    # Recent state and memory context
    recent_context = _build_recent_state_context(ctx)
    if recent_context:
        lines.append("--- Recent State ---\n" + recent_context)
    
    # Lattice guidance for next logical steps
    lattice_guidance = _build_lattice_guidance(ctx)
    lines.append("--- " + lattice_guidance.split(':')[0] + " ---\n" + lattice_guidance)
    
    # Progress verification guidance
    delta_verification = _build_delta_verification(ctx)
    lines.append("--- " + delta_verification.split(':')[0] + " ---\n" + delta_verification)
    
    # Current page state
    lines.append(f"--- Page State ---\nURL: {ctx.url}\nTitle: {ctx.title}\nSignature: {ctx.signature}")
    
    # DOM skeleton
    lines.append("--- DOM Skeleton (truncated) ---\n" + skeleton)
    
    # Ranked candidates with discipline reminders
    lines.append("--- Ranked Candidates (USE THESE SELECTORS) ---")
    for i, c in enumerate(candidates, 1):
        sels = ", ".join(c["selectors"])
        text = c["text"] or ""
        lines.append(f"{i}. <{c['tag']}> score={c['score']} text=\"{text}\" selectors=[{sels}]")
    
    # Progress breadcrumbs (plain English summary)
    if breadcrumbs:
        lines.append("--- Progress So Far ---")
        for breadcrumb in breadcrumbs[-5:]:  # Last 5 breadcrumbs
            lines.append(f"✅ {breadcrumb}")
    
    # Legacy recent actions (if any)
    if recent_actions:
        lines.append("--- Legacy Recent Actions ---")
        for a in recent_actions[-3:]:  # Reduced to 3 since we have richer context now
            lines.append(f"- {a}")
    
    # Constraints and stop conditions
    lines.append("--- Constraints ---")
    lines.append("- Do NOT click login/rewards/marketing unless explicitly required")
    lines.append("- Focus ONLY on location search functionality") 
    lines.append("- If no search field visible, click elements that reveal search boxes")
    lines.append("- DO NOT repeat actions from recent history - avoid clicking same elements")
    lines.append("- If stuck in a loop, try: different selectors, navigation links, or wait commands")
    lines.append("- STOP if goal is achieved or clearly impossible")
    
    # Compact goal restatement for focus
    lines.append("--- Goal Restatement ---")
    lines.append(f"PRIMARY OBJECTIVE: {goal.strip()}")
    
    # Response format with examples
    lines.append("--- Respond ---\n"
                 "Return ONLY valid JSON with these exact fields:\n"
                 "{\n"
                 '  "commands": [{"type": "type", "selector": "input[name=search]", "text": "45305"}, {"type": "press", "key": "Enter"}],\n'
                 '  "confidence": 0.8,\n'
                 '  "rationale": "Found search input from candidate #3, typing ZIP and pressing Enter per web standard",\n'
                 '  "breadcrumb": "Entered ZIP code 45305 into location search field"\n'
                 "}\n"
                 "INTELLIGENT SELECTION: Don't j.\n"
                 "TYPING PROTOCOL: Always follow 'type' with 'press Enter' for search fields.\n"
                 "BREADCRUMB: Write a brief note for your future self about what you just accomplished. "
                 "Keep it simple: 'Selected Burrito Bowl', 'Added chicken protein', 'Entered ZIP 45305', etc. "
                 "This helps maintain context across the ordering workflow.\n"
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
