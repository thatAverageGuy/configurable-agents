# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added - T-004.5: Runtime Feature Gating ✅

**Commit**: T-004.5: Runtime feature gating - Version checks

**What Was Done**:
- Implemented runtime feature gating to reject unsupported v0.2+ and v0.3+ features
- Hard blocks for incompatible features (conditional routing)
- Soft blocks with warnings for future features (optimization, MLFlow)
- Helpful error messages with version timelines and workarounds
- Feature support query API
- 19 comprehensive tests for all feature gates
- Total: 172 tests passing (up from 153)

**Files Created**:
```
src/configurable_agents/runtime/
└── feature_gate.py (runtime version checks and feature gating)

tests/runtime/
├── __init__.py
└── test_feature_gate.py (19 comprehensive tests)
```

**Feature Gating System**:

**Hard Blocks (UnsupportedFeatureError)**:
- ✅ Conditional routing (edge routes) - v0.2+ feature
  - Raises error with timeline and workaround
  - Suggests using linear edges instead
  - Points to roadmap

**Soft Blocks (UserWarning)**:
- ✅ Global DSPy optimization (optimization.enabled) - v0.3+ feature
  - Warns that feature will be IGNORED
  - Workflow runs without optimization
- ✅ Node-level optimization (node.optimize.enabled) - v0.3+ feature
  - Warns per-node that optimization ignored
- ✅ MLFlow observability (config.observability.mlflow) - v0.2+ feature
  - Warns that only console logging available
  - MLFlow tracking ignored

**Supported in v0.1**:
- ✅ Basic logging (config.observability.logging)
- ✅ Linear workflows
- ✅ All core features (state, nodes, LLM, tools)

**How to Verify**:

1. **Test feature gates**:
   ```bash
   pytest tests/runtime/test_feature_gate.py -v
   # Expected: 19 passed
   ```

2. **Run full test suite**:
   ```bash
   pytest -v
   # Expected: 172 passed (19 runtime + 153 existing)
   ```

3. **Use feature gating**:
   ```python
   from configurable_agents.config import parse_config_file, WorkflowConfig
   from configurable_agents.runtime import validate_runtime_support, UnsupportedFeatureError

   # Load config
   config_dict = parse_config_file("workflow.yaml")
   config = WorkflowConfig(**config_dict)

   # Check runtime support (raises if unsupported features)
   try:
       validate_runtime_support(config)
       print("✅ Config is compatible with v0.1 runtime")
   except UnsupportedFeatureError as e:
       print(f"❌ {e}")
       print(f"   Available in: {e.available_in}")
       print(f"   Timeline: {e.timeline}")
       print(f"   Workaround: {e.workaround}")
   ```

4. **Query feature support**:
   ```python
   from configurable_agents.runtime import check_feature_support

   # Check if a feature is supported
   result = check_feature_support("Conditional routing (if/else)")
   print(f"Supported: {result['supported']}")
   print(f"Available in: {result['version']}")
   print(f"Timeline: {result['timeline']}")
   ```

**What to Expect**:

- ✅ Configs with v0.2+ features are rejected at runtime with clear errors
- ✅ Configs with v0.3+ features trigger warnings but still run (degraded mode)
- ✅ Error messages include version info, timeline, and workarounds
- ✅ Valid v0.1 configs pass without errors or warnings
- ✅ Feature support can be queried programmatically

**Example Error Messages**:

```python
# Hard block - conditional routing
UnsupportedFeatureError: Feature 'Conditional routing (edge routes)' is not supported in v0.1
Available in: v0.2
Estimated timeline: 8-12 weeks from initial release

Workaround: Use linear edges (from/to) instead. For decision logic, create multiple separate workflows and chain them externally.

See roadmap: docs/PROJECT_VISION.md

# Soft block - optimization
UserWarning: DSPy optimization (optimization.enabled=true) is not supported in v0.1.
This setting will be IGNORED. Available in: v0.3 (12-16 weeks from initial release).
Your workflow will run without optimization. See docs/PROJECT_VISION.md for roadmap.
```

