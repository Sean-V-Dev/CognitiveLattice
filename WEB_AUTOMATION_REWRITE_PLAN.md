## 🎯 Goal
Replace the complex web automation with a simple, focused system that follows your exact workflow:
```
User Intent → Create Plan → Navigate → DOM Skeleton → LLM Reasoning → Press Button → DOM Diff → Repeat → Update Lattice
```

## 📁 File Structure & Responsibilities

```
tools/web_automation/
├── browser_controller.py                   # 🆕 CREATE (browser only)
├── browser_engine_tool.py
├── cognitive_lattice_web_coordinator.py    # 🔄 MODIFY (entry point)
├── dom_processor.py                        # 🆕 CREATE (DOM + skeleton)
├── lattice_logger.py
├── models.py
├── prompt_builder.py
├── safety.py
├── simple_web_agent.py                     # 🆕 CREATE (main orchestrator)
├── step_executor.py                        # 🆕 CREATE (single step execution)
└── [keep old files as backup]              # 📦 KEEP (no changes)
```

## 🔗 Call Chain Map

```
main.py
└── execute_cognitive_web_task(goal, url, external_client, cognitive_lattice)
    └── CognitiveLatticeWebCoordinator.execute_web_task()
        └── constructs SimpleWebAgent(
              llm=external_client,
              lattice=cognitive_lattice,
              browser=BrowserController(profile, headless, type),
              safety=SafetyManager(),
              logger=LatticeLogger(cognitive_lattice)
            )
            └── SimpleWebAgent.execute_task(goal, url)
                ├── browser.initialize()
                ├── browser.navigate(url)                      # first step only
                └── LOOP (until goal reached / user pause / max steps)
                    ├─ raw_dom, title = browser.get_current_dom()
                    ├─ ctx = dom_processor.create_page_context(url, title, raw_dom, goal)
                    │     • ctx = PageContext{ url, title, signature, skeleton, interactive[] }
                    │
                    ├─ prompt = prompt_builder.build_reasoning_prompt(goal, ctx, recent_actions)
                    ├─ llm_json = llm.query_json(prompt)
                    ├─ StepExecutor.reason_and_act(goal, ctx, mode, recent_actions)
                    │     ├─ parses llm_json → CommandBatch(commands[])
                    │     ├─ safety.requires_human_confirmation(batch, ctx, mode, confidence)
                    │     │     • if require_confirmation → return pause outcome
                    │     ├─ evidence = browser.execute_action_batch(CommandBatch)
                    │     │     • returns Evidence{ success, dom_after_sig, findings, timing_ms, ... }
                    │     ├─ logger.log_decision(ctx, batch, mode, rationale, confidence)
                    │     └─ logger.log_result(ctx, batch, evidence)
                    │
                    ├─ raw_dom_after, _ = browser.get_current_dom()
                    ├─ ctx_after = dom_processor.create_page_context(url, title, raw_dom_after, goal)
                    │     • compare ctx_after.signature vs ctx.signature (DOM diff proxy)
                    │
                    ├─ lattice.add_event("web_progress", { step, changed, evidence.findings }, source="web_automation")
                    ├─ if goal_reached(goal, evidence, ctx_after):
                    │     ├─ logger.log_step_completion(ctx_after, f"Completed: {goal}", evidence.timing_ms, True)
                    │     ├─ lattice.complete_task(result=..., success=True)
                    │     └─ break
                    └─ continue loop
                └── finally: browser.close(save_state=True)
```

### 🧩 Module Roles & Data Objects
- **dom_processor.py** → builds `PageContext` (skeleton + ranked `interactive`), computes `page_signature`.
- **prompt_builder.py** → formats compact prompts from `PageContext` (+ recent actions).
- **step_executor.py** → converts LLM JSON → `CommandBatch`, runs via `BrowserController`, returns `Evidence`.
- **browser_controller.py** → thin adapter over `browser_engine_tool.py`; handles navigate/click/type/press; returns DOM & `Evidence`.
- **browser_engine_tool.py** → Playwright session, **persistent profiles** (user_data_dir/storage_state), low-level ops.
- **safety.py** → gates risky actions (auth/payment/low confidence/PII/etc.).
- **lattice_logger.py** → `web_decision`, `web_execution_result`, `web_step_completed`.
- **models.py** → typed dataclasses: `PageContext`, `Element`, `Command`, `CommandBatch`, `Evidence`, etc.

