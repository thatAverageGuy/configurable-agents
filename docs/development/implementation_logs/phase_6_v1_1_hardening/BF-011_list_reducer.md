# BF-011: Fix List Field Reducer — Replace Semantics for Loops

**Status**: TODO
**Priority**: HIGH
**Created**: 2026-03-23
**ADR**: [ADR-029](../../adr/ADR-029-list-field-reducer-config.md)

---

## Problem

All list-type state fields use `_list_concat_reducer` (append). This is correct for parallel branch merging but wrong for retry loops. In a loop, each iteration appends to the previous iteration's list instead of replacing it. After N retries, the field contains N× the expected data, with duplicates.

Example: `search_results: list[str]` in a research retry loop accumulates results from every search attempt instead of holding only the latest search's results.

---

## Success Criteria

- List fields with `reducer: replace` return only the latest write (not accumulated)
- List fields without `reducer` specified default to `append` — existing behavior unchanged
- Config validator rejects `reducer` on non-list fields
- All existing test configs pass without changes (all currently use implicit `append`)

---

## Implementation Approach

### Step 1: Add `reducer` field to `StateFieldConfig` schema

**File**: `src/configurable_agents/config/schema.py`

```python
from typing import Literal

class StateFieldConfig(BaseModel):
    type: str = Field(...)
    required: bool = Field(False)
    default: Optional[Any] = Field(None)
    description: Optional[str] = Field(None)
    schema_: Optional[Dict[str, Any]] = Field(None, alias="schema")
    reducer: Literal["append", "replace"] = Field(
        "append",
        description="List field reducer: 'append' (default, for parallel branches) or 'replace' (for retry loops)"
    )
```

### Step 2: Add `_last_value_reducer` for replace semantics

**File**: `src/configurable_agents/core/state_builder.py`

Add a `_replace_reducer` that simply returns the new value (same as `_last_value_reducer` but semantically clear):
```python
def _replace_reducer(current: List, new: Any) -> Any:
    """
    'Replace' reducer — returns new value, discarding current.
    Use for list fields that represent current state (not accumulated history).
    Correct for retry loops where each iteration replaces the previous result.
    """
    return new
```

### Step 3: Update `_get_reducer_for_type()` → `_get_reducer_for_field()`

**File**: `src/configurable_agents/core/state_builder.py`

Replace the type-only lookup with a field-config-aware function:
```python
def _get_reducer_for_field(python_type: Type, field_config: StateFieldConfig) -> Callable:
    """Get reducer based on type AND explicit field config."""
    origin = getattr(python_type, '__origin__', None)
    is_list = (origin is list or python_type is list)

    if is_list:
        if field_config.reducer == "replace":
            return _replace_reducer
        return _list_concat_reducer  # default: append

    return _last_value_reducer
```

### Step 4: Add validation — reject `reducer` on non-list fields

**File**: `src/configurable_agents/config/schema.py`

Add a `model_validator` to `StateFieldConfig`:
```python
@model_validator(mode="after")
def validate_reducer_for_list_only(self) -> "StateFieldConfig":
    if self.reducer == "replace":
        # Only meaningful on list types — check type string
        if not self.type.startswith("list"):
            raise ValueError(
                f"'reducer: replace' is only valid for list types, got type='{self.type}'. "
                "Scalar types always use last-value semantics."
            )
    return self
```

### Step 5: Update `_create_field_definition()` to pass field config

**File**: `src/configurable_agents/core/state_builder.py`

Update the call from `_get_reducer_for_type(field_type)` to `_get_reducer_for_field(field_type, field_config)`.

---

## Files to Change

| File | Change |
|------|--------|
| `src/configurable_agents/config/schema.py` | Add `reducer` field to `StateFieldConfig`, add validator |
| `src/configurable_agents/core/state_builder.py` | Add `_replace_reducer`, update `_get_reducer_for_field()`, update `_create_field_definition()` |

---

## Testing Strategy

**Unit tests**:
- `test_state_builder.py`: verify `replace` reducer returns new value on second write
- `test_state_builder.py`: verify `append` reducer still concatenates (no regression)
- `test_schema.py`: verify `reducer: replace` on `type: str` raises validation error

**Integration tests**:
- New test config: loop with `search_results: list[str], reducer: replace` → after 3 iterations, `search_results` contains only the latest iteration's data
- Existing test configs: all pass unchanged (implicit `append` still works)

---

## Notes

- The `reducer` field appears in YAML under `state.fields.{name}`, e.g.:
  ```yaml
  state:
    fields:
      search_results:
        type: list[str]
        reducer: replace
  ```
- Documentation update needed: `docs/user/CONFIG_REFERENCE.md` — add `reducer` to state field schema table
