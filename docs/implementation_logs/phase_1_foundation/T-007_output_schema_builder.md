# T-007: Output Schema Builder

**Status**: ✅ Complete
**Completed**: 2026-01-24
**Commit**: `9d453e9` - T-007: Output schema builder - Type-enforced LLM outputs
**Phase**: Phase 1 (Foundation)
**Progress After**: 8/20 tasks (40%)

---

## 🎯 What Was Done

- Implemented dynamic Pydantic model generation from OutputSchema configs
- Enables type-enforced LLM responses
- Supports simple outputs (single type wrapped in 'result' field)
- Supports object outputs (multiple fields)
- Supports all type system types (basic, collections)
- Includes field descriptions to help LLM understand what to return
- 29 comprehensive tests covering all scenarios
- Total: 231 tests passing (up from 202)
- **Phase 1 (Foundation) Complete**: 8/8 tasks done

---

## 📦 Files Created

### Source Code

```
src/configurable_agents/core/
└── output_builder.py (dynamic output model builder)
```

### Tests

```
tests/core/
└── test_output_builder.py (29 comprehensive tests)
```

---

## 🔧 How to Verify

### 1. Test output builder

```bash
pytest tests/core/test_output_builder.py -v
# Expected: 29 passed
```

### 2. Run full test suite

```bash
pytest -v
# Expected: 231 passed (29 new + 202 existing)
```

### 3. Use output builder

```python
from configurable_agents.config import OutputSchema, OutputSchemaField
from configurable_agents.core import build_output_model

# Simple output
schema = OutputSchema(type="str", description="Article text")
OutputModel = build_output_model(schema, "write")
output = OutputModel(result="Hello world")
assert output.result == "Hello world"

# Object output
schema = OutputSchema(
    type="object",
    fields=[
        OutputSchemaField(name="article", type="str", description="Article text"),
        OutputSchemaField(name="word_count", type="int", description="Word count"),
    ]
)
OutputModel = build_output_model(schema, "write")
output = OutputModel(article="Test article", word_count=100)
assert output.article == "Test article"
assert output.word_count == 100
```

---

## ✅ What to Expect

**Working**:
- ✅ Dynamic Pydantic models generated from output schemas
- ✅ Simple outputs wrapped in 'result' field
- ✅ Object outputs with explicit fields
- ✅ All type system types supported (basic, collections)
- ✅ Type validation enforced (ValidationError if wrong type)
- ✅ All fields required (ValidationError if missing)
- ✅ Field descriptions included in model schema (helps LLM)
- ✅ Clear error messages with node_id context
- ✅ Model naming: Output_{node_id}

**Not Yet Working**:
- ⚠️ Nested objects not yet supported (use dicts instead)
- ❌ No LLM integration yet (T-009: LLM Provider)
- ❌ No runtime output validation during workflow execution (T-011)

---

## 💻 Public API

### Main Function

```python
from configurable_agents.core import build_output_model, OutputBuilderError

# Build dynamic output model
OutputModel = build_output_model(output_schema, node_id="write")

# Create instance (simple output)
output = OutputModel(result="Generated article")

# Create instance (object output)
output = OutputModel(article="...", word_count=500)
```

### Error Handling

```python
from configurable_agents.core import OutputBuilderError

try:
    OutputModel = build_output_model(invalid_schema, "test")
except OutputBuilderError as e:
    print(f"Builder error: {e}")
```

### Complete Public API

```python
# From configurable_agents.core

from configurable_agents.core import (
    build_output_model,      # Build output Pydantic model
    OutputBuilderError,      # Exception for builder errors
)
```

---

## 📚 Dependencies Used

- `pydantic >= 2.0` - Dynamic model generation and validation
- Type system from T-003 (parse_type_string, get_python_type)

---

## 💡 Design Decisions

### Why Wrap Simple Outputs in 'result' Field?

- LLM structured output requires a Pydantic model (not raw str/int)
- Consistency: all outputs are models with named fields
- Example: `OutputModel(result="text")` instead of raw `"text"`
- Simplifies downstream code (always access fields by name)

### Why All Output Fields Required?

- LLM must provide all requested outputs (no optional outputs)
- Fail-fast if LLM doesn't generate expected fields
- Optional outputs would complicate error handling
- User can make state fields optional (different concern)

### Why Model Naming: Output_{node_id}?

- Clear which node the output is for
- Helpful in error messages and logs
- Example: `Output_write`, `Output_analyze`, `Output_summarize`
- Distinguishes output models from state models

### Why No Nested Objects?

- Keep v0.1 simple and focused
- Nested objects in outputs add complexity
- Can use dict[str, Any] as workaround
- Can add in future version if needed (v0.2+)

### Why Include Descriptions?

- LLM uses descriptions to understand what to generate
- Example: "article" field with description "Write a comprehensive article about the topic"
- Improves LLM output quality
- Standard practice for structured output

---

## 🧪 Tests Created

**File**: `tests/core/test_output_builder.py`

### Test Categories (29 tests total)

1. **Simple Outputs** (8 tests)
   - Build model for str, int, float, bool outputs
   - Wrapped in 'result' field
   - Type validation
   - Field descriptions preserved
   - Model naming

2. **Object Outputs** (10 tests)
   - Multiple fields
   - All type system types (basic, collections)
   - Required fields validation
   - Field order preserved
   - Descriptions for each field
   - Object with list field
   - Object with dict field
   - Object with typed collections

3. **Model Naming** (2 tests)
   - Model named Output_{node_id}
   - Different node_ids produce different names

4. **Error Handling** (5 tests)
   - Missing output_schema (OutputBuilderError)
   - Invalid type string (OutputBuilderError)
   - Nested objects not supported (OutputBuilderError)
   - Missing required field (ValidationError)
   - Wrong type (ValidationError)

5. **Round-trip Serialization** (2 tests)
   - model_dump() and model_dump_json() work
   - Can reconstruct from dict/json

6. **Validation Enforcement** (2 tests)
   - All fields required
   - Type validation enforced by Pydantic

---

## ✅ Output Builder Features

### Supported Output Types

**Simple Outputs** (wrapped in 'result' field):
- ✅ str
- ✅ int
- ✅ float
- ✅ bool
- ✅ list (untyped)
- ✅ dict (untyped)
- ✅ list[T] (typed)
- ✅ dict[K, V] (typed)

**Object Outputs** (multiple fields):
- ✅ Multiple fields with different types
- ✅ All basic types
- ✅ All collection types
- ✅ Field descriptions
- ⚠️ No nested objects (use dict instead)

### Model Generation

**Model Naming**:
- ✅ Pattern: `Output_{node_id}`
- ✅ Examples: `Output_write`, `Output_analyze`, `Output_summarize`

**Field Configuration**:
- ✅ All fields required
- ✅ Field descriptions included
- ✅ Type validation enforced by Pydantic

**Type Validation**:
- ✅ Enforced at model instantiation
- ✅ ValidationError for wrong types
- ✅ ValidationError for missing fields

---

## 📖 Example Usage

### Simple Output (String)

```python
from configurable_agents.config import OutputSchema
from configurable_agents.core import build_output_model

schema = OutputSchema(
    type="str",
    description="Generated article text"
)

OutputModel = build_output_model(schema, "write")

# Create output
output = OutputModel(result="This is the generated article...")
assert output.result == "This is the generated article..."
```

### Simple Output (List)

```python
schema = OutputSchema(
    type="list[str]",
    description="List of key points"
)

OutputModel = build_output_model(schema, "extract")

output = OutputModel(result=["Point 1", "Point 2", "Point 3"])
assert len(output.result) == 3
```

### Object Output (Multiple Fields)

```python
from configurable_agents.config import OutputSchemaField

schema = OutputSchema(
    type="object",
    fields=[
        OutputSchemaField(
            name="article",
            type="str",
            description="Full article text"
        ),
        OutputSchemaField(
            name="word_count",
            type="int",
            description="Number of words in article"
        ),
        OutputSchemaField(
            name="tags",
            type="list[str]",
            description="Relevant tags for the article"
        ),
    ]
)

OutputModel = build_output_model(schema, "write")

output = OutputModel(
    article="This is the article...",
    word_count=250,
    tags=["ai", "technology", "future"]
)

assert output.article == "This is the article..."
assert output.word_count == 250
assert len(output.tags) == 3
```

### Complex Output (Typed Collections)

