# ADR-028: Loop Counter Auto-Injection into State

**Status**: ACCEPTED
**Date**: 2026-03-23
**Task**: BF-010

---

## Context

Loop edges in workflow configs support a `max_iterations` field:
```yaml
edges:
  - from: search
    loop:
      max_iterations: 5
      condition_field: quality_met
      exit_to: END
```

The `max_iterations` guard was silently broken in v1.0. The loop counter `_loop_iteration_{node_id}` is written into the node output dict by `_wrap_with_loop_counter()` in `graph_builder.py`, but Pydantic's `create_model()` uses `extra = "ignore"` by default — unknown fields are silently dropped. The counter never persists across iterations. `iteration >= max_iterations` is always `0 >= N` = False. The loop can only exit via `condition_field` becoming True.

This means any workflow relying on `max_iterations` as a safety backstop has no protection against infinite loops.

---

## Decision

**Auto-inject loop counter fields into the state model at graph build time.**

The `graph_builder.py` already calls `_collect_loop_targets()` to identify which nodes need loop wrapping. Extend this scan to also collect counter field names, then pass them to `build_state_model()` via a new optional parameter `extra_fields`.

```python
# graph_builder.py
loop_counter_fields = {
    f"__loop_counter_{edge.from_}": StateFieldConfig(type="int", default=0)
    for edge in config.edges
    if edge.loop
}

state_model = build_state_model(config.state, extra_fields=loop_counter_fields)
```

The counter fields use `__` prefix (double underscore) to signal they are framework-internal and not user-defined. They are:
- Visible in `state.model_dump()` (for debugging)
- Not required to be declared in YAML (auto-injected)
- Reset to 0 at workflow start (via default)
- Accessible in prompts via `{__loop_counter_search}` if needed (undocumented power-user feature)

The `_wrap_with_loop_counter()` function already writes the counter into the output dict. With auto-injection, the state model now accepts the field, and the counter persists correctly across iterations.

---

## Alternatives Considered

**A: User-declared counter field**
Require users to declare the counter in their state schema:
```yaml
state:
  fields:
    retry_count: { type: int, default: 0 }
edges:
  - from: search
    loop:
      counter_field: retry_count  # user declares this
      max_iterations: 5
```
Rejected as primary mechanism: adds boilerplate, breaks all existing loop configs, and the counter is an implementation detail users shouldn't need to manage. Kept as optional power-user feature (allows counter visibility in prompts).

**B: Executor-level counter outside state**
Track loop counts in a dict in the executor, not in state. Routing functions in LangGraph receive only state — they cannot read executor-level context without significant restructuring. Rejected: would require changing LangGraph's routing function signature or introducing a global/thread-local counter store.

**C: Mutable closure counter**
Capture a `count = [0]` mutable list in the routing function closure, increment it on each call. Rejected: breaks if the graph is invoked concurrently (shared closure state), and is invisible to MLFlow tracing.

---

## Consequences

**Positive**:
- `max_iterations` works correctly with no user config changes
- All existing loop configs are fixed without modification
- Counter is visible in execution state for debugging
- Compatible with user-declared counter field as an opt-in override

**Negative**:
- State model now has fields the user didn't declare — could be surprising when inspecting `state.model_dump()`
- The `__` prefix convention needs to be documented

**Future**:
- When structural memory is added (Phase 2), loop iteration counts can be stored as structural memory signals
- Counter accessibility in prompts (`{__loop_counter_X}`) can be formally documented if users request it
