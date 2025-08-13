# CognitiveLattice Web Automation Agent (Dynamic Web Agent Roadmap)

## Objective
Dynamic autonomous web agent that can execute multi-step goals (e.g., place an order) by reasoning over live DOM + visual context—without site-specific code.

## Core Components
1. Browser Engine (DONE): Pure primitives (init, navigate, click, type, screenshot, dom, close).
2. Vision / DOM Reasoner: Compresses DOM + pairs with screenshot → LLM proposes actions.
3. AI Web Agent Orchestrator: Implements Observe → Reason → Act → Verify loop per lattice step.
4. Order / Intent Parser (generic): Turns user natural language into structured goal context (brand, product type, constraints) but does not map to selectors.
5. Payment Stub (optional, later): Simulated confirmation layer (never auto-executes without user confirmation).

## Planned Step Loop (per lattice step)
1. Fetch current active step from lattice.
2. Gather observations:
   - url, title
   - screenshot path
   - compressed_dom (token-limited structural summary)
   - prior semantic element memory (if any)
3. Reason (LLM prompt): "Given goal: {step_goal} and observations, propose minimal safe actions."
4. Execute actions sequentially (primitive tool).
5. Re-observe & verify (LLM yes/no + confidence).
6. Store results in lattice: node type=web_step (status, actions, verification, artifacts).
7. If verified → advance step; else → retry strategy or request user clarification.

## Memory Artifacts Stored in Lattice
- element_fingerprints: {selector / text / role / hash → semantic_label}
- successful_action_patterns
- failures (selector, error, timestamp)
- last_dom_signature (hash for change detection)

## Generic Example Task Plan (Order Food)
1. Identify target platform (infer domain or search if missing).
2. Reach actionable start (accept cookies / dismiss modals).
3. Locate location-or-fulfillment control (pickup/delivery) using ZIP/postal context.
4. Confirm location selected (LLM verifies UI state change).
5. Navigate to desired product category (e.g., "bowl" inferred, no hardcoded selector).
6. Configure product (map natural language components to available toggles).
7. Open / view cart or summary (verify items + pricing).
8. Present summary to user for explicit confirmation.
9. (Optional) Payment authorization (stub until real integration).
10. Final confirmation + lattice closure.

## File Structure (Revised)
```
tools/
  web_automation/
    browser_engine_tool.py         # primitives
    ai_web_agent_tool.py           # orchestrator
    vision_dom_reasoner.py         # reasoning layer (LLM calls)
    order_intent_parser.py         # generic intent → structured goal context
    payment_stub_tool.py           # optional confirmation/pay stub
memory/
  web_semantic_cache.json          # persisted element semantics (if enabled)
```

## Phases
Phase 1: Reasoner + Orchestrator skeleton; run a single goal "navigate to https://chipotle.com".
Phase 2: Add location selection step (generic reasoning, no fixed selectors).
Phase 3: Add product configuration loop (match user ingredients to DOM-discovered tokens).
Phase 4: Verification & confirmation gating.
Phase 5: Robust retries, memory consolidation, and multi-site tests.

## Key Constraint
No static selector constants tied to a brand. All selectors emerge from runtime reasoning over current DOM + screenshot.




## additional gaps to close on roadmap as identified by gpt 5 ##

Add verification gating before advancing lattice step
Where: cognitive_lattice_web_agent.py
Do: after actions + DOM diff, call a verify function (llm or rules-based) to confirm the step_goal result (e.g., “location selected”, “menu visible”).
Store: lattice node = web_step {verified: true/false, signals, dom_change_type, artifacts}.
If not verified: apply retry strategy, then ask for clarification if still failing.
Persist semantic element memory (agnostic selectors)
File: memory/web_semantic_cache.json as in the roadmap.
Shape:
element_fingerprints: [{domain, semantic_label, text_patterns, role, attrs, candidate_selectors[], last_seen_dom_hash, confidence}]
successful_action_patterns, failures, last_dom_signature
Where to integrate:
observe(): merge current DOM hints with cached memory for the same domain.
Reasoner prompt: include memory slice relevant to current step.
After successful actions: upsert/update fingerprints and successful patterns.
Standardize the agent I/O contracts
Observation payload to LLM:
{url, title, dom_signature, compressed_dom, screenshot_path, known_elements[], lattice_progress{current_step_index, completed, next_step}}
Reasoner output:
{reasoning, actions: [{type, selectors[], text?, wait_for?, rationale}], verify: {expected_indicators[], success_criteria}}
Lattice web_step node:
{step_id, goal, actions, action_results, dom_analysis, verified, signals, artifacts, timestamp}
Enforce: parse strictly and guard against non-JSON responses.
Retry and recovery policy (site-agnostic)
Modal handling heuristics (buttons: accept/agree/close/got it/continue; roles: dialog; aria-labels).
Navigation assertions (url change, title change, key element visibility).
Exponential backoff up to N attempts, then fallback to alternative CTA patterns (e.g., synonyms for “order”, “start”, “menu”, “find location”).
Expand cross-site tests (prove generality)
Cookie/consent modal suite across 3–5 domains.
Generic “find the search box and query” tasks (Wikipedia, a news site).
“Locate/store selector” pattern for “location/fulfillment” across at least two retailers (ZIP entry).
Ensure no hardcoded brand selectors.
Make model config explicit and switchable
External API client: allow model override per call with fallback (gpt-5-mini → 4o-mini).
Timeouts, temperature, and response_format JSON enforcement.
Observability and artifacts
Save screenshot per step and link path in lattice node.
Keep DOM signature/hash history per step in dom_history.
Log structured events only (you already use add_event).
Where to implement

Verification: cognitive_lattice_web_agent.py in execute_plan_with_monitoring() right after DOM analysis (use llm_verify if available, else add it).
Memory: load/save JSON in a small helper; use in observe() and after successful actions.
Reasoner prompt: vision_dom_reasoner.py to include lattice progress and memory snippets.
Lattice: continue using create_new_task(query, task_plan), get_active_task(), execute_step(...), add_event(...), save().
Suggested immediate next steps

Add verify() and gate advancing steps only on verified=true.
Introduce memory store with element_fingerprints and wire into observe() and prompts.
Add two non-Chipotle tests: cookie consent dismissal on another site; generic search-box find-and-type.
Parameterize model in ExternalAPIClient and wire through the agent for quick switching.
This keeps the agent fully agnostic: selectors emerge from runtime reasoning over DOM+screenshot, guided by lattice progress and accumulated semantic memory, not site-specific code.