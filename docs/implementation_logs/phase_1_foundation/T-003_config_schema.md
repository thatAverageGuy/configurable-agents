# T-003: Config Schema (Pydantic Models)

**Status**: ✅ Complete
**Completed**: 2026-01-24
**Commit**: `dc9ef89` - T-003: Config schema - Pydantic models for Schema v1.0
**Phase**: Phase 1 (Foundation)
**Progress After**: 3/20 tasks (15%)

---

## 🎯 What Was Done

- Implemented complete type system for parsing type strings (str, int, float, bool, list, dict, list[T], dict[K,V], object)
- Created comprehensive Pydantic models for entire Schema v1.0
- Full Schema Day One: All models support features through v0.3 (ADR-009)
- 13 Pydantic models covering workflow, state, nodes, edges, optimization, config
- Type validation, field validation, cross-field validation
- Support for YAML/JSON round-trip conversion
- Created 103 new tests (31 type tests + 67 schema tests + 5 integration tests)
- Total: 124 tests passing (up from 21)

---

## 📦 Files Created

### Source Code

```
src/configurable_agents/config/
├── types.py (type string parsing system)
└── schema.py (13 Pydantic models for Schema v1.0)
```

### Tests

```
tests/config/
├── test_types.py (31 tests for type system)
├── test_schema.py (67 tests for Pydantic models)
└── test_schema_integration.py (5 integration tests)
```

### Pydantic Models Created

```python
# Top-level
WorkflowConfig

# Components
FlowMetadata
StateSchema, StateFieldConfig
NodeConfig
OutputSchema, OutputSchemaField
EdgeConfig, Route, RouteCondition

# Configuration
OptimizationConfig, OptimizeConfig
LLMConfig
ExecutionConfig
GlobalConfig
ObservabilityConfig, ObservabilityMLFlowConfig, ObservabilityLoggingConfig
```

---

## 🔧 How to Verify

### 1. Test type system

```bash
pytest tests/config/test_types.py -v
# Expected: 31 passed
```

### 2. Test Pydantic models

```bash
pytest tests/config/test_schema.py -v
# Expected: 67 passed
```

### 3. Test integration (YAML → Pydantic)

```bash
pytest tests/config/test_schema_integration.py -v
# Expected: 5 passed
```

### 4. Run full test suite

```bash
pytest -v
# Expected: 124 passed (18 parser + 3 setup + 31 types + 67 schema + 5 integration)
```

### 5. Load and validate a config

```python
from configurable_agents.config import parse_config_file, WorkflowConfig

# Load YAML to dict
config_dict = parse_config_file("workflow.yaml")

# Parse into Pydantic model (validates structure)
config = WorkflowConfig(**config_dict)

# Access validated data
print(f"Flow: {config.flow.name}")
print(f"Nodes: {len(config.nodes)}")
```

---

## ✅ What to Expect

**Working**:
- ✅ Complete type system (str, int, float, bool, list, dict, nested)
- ✅ Full Schema v1.0 Pydantic models
- ✅ YAML/JSON configs parse into type-safe models
- ✅ Validation errors with helpful messages
- ✅ Support for v0.2/v0.3 features in schema (conditional edges, optimization)
- ✅ Round-trip: config → dict → YAML/JSON → dict → config

**Not Yet Working**:
- ❌ No cross-reference validation yet (T-004: outputs match state, node IDs exist)
- ❌ No runtime feature gating yet (T-004.5: reject unsupported features)

---

## 💻 Public API

### Type System Examples

```python
from configurable_agents.config.types import parse_type_string, get_python_type

# Parse basic types
parse_type_string("str")     # {"kind": "basic", "type": str}
parse_type_string("int")     # {"kind": "basic", "type": int}

# Parse collection types
parse_type_string("list[str]")        # {"kind": "list", "item_type": ...}
parse_type_string("dict[str, int]")   # {"kind": "dict", "key_type": ..., "value_type": ...}

# Parse object types
parse_type_string("object")  # {"kind": "object"}

# Get Python type
get_python_type("str")       # str
get_python_type("list[int]") # list
```

### Pydantic Model Examples

```python
from configurable_agents.config import WorkflowConfig, FlowMetadata, StateSchema

# Minimal config
config = WorkflowConfig(
    schema_version="1.0",
    flow=FlowMetadata(name="my_flow"),
    state=StateSchema(fields={"input": {"type": "str"}}),
    nodes=[...],
    edges=[...]
)

# Access validated data
config.flow.name              # "my_flow"
config.state.fields["input"]  # StateFieldConfig(type="str", ...)

# Export to dict/YAML/JSON
config_dict = config.model_dump(by_alias=True, exclude_none=True)
```

### Complete Public API

```python
# From configurable_agents.config

# Parser (T-002)
from configurable_agents.config import parse_config_file, ConfigLoader

# Types (T-003)
from configurable_agents.config import (
    parse_type_string,
    validate_type_string,
    get_python_type,
    TypeParseError
)

# Schema models (T-003)
from configurable_agents.config import (
    WorkflowConfig,
    FlowMetadata,
    StateSchema,
    StateFieldConfig,
    NodeConfig,
    OutputSchema,
    EdgeConfig,
    OptimizationConfig,
    LLMConfig,
    GlobalConfig,
    # ... and 8 more models
)
```

