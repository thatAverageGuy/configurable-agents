---
phase: 02-agent-infrastructure
plan: 02B
type: execute
wave: 1
depends_on: []
files_modified:
  - src/configurable_agents/runtime/profiler.py
  - src/configurable_agents/core/node_executor.py
  - src/configurable_agents/runtime/executor.py
  - tests/observability/test_profiler.py
  - tests/observability/test_bottleneck_analysis.py
autonomous: true

must_haves:
  truths:
    - "profile_node decorator measures execution time using time.perf_counter()"
    - "Decorator works with both sync and async functions"
    - "Node execution time is logged to MLFlow as node_{node_id}_duration_ms metric"
    - "BottleneckAnalyzer identifies nodes taking >50% of total workflow time"
    - "get_slowest_node() returns node with highest total_duration_ms"
    - "MultiProviderCostTracker is explicitly wired to node_executor for cost tracking"
  artifacts:
    - path: "src/configurable_agents/runtime/profiler.py"
      provides: "Performance profiling decorator"
      exports: ["profile_node", "BottleneckAnalyzer"]
      min_lines: 100
    - path: "src/configurable_agents/core/node_executor.py"
      provides: "Node executor with profiling"
      contains: "profile_node decorator usage and MultiProviderCostTracker wiring"
    - path: "src/configurable_agents/runtime/executor.py"
      provides: "Runtime executor with bottleneck reporting"
      contains: "BottleneckAnalyzer lifecycle management"
  key_links:
    - from: "src/configurable_agents/core/node_executor.py"
      to: "src/configurable_agents/runtime/profiler.py"
      via: "profile_node decorator"
      pattern: "@profile_node"
    - from: "src/configurable_agents/core/node_executor.py"
      to: "src/configurable_agents/observability/multi_provider_tracker.py"
      via: "MultiProviderCostTracker for per-node cost tracking"
      pattern: "from configurable_agents.observability.multi_provider_tracker import MultiProviderCostTracker"
    - from: "src/configurable_agents/runtime/executor.py"
      to: "src/configurable_agents/runtime/profiler.py"
      via: "BottleneckAnalyzer import and lifecycle management"
      pattern: "from configurable_agents.runtime.profiler import BottleneckAnalyzer"
---

<objective>
Implement performance profiling with bottleneck detection and explicit cost tracker wiring.

**Purpose:** Enable users to identify performance bottlenecks through node-level timing metrics. The profiler decorator measures execution time for each node, and BottleneckAnalyzer identifies which nodes consume the most time. Also explicitly wire MultiProviderCostTracker to node_executor for per-node cost tracking.

**Output:**
- profile_node decorator for sync/async timing measurement
- BottleneckAnalyzer for bottleneck detection (>50% threshold)
- Node executor updated with @profile_node decorator
- Explicit MultiProviderCostTracker wiring in node_executor
- Runtime executor updated with BottleneckAnalyzer lifecycle management
- Per-node timing and cost metrics logged to MLFlow
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

# Existing infrastructure (Phase 1)
@src/configurable_agents/core/node_executor.py
@src/configurable_agents/runtime/executor.py
@src/configurable_agents/observability/mlflow_tracker.py
@src/configurable_agents/observability/multi_provider_tracker.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create performance profiler decorator</name>
  <files>src/configurable_agents/runtime/profiler.py</files>
  <action>
Create performance profiling module:

**Create src/configurable_agents/runtime/profiler.py**:

- `profile_node(node_id: str)` decorator:
  - Wrapper function that times node execution
  - Uses `time.perf_counter()` for high-resolution timing
  - Logs duration_ms to MLFlow as metric: `f"node_{node_id}_duration_ms"`
  - Stores timing in thread-local storage for bottleneck analysis
  - Handles both sync and async functions (via `functools.wraps`)
  - Timing captured even on exceptions (try/finally)

- `NodeTimings` dataclass:
  - Stores: node_id, duration_ms, timestamp, call_count, total_duration_ms
  - Used for aggregating timing data across workflow execution

