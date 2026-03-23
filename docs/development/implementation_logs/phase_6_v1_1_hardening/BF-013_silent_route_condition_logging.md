# BF-013: Fix Silent Route Condition Failure

**Status**: TODO
**Priority**: MEDIUM
**Created**: 2026-03-23

---

## Problem

In `control_flow.py`, route condition evaluation failures are silently swallowed:

```python
try:
    if _evaluate_condition(route.condition.logic, state_dict):
        return route.to
except ControlFlowError:
    # Skip failed condition evaluation, continue to next
    continue
```

If a condition like `{state.quality_score} >= 7` has a typo, references an undefined field, or has a syntax error, the `ControlFlowError` is caught and the route is silently skipped. Execution falls to the `default` route with no indication that a condition failed.

This makes debugging conditional flows very difficult — the workflow appears to work (it takes the default route) but it's silently ignoring broken conditions.

---

## Success Criteria

- Failed condition evaluations are logged at WARNING level with the condition text and the error reason
- The fallback-to-default behavior is preserved (no behavior change, only visibility change)
- Log message is actionable: tells the user which condition failed and why

---

## Implementation Approach

**File**: `src/configurable_agents/core/control_flow.py`

Change the silent `continue` to a warning log:

```python
try:
    if _evaluate_condition(route.condition.logic, state_dict):
        target = route.to if route.to != "END" else END
        return target
except ControlFlowError as e:
    logger.warning(
        f"Route condition evaluation failed — skipping to next route. "
        f"Condition: '{route.condition.logic}' | Error: {e} | "
        f"State fields available: {list(state_dict.keys())}"
    )
    continue
```

Also add a log when the default route is taken because no condition matched (not an error, but useful context):
```python
# No condition matched, use default
logger.debug(
    f"No route condition matched — using default route to '{default_target}'. "
    f"Evaluated {len(routes) - 1} condition(s)."
)
target = default_target if default_target != "END" else END
return target
```

---

## Files to Change

| File | Change |
|------|--------|
| `src/configurable_agents/core/control_flow.py` | Add WARNING log on condition failure; add DEBUG log on default route taken |

---

## Testing Strategy

- Test with a condition referencing a non-existent state field → verify WARNING log appears
- Test with a syntactically invalid condition → verify WARNING log appears
- Test with a valid condition that doesn't match → verify DEBUG log for default route taken
- Existing conditional routing tests → verify no regression

---

## Notes

This is a pure observability fix. No behavior changes. The WARNING level is appropriate because a condition failure likely indicates a config bug that the user should investigate.
