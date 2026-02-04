---
phase: 02-agent-infrastructure
plan: 02A
type: execute
wave: 1
depends_on: []
files_modified:
  - src/configurable_agents/observability/multi_provider_tracker.py
  - src/configurable_agents/observability/mlflow_tracker.py
  - tests/observability/test_multi_provider_tracker.py
autonomous: true

must_haves:
  truths:
    - "MultiProviderCostTracker aggregates costs by provider/model combination"
    - "Provider detection correctly identifies openai, anthropic, google, ollama from model names"
    - "Ollama providers return $0.00 cost (local models)"
    - "generate_cost_report() queries MLFlow and returns unified cost summary"
    - "MLFlowTracker integrates MultiProviderCostTracker for provider-aware tracking"
    - "Per-provider costs are logged to MLFlow as params (provider_{name}_cost_usd)"
  artifacts:
    - path: "src/configurable_agents/observability/multi_provider_tracker.py"
      provides: "Multi-provider cost aggregation"
      exports: ["MultiProviderCostTracker", "generate_cost_report"]
      min_lines: 150
    - path: "src/configurable_agents/observability/mlflow_tracker.py"
      provides: "MLFlowTracker with multi-provider integration"
      contains: "track_provider_call, get_workflow_cost_summary with by_provider breakdown"
  key_links:
    - from: "src/configurable_agents/observability/multi_provider_tracker.py"
      to: "src/configurable_agents/observability/mlflow_tracker.py"
      via: "MLFlowTracker integration"
      pattern: "MultiProviderCostTracker"
    - from: "src/configurable_agents/observability/multi_provider_tracker.py"
      to: "src/configurable_agents/observability/cost_estimator.py"
      via: "CostEstimator for cost calculation"
      pattern: "from configurable_agents.observability.cost_estimator import"
---

<objective>
Implement multi-provider cost tracking with MLFlow integration.

**Purpose:** Enable unified cost reporting across all LLM providers (OpenAI, Anthropic, Gemini, Ollama) used in a workflow. Users can see total costs, token counts, and per-provider breakdowns. This integrates with existing MLFlowTracker to log provider-specific metrics.

**Output:**
- MultiProviderCostTracker for unified cost reporting
- Provider detection logic (openai, anthropic, google, ollama)
- generate_cost_report() standalone function for CLI usage
- MLFlowTracker integration with track_provider_call()
- Enhanced get_workflow_cost_summary() with by_provider breakdown
- Per-provider metrics logged to MLFlow
</objective>

<execution_context>
@C:\Users\ghost\.claude\get-shit-done/workflows/execute-plan.md
@C:\Users\ghost\.claude\get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02-agent-infrastructure/02-RESEARCH.md

# Existing observability infrastructure (Phase 1)
@src/configurable_agents/observability/mlflow_tracker.py
@src/configurable_agents/observability/cost_estimator.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create MultiProviderCostTracker for unified cost reporting</name>
  <files>src/configurable_agents/observability/multi_provider_tracker.py</files>
  <action>
Create multi-provider cost aggregation module:

**Create src/configurable_agents/observability/multi_provider_tracker.py**:

- `MultiProviderCostTracker` class:
  - `__init__(self, mlflow_tracker: MLFlowTracker | None = None)`
    - Store mlflow_tracker reference
    - Initialize empty dict for tracking costs by provider/model
  - `track_call(self, provider: str, model: str, response: Any) -> dict`
    - Extracts token usage from LLM response (input_tokens, output_tokens)
    - Uses existing CostEstimator for cost calculation
    - Returns dict with: input_tokens, output_tokens, total_tokens, cost_usd, provider, model
    - Handles both LiteLLM response format and direct provider responses
    - Stores call data in internal tracking dict
  - `get_cost_summary(self, runs: list) -> dict`
    - Aggregates costs by provider/model combination
    - Returns: {total_cost_usd, total_tokens, by_provider: {provider: {total_cost, total_tokens, call_count}}}
  - `generate_report(self, experiment_name: str) -> dict`
    - Queries MLFlow for all runs in experiment
    - Extracts provider/model from run params and metrics
    - Aggregates costs and returns summary report

- `_extract_provider(model_name: str) -> str` helper:
  - Extract provider from model name (e.g., "openai/gpt-4o" -> "openai")
  - Support providers: openai, anthropic, google, ollama
  - Default: "unknown" if pattern doesn't match

- `_is_ollama_model(provider: str) -> bool` helper:
  - Returns True if provider is "ollama"
  - Used to zero out costs (local models)