**Public API**:
```python
# From configurable_agents.runtime

from configurable_agents.runtime import (
    UnsupportedFeatureError,      # Exception for hard blocks
    validate_runtime_support,      # Main validation function
    get_supported_features,        # Get feature list
    check_feature_support,         # Check specific feature
)
```

**Documentation Updated**:
- ✅ CHANGELOG.md (this file)
- ✅ docs/TASKS.md (T-004.5 marked DONE, progress updated to 5/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)

**Git Commit Command**:
```bash
git add .
git commit -m "T-004.5: Runtime feature gating - Version checks

- Implemented feature gating for v0.2+ and v0.3+ features
  - Hard blocks: Conditional routing (UnsupportedFeatureError)
  - Soft blocks: Optimization, MLFlow (UserWarning)
  - Clear error messages with timelines and workarounds

- Feature support query API
  - get_supported_features() - list all features
  - check_feature_support(name) - check specific feature
  - Returns version, timeline, support status

- Comprehensive error messages
  - Feature name and version when available
  - Timeline estimate (8-12 weeks, 12-16 weeks, etc.)
  - Workarounds for v0.1
  - Links to roadmap documentation

- Created 19 comprehensive tests
  - Valid v0.1 configs pass
  - Conditional routing blocked (hard)
  - Optimization warned (soft)
  - MLFlow observability warned (soft)
  - Multiple feature combinations
  - Feature query API

Verification:
  pytest -v
  Expected: 172 passed (19 runtime + 153 existing)

Progress: 5/20 tasks (25%) - Foundation phase
Next: T-005 (Type System - mostly done in T-003)"
```

---

### Added - T-005: Type System ✅

**Commit**: T-005: Type system - Formal closure (implemented in T-003)

**What Was Done**:
- Formally closed T-005 by documenting existing type system implementation
- Type system was already implemented as part of T-003 (Config Schema)
- 31 comprehensive tests already passing
- All acceptance criteria met

**Type System Features**:
- ✅ Parse basic types: `str`, `int`, `float`, `bool`
- ✅ Parse collection types: `list`, `dict`, `list[str]`, `dict[str, int]`
- ✅ Parse nested object types: `object` (with schema in StateFieldConfig)
- ✅ Convert type strings to Python types
- ✅ Validate type strings (with TypeParseError for invalid types)
- ✅ Support type descriptions (via StateFieldConfig.description field)
- ✅ Comprehensive error messages for invalid types

**Files** (created in T-003):
```
src/configurable_agents/config/
└── types.py (type parsing and validation utilities)

tests/config/
└── test_types.py (31 comprehensive tests)
```

**Public API**:
```python
from configurable_agents.config.types import (
    TypeParseError,              # Exception for invalid types
    parse_type_string,           # Parse type string to dict
    validate_type_string,        # Validate type string
    get_python_type,             # Convert to Python type
)
```

**How to Verify**:

1. **Test type system**:
   ```bash
   pytest tests/config/test_types.py -v
   # Expected: 31 passed
   ```

2. **Run full test suite**:
   ```bash
   pytest -v
   # Expected: 172 passed (no change from T-004.5)
   ```

3. **Use type parsing**:
   ```python
   from configurable_agents.config.types import parse_type_string, get_python_type

   # Parse type string
   parsed = parse_type_string("list[str]")
   print(parsed)  # {"kind": "list", "item_type": {...}, "name": "list[str]"}

   # Get Python type
   py_type = get_python_type("list[str]")
   print(py_type)  # <class 'list'>

   # Validate
   from configurable_agents.config.types import validate_type_string
   assert validate_type_string("dict[str, int]") is True
   assert validate_type_string("unknown_type") is False
   ```

**What to Expect**:

