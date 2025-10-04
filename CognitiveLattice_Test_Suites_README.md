# CognitiveLattice Test Suites

## Overview
This archive contains comprehensive test suites demonstrating the **CognitiveLattice web automation system** executing end-to-end workflows on Chipotle.com. Each suite validates the agent's ability to complete complex multi-step tasks using only natural language prompts—no hardcoded scripts, selectors, or pre-defined workflows.

> **Archive Information**  
> All test results are packaged in `CognitiveLattice_E2E_Acceptance_Suite_Tests.zip` (65MB compressed, 730MB uncompressed).  
> The archive contains complete documentation for 100 test runs with full audit trails, cognitive lattice states, DOM debug files, and AI decision logs.

### Key Capabilities Demonstrated
- **100% prompt-driven automation** (no hardcoded selectors)
- **Cognitive lattice reasoning** for multi-step task decomposition
- **Real-time DOM analysis** and intelligent element selection
- **Complete audit trails** for every decision and action
- **High reliability** across diverse order configurations

---
## Technical Achievement Context

### Why 100% Success Rate Matters
Traditional web automation fails on modern SPAs due to:
- Dynamic content loading
- Changing DOM structures  
- Complex multi-step workflows
- Inconsistent element identifiers

CognitiveLattice solves these through:
- Real-time DOM analysis (no hardcoded selectors)
- Goal-aware element scoring
- Cognitive state management across steps
- Natural language task decomposition

---

## Test Suite Categories
The following test suites are included, each targeting different complexity levels:

| Suite Name | Tests | Focus Area | Complexity |
|------------|-------|------------|------------|
| `simple_bowl_soak_tests_40x` | 40 | Basic bowl orders | Low |
| `complex_bowl_tests_10x` | 10 | Advanced bowl customization | High |
| `complex_burrito_tests_10x` | 10 | Burrito with multiple ingredients | High |
| `complex_salad_tests_10x` | 10 | Salad with custom toppings | High |
| `complex_tacos_tests_10x` | 10 | Multi-taco orders | High |
| `bowl_with_extra_meat_10x` | 10 | Double protein configurations | Medium |
| `bowl_with_side_items_tests_10x` | 10 | Orders with sides and drinks | Medium |

---

## Archive Structure

This section describes the folder and file layout for each test suite.

### Suite Folder Layout
```
CognitiveLattice_E2E_Acceptance_Suite_Tests/
├── complex_bowl_tests_10x/
│   ├── chipotle_bulk_test_results_YYYYMMDD_HHMMSS.json  # Suite summary
│   ├── run_YYYYMMDD_HHMMSS_######/                     # Individual test run
│   └── ... (10 total runs)
└── [other test suites...]
```

### Suite Summary File (`bulk_test_results.json`)
Each suite contains a comprehensive summary with performance metrics:

```json
{
  "test_summary": {
    "total_tests": 10,
    "successful_tests": 10,
    "failed_tests": 0,
    "success_rate": 100.0,
    "average_duration_seconds": 188.07,
    "min_duration_seconds": 184.73,
    "max_duration_seconds": 194.15,
    "total_steps": 110,
    "completed_steps": 110,
    "step_success_rate": 100.0,
    "test_prompt": "Build me a bowl with chicken (double), white rice, black beans...",
    "test_url": "https://chipotle.com",
    "timestamp": "2025-09-29_173950"
  },
  "individual_test_results": [
    {
      "test_number": 1,
      "start_time": "2025-09-29 17:39:50",
      "end_time": "2025-09-29 17:43:04",
      "duration_seconds": 194.15,
      "prompt": "...",
      "total_steps": 11,
      "completed_steps": 11,
      "success_rate": 100.0,
      "final_result": "SUCCESS"
    }
    // ... additional test records
  ]
}
```

---

## Individual Test Run Contents
Each `run_YYYYMMDD_HHMMSS_######/` folder contains a complete audit trail:

### Cognitive Lattice States
- **`cognitive_lattice_interactive_session_YYYYMMDD_HHMMSS.json`** – Complete lattice evolution
- **`lattice_state_after_step[N].json`** – Progressive snapshots after each step

### DOM Analysis & Debugging
- **`dom_debug_step[N]_YYYYMMDD_HHMMSS_###.txt`** – DOM selector candidates for action steps
- Contains both raw element lists and goal-sorted selector rankings
- Only generated when the agent needed to interact with page elements

### Page State Tracking
- **`page_state_step[N].txt`** – URL and navigation state after each step
- Tracks all page transitions within the Chipotle.com domain

### AI Prompts & Responses
#### Action Steps:
- **`web_prompt_step[N]of[TOTAL]_pass1_YYYYMMDD_HHMMSS_######.txt`** – Prompts with top-10 DOM selector candidates
- **`web_response_step[N]of[TOTAL]_YYYYMMDD_HHMMSS_######.txt`** – Agent's selector choice + reasoning
#### Observation Steps:
- **`observation_prompt_step[N]_YYYYMMDD_HHMMSS_######.txt`** – Non-action queries for verification
- **`observation_response_step[N]_YYYYMMDD_HHMMSS_######.txt`** – Agent's analysis responses
- Used for confirming ingredient selections, prices, and order totals