- `generate_cost_report(experiment_name: str, mlflow_uri: str | None = None) -> dict`:
  - Standalone function for CLI usage
  - Creates MLflow client, queries experiment, generates report
  - Returns report with: experiment, total_cost_usd, total_tokens, by_provider breakdown

Provider detection logic:
- OpenAI: models starting with "openai/" or "gpt-"
- Anthropic: models starting with "anthropic/" or "claude-"
- Google: models starting with "google/" or "gemini-"
- Ollama: models starting with "ollama/"
- Ollama costs are always $0.00 (local models)

Reference: RESEARCH.md Pattern 4 (Multi-Provider Cost Tracking code example), existing CostEstimator in cost_estimator.py.
  </action>
  <verify>
Step 1: `python -c "from configurable_agents.observability import MultiProviderCostTracker; print('MultiProviderCostTracker imported')"`

Step 2: `python -c "from configurable_agents.observability.multi_provider_tracker import generate_cost_report; print('generate_cost_report function available')"`

Step 3: Test provider detection:
```bash
python -c "
from configurable_agents.observability.multi_provider_tracker import _extract_provider
test_cases = [
    ('openai/gpt-4o', 'openai'),
    ('anthropic/claude-3-opus', 'anthropic'),
    ('google/gemini-pro', 'google'),
    ('ollama/llama2', 'ollama'),
]
for model, expected in test_cases:
    result = _extract_provider(model)
    print(f'{model} -> {result} (expected: {expected}) -> {\"PASS\" if result == expected else \"FAIL\"}')"
```
Expected: All test cases PASS.
  </verify>
  <done>
MultiProviderCostTracker created with track_call/get_cost_summary/generate_report methods, provider detection handles openai/anthropic/google/ollama, cost aggregation by provider/model complete, generate_cost_report standalone function for CLI, Ollama models return $0.00 cost.
  </done>
</task>

<task type="auto">
  <name>Task 2: Enhance MLFlowTracker with multi-provider tracking</name>
  <files>src/configurable_agents/observability/mlflow_tracker.py</files>
  <action>
Update MLFlowTracker to integrate multi-provider cost tracking:

**Read existing mlflow_tracker.py** and:

1. Add MultiProviderCostTracker integration:
   - Import: `from configurable_agents.observability.multi_provider_tracker import MultiProviderCostTracker`
   - In `__init__`: Create `self.cost_tracker = MultiProviderCostTracker(self)`
   - Add method: `track_provider_call(self, provider: str, model: str, response: Any) -> dict`
     - Delegates to `self.cost_tracker.track_call(provider, model, response)`
     - Returns cost dict for immediate use
     - Logs provider/model metrics to MLFlow

2. Update `get_workflow_cost_summary()`:
   - Use `MultiProviderCostTracker` for provider-aware aggregation
   - Add `by_provider` field to returned summary
   - Include: provider, model, total_cost_usd, total_tokens, call_count
   - Example:
     ```python
     {
         "total_cost_usd": 0.50,
         "total_tokens": 10000,
         "by_provider": {
             "openai": {"total_cost_usd": 0.30, "total_tokens": 6000, "calls": 5},
             "anthropic": {"total_cost_usd": 0.20, "total_tokens": 4000, "calls": 3}
         }
     }
     ```

3. Update `log_workflow_summary()`:
   - Log per-provider costs as MLFlow params: `provider_{name}_cost_usd`
   - Log per-provider token counts as MLFlow params: `provider_{name}_tokens`
   - This enables MLFlow UI filtering and comparison

Reference: Existing MLFlowTracker patterns, RESEARCH.md Pattern 4 (multi-provider aggregation).
  </action>
  <verify>
Step 1: `python -c "from configurable_agents.observability import MLFlowTracker; print('MLFlowTracker imports MultiProviderCostTracker')"`

Step 2: Check MLFlowTracker has new methods:
```bash
python -c "
from configurable_agents.observability import MLFlowTracker
import inspect

# Check track_provider_call exists
has_track = hasattr(MLFlowTracker, 'track_provider_call')
print(f'track_provider_call method exists: {has_track}')

# Check method signature if exists
if has_track:
    sig = inspect.signature(MLFlowTracker.track_provider_call)
    print(f'Method signature: {sig}')
"
```
Expected: track_provider_call method exists with signature (self, provider, model, response).

Step 3: Verify get_workflow_cost_summary includes by_provider:
```bash
python -c "
from configurable_agents.observability import MLFlowTracker
import inspect

sig = inspect.signature(MLFlowTracker.get_workflow_cost_summary)
print(f'get_workflow_cost_summary signature: {sig}')

# Check docstring mentions by_provider
docstring = MLFlowTracker.get_workflow_cost_summary.__doc__ or ''
print(f'Mentions by_provider: {\"by_provider\" in docstring.lower()}')"
```
  </verify>
  <done>