- ✅ All type strings used in configs are validated
- ✅ Invalid types raise TypeParseError with helpful messages
- ✅ Type descriptions supported at field level (StateFieldConfig)
- ✅ Type system fully integrated with Pydantic schema validation

**Note**: Files are in `config/` package (not `core/` as originally specified in task). Type descriptions are handled via `StateFieldConfig.description` field in schema.py, not in the type system itself.

**Documentation Updated**:
- ✅ CHANGELOG.md (this file)
- ✅ docs/TASKS.md (T-005 marked DONE, progress updated to 6/20)
- ✅ README.md (progress statistics updated)

**Git Commit Command**:
```bash
git add docs/
git commit -m "T-005: Type system - Formal closure

- Type system already implemented in T-003
- 31 tests passing (parse_type_string, validate_type_string, get_python_type)
- All acceptance criteria met
- Type descriptions supported via StateFieldConfig.description

Verification:
  pytest tests/config/test_types.py -v
  Expected: 31 passed

Progress: 6/20 tasks (30%) - Foundation phase 6/7 complete
Next: T-006 (State Schema Builder)"
```

---

### Added - T-004: Config Validator ✅

**Commit**: T-004: Config validator - Comprehensive validation

**What Was Done**:
- Implemented comprehensive config validation beyond Pydantic schema checks
- Cross-reference validation (node IDs, state fields, output types)
- Graph structure validation (connectivity, reachability)
- Linear flow enforcement (v0.1 constraints: no cycles, no conditional routing)
- Fail-fast error handling with helpful suggestions
- "Did you mean...?" suggestions for typos using edit distance
- Context-aware error messages with clear guidance
- 29 comprehensive validator tests
- Total: 153 tests passing (up from 124)

**Files Created**:
```
src/configurable_agents/config/
└── validator.py (validation engine with 8 validation stages)

tests/config/
└── test_validator.py (29 comprehensive tests)
```

**Validation Features**:
- ✅ Edge reference validation (from/to point to valid nodes)
- ✅ Node output validation (outputs exist in state fields)
- ✅ Output schema alignment (schema fields match outputs list)
- ✅ Type alignment (output types match state field types)
- ✅ Prompt placeholder validation ({variable} references valid fields)
- ✅ State type validation (all type strings are valid)
- ✅ Graph structure (START/END connectivity, no orphaned nodes)
- ✅ Linear flow constraints (no cycles, no conditional routing, single entry point)

**How to Verify**:

1. **Test validation**:
   ```bash
   pytest tests/config/test_validator.py -v
   # Expected: 29 passed
   ```

2. **Run full test suite**:
   ```bash
   pytest -v
   # Expected: 153 passed (18 parser + 67 schema + 31 types + 5 integration + 29 validator + 3 setup)
   ```

3. **Validate a config programmatically**:
   ```python
   from configurable_agents.config import parse_config_file, WorkflowConfig, validate_config

   # Load and parse YAML/JSON
   config_dict = parse_config_file("workflow.yaml")
   config = WorkflowConfig(**config_dict)

   # Validate (raises ValidationError if invalid)
   validate_config(config)
   print("Config is valid!")
   ```

**What to Expect**:
- ✅ Comprehensive validation catches common errors early
- ✅ Helpful error messages with context and suggestions
- ✅ "Did you mean 'process'?" for typos (edit distance ≤ 2)
- ✅ Fail-fast: stops at first error category
- ✅ Clear distinction between v0.1 features vs v0.2+ (with timeline info)
- ✅ Graph validation ensures all nodes reachable and can reach END
- ✅ Type safety: output types must match state field types
- ✅ No hidden surprises: placeholders validated at parse time

