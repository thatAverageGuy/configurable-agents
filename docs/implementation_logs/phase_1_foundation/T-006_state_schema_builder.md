# T-006: State Schema Builder

**Status**: ✅ Complete
**Completed**: 2026-01-24
**Commit**: `b7e3155` - T-006: State schema builder - Dynamic Pydantic models
**Phase**: Phase 1 (Foundation)
**Progress After**: 7/20 tasks (35%)

---

## 🎯 What Was Done

- Implemented dynamic Pydantic model generation from StateSchema configs
- Supports all type system types (basic, collections, nested objects)
- Recursive nested object handling with meaningful model names
- Required/optional fields with proper validation
- Default values preserved and enforced
- Field descriptions included in generated models
- 30 comprehensive tests covering all scenarios
- Total: 202 tests passing (up from 172)

---

## 📦 Files Created

### Source Code

```
src/configurable_agents/core/
└── state_builder.py (dynamic Pydantic model builder)
```

### Tests

```
tests/core/
├── __init__.py
└── test_state_builder.py (30 comprehensive tests)
```

---

## 🔧 How to Verify

### 1. Test state builder

```bash
pytest tests/core/test_state_builder.py -v
# Expected: 30 passed
```

### 2. Run full test suite

```bash
pytest -v
# Expected: 202 passed (30 new + 172 existing)
```

### 3. Use state builder

```python
from configurable_agents.config import StateSchema, StateFieldConfig
from configurable_agents.core import build_state_model

# Define state config
state_config = StateSchema(
    fields={
        "topic": StateFieldConfig(type="str", required=True),
        "score": StateFieldConfig(type="int", default=0),
        "tags": StateFieldConfig(type="list[str]", default=[]),
        "metadata": StateFieldConfig(
            type="object",
            required=False,
            schema={"author": "str", "timestamp": "int"},
        ),
    }
)

# Build model
StateModel = build_state_model(state_config)

# Create instance (minimal)
state1 = StateModel(topic="AI Safety")
assert state1.topic == "AI Safety"
assert state1.score == 0
assert state1.tags == []
assert state1.metadata is None

# Create instance (full)
state2 = StateModel(
    topic="AI Safety",
    score=95,
    tags=["ai", "safety"],
    metadata={"author": "Alice", "timestamp": 1234567890},
)
assert state2.metadata.author == "Alice"
assert state2.metadata.timestamp == 1234567890
```

---

## ✅ What to Expect

**Working**:
- ✅ Dynamic Pydantic models generated from configs
- ✅ All type system types supported (basic, collections, nested objects)
- ✅ Required fields enforced (ValidationError if missing)
- ✅ Optional fields default to None
- ✅ Default values work correctly
- ✅ Field descriptions included in model schema
- ✅ Nested objects have meaningful names (WorkflowState_metadata, etc.)
- ✅ Type validation enforced by Pydantic
- ✅ Clear error messages for invalid configs

**Not Yet Working**:
- ❌ No runtime state updates yet (T-011: Node Executor)
- ❌ No state serialization/deserialization for persistence

---

## 💻 Public API

### Main Function

```python
from configurable_agents.core import build_state_model, StateBuilderError

# Build dynamic state model
StateModel = build_state_model(state_config)

# Create state instance
state = StateModel(topic="AI Safety", score=95)
```

### Error Handling

```python
from configurable_agents.core import StateBuilderError

try:
    StateModel = build_state_model(invalid_config)
except StateBuilderError as e:
    print(f"Builder error: {e}")
```

### Complete Public API

```python
# From configurable_agents.core

from configurable_agents.core import (
    build_state_model,      # Build state Pydantic model
    StateBuilderError,      # Exception for builder errors
)
```

---

## 📚 Dependencies Used

- `pydantic >= 2.0` - Dynamic model generation and validation
- Type system from T-003 (parse_type_string, get_python_type)

---

## 💡 Design Decisions

### Why Dynamic Models Instead of Generic Dict?

- Type safety at runtime (Pydantic validation)
- Better error messages (field-level validation)
- IDE autocomplete support (generated models have proper types)
- Consistent with LangGraph patterns (typed state objects)

