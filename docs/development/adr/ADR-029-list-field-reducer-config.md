# ADR-029: List Field Reducer Configuration

**Status**: ACCEPTED
**Date**: 2026-03-23
**Task**: BF-011

---

## Context

LangGraph requires state fields to have reducer functions (via `Annotated[type, reducer]`) to handle concurrent updates from parallel branches. The v1.0 implementation assigns reducers automatically based on type:
- Scalar types (str, int, float, bool): `_last_value_reducer` (last writer wins)
- List types: `_list_concat_reducer` (append new items to existing list)

The append reducer is correct for parallel execution: if two parallel branches both write to a list field, their outputs should be merged, not one overwriting the other.

However, it is wrong for retry loops. A typical pattern:
```yaml
nodes:
  - id: search
    outputs: [search_results]  # type: list[str]
  - id: evaluate
    outputs: [quality_met]     # type: bool
edges:
  - from: search
    loop:
      condition_field: quality_met
      max_iterations: 5
      exit_to: summarize
```

In this pattern, the user intends `search_results` to contain the results from the *latest* search iteration. With the append reducer, `search_results` accumulates results from every iteration — after 3 retries, it contains 3× the data, with duplicates. The summarize node then processes all accumulated results, not just the best ones.

---

## Decision

Add an optional `reducer` field to `StateFieldConfig` in the config schema:

```yaml
state:
  fields:
    search_results:
      type: list[str]
      reducer: replace   # replace on each write — correct for retry loops
    parallel_outputs:
      type: list[str]
      reducer: append    # accumulate from parallel branches — default behavior
```

**Default behavior is unchanged**: if `reducer` is not specified, list fields default to `append`. This maintains backward compatibility with all existing configs and all parallel execution use cases.

**Validation**: The `reducer` field is only meaningful for list types. If specified on a scalar type, the config validator raises an error (reducers on scalars are not configurable — always `last_value`).

**Schema change**:
```python
class StateFieldConfig(BaseModel):
    type: str
    required: bool = False
    default: Optional[Any] = None
    description: Optional[str] = None
    schema_: Optional[Dict[str, Any]] = Field(None, alias="schema")
    reducer: Literal["append", "replace"] = "append"  # NEW
```

**State builder change**: `_get_reducer_for_type()` is replaced by `_get_reducer_for_field()` which takes both the type and the field config's explicit reducer setting.

---

## Alternatives Considered

**A: Infer reducer from loop topology**
If a list field is written to by a node inside a loop, default to `replace`; otherwise `append`. Rejected: inference is implicit and hard to debug. A user modifying the graph topology wouldn't know they also changed reducer semantics. Explicit > implicit.

**B: Always replace for list fields**
Change the default to `replace` and require explicit `reducer: append` for parallel use cases. Rejected: this is a breaking change. Parallel execution (the original motivation for list reducers) would silently break for all existing configs.

**C: Separate parallel vs loop field types**
Introduce `list_parallel` and `list_serial` types. Rejected: type explosion, confusing, doesn't map to user mental model.

---

## Consequences

**Positive**:
- Retry loops produce correct results (latest iteration's data only)
- Existing parallel-execution configs unchanged (append remains default)
- Explicit and auditable — the YAML clearly states the intent
- Composable with the loop counter fix (ADR-028)

**Negative**:
- Existing loop configs that relied on accumulation behavior will get different results after this fix. This is correct behavior, but is technically a behavior change for anyone who built around the bug.
- Users need to know this option exists — documentation update required.

**Migration**: Existing loop configs should review list fields used as "current results" buffers and add `reducer: replace`. Configs that intentionally accumulated across loops (if any) are unaffected since `append` remains the default.