```python
schema = OutputSchema(
    type="object",
    fields=[
        OutputSchemaField(
            name="summary",
            type="str",
            description="Article summary"
        ),
        OutputSchemaField(
            name="metadata",
            type="dict[str, int]",
            description="Article metadata (views, likes, shares)"
        ),
    ]
)

OutputModel = build_output_model(schema, "analyze")

output = OutputModel(
    summary="Summary here...",
    metadata={"views": 1000, "likes": 50, "shares": 25}
)

assert output.metadata["views"] == 1000
```

---

## 📖 Example Error Messages

### Missing Output Schema

```
OutputBuilderError: Node 'test': output_schema is required
```

### Invalid Type

```
OutputBuilderError: Node 'write': Invalid output type 'unknown_type': ...
```

### Nested Objects Not Supported

```
OutputBuilderError: Node 'test': Nested objects in output schema not yet supported.
Field 'metadata' has type 'object'. Use basic types, lists, or dicts instead.
```

### Missing Required Field (Pydantic)

```
ValidationError: 1 validation error for Output_write
result
  Field required [type=missing, input_value={}, input_type=dict]
```

### Wrong Type (Pydantic)

```
ValidationError: 1 validation error for Output_write
result
  Input should be a valid string [type=string_type, input_value=123, input_type=int]
```

---

## 📖 Documentation Updated

- ✅ CHANGELOG.md (comprehensive entry created)
- ✅ docs/TASKS.md (T-007 marked DONE, progress updated to 8/20, Phase 1 complete)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated, Phase 1 complete)

---

## 📝 Git Commit Template

```bash
git add .
git commit -m "T-007: Output schema builder - Type-enforced LLM outputs

- Implemented dynamic Pydantic model generation from OutputSchema
- Simple outputs wrapped in 'result' field (str, int, float, bool)
- Object outputs with multiple fields
- Supports all type system types (basic, collections)
- Type validation enforced by Pydantic
- All output fields required (LLM must provide them)
- Field descriptions preserved to help LLM

- Created 29 comprehensive tests
  - Simple outputs (str, int, float, bool)
  - Object outputs (multiple fields, all types)
  - Collection types (list, dict, typed variants)
  - Object with list/dict fields
  - Model naming and error handling
  - Round-trip serialization
  - Validation enforcement

Verification:
  pytest -v
  Expected: 231 passed (29 output builder + 202 existing)

Progress: 8/20 tasks (40%) - Phase 1 (Foundation) COMPLETE!
Next: T-008 (Tool Registry) - Phase 2 start

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## 🔗 Related Documentation

- **[../../TASKS.md](../../TASKS.md)** - Task T-007 acceptance criteria
- **[../../SPEC.md](../../SPEC.md)** - Output schema specification
- **[../../ARCHITECTURE.md](../../ARCHITECTURE.md)** - Output builder component
- **[T-003_config_schema.md](./T-003_config_schema.md)** - Type system implementation
- **[T-006_state_schema_builder.md](./T-006_state_schema_builder.md)** - State builder reference

---

## 📖 Phase 1 Complete!

With T-007 complete, **Phase 1 (Foundation) is 100% complete** (8/8 tasks):

✅ **Phase 1: Foundation** (8/8 tasks)
- ✅ T-001: Project Setup
- ✅ T-002: Config Parser (YAML/JSON)
- ✅ T-003: Config Schema (Pydantic Models)
- ✅ T-004: Config Validator
- ✅ T-004.5: Runtime Feature Gating
- ✅ T-005: Type System
- ✅ T-006: State Schema Builder
- ✅ T-007: Output Schema Builder

**Test Coverage**: 231 tests passing across all components

**What's Working**:
- Complete YAML/JSON config parsing
- Full Schema v1.0 Pydantic models
- Comprehensive config validation
- Runtime feature gating for v0.1/v0.2/v0.3
- Type system (basic, collections, objects)
- Dynamic state model generation
- Dynamic output model generation

**Next Phase**: Phase 2 - Core Execution
- T-008: Tool Registry (web search integration)
- T-009: LLM Provider (Google Gemini)
- T-010: Prompt Template Resolver
- T-011: Node Executor
- T-012: Graph Builder
- T-013: Runtime Executor

---

*Implementation completed: 2026-01-24*
*Next task: T-008 (Tool Registry) - Starting Phase 2*