### Why All Models Named "WorkflowState"?

- Readability in error messages and logs
- Consistent naming across workflows
- No need for hash-based names (models are ephemeral)
- Nested models use descriptive names (WorkflowState_metadata)

### Why No Redundant Validation?

- Config already validated by T-004 validator
- Trust that state_config is valid and consistent
- Fail-fast only for builder-specific issues (object without schema)
- Reduces code duplication and maintenance burden

### Why Support Both Schema Formats?

**Simple format** (type string only):
```python
{"name": "str", "age": "int"}
```

**Full format** (StateFieldConfig object):
```python
{"name": {"type": "str", "required": true}}
```

- Simple format is convenient for small configs
- Full format supports all features (required, defaults, descriptions)
- Both formats validated by T-003 schema models
- Builder handles both transparently

### Why Nested Model Naming?

- Example: `WorkflowState_metadata_flags`
- Descriptive names help with debugging
- Shows field path in error messages
- Avoids collisions between different nested objects

---

## 🧪 Tests Created

**File**: `tests/core/test_state_builder.py`

### Test Categories (30 tests total)

1. **Basic Types** (6 tests)
   - Build model with str, int, float, bool fields
   - Required vs optional fields
   - Default values
   - Field validation
   - Type validation (Pydantic enforces types)

2. **Collection Types** (6 tests)
   - Untyped list and dict
   - Typed list (list[str], list[int])
   - Typed dict (dict[str, int], dict[str, str])
   - Empty lists and dicts as defaults
   - Collection validation

3. **Nested Objects** (8 tests)
   - Single-level nesting
   - Multi-level nesting (3+ levels)
   - Required vs optional nested objects
   - Nested object validation
   - Nested object with default values
   - Model naming for nested objects

4. **Required/Optional/Default** (4 tests)
   - Required field missing (ValidationError)
   - Optional field defaults to None
   - Default value applied correctly
   - Default value validation

5. **Field Descriptions** (2 tests)
   - Descriptions included in model schema
   - Descriptions accessible via model_fields

6. **Error Handling** (4 tests)
   - Object without schema (StateBuilderError)
   - Empty nested schema (StateBuilderError)
   - Invalid type string (TypeParseError)
   - Missing required field (ValidationError)

---

## ✅ State Builder Features

### Supported Field Types

**Basic Types**:
- ✅ str, int, float, bool

**Collection Types**:
- ✅ list (untyped)
- ✅ dict (untyped)
- ✅ list[T] (typed, e.g., list[str])
- ✅ dict[K, V] (typed, e.g., dict[str, int])

**Nested Objects**:
- ✅ object (1 level deep)
- ✅ Deeply nested objects (3+ levels)

### Field Configuration

**Required Fields**:
- ✅ Must be provided when creating state instance
- ✅ ValidationError if missing

**Optional Fields**:
- ✅ Default to None if not provided
- ✅ Can be omitted when creating instance

**Default Values**:
- ✅ Applied automatically if field not provided
- ✅ Validated by Pydantic

**Field Descriptions**:
- ✅ Preserved in generated model
- ✅ Accessible via model_fields

### Model Generation

**Model Naming**:
- ✅ Top-level: `WorkflowState`
- ✅ Nested objects: `WorkflowState_fieldname`
- ✅ Deeply nested: `WorkflowState_field1_field2_field3`

**Type Validation**:
- ✅ Enforced by Pydantic at instance creation
- ✅ Type coercion where possible (int to float)
- ✅ ValidationError for incompatible types

**Model Reuse**:
- ✅ Each state_config generates new model
- ✅ Models are ephemeral (not cached)
- ✅ Safe for concurrent workflows

---

## 📖 Example Usage

### Simple State

```python
from configurable_agents.config import StateSchema, StateFieldConfig
from configurable_agents.core import build_state_model

# Define state
state_config = StateSchema(
    fields={
        "input": StateFieldConfig(type="str", required=True),
        "output": StateFieldConfig(type="str", required=False),
    }
)

# Build model
StateModel = build_state_model(state_config)

# Create instance
state = StateModel(input="Hello world")
assert state.input == "Hello world"
assert state.output is None
```