### Audit Documentation
- **`RUN_SUMMARY_AUDIT_TRAIL.md`** – Complete test run documentation including:
  - File inventory & verification instructions
  - System environment details
  - Notes on candidate disclosure
  - Task objectives & executive summary

---

## How to Navigate the Test Results
This section explains how to use the results for quick review or deep analysis.

### Quick Performance Review
1. **Start with `bulk_test_results.json`** for high-level suite metrics
2. **Check `individual_test_results[]`** for per-run breakdowns
3. **Look for patterns** in duration, step counts, and success rates

### Deep Dive Analysis
1. **Choose a representative run folder** (successful vs failed if any)
2. **Review `RUN_SUMMARY_AUDIT_TRAIL.md`** for overview and objectives
3. **Trace the cognitive lattice evolution** through progressive state files
4. **Examine decision-making** in web prompt/response pairs
5. **Analyze DOM reasoning** in debug files for complex selector choices

### Debugging & Research
- **DOM Debug Files**: Understand how the agent evaluated page elements
- **Observation Steps**: See how the agent verified its actions worked correctly
- **Page State Files**: Track navigation flow and detect any unexpected redirects
- **Lattice States**: Deep dive into the agent's internal reasoning and task decomposition

---

## Known Limitations & Scope

### Current Scope
- **Supported Sites**: Currently validated on Chipotle.com (SPA with semantic markup)
- **Browser**: Optimized for Chromium-based browsers via Playwright
- **Order Types**: Food ordering and customization workflows

### Technical Constraints
- Requires consistent internet connection for LLM API calls
- Average latency: 3-5 minutes per complete order workflow
- Bot detection: Some sites may require additional configuration

### Not Yet Supported
- Payment processing (by design - requires user confirmation)
- CAPTCHA solving
- Multi-tab workflows
- File uploads/downloads

*These limitations reflect deliberate architectural choices prioritizing reliability and user control.*

---

## Aggregate Test Statistics
- **Total Test Runs**: 100
- **Total DOM Interactions**: 1,189
- **Total Steps Executed**: 1,100+
- **Failure Rate**: 0.0%

---

### Performance Comparison
- **Human baseline**: 2-3 minutes for familiar order
- **CognitiveLattice**: 3-5 minutes (includes verification steps)
- **Traditional RPA**: Often fails on dynamic content

---

## Note on Cold Runs & Reliability
All tests in this suite are "cold runs"—the agent receives a fresh page load and must build its understanding from scratch each time. This approach validates the system's ability to reliably interpret and automate the site without relying on previously saved paths or cached DOM maps. In production, path caching and change detection would further improve speed and efficiency, but these tests demonstrate true end-to-end robustness.

---

## Key Success Metrics
A summary of the system's performance and reliability.

- ** 100% Task Completion Rate** across all complexity levels
- ** Average 3+ minutes per order** (including complex customizations)
- ** Consistent Performance** across multiple runs of identical prompts
- ** Zero Hardcoded Logic** – pure prompt-driven intelligence
- ** Complete Auditability** – every decision and action is logged

This test suite archive provides complete transparency into CognitiveLattice's autonomous web automation capabilities and serves as comprehensive validation of the system's reliability for real-world e-commerce interactions.

---

## Technical Implementation Notes
Technical details on how the system works and ensures quality.

### Progressive Candidate Disclosure System
The system uses a sophisticated approach to DOM element selection:
- Analyzes entire page DOM structure
- Ranks candidates by relevance to current task step
- Provides top-10 most promising selectors to the AI agent
- Agent chooses optimal selector with heuristic reasoning

### Cognitive Lattice Architecture
- **Multi-dimensional task representation** enabling complex reasoning
- **Progressive state evolution** with complete audit trails
- **Context-aware decision making** based on previous steps
- **Adaptive strategy adjustment** based on page responses

### Quality Assurance Features
- **Deterministic replay capability** through complete state capture
- **Cross-run consistency validation** via identical prompt testing
- **Performance regression detection** through metric tracking
- **Failure pattern analysis** for continuous improvement
---

##  Running the System

### Prerequisites
The system requires a **local Llama server** for intent diagnosis and task routing. The reference implementation uses:
- **Model**: `mistral-7b-instruct-v0.2.Q4_K_M.gguf`
- **Purpose**: Determines workflow type (web automation, stepwise automation (see main README for more information about stepwise automation), or document processing (currently disabled in this version of code))

### Setup Options
1. **Local Llama Server** (Recommended)
   - Install and run a local Llama server with the model above
   - See the main README for detailed setup instructions

2. **External API** (Advanced)
   - Point the intent diagnosis to an external LLM API
   - Requires code modifications (not officially supported)

### Running Tests

#### Single Test Run
```bash
python main.py
```
Uses the same prompts from the test suite for a single execution.

#### Bulk Test Run
```bash
python tests/test_chipotle_automation_bulk.py
```
Runs multiple tests and generates the same comprehensive debug outputs as this test suite (cognitive lattice states, DOM debug files, prompts/responses, audit trails).

**Note**: The bulk test script will create the same folder structure documented in this README, making it easy to reproduce or extend the test suite.

**Known Limitation while testing**: If there is a popup (e.g., cookie consent, rewards) that obscures key elements, the agent may fail to proceed. Future versions will include handling for common popups.