- `BottleneckAnalyzer` class:
  - `__init__(self)`
    - Initialize empty timings dict: `_timings: dict[str, NodeTimings]`
    - Enable/disable flag: `enabled = True`
  - `record_node(self, node_id: str, duration_ms: float) -> None`
    - Store or aggregate timing data per node
    - If node exists: increment call_count, add to total_duration_ms
    - If new: create new NodeTimings entry
  - `get_bottlenecks(self, threshold_percent: float = 50.0) -> list[dict]`
    - Calculate total workflow time from all nodes
    - Return nodes contributing >threshold_percent% of total time
    - Each entry: node_id, total_duration_ms, avg_duration_ms, call_count, percent_of_total
  - `get_slowest_node(self) -> dict | None`
    - Return node with highest total_duration_ms
    - Returns None if no timings recorded
  - `get_summary(self) -> dict`
    - Return: total_time_ms, node_count, slowest_node, bottlenecks

- Global `_profiler_context` (thread-local storage):
  - `import threading`
  - `_context = threading.local()`
  - `_context.analyzer: BottleneckAnalyzer | None = None`
  - Accessor functions:
    - `get_profiler() -> BottleneckAnalyzer | None`
    - `set_profiler(analyzer: BottleneckAnalyzer) -> None`
    - `clear_profiler() -> None`

Reference: RESEARCH.md Pattern 5 (Performance Profiling Decorator code example).
  </action>
  <verify>
Step 1: `python -c "from configurable_agents.runtime.profiler import profile_node, BottleneckAnalyzer; print('Profiler imported')"`

Step 2: Test decorator on sync function:
```bash
python -c "
from configurable_agents.runtime.profiler import profile_node
import time

@profile_node('test_node')
def test_function():
    time.sleep(0.01)
    return 'done'

result = test_function()
print(f'Function result: {result}')
print('Decorator works for sync function')
"
```
Expected: No errors, function executes correctly.

Step 3: Test BottleneckAnalyzer:
```bash
python -c "
from configurable_agents.runtime.profiler import BottleneckAnalyzer

analyzer = BottleneckAnalyzer()
analyzer.record_node('node1', 100)
analyzer.record_node('node2', 200)
analyzer.record_node('node1', 150)  # node1 total: 250

summary = analyzer.get_summary()
print(f'Total time: {summary[\"total_time_ms\"]}ms')
print(f'Slowest node: {summary[\"slowest_node\"]}')
print(f'Bottlenecks: {summary[\"bottlenecks\"]}')
"
```
Expected: Total time: 350ms, slowest node: node2 (200ms).
  </verify>
  <done>
Performance profiler decorator created with sync/async support, BottleneckAnalyzer tracks node timings, bottleneck detection identifies nodes >50% of total time, thread-local context for profiler access, get_slowest_node method returns bottleneck summary, timing captured on exceptions via try/finally.
  </done>
</task>

<task type="auto">
  <name>Task 2: Integrate profiler and cost tracker with node executor</name>
  <files>src/configurable_agents/core/node_executor.py</files>
  <action>
Update node executor to use performance profiling and cost tracking:

**Read existing node_executor.py** and:

1. Add profiler and cost tracker imports:
   ```python
   from configurable_agents.runtime.profiler import profile_node, get_profiler, set_profiler, BottleneckAnalyzer
   from configurable_agents.observability.multi_provider_tracker import MultiProviderCostTracker
   ```

2. In node execution function (likely `execute_node` or similar):
   - Wrap LLM call with `@profile_node(node_id)` decorator
   - Ensure timing is captured even on exceptions (use try/finally)
   - Store timing info in node output state for analysis

3. **Explicit MultiProviderCostTracker wiring** (addresses checker warning):
   - Add `self.cost_tracker: MultiProviderCostTracker | None = None` to node executor
   - In executor initialization: `self.cost_tracker = MultiProviderCostTracker(mlflow_tracker)`
   - After each LLM call, track provider cost:
     ```python
     provider = _extract_provider(model)
     cost_info = self.cost_tracker.track_call(provider, model, response)
     # Store cost_info in node output
     ```
   - Log per-node cost to MLFlow as metric: `f"node_{node_id}_cost_usd"`

4. Update node output to include timing and cost metadata:
   - Add `_execution_time_ms` field to node output state
   - Add `_cost_usd` field to node output state
   - This will be stored in ExecutionStateRecord for later analysis

5. Integrate with MLFlowTracker:
   - After node execution, log `node_{node_id}_duration_ms` as MLFlow metric
   - Log `node_{node_id}_cost_usd` as MLFlow metric
   - This enables MLFlow query-based bottleneck and cost analysis

Reference: Existing node_executor.py patterns, RESEARCH.md Pattern 5 (decorator integration with MLFlow).
  </action>
  <verify>