**Example Error Messages**:
```python
# Missing state field
ValidationError: Node 'process': output 'missing_field' not found in state fields
Suggestion: Add 'missing_field' to state.fields or check spelling. Available fields: ['input', 'output']

# Typo in node reference
ValidationError: Edge 0: 'to' references unknown node 'proces'
Suggestion: Did you mean 'process'?

# Cycle detected
ValidationError: Cycle detected in workflow: step1 -> step2 -> step1
Suggestion: Remove edges to break the cycle. Linear workflows cannot have loops (loops available in v0.2+)
Context: v0.1 supports linear flows only

# Conditional routing (v0.2+ feature)
ValidationError: Edge 0: Conditional routing not supported in v0.1
Suggestion: Use linear edges (from/to) instead. Conditional routing available in v0.2+ (8-12 weeks)
Context: Edge: START -> routes. See docs/PROJECT_VISION.md for roadmap
```

**Validation Stages** (fail-fast order):
1. Edge references (nodes exist)
2. Node outputs (state fields exist)
3. Output schema alignment (schema ↔ outputs)
4. Type alignment (output types ↔ state types)
5. Prompt placeholders (valid references)
6. State types (valid type strings)
7. Linear flow constraints (v0.1 specific)
8. Graph structure (connectivity)

**Public API Updated**:
```python
# From configurable_agents.config

# Validator (T-004)
from configurable_agents.config import (
    ValidationError,   # Custom exception with helpful messages
    validate_config,   # Main validation function
)

# Usage
try:
    validate_config(config)
except ValidationError as e:
    print(e)  # Includes message, context, and suggestion
```

**Documentation Updated**:
- ✅ CHANGELOG.md (this file)
- ✅ docs/TASKS.md (T-004 marked DONE, progress updated to 4/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)

**Git Commit Command**:
```bash
git add .
git commit -m "T-004: Config validator - Comprehensive validation

- Implemented cross-reference validation
  - Node IDs, state fields, output types
  - Prompt placeholders, type alignment
  - 'Did you mean?' suggestions for typos

- Implemented graph validation
  - START/END connectivity
  - All nodes reachable from START
  - All nodes have path to END
  - No orphaned nodes

- Implemented linear flow enforcement (v0.1)
  - No conditional routing (v0.2+ feature)
  - No cycles in graph
  - Each node has at most one outgoing edge
  - Single entry point from START

- Fail-fast error handling
  - Stops at first error category
  - Context-aware messages
  - Helpful suggestions with alternatives

- Created 29 comprehensive tests
  - Valid config tests
  - Edge reference validation
  - Cross-reference validation
  - Type alignment validation
  - Graph structure validation
  - Linear flow constraint tests

Verification:
  pytest -v
  Expected: 153 passed (29 validator + 124 existing)

Progress: 4/20 tasks (20%) - Foundation phase
Next: T-004.5 (Runtime Feature Gating)"
```

---

## [0.1.0-dev] - 2026-01-24

### Added - T-003: Config Schema (Pydantic Models) ✅

**Commit**: T-003: Config schema - Pydantic models for Schema v1.0

**What Was Done**:
- Implemented complete type system for parsing type strings (str, int, float, bool, list, dict, list[T], dict[K,V], object)
- Created comprehensive Pydantic models for entire Schema v1.0
- Full Schema Day One: All models support features through v0.3 (ADR-009)
- 13 Pydantic models covering workflow, state, nodes, edges, optimization, config
- Type validation, field validation, cross-field validation
- Support for YAML/JSON round-trip conversion
- Created 103 new tests (31 type tests + 67 schema tests + 5 integration tests)
- Total: 124 tests passing (up from 21)

**Files Created**:
```
src/configurable_agents/config/
├── types.py (type string parsing system)
└── schema.py (13 Pydantic models for Schema v1.0)

tests/config/
├── test_types.py (31 tests for type system)
├── test_schema.py (67 tests for Pydantic models)
└── test_schema_integration.py (5 integration tests)
```

**Pydantic Models Created**:
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

**How to Verify**:

1. **Test type system**:
   ```bash
   pytest tests/config/test_types.py -v
   # Expected: 31 passed
   ```