### State with Collections

```python
state_config = StateSchema(
    fields={
        "topic": StateFieldConfig(type="str", required=True),
        "tags": StateFieldConfig(type="list[str]", default=[]),
        "metadata": StateFieldConfig(type="dict[str, int]", default={}),
    }
)

StateModel = build_state_model(state_config)

state = StateModel(
    topic="AI",
    tags=["ai", "ml"],
    metadata={"views": 100, "likes": 50}
)
```

### State with Nested Objects

```python
state_config = StateSchema(
    fields={
        "article": StateFieldConfig(type="str", required=True),
        "author": StateFieldConfig(
            type="object",
            required=True,
            schema={
                "name": "str",
                "email": "str",
                "profile": {
                    "type": "object",
                    "schema": {"bio": "str", "avatar": "str"}
                }
            }
        ),
    }
)

StateModel = build_state_model(state_config)

state = StateModel(
    article="My article",
    author={
        "name": "Alice",
        "email": "alice@example.com",
        "profile": {"bio": "Writer", "avatar": "avatar.jpg"}
    }
)

assert state.author.name == "Alice"
assert state.author.profile.bio == "Writer"
```

---

## 📖 Example Error Messages

### Missing Required Field

```
ValidationError: 1 validation error for WorkflowState
topic
  Field required [type=missing, input_value={}, input_type=dict]
```

### Wrong Type

```
ValidationError: 1 validation error for WorkflowState
score
  Input should be a valid integer [type=int_type, input_value='not_a_number', input_type=str]
```

### Object Without Schema

```
StateBuilderError: Field 'metadata' has type 'object' but no 'schema' defined
```

### Empty Nested Schema

```
StateBuilderError: Field 'data' has type 'object' with empty schema
```

---

## 📖 Documentation Updated

- ✅ CHANGELOG.md (comprehensive entry created)
- ✅ docs/TASKS.md (T-006 marked DONE, progress updated to 7/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)

---

## 📝 Git Commit Template

```bash
git add .
git commit -m "T-006: State schema builder - Dynamic Pydantic models

- Implemented dynamic Pydantic model generation from StateSchema
- Supports all type system types (basic, collections, nested objects)
- Recursive nested object handling with meaningful names
- Required/optional fields, defaults, descriptions
- No redundant validation (leverages T-004)
- Fail-fast error handling

- Created 30 comprehensive tests
  - Basic types (str, int, float, bool)
  - Collection types (list, dict, list[T], dict[K,V])
  - Nested objects (1 level and 3+ levels deep)
  - Required/optional/default fields
  - Field descriptions
  - Error handling
  - Model reuse

Verification:
  pytest -v
  Expected: 202 passed (30 core + 172 existing)

Progress: 7/20 tasks (35%) - Foundation phase 7/7 complete!
Next: T-007 (Output Schema Builder)"
```

---

## 🔗 Related Documentation

- **[../../TASKS.md](../../TASKS.md)** - Task T-006 acceptance criteria
- **[../../SPEC.md](../../SPEC.md)** - State schema specification
- **[../../ARCHITECTURE.md](../../ARCHITECTURE.md)** - State builder component
- **[T-003_config_schema.md](./T-003_config_schema.md)** - Type system implementation
- **[T-005_type_system.md](./T-005_type_system.md)** - Type system reference

---

## 📖 Phase 1 Progress

With T-006 complete, **Phase 1 (Foundation) is 7/8 tasks complete** (87.5%):
- ✅ T-001: Project Setup
- ✅ T-002: Config Parser
- ✅ T-003: Config Schema (Pydantic Models)
- ✅ T-004: Config Validator
- ✅ T-004.5: Runtime Feature Gating
- ✅ T-005: Type System
- ✅ T-006: State Schema Builder
- ⏳ T-007: Output Schema Builder (next)

---

*Implementation completed: 2026-01-24*
*Next task: T-007 (Output Schema Builder)*
