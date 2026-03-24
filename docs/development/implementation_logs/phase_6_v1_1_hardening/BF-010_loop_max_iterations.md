# BF-010: Fix Loop `max_iterations` — Loop Counter State Injection

**Status**: DONE (2026-03-24)
**Priority**: HIGH
**Created**: 2026-03-23
**ADR**: [ADR-028](../../adr/ADR-028-loop-counter-state-injection.md)

---

## Problem

Loop edges support `max_iterations` as a safety backstop:
```yaml
edges:
  - from: search
    loop:
      max_iterations: 5
      condition_field: quality_met
      exit_to: END
```

The guard is silently broken. `_wrap_with_loop_counter()` in `graph_builder.py` returns `{_loop_iteration_search: N}` in the node output dict, but Pydantic's `create_model()` defaults to `extra = "ignore"` — the counter update is dropped. The routing function reads `state_dict.get("_loop_iteration_search", 0)` which always returns 0. `max_iterations` is never reached. Loops can only exit via `condition_field`.

---

## Success Criteria

- `max_iterations: 3` on a loop with `condition_field` that never becomes True terminates after exactly 3 iterations
- `max_iterations: 3` on a loop where `condition_field` becomes True on iteration 2 exits early (correct)
- Existing loop configs without `max_iterations` are unaffected
- Counter is visible in `state.model_dump()` for debugging with `__loop_counter_` prefix
- No changes required to any user YAML config

---

## Implementation Approach

### Step 1: Update `build_state_model()` signature

**File**: `src/configurable_agents/core/state_builder.py`

Add optional `extra_fields` parameter:
```python
def build_state_model(
    state_config: StateSchema,
    extra_fields: Optional[Dict[str, StateFieldConfig]] = None,
) -> Type[BaseModel]:
```

Merge `extra_fields` into `field_definitions` before calling `create_model()`. Extra fields are processed with the same `_create_field_definition()` logic, so they get proper Annotated types and reducers.

### Step 2: Collect loop counter fields in `build_graph()`

**File**: `src/configurable_agents/core/graph_builder.py`

After `_collect_loop_targets()`, build extra fields dict:
```python
from configurable_agents.config.schema import StateFieldConfig

loop_counter_fields = {}
for edge in config.edges:
    if edge.loop:
        counter_key = f"__loop_counter_{edge.from_}"
        loop_counter_fields[counter_key] = StateFieldConfig(
            type="int",
            default=0,
            description=f"Internal loop counter for node '{edge.from_}'. Auto-injected by framework."
        )

state_model = build_state_model(config.state, extra_fields=loop_counter_fields)
```

### Step 3: Update counter key in `_wrap_with_loop_counter()`

**File**: `src/configurable_agents/core/graph_builder.py`

Change from `_loop_iteration_{node_id}` to `__loop_counter_{node_id}` to match the injected field name:
```python
iteration_key = f"__loop_counter_{node_id}"  # was: f"_loop_iteration_{node_id}"
```

### Step 4: Update `create_loop_router()` to use new key

**File**: `src/configurable_agents/core/control_flow.py`

Update `get_loop_iteration_key()` to return new prefix:
```python
def get_loop_iteration_key(from_node: str) -> str:
    return f"__loop_counter_{from_node}"  # was: f"_loop_iteration_{from_node}"
```

### Step 5: Update executor to pass extra fields

**File**: `src/configurable_agents/runtime/executor.py`

The executor calls `build_state_model(config.state)`. Change to `build_graph()` already handles this since `build_graph()` now calls `build_state_model()` with extra fields internally. No executor change needed if `build_graph()` owns the extra fields injection.

---

## Files Changed

| File | Change |
|------|--------|
| `src/configurable_agents/core/state_builder.py` | Added `extra_fields: Optional[Dict[str, StateFieldConfig]] = None` param to `build_state_model()` |
| `src/configurable_agents/core/graph_builder.py` | Added `get_loop_counter_fields(config)` public helper; updated `_wrap_with_loop_counter()` via `get_loop_iteration_key()` (no direct change needed) |
| `src/configurable_agents/core/control_flow.py` | Updated `get_loop_iteration_key()` prefix `_loop_iteration_` → `__loop_counter_`; updated `create_loop_router()` to use `get_loop_iteration_key()` instead of hardcoded string |
| `src/configurable_agents/runtime/executor.py` | Changed `build_state_model(config.state)` → `build_state_model(config.state, extra_fields=get_loop_counter_fields(config))` |
| `src/configurable_agents/core/__init__.py` | Exported `get_loop_counter_fields` |

**Note on Step 5 deviation**: The planning doc said "no executor change needed if `build_graph()` owns state model creation." In practice, `build_graph()` receives the model as a parameter (not building it internally), so the executor was updated instead. This is Option A (minimal blast radius) — same outcome.

---

## Testing Notes

Tests were written but **not executed** due to a supply chain compromise of `litellm` (PyPI quarantine, 2026-03-24). The dev environment cannot be set up until the dependency is resolved.

**Tests added** (syntax-verified clean):
- `test_state_builder.py::TestExtraFields` — 6 unit tests for `extra_fields` injection
- `test_control_flow.py::TestGetLoopIterationKey` — 2 tests for new key prefix
- `test_graph_builder.py` — 3 tests for `get_loop_counter_fields()`

**Existing tests updated**:
- `test_control_flow.py`: replaced `_loop_iteration_` → `__loop_counter_` in all test state dict keys (6 occurrences)

---

## Edge Cases

- Multiple loops in one workflow: each gets its own `__loop_counter_{node_id}` field — no collision
- Nested loops (node A loops, within its execution it triggers node B which also loops): each counter is independent
- `max_iterations: 1` → node runs once, then exits regardless of condition — verify this works