Step 1: `python -c "from configurable_agents.core.node_executor import execute_node; print('Node executor imports profiler')"`

Step 2: Check for cost tracker wiring:
```bash
python -c "
from configurable_agents.core.node_executor import NodeExecutor
import inspect

# Check NodeExecutor has cost_tracker attribute
print('NodeExecutor class:', NodeExecutor)
print('Has cost_tracker attribute:', hasattr(NodeExecutor, 'cost_tracker'))

# Check init signature if possible
sig = inspect.signature(NodeExecutor.__init__)
print(f'__init__ parameters: {list(sig.parameters.keys())}')
"
```
Expected: cost_tracker attribute exists on NodeExecutor.

Step 3: Execute a workflow and check MLFlow UI for node_*_duration_ms and node_*_cost_usd metrics
Expected: Per-node metrics are logged to MLFlow.
  </verify>
  <done>
Node executor updated with @profile_node decorator, timing captured for all node executions, MultiProviderCostTracker explicitly wired in __init__, per-node cost tracking via track_call(), execution_time_ms and cost_usd added to node output state, MLFlow metrics logged per node (duration and cost).
  </done>
</task>

<task type="auto">
  <name>Task 3: Update runtime executor for bottleneck reporting</name>
  <files>src/configurable_agents/runtime/executor.py</files>
  <action>
Update runtime executor to collect and report bottlenecks:

**Read existing executor.py** and:

1. In `run_workflow_from_config()` or similar entry point:
   - At workflow start: Create `BottleneckAnalyzer` instance
   - Set via `set_profiler(analyzer)` for decorator access
   - Store reference for later reporting

2. At workflow completion (after graph execution):
   - Get BottleneckAnalyzer from profiler: `analyzer = get_profiler()`
   - Call `analyzer.get_summary()` for bottleneck report
   - Call `tracker.log_bottleneck_report(analyzer.get_summary())` if available
   - Log bottleneck info to console for immediate feedback

3. Add bottleneck summary to workflow completion logging:
   - Print "Slowest node: {node_id} ({avg_duration_ms:.2f}ms avg)"
   - Print "Bottlenecks (>{threshold}% of total time):"
   - List each bottleneck with percentage
   - Format: "  - {node_id}: {percent_of_total:.1f}% ({total_duration_ms:.0f}ms total)"

4. Store bottleneck data in WorkflowRunRecord:
   - Add `bottleneck_info` field to record (JSON serialized)
   - Contains: slowest_node, bottlenecks list, total_time_ms
   - Enables historical analysis via storage queries

Reference: Existing executor.py completion logging patterns, RESEARCH.md Pattern 5 (bottleneck reporting).
  </action>
  <verify>
Step 1: `python -c "from configurable_agents.runtime.executor import WorkflowExecutor; print('Executor imports BottleneckAnalyzer')"`

Step 2: Check executor has bottleneck lifecycle management:
```bash
python -c "
from configurable_agents.runtime.executor import WorkflowExecutor
import inspect

# Check for set_profiler, get_profiler usage
source = inspect.getsource(WorkflowExecutor.run_workflow_from_config)
print('Uses set_profiler:', 'set_profiler' in source)
print('Uses get_profiler:', 'get_profiler' in source)
print('Logs bottleneck:', 'bottleneck' in source.lower())
"
```
Expected: All checks return True.

Step 3: Run a workflow and verify bottleneck info is printed to console
Expected: Console shows "Slowest node" and bottleneck information.
  </verify>
  <done>
Runtime executor creates BottleneckAnalyzer at workflow start, sets via set_profiler() for decorator access, collects bottleneck data at workflow end, logs bottleneck report to MLFlow and console, stores bottleneck info in WorkflowRunRecord, bottleneck summary includes slowest node and threshold-based bottlenecks.
  </done>
</task>

<task type="auto">
  <name>Task 4: Add profiler tests</name>
  <files>tests/observability/test_profiler.py, tests/observability/test_bottleneck_analysis.py</files>
  <action>
Create tests for performance profiling features:

**Create tests/observability/test_profiler.py**:

- `test_profile_node_times_sync_function`: Decorator measures timing accurately for sync function
- `test_profile_node_times_async_function`: Decorator measures timing accurately for async function
- `test_profile_node_captures_exception`: Timing captured even when function raises exception
- `test_profile_node_logs_to_mlflow`: Verify MLFlow metric logging (mock MLFlowTracker)
- `test_timing_stored_in_thread_local_context`: Verify timing stored in global context
- `test_multiple_calls_aggregate_timing`: Multiple calls to same node aggregate correctly