### 🔄 Data Flow (per step)
`PageContext` → **prompt_builder** → LLM(JSON) → `CommandBatch` → **browser_controller** → `Evidence` → DOM re-read → new `PageContext` → lattice/logging.

## 📝 Detailed File Specifications

### 1. `models.py` (✅ COMPLETE)
**Responsibility**: Type-safe contracts for all web automation components  
**Status**: Complete with Element, PageContext, ContextPacket, Command, CommandBatch, Evidence dataclasses
**Key Features**: Typed enums, field defaults, forward references, Money dataclass for pricing

### 2. `lattice_logger.py` (✅ COMPLETE)
**Responsibility**: Single interface for all lattice logging from web automation  
**Status**: Production-ready with PII redaction, schema versioning, UTC timestamps
**Key Features**: Structured event logging, security-aware text redaction, event ID tracking

### 3. `safety.py` (✅ COMPLETE)
**Responsibility**: Risk-aware safety policies and confirmation logic  
**Status**: Complete with phase detection, confidence thresholds, spend caps
**Key Features**: Policy-driven confirmation, cumulative risk scoring, domain restrictions

### 4. `dom_processor.py` (✅ COMPLETE)
**Responsibility**: Pure DOM processing without LLM/lattice coupling  
**Status**: Surgically refactored from vision_dom_reasoner.py with all identified bugs fixed
**Key Features**: Goal-aware compression, interactive element extraction, selector generation with escaping

### 5. `prompt_builder.py` (✅ COMPLETE)
**Responsibility**: Formats compact, model-friendly planning prompts  
**Status**: Complete with proper string formatting (fixed multi-line issues)
**Key Features**: Hard caps for deterministic prompts, JSON schema validation, compact candidate shaping

### 6. `browser_controller.py` (✅ COMPLETE)
**Responsibility**: Clean wrapper around browser_engine_tool.py using new models  
**Status**: Complete with all import/reference issues fixed
**Key Features**: Type-safe browser operations, Evidence-based results, proper async handling

### 7. `step_executor.py` (✅ COMPLETE)
**Responsibility**: Single-step executor: PageContext + goal → CommandBatch → Evidence  
**Status**: Complete with proper string formatting (fixed multi-line issues)
**Key Features**: LLM integration, safety pre-checks, fallback prompt builder, lenient JSON parsing

### 8. `simple_web_agent.py` (🆕 CREATE - ~200 lines)
**Responsibility**: Main orchestrator for web automation workflow  
**Key Methods**:
```python
class SimpleWebAgent:
    def __init__(external_client, cognitive_lattice)
    async def execute_task(goal, url) -> dict
    async def create_plan(goal, url) -> list[str]
    async def execute_step(step_description, step_number) -> dict
    def update_lattice(step_info) -> None
```
**Dependencies**: Uses BrowserController, DOMProcessor, StepExecutor

### 9. `cognitive_lattice_web_coordinator.py` (🔄 MODIFY)
**Responsibility**: Entry point that main.py calls  
**Changes**: 
- Update `execute_cognitive_web_task()` to use new `SimpleWebAgent` instead of old `WebAgentCore`
- Keep same function signature (no main.py changes needed)

## 🔄 Integration Steps

### Phase 1: Create New Files
1. Create `browser_controller.py` - pure browser operations
2. Create `dom_processor.py` - DOM handling only  
3. Create `step_executor.py` - single step execution
4. Create `simple_web_agent.py` - main orchestrator

### Phase 2: Update Coordinator  
5. Modify `cognitive_lattice_web_coordinator.py` to use `SimpleWebAgent`