MLFlowTracker integrates MultiProviderCostTracker, track_provider_call method added, get_workflow_cost_summary returns by_provider breakdown, log_workflow_summary logs per-provider metrics (provider_{name}_cost_usd, provider_{name}_tokens), MLFlow UI filtering enabled.
  </done>
</task>

<task type="auto">
  <name>Task 3: Add multi-provider cost tracker tests</name>
  <files>tests/observability/test_multi_provider_tracker.py</files>
  <action>
Create tests for multi-provider cost tracking:

**Create tests/observability/test_multi_provider_tracker.py**:

- `test_tracker_initialization`: Verify MultiProviderCostTracker initializes with/without mlflow_tracker
- `test_track_call_extracts_tokens`: Mock LLM response, verify input/output tokens extracted
- `test_track_call_calculates_cost`: Verify cost calculation using CostEstimator
- `test_provider_detection_openai`: Verify "openai/gpt-4o" -> "openai"
- `test_provider_detection_anthropic`: Verify "anthropic/claude-3-opus" -> "anthropic"
- `test_provider_detection_google`: Verify "google/gemini-pro" -> "google"
- `test_provider_detection_ollama`: Verify "ollama/llama2" -> "ollama"
- `test_ollama_zero_cost`: Verify Ollama models return $0.00 cost
- `test_cost_summary_aggregation`: Track multiple calls, verify aggregated summary
- `test_cost_summary_by_provider`: Verify by_provider breakdown is correct
- `test_generate_cost_report`: Mock MLFlow query, verify report generation

Use pytest with unittest.mock for MLFlow API mocking and LLM response mocking.

Reference: Existing test patterns in tests/core/test_parallel.py.
  </action>
  <verify>
Step 1: `pytest tests/observability/test_multi_provider_tracker.py -v`

Expected: All tests pass.

Step 2: `pytest tests/observability/test_multi_provider_tracker.py -k "test_provider_detection" -v`

Expected: All provider detection tests pass.

Step 3: `pytest tests/observability/test_multi_provider_tracker.py -k "test_ollama" -v`

Expected: Ollama zero-cost test passes.

Step 4: `pytest tests/observability/test_multi_provider_tracker.py --cov=src/configurable_agents/observability/multi_provider_tracker --cov-report=term-missing`

Expected: Coverage >80% for multi_provider_tracker module.
  </verify>
  <done>
Multi-provider cost tracker tests created, provider detection tests cover all supported providers, Ollama zero-cost test passes, cost aggregation tests verify by_provider breakdown, MLFlow mocking correctly simulates API responses, coverage >80%.
  </done>
</task>

</tasks>

<verification>
After completing all tasks:

1. **Import Verification**:
   - Import MultiProviderCostTracker successfully
   - Import generate_cost_report function
   - Import MLFlowTracker with new methods

2. **Provider Detection Verification**:
   - Test all provider patterns (openai, anthropic, google, ollama)
   - Verify edge cases (unknown providers, malformed model names)
   - Verify Ollama models are identified correctly

3. **Cost Aggregation Verification**:
   - Track multiple provider calls
   - Verify get_cost_summary returns correct totals
   - Verify by_provider breakdown is accurate

4. **MLFlow Integration Verification**:
   - Verify track_provider_call delegates to MultiProviderCostTracker
   - Verify get_workflow_cost_summary includes by_provider field
   - Verify log_workflow_summary logs per-provider params

5. **Test Coverage Verification**:
   - Run all multi-provider tracker tests
   - Verify coverage >80%
</verification>

<success_criteria>
**Plan Success Criteria Met:**
1. MultiProviderCostTracker aggregates costs by provider/model combination
2. Provider detection correctly identifies openai, anthropic, google, ollama
3. Ollama providers return $0.00 cost
4. generate_cost_report() returns unified cost summary
5. MLFlowTracker.track_provider_call() method exists and works
6. get_workflow_cost_summary() returns by_provider breakdown
7. Per-provider metrics logged to MLFlow as params
8. Test coverage >80% for multi_provider_tracker module
</success_criteria>

<output>
After completion, create `.planning/phases/02-agent-infrastructure/02-02A-SUMMARY.md` with:
- Frontmatter (phase, plan, wave, status, completed_at, tech_added, patterns_established, key_files)
- Summary of changes (MultiProviderCostTracker, MLFlowTracker integration)
- Verification results (provider detection, cost aggregation, MLFlow integration)
- Next steps link (02-02B: Performance Profiling)
</output>