**Create tests/observability/test_bottleneck_analysis.py**:

- `test_bottleneck_analyzer_record_node`: Verify node timing is recorded
- `test_bottleneck_analyzer_aggregates_multiple_calls`: Multiple calls to same node aggregate
- `test_get_bottlenecks_default_threshold`: Identifies nodes >50% of total time
- `test_get_bottlenecks_custom_threshold`: Respects custom threshold parameter
- `test_get_slowest_node`: Returns node with highest total_duration_ms
- `test_get_summary_returns_complete_analysis`: Includes total_time_ms, node_count, slowest_node, bottlenecks
- `test_single_node_not_bottleneck`: Single node with 100% is not >50% threshold (edge case)
- `test_zero_duration_handled`: Zero duration nodes don't cause errors
- `test_empty_analyzer_returns_none_slowest`: No timings returns None for slowest_node

Use pytest with unittest.mock for MLFlow API mocking.

Reference: Existing test patterns in tests/core/test_parallel.py.
  </action>
  <verify>
Step 1: `pytest tests/observability/test_profiler.py -v`

Expected: All profiler tests pass.

Step 2: `pytest tests/observability/test_bottleneck_analysis.py -v`

Expected: All bottleneck analysis tests pass.

Step 3: `pytest tests/observability/test_profiler.py tests/observability/test_bottleneck_analysis.py --cov=src/configurable_agents/runtime/profiler --cov-report=term-missing`

Expected: Coverage >80% for profiler module.

Step 4: `pytest tests/observability/test_profiler.py -k "test_exception" -v`

Expected: Exception handling test passes (timing captured on error).
  </verify>
  <done>
Profiler test suite created with sync/async tests, BottleneckAnalyzer test suite covers all methods, exception handling test verifies timing captured on errors, edge cases tested (single node, zero duration, empty analyzer), MLFlow mocking correctly simulates API responses, coverage >80% for profiler module.
  </done>
</task>

</tasks>

<verification>
After completing all tasks:

1. **Profiler Verification**:
   - Import profile_node and BottleneckAnalyzer successfully
   - Test decorator on sync function - timing measured
   - Test decorator on async function - timing measured
   - Test exception handling - timing captured on exception

2. **Node Executor Verification**:
   - Verify node_executor has @profile_node decorator
   - Verify MultiProviderCostTracker is wired in __init__
   - Verify per-node costs tracked via track_call()
   - Verify node output includes _execution_time_ms and _cost_usd
   - Verify MLFlow metrics logged (node_*_duration_ms, node_*_cost_usd)

3. **Bottleneck Analyzer Verification**:
   - Verify get_slowest_node() returns correct node
   - Verify get_bottlenecks() identifies nodes >50% threshold
   - Verify get_summary() returns complete analysis

4. **Runtime Executor Verification**:
   - Verify BottleneckAnalyzer created at workflow start
   - Verify set_profiler() called for decorator access
   - Verify bottleneck info logged to console
   - Verify bottleneck info stored in WorkflowRunRecord

5. **Test Coverage Verification**:
   - Run all profiler and bottleneck tests
   - Verify coverage >80%
</verification>

<success_criteria>
**Plan Success Criteria Met:**
1. profile_node decorator measures execution time via time.perf_counter()
2. Decorator works with both sync and async functions
3. Node execution time logged to MLFlow as node_{node_id}_duration_ms
4. BottleneckAnalyzer identifies nodes >50% of total time
5. get_slowest_node() returns node with highest total_duration_ms
6. MultiProviderCostTracker explicitly wired in node_executor.__init__
7. Per-node costs tracked via track_call() and stored in node output
8. Per-node costs logged to MLFlow as node_{node_id}_cost_usd
9. Bottleneck info stored in WorkflowRunRecord
10. Test coverage >80% for profiler module
</success_criteria>

<output>
After completion, create `.planning/phases/02-agent-infrastructure/02-02B-SUMMARY.md` with:
- Frontmatter (phase, plan, wave, status, completed_at, tech_added, patterns_established, key_files)
- Summary of changes (profiler decorator, bottleneck analyzer, cost tracker wiring)
- Verification results (profiler functionality, bottleneck detection, cost tracking)
- Next steps link (02-02C: CLI Integration)
</output>