2. **Test Pydantic models**:
   ```bash
   pytest tests/config/test_schema.py -v
   # Expected: 67 passed
   ```

3. **Test integration (YAML → Pydantic)**:
   ```bash
   pytest tests/config/test_schema_integration.py -v
   # Expected: 5 passed
   ```

4. **Run full test suite**:
   ```bash
   pytest -v
   # Expected: 124 passed (18 parser + 3 setup + 31 types + 67 schema + 5 integration)
   ```

5. **Load and validate a config**:
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

**What to Expect**:
- ✅ Complete type system (str, int, float, bool, list, dict, nested)
- ✅ Full Schema v1.0 Pydantic models
- ✅ YAML/JSON configs parse into type-safe models
- ✅ Validation errors with helpful messages
- ✅ Support for v0.2/v0.3 features in schema (conditional edges, optimization)
- ✅ Round-trip: config → dict → YAML/JSON → dict → config
- ❌ No cross-reference validation yet (T-004: outputs match state, node IDs exist)
- ❌ No runtime feature gating yet (T-004.5: reject unsupported features)

**Type System Examples**:
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

**Pydantic Model Examples**:
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

**Validation Features**:
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

**Public API Updated**:
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

**Dependencies Used**:
- `pydantic >= 2.0` - Schema validation and models
- Type hints from `typing` - Python type system

**Documentation Updated**:
- ✅ CHANGELOG.md (this file)
- ✅ docs/TASKS.md (T-003 marked DONE, progress updated)
- ✅ docs/DISCUSSION.md (status updated to 3/20 tasks)
- ✅ README.md (progress statistics updated)

**Git Commit Command**:
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

### Added - T-002: Config Parser ✅

**Commit**: T-002: Config parser - YAML and JSON support

**What Was Done**:
- Implemented `ConfigLoader` class for loading YAML/JSON files
- Auto-detects format from file extension (.yaml, .yml, .json)
- Handles both absolute and relative file paths
- Comprehensive error handling with helpful messages
- Convenience function `parse_config_file()` for simple use cases
- Created 18 comprehensive unit tests for parser (all pass)
- Created 3 setup verification tests
- Total: 21 tests passing
- Test fixtures for valid/invalid YAML and JSON
- **Automated setup scripts** for one-command venv setup (Windows & Unix)
- Setup scripts check if venv exists to avoid redundant installations

**Files Created**:
```
src/configurable_agents/config/
├── parser.py (ConfigLoader class + parse_config_file function)
└── __init__.py (exports public API)

tests/config/
├── __init__.py
├── test_parser.py (18 test functions)
└── fixtures/
    ├── valid_config.yaml
    ├── valid_config.json
    ├── invalid_syntax.yaml
    └── invalid_syntax.json

Development Setup:
├── setup.bat (Windows automated setup)
├── setup.sh (Unix/Linux/macOS automated setup)
└── SETUP.md (updated with Quick Setup section)
```

**How to Verify**:

1. **Test imports work**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file, ConfigLoader; print('Imports OK')"
   # Expected: Imports OK
   ```

2. **Load a YAML file**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file; config = parse_config_file('tests/config/fixtures/valid_config.yaml'); print('Flow:', config['flow']['name'])"
   # Expected: Flow: test_workflow
   ```

3. **Load a JSON file**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file; config = parse_config_file('tests/config/fixtures/valid_config.json'); print('Flow:', config['flow']['name'])"
   # Expected: Flow: test_workflow
   ```

4. **Test error handling** (file not found):
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file; parse_config_file('missing.yaml')"
   # Expected: FileNotFoundError: Config file not found: missing.yaml
   ```