---

## 📚 Dependencies Used

- `pydantic >= 2.0` - Schema validation and models
- Type hints from `typing` - Python type system

---

## 💡 Design Decisions

### Why Full Schema Day One (ADR-009)?

- Schema supports all features through v0.3 from day one
- Conditional edges (v0.2+) and optimization config (v0.3+) accepted in schema
- Runtime will implement features incrementally
- Users can write future configs now, validated at runtime (T-004.5)

### Why separate types.py?

- Isolates type parsing logic from schema models
- Type system reused by state builder and output builder
- Easier to test and maintain
- Clear separation of concerns

### Why 13 Pydantic models?

- Each major config section gets its own model
- Nested models for complex structures (edges, optimization)
- Enables granular validation and better error messages
- Supports YAML/JSON round-trip with proper serialization

---

## 🧪 Tests Created

### Type System Tests (31 tests)

**File**: `tests/config/test_types.py`

- Basic type parsing (str, int, float, bool)
- Collection type parsing (list, dict, list[T], dict[K,V])
- Object type parsing
- Type validation
- Error handling for invalid types
- Python type conversion

### Schema Model Tests (67 tests)

**File**: `tests/config/test_schema.py`

- WorkflowConfig validation
- FlowMetadata validation
- StateSchema validation (required/optional fields, defaults)
- NodeConfig validation (IDs, types, outputs)
- OutputSchema validation (simple vs object outputs)
- EdgeConfig validation (linear vs conditional)
- OptimizationConfig validation
- LLMConfig validation (temperature, timeouts)
- GlobalConfig and ObservabilityConfig
- Cross-field validation (required + default conflict)
- Model-level validation (unique node IDs)
- YAML/JSON aliasing (from, schema)

### Integration Tests (5 tests)

**File**: `tests/config/test_schema_integration.py`

- YAML → dict → Pydantic round-trip
- JSON → dict → Pydantic round-trip
- Pydantic → dict → YAML export
- Complex nested config validation
- Error message quality

---

## ✅ Validation Features

- ✅ Schema version must be "1.0"
- ✅ Flow name cannot be empty
- ✅ State must have at least one field
- ✅ Required fields cannot have defaults
- ✅ Node IDs must be unique
- ✅ Node IDs must be valid Python identifiers (no hyphens)
- ✅ Temperature must be 0.0-1.0
- ✅ Timeouts/retries must be positive
- ✅ Output schema for type="object" must have fields
- ✅ Edges must have either 'to' or 'routes' (not both)
- ✅ Log levels validated (DEBUG, INFO, WARNING, ERROR, CRITICAL)

---

## 📖 Documentation Updated

- ✅ CHANGELOG.md (comprehensive entry created)
- ✅ docs/TASKS.md (T-003 marked DONE, progress updated)
- ✅ docs/DISCUSSION.md (status updated to 3/20 tasks)
- ✅ README.md (progress statistics updated)

---

## 📝 Git Commit Template

```bash
git add .
git commit -m "T-003: Config schema - Pydantic models for Schema v1.0

- Implemented type system for parsing type strings
  - Basic types: str, int, float, bool
  - Collection types: list, dict, list[T], dict[K,V]
  - Nested object types: object
  - 31 type system tests

- Created 13 Pydantic models for complete Schema v1.0
  - WorkflowConfig (top-level)
  - FlowMetadata, StateSchema, NodeConfig, EdgeConfig
  - OutputSchema with field definitions
  - OptimizationConfig, LLMConfig, ExecutionConfig, GlobalConfig
  - ObservabilityConfig for v0.2+ features
  - 67 schema model tests

- Full Schema Day One (ADR-009)
  - Schema supports all features through v0.3
  - Conditional edges (v0.2+) accepted in schema
  - Optimization config (v0.3+) accepted in schema
  - Runtime will implement features incrementally

- Comprehensive validation
  - Field-level validation (required, defaults, types)
  - Cross-field validation (required + default conflict)
  - Model-level validation (unique node IDs)
  - Type validation (temperature 0-1, positive integers)

- YAML/JSON round-trip support
  - Parse YAML/JSON → dict → Pydantic model
  - Export Pydantic model → dict → YAML/JSON
  - Aliases for reserved keywords (from, schema)
  - 5 integration tests

Verification:
  pytest -v
  Expected: 124 passed (31 types + 67 schema + 5 integration + 21 existing)

Progress: 3/20 tasks (15%) - Foundation phase
Next: T-004 (Config Validator)"
```

---

## 🔗 Related Documentation

- **[../../TASKS.md](../../TASKS.md)** - Task T-003 acceptance criteria
- **[../../SPEC.md](../../SPEC.md)** - Schema v1.0 specification
- **[../../ARCHITECTURE.md](../../ARCHITECTURE.md)** - Config schema component
- **[../../adr/ADR-009.md](../../adr/)** - Full Schema Day One decision

---

*Implementation completed: 2026-01-24*
*Next task: T-004 (Config Validator)*