### Phase 3: Switch Main.py
6. Change import in `main.py` from:
   ```python
   from tools.web_automation.cognitive_lattice_web_agent import WebAgentCore, execute_cognitive_web_task
   ```
   To:
   ```python
   from tools.web_automation.cognitive_lattice_web_coordinator import execute_cognitive_web_task
   ```

### Phase 4: Test & Validate
7. Test web automation with simple case
8. If working, remove old complex files
9. If broken, revert main.py import

## 🎯 Key Design Principles

1. **Single Responsibility**: Each file does ONE thing
2. **Clear Dependencies**: No circular imports
3. **Easy Testing**: Each component can be tested independently  
4. **No Defensive Programming**: Let it fail fast, fix the real issue
5. **Explicit Call Chain**: Always clear what calls what

## 🚨 Safety Measures

- **Backup**: Old files stay untouched until new system works
- **Minimal Main.py Change**: Only one import line changes
- **Rollback Plan**: Revert import if anything breaks
- **Incremental**: Build and test each file separately

## 📊 Success Metrics

- [x] **Foundation**: Type-safe contracts and logging infrastructure
- [x] **Safety**: Risk-aware policies and confirmation logic  
- [x] **DOM Processing**: Clean skeleton extraction and element ranking
- [x] **Prompt System**: Compact, deterministic LLM prompts
- [x] **Browser Integration**: Clean wrapper with Evidence-based results
- [x] **Step Execution**: Single-step reasoning and action execution
- [x] **Orchestration**: Full workflow coordination (simple_web_agent.py)
- [x] **End-to-End**: Browser opens and navigates to URL ✅ WORKING
- [x] **API Integration**: ExternalAPIClient compatibility fixed ✅ WORKING
- [x] **Command Parsing**: Fixed Command constructor and ActionType validation ✅ WORKING
- [x] **LLM Integration**: LLM receives clean skeleton and returns action ✅ WORKING
- [x] **Action Execution**: Action executes and DOM changes ✅ WORKING
- [x] **Change Detection**: DOM diff detects change ✅ WORKING
- [x] **Lattice Updates**: Lattice gets updated with progress ✅ WORKING
- [x] **Multi-Step**: Process repeats for multiple steps ✅ WORKING
- [x] **Goal Completion**: Detect when task is successfully finished
- [x] **Resilience**: Handle overlays/modals that block interactions

## ✅ Progress Tracker

### Phase 1: Foundation Components
- [x] **models.py** - All contracts defined (Element, PageContext, Evidence, etc.)
- [x] **lattice_logger.py** - Single lattice interface with PII protection
- [x] **safety.py** - Production-grade risk-aware safety policies  
- [x] **dom_processor.py** - Pure DOM processing (extracted from vision_dom_reasoner.py)
- [x] **prompt_builder.py** - Compact LLM prompt formatting (fixed string formatting issues)

### Phase 2: Core Components  
- [x] **browser_controller.py** - Pure browser operations (fixed import/reference issues)
- [x] **step_executor.py** - Single step execution logic (fixed string formatting issues)
- [x] **simple_web_agent.py** - Main orchestrator

### Phase 3: Integration
- [x] Update **cognitive_lattice_web_coordinator.py** - Fixed CognitiveLattice API compatibility
- [ ] **resilience.py** - Popup/modal handling (future enhancement)
- [x] **API Integration** - Ready for testing with correct method signatures

### Phase 4: Cleanup
- [x] Remove old complex files
- [x] Validation testing

## 🚀 Implementation Order

1. ✅ **Foundation**: `models.py`, `lattice_logger.py`, `safety.py` (complete)
2. ✅ **DOM Processing**: `dom_processor.py` (surgically refactored, complete)
3. ✅ **Prompt System**: `prompt_builder.py` (complete, string formatting fixed)
4. ✅ **Browser Layer**: `browser_controller.py` (complete, import issues fixed)
5. ✅ **Step Logic**: `step_executor.py` (complete, string formatting fixed)
6. 🔄 **Next**: `simple_web_agent.py` (orchestration) - **READY TO CREATE**
7. 🔄 **Then**: Update coordinator and main.py import

---