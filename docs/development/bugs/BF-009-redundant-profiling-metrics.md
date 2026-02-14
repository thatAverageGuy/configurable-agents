# BF-009: Redundant Profiling Metrics

**Status**: Identified (Fix Deferred)
**Severity**: Low (Code cleanliness, no functional impact)
**Date**: 2026-02-14
**Related**: CLI Verification, ADR-018 (MLflow 3.9 Migration)

---

## Problem

The custom profiler in `profiler.py` logs `node_{node_id}_duration_ms` metrics to MLflow, but these metrics are **completely redundant** because:

1. MLflow 3.9's `autolog()` already captures span timing via `start_time_ns` and `end_time_ns`
2. The `profile-report` command reads from MLflow **traces**, not from custom metrics
3. Nothing in the codebase reads the `node_*_duration_ms` metrics

---

## Evidence

### Custom Profiler Logs (Redundant)
```python
# profiler.py:364-368
if MLFLOW_AVAILABLE and mlflow.active_run():
    mlflow.log_metric(metric_name, duration_ms)  # node_{node_id}_duration_ms
```

### profile-report Uses Traces (Not Custom Metrics)
```python
# cli.py:1001-1004
for span in trace.data.spans:
    if span.start_time_ns and span.end_time_ns:
        duration_ms = (span.end_time_ns - span.start_time_ns) / 1_000_000
        # Uses span timing, NOT custom node_*_duration_ms metrics
```

### MLflow 3.9 Already Captures Timing
```python
# mlflow_tracker.py:184-189
mlflow.langchain.autolog(
    log_traces=True,  # Automatically captures span timing
    run_tracer_inline=True,
)
```

---

## Impact

| Aspect | Impact |
|--------|--------|
| Functionality | None - everything works correctly |
| Performance | Minimal - extra metric logging has negligible overhead |
| Storage | Minimal waste - redundant metrics stored in MLflow |
| Code clarity | Confusing - two systems logging same data |

---

## Recommendation

**Deferred Fix**: This is low priority. Consider addressing during:

1. **ADR-018 Implementation** (MLflow 3.9 comprehensive migration)
2. **Code cleanup sprint**

**Proposed Fix**:
```python
# profiler.py - Remove MLflow metric logging
def _record_timing(node_id: str, duration_ms: float) -> None:
    # Record to BottleneckAnalyzer (if set)
    analyzer = get_profiler()
    if analyzer:
        analyzer.record_node(node_id, duration_ms)

    # REMOVE: Redundant - MLflow autolog already captures span timing
    # if MLFLOW_AVAILABLE and mlflow.active_run():
    #     mlflow.log_metric(f"node_{node_id}_duration_ms", duration_ms)

    logger.debug(f"Node '{node_id}' executed in {duration_ms:.2f}ms")
```

---

## Related Issue Also Fixed

**BF-009a**: Removed `--enable-profiling` CLI flag (also vestigial)

The flag was defined but never connected to any functionality:
- Not passed to `run_workflow()`
- BottleneckAnalyzer always created regardless
- MLflow autolog controlled by YAML config, not CLI flag

**Fix**: Removed flag from CLI argument parser and removed backwards-compatibility comment.

---

## Files Affected

| File | Change |
|------|--------|
| `src/configurable_agents/cli.py` | Removed `--enable-profiling` flag (DONE) |
| `src/configurable_agents/runtime/profiler.py` | Consider removing redundant MLflow logging (DEFERRED) |

---

## Verification

After removing `--enable-profiling` flag:
```bash
configurable-agents run --help
# Should NOT show --enable-profiling option

configurable-agents run test.yaml --input msg=test
# Should work without error
```

---

*Bug identified during comprehensive CLI verification (2026-02-14)*
