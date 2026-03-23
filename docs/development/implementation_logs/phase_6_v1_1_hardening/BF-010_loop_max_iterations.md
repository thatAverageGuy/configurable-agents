# BF-010: Fix Loop `max_iterations` — Loop Counter State Injection

**Status**: TODO
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

## Files to Change

| File | Change |
|------|--------|
| `src/configurable_agents/core/state_builder.py` | Add `extra_fields` param to `build_state_model()` |
| `src/configurable_agents/core/graph_builder.py` | Inject counter fields, update `_wrap_with_loop_counter()` key prefix |
| `src/configurable_agents/core/control_flow.py` | Update `get_loop_iteration_key()` prefix |
| `src/configurable_agents/runtime/executor.py` | Verify `build_state_model()` call path — likely no change needed |

---

## Testing Strategy

**Unit tests**:
- `test_state_builder.py`: test `extra_fields` injection — field present in model, correct type, correct default
- `test_control_flow.py`: verify `get_loop_iteration_key()` returns new prefix
- `test_graph_builder.py`: verify counter field injected into state model for loop edges

**Integration tests**:
- New test config: loop with `max_iterations: 3`, condition that never becomes True → verify exits after exactly 3
- New test config: loop with `max_iterations: 5`, condition True on iteration 2 → verify exits at 2
- Existing loop test configs (07, 12) → verify no regression

**Manual verification**:
- Run `examples/article_writer.yaml` if it has loops — verify counter visible in output state

---

## Edge Cases

- Multiple loops in one workflow: each gets its own `__loop_counter_{node_id}` field — no collision
- Nested loops (node A loops, within its execution it triggers node B which also loops): each counter is independent
- `max_iterations: 1` → node runs once, then exits regardless of condition — verify this works