5. **Test error handling** (invalid syntax):
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file; parse_config_file('tests/config/fixtures/invalid_syntax.yaml')"
   # Expected: ConfigParseError: Invalid YAML syntax...
   ```

6. **Run automated setup** (recommended - installs venv & dependencies):
   ```bash
   # Windows
   setup.bat

   # Unix/Linux/macOS
   ./setup.sh
   # Expected: Virtual environment created, dependencies installed
   ```

7. **Run full test suite** (after running setup script):
   ```bash
   .venv/Scripts/pytest tests/config/test_parser.py -v  # Windows
   .venv/bin/pytest tests/config/test_parser.py -v      # Unix
   # Expected: 18 passed in ~0.1s
   ```

**What to Expect**:
- ✅ Load YAML files (.yaml, .yml extensions)
- ✅ Load JSON files (.json extension)
- ✅ Auto-detect format from extension
- ✅ Both absolute and relative paths work
- ✅ Clear error messages for file not found
- ✅ Clear error messages for syntax errors
- ✅ Raises `ConfigParseError` for unsupported extensions
- ❌ No validation yet (returns raw dict, validation is T-004)
- ❌ No programmatic dict loading yet (just files)

**Public API**:
```python
# Recommended usage (convenience function)
from configurable_agents.config import parse_config_file

config = parse_config_file("workflow.yaml")  # or .json
# Returns: dict with config structure

# Advanced usage (class)
from configurable_agents.config import ConfigLoader

loader = ConfigLoader()
config = loader.load_file("workflow.yaml")
# Returns: dict with config structure

# Error handling
from configurable_agents.config import ConfigParseError

try:
    config = parse_config_file("config.yaml")
except FileNotFoundError:
    print("File not found")
except ConfigParseError as e:
    print(f"Parse error: {e}")
```

**Dependencies Used**:
- `pyyaml` - YAML parsing
- `json` (built-in) - JSON parsing
- `pathlib` (built-in) - Path handling

**Documentation Updated**:
- ✅ docs/TASKS.md (T-002 implementation details added)
- ✅ docs/ARCHITECTURE.md (Component 1 updated)
- ✅ docs/DISCUSSION.md (T-002 decisions documented)

**Git Commit Command**:
```bash
git add .
git commit -m "T-002: Config parser - YAML and JSON support

- Implemented ConfigLoader class with YAML/JSON auto-detection
- Added parse_config_file() convenience function
- Support for .yaml, .yml, and .json file extensions
- Comprehensive error handling (FileNotFoundError, ConfigParseError)
- Both absolute and relative path support
- Created 18 unit tests with valid/invalid fixtures
- Exported public API from config module
- Added automated setup scripts (setup.bat, setup.sh)
- Setup scripts check for existing venv to avoid redundant installs
- Updated SETUP.md with Quick Setup section

Verification:
  ./setup.sh  # or setup.bat on Windows
  .venv/Scripts/pytest tests/config/test_parser.py -v
  Expected: 18 passed

Progress: 2/20 tasks (10%) - Foundation phase
Next: T-003 (Config Schema - Pydantic Models)"
```

---

### Added - T-001: Project Setup ✅

**Commit**: T-001: Project setup - Package structure and dependencies

**What Was Done**:
- Created Python package structure (`src/configurable_agents/`)
- Set up all core modules: `config/`, `core/`, `llm/`, `tools/`, `runtime/`
- Configured dependencies in `pyproject.toml`
- Created development environment setup files
- Added logging configuration
- Set up comprehensive test structure
- Created development documentation

**Files Created**:
```
src/configurable_agents/
├── __init__.py (v0.1.0-dev)
├── logging_config.py
├── config/__init__.py
├── core/__init__.py
├── llm/__init__.py
├── tools/__init__.py
└── runtime/__init__.py

tests/
├── __init__.py
├── conftest.py (shared fixtures)
├── test_setup.py (verification tests)
└── {config,core,llm,tools,runtime,integration}/

Configuration:
├── pyproject.toml (dependencies & project metadata)
├── pytest.ini (test configuration)
├── .env.example (API key template)
└── .gitignore (comprehensive Python patterns)

