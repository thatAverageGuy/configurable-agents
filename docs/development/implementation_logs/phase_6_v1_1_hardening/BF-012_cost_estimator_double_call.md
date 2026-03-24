# BF-012: Fix Double CostEstimator Call Per Node

**Status**: DONE (2026-03-24)
**Priority**: MEDIUM
**Created**: 2026-03-23

---

## Problem

`execute_node()` in `node_executor.py` creates and calls `CostEstimator` twice per node execution:

1. **Lines ~596-604**: `cost_usd` calculated, assigned to local variable, never used.
2. **Lines ~681-692**: New `CostEstimator()` instance created, same calculation repeated to populate `state_snapshot["cost_usd"]` for storage.

This is wasted computation and a code smell — if the cost rate tables change between the two calls (unlikely but possible), they'd return inconsistent values.

---

## Success Criteria

- CostEstimator is called exactly once per node execution
- `cost_usd` value is the same in both the profiler context and the storage snapshot
- No change to observable behavior (cost values, storage records)

---

## Implementation Approach

**File**: `src/configurable_agents/core/node_executor.py`

Remove the first calculation (lines ~596-604) entirely. The `cost_usd` variable was unused — it served no purpose.

The second calculation (inside the storage persistence block at lines ~681-692) remains as-is. It is correctly scoped inside the `if execution_state_repo and run_id:` guard.

If cost needs to be available outside the storage block in the future (e.g., for return value enrichment), extract to a single calculation before both use sites:
```python
# Calculate cost once after LLM call
cost_usd = 0.0
try:
    cost_estimator = CostEstimator()
    cost_usd = cost_estimator.estimate_cost(
        model=model_name,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
    )
except Exception as e:
    logger.debug(f"Failed to estimate cost for node '{node_id}': {e}")

# ... later in storage block ...
state_snapshot["cost_usd"] = cost_usd  # reuse, no second call
```

---

## Files to Change

| File | Change |
|------|--------|
| `src/configurable_agents/core/node_executor.py` | Remove first dead CostEstimator call (~lines 596-604); optionally consolidate into single calculation |

---

## Testing Strategy

- Existing tests for node execution — verify no regression in cost values stored
- Verify cost appears correctly in MLFlow traces after change
- This is a small, surgical fix — low risk

---

## Actual Implementation (2026-03-24)

### What Was Done

Removed the redundant `CostEstimator` instantiation inside the `if execution_state_repo and run_id:` storage block (lines ~681-692). Replaced the 11-line block with a single assignment:

```python
# Reuse cost_usd calculated above (single CostEstimator call per node)
state_snapshot["cost_usd"] = cost_usd
```

The `cost_usd` variable computed earlier (lines 596-605) is now the single source of truth for both any future use and the storage snapshot.

### Result

- 1 `CostEstimator()` instantiation removed per node execution
- `cost_usd` value is guaranteed consistent between both use sites
- No change to observable behavior