Documentation:
├── README.md (complete user-facing documentation)
├── SETUP.md (development setup guide)
└── CHANGELOG.md (this file)
```

**How to Verify**:

1. **Check package structure exists**:
   ```bash
   ls -la src/configurable_agents/
   # Should see: __init__.py, logging_config.py, and 5 subdirectories
   ```

2. **Verify package imports work**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); import configurable_agents; print(f'Version: {configurable_agents.__version__}')"
   # Expected output: Version: 0.1.0-dev
   ```

3. **Verify all submodules import**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents import config, core, llm, tools, runtime; print('All modules imported successfully')"
   # Expected output: All modules imported successfully
   ```

4. **Check dependencies are defined**:
   ```bash
   grep -A 10 "dependencies = \[" pyproject.toml
   # Should show: pydantic, pyyaml, langgraph, langchain, etc.
   ```

5. **Verify test structure**:
   ```bash
   ls -la tests/
   # Should see: __init__.py, conftest.py, test_setup.py, and subdirectories
   ```

6. **Check environment template exists**:
   ```bash
   cat .env.example
   # Should show: GOOGLE_API_KEY, SERPER_API_KEY placeholders
   ```

**What to Expect**:
- ✅ Clean package structure following Python best practices
- ✅ All imports work (no module errors)
- ✅ Test framework ready (pytest configured)
- ✅ Dependencies declared (not yet installed by user)
- ✅ Development documentation available
- ❌ No actual functionality yet (just structure)
- ❌ Tests will pass but modules are empty placeholders

**Next Steps for User**:
```bash
# Install the package in development mode
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env

# Edit .env with your API keys (not needed until T-009)
# GOOGLE_API_KEY=your-key-here

# Verify installation
python -c "import configurable_agents; print(configurable_agents.__version__)"

# Run setup verification tests
pytest tests/test_setup.py -v
```

**Dependencies Status**:
- Core: pydantic, pyyaml, langgraph, langchain, langchain-google-genai, python-dotenv
- Dev: pytest, pytest-cov, pytest-asyncio, black, ruff, mypy
- Status: Declared in pyproject.toml, not yet used in code

**Documentation Updated**:
- ✅ docs/TASKS.md (T-001 marked DONE, progress tracker added)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (complete rewrite with roadmap)
- ✅ SETUP.md (development guide created)
- ✅ CHANGELOG.md (this file created)

**Git Commit Command**:
```bash
git add .
git commit -m "T-001: Project setup - Package structure and dependencies

- Created src/configurable_agents/ package structure
- Set up config, core, llm, tools, runtime modules
- Configured pyproject.toml with all dependencies
- Added pytest configuration and test structure
- Created .env.example for API keys
- Updated .gitignore with comprehensive Python patterns
- Added logging_config.py for application logging
- Created SETUP.md development guide
- Rewrote README.md with roadmap and progress tracker
- Updated docs/TASKS.md and docs/DISCUSSION.md

Verification: python -c 'import sys; sys.path.insert(0, \"src\"); import configurable_agents; print(configurable_agents.__version__)'
Expected: 0.1.0-dev

Progress: 1/20 tasks (5%) - Foundation phase
Next: T-002 (Config Parser)"
```

---

## Template for Future Tasks

```markdown
## [Version] - YYYY-MM-DD

### Added - T-XXX: Task Name ✅

**Commit**: T-XXX: Brief description

**What Was Done**:
- Bullet points of changes

**Files Created/Modified**:
- List of files

**How to Verify**:
1. Command to run
2. Expected output

**What to Expect**:
- ✅ What works
- ❌ What doesn't work yet

**Next Steps for User**:
- Commands to run
- What to test

**Git Commit Command**:
```bash
git add .
git commit -m "..."
```
```

---

## Notes

- Each task gets one commit
- CHANGELOG updated before commit
- Verification steps included for reproducibility
- Progress tracked in both CHANGELOG and docs/TASKS.md
- Version stays at 0.1.0-dev until v0.1 release
