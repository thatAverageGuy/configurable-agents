# T-013: Runtime Executor

**Status**: ✅ Complete
**Completed**: 2026-01-26
**Commit**: T-013: Runtime executor - Orchestrate config → execution
**Phase**: Phase 2 (Core Execution)
**Progress After**: 14/20 tasks (70%)

---

## 🎯 What Was Done

- Implemented runtime executor orchestrating complete workflow execution
- Load and parse config from YAML/JSON files
- Validate config with comprehensive checks and feature gating
- Build state model and initialize with inputs
- Build and compile LangGraph execution graph
- Execute complete workflows end-to-end
- Return final state as dict with execution metrics
- Comprehensive error handling with 6 exception types
- Verbose logging option for debugging
- 23 comprehensive tests covering all scenarios
- 4 integration tests for end-to-end validation
- Total: 406 tests passing (up from 383)

---

## 📦 Files Created

### Source Code

```
src/configurable_agents/runtime/
├── executor.py (330 lines - run_workflow, validate_workflow, 6 error types)
└── __init__.py (updated exports)
```

### Tests

```
tests/runtime/
├── test_executor.py (670 lines, 23 comprehensive tests)
└── test_executor_integration.py (295 lines, 4 integration tests)
```

### Examples

```
examples/
├── simple_workflow.yaml (minimal working example)
└── README.md (usage guide with error handling examples)
```

---

## 🔧 How to Verify

### 1. Test runtime executor

```bash
pytest tests/runtime/test_executor.py -v
# Expected: 23 passed
```

### 2. Run integration tests

```bash
pytest tests/runtime/test_executor_integration.py -v -m integration
# Expected: 4 integration tests
```

### 3. Run full test suite

```bash
pytest -v -m "not integration"
# Expected: 406 passed (23 executor + 383 existing)
```

### 4. Use runtime executor

```python
from configurable_agents.runtime import run_workflow

# Execute workflow
result = run_workflow("workflow.yaml", {"topic": "AI Safety"})
print(result["article"])
```

---

## ✅ What to Expect

**Working**:
- ✅ Execute workflow from file path
- ✅ Execute from config object
- ✅ Validate without execution
- ✅ 7-phase execution pipeline
- ✅ Granular error handling (6 exception types)
- ✅ Execution timing and metrics
- ✅ Verbose logging option
- ✅ Clear error messages
- ✅ All error types preserve original exceptions
- ✅ Works with YAML and JSON configs

**Not Yet Working**:
- ❌ No workflow pause/resume
- ❌ No checkpoint/replay
- ❌ No streaming execution

---

## 💻 Public API

### Main Execution Functions

```python
from configurable_agents.runtime import (
    # Main functions
    run_workflow,              # Execute from file
    run_workflow_from_config,  # Execute from config
    validate_workflow,         # Validate only
)

# Execute workflow
result = run_workflow("workflow.yaml", {"topic": "AI Safety"})
print(result["article"])

# Validate without executing
validate_workflow("workflow.yaml")

# Execute with verbose logging
result = run_workflow("workflow.yaml", {"topic": "AI"}, verbose=True)
```

### Error Handling

```python
from configurable_agents.runtime import (
    # Error hierarchy
    ExecutionError,            # Base exception
    ConfigLoadError,           # File/parsing errors
    ConfigValidationError,     # Validation errors
    StateInitializationError,  # Invalid inputs
    GraphBuildError,           # Graph construction errors
    WorkflowExecutionError,    # Execution errors
)

try:
    result = run_workflow("workflow.yaml", {"name": "Alice"})
except ConfigLoadError as e:
    # File not found, invalid YAML/JSON
    print(f"Failed to load: {e.phase}")
except ConfigValidationError as e:
    # Invalid config, unsupported features
    print(f"Invalid config: {e.phase}")
except StateInitializationError as e:
    # Missing required inputs, wrong types
    print(f"Invalid inputs: {e}")
except GraphBuildError as e:
    # State model or graph construction failed
    print(f"Build failed: {e.phase}")
except WorkflowExecutionError as e:
    # Node execution error, LLM failure
    print(f"Execution failed: {e.phase}")
```

### Complete Public API

```python
# From configurable_agents.runtime

# Main functions
from configurable_agents.runtime import (
    run_workflow,              # Execute from file
    run_workflow_from_config,  # Execute from config object
    validate_workflow,         # Validate only (no execution)
)

# Error hierarchy (all inherit from ExecutionError)
from configurable_agents.runtime import (
    ExecutionError,            # Base exception
    ConfigLoadError,           # Phase 1: Config load
    ConfigValidationError,     # Phase 2-4: Validation
    StateInitializationError,  # Phase 5: State init
    GraphBuildError,           # Phase 6: Graph build
    WorkflowExecutionError,    # Phase 7: Execution
)

# Usage
result = run_workflow("workflow.yaml", {"topic": "AI"})
```

---

## 📚 Dependencies Used

### Existing Dependencies

- All previous tasks:
  - Config parser (T-002)
  - Config schema (T-003)
  - Config validator (T-004)
  - Runtime feature gating (T-004.5)
  - State schema builder (T-006)
  - Graph builder (T-012)
- `pydantic >= 2.0` - State validation
- `logging` - Execution logging

**Status**: No new dependencies required

---

## 💡 Design Decisions

### Why Two Entry Points?

- File path vs pre-loaded config for flexibility
- `run_workflow()` for simple use cases
- `run_workflow_from_config()` for advanced scenarios
- Enables config reuse and testing

### Why Phase-Based Errors?

- Each phase has specific exception type
- Clear error categorization
- Easy to handle different failure modes
- Helpful for debugging and monitoring

### Why Original Exception Preservation?

- All errors wrap original for debugging
- `__cause__` chain maintained
- Full stack trace available
- Root cause analysis easier

### Why Verbose Logging?

- Optional DEBUG level for detailed traces
- INFO level by default (minimal noise)
- Execution timing always logged
- Performance monitoring enabled

### Why Execution Metrics?

- Timing logged for performance monitoring
- Phase durations tracked
- Enables optimization
- Production observability

### Why Validation-Only Mode?

- `validate_workflow()` for pre-flight checks
- No LLM API calls (free and fast)
- CI/CD integration
- Config development workflow

---

## 🧪 Tests Created

**Files**:
- `tests/runtime/test_executor.py` (23 tests)
- `tests/runtime/test_executor_integration.py` (4 integration tests)

### Test Categories (23 unit + 4 integration)

#### Workflow Execution (6 tests)

1. **Basic Execution** (3 tests)
   - Execute simple workflow
   - Return final state as dict
   - All state fields present

2. **Config Loading** (3 tests)
   - Load from YAML file
   - Load from JSON file
   - Load from config object

#### Validation (4 tests)

1. **Validation Only** (2 tests)
   - Validate without executing
   - No LLM calls made

2. **Validation Errors** (2 tests)
   - Invalid config rejected
   - Helpful error messages

#### Input Handling (5 tests)

1. **Input Processing** (3 tests)
   - Inputs passed to state
   - Required inputs validated
   - Optional inputs handled

2. **Input Validation** (2 tests)
   - Missing required inputs rejected
   - Wrong input types rejected

#### Error Handling (6 tests)

1. **Error Types** (6 tests)
   - ConfigLoadError (file not found)
   - ConfigValidationError (invalid config)
   - StateInitializationError (bad inputs)
   - GraphBuildError (graph construction)
   - WorkflowExecutionError (execution failure)
   - Original exception preserved

#### Verbose Mode (2 tests)

1. **Logging Levels** (2 tests)
   - Verbose=True enables DEBUG
   - Verbose=False uses INFO

#### Integration Tests (4 tests - marked)

1. **End-to-End** (4 tests)
   - Complete workflow execution
   - Multi-step workflows
   - Tool integration
   - Error recovery

---

## 🎨 Execution Pipeline

### 7-Phase Pipeline

```
Phase 1: Config Load
  ↓ Load YAML/JSON file → dict
  ↓ (ConfigLoadError if file not found or invalid syntax)

Phase 2: Schema Validation
  ↓ Parse dict → Pydantic WorkflowConfig
  ↓ (ConfigValidationError if schema invalid)

Phase 3: Config Validation
  ↓ Cross-reference validation (T-004)
  ↓ Graph structure validation
  ↓ (ConfigValidationError if invalid references)

Phase 4: Feature Gating
  ↓ Check v0.1 compatibility (T-004.5)
  ↓ (ConfigValidationError if unsupported features)

Phase 5: State Initialization
  ↓ Build state model (T-006)
  ↓ Initialize with inputs
  ↓ (StateInitializationError if inputs invalid)

Phase 6: Graph Build
  ↓ Build LangGraph StateGraph (T-012)
  ↓ Compile graph
  ↓ (GraphBuildError if construction fails)

Phase 7: Execution
  ↓ Execute graph with initial state
  ↓ Return final state as dict
  ↓ (WorkflowExecutionError if node fails)
```

### Error Handling Flow

```python
try:
    # Phase 1: Load
    config_dict = parse_config_file(path)
except Exception as e:
    raise ConfigLoadError("config_load", str(e)) from e

try:
    # Phase 2: Schema
    config = WorkflowConfig(**config_dict)
except Exception as e:
    raise ConfigValidationError("schema_validation", str(e)) from e

try:
    # Phase 3: Validate
    validate_config(config)
except Exception as e:
    raise ConfigValidationError("config_validation", str(e)) from e

# ... and so on for each phase
```

---

## 🔧 Usage Examples

### 1. Basic Execution

```python
from configurable_agents.runtime import run_workflow

result = run_workflow("article_writer.yaml", {"topic": "AI Safety"})
print(result["article"])
```

### 2. Pre-Loaded Config

```python
from configurable_agents.config import parse_config_file, WorkflowConfig
from configurable_agents.runtime import run_workflow_from_config

config_dict = parse_config_file("workflow.yaml")
config = WorkflowConfig(**config_dict)
result = run_workflow_from_config(config, {"topic": "AI"})
```

### 3. Validation Only

```python
from configurable_agents.runtime import validate_workflow

try:
    validate_workflow("workflow.yaml")
    print("✅ Config is valid!")
except Exception as e:
    print(f"❌ Validation failed: {e}")
```

### 4. Verbose Logging

```python
from configurable_agents.runtime import run_workflow

# Enable verbose logging (DEBUG level)
result = run_workflow(
    "workflow.yaml",
    {"topic": "AI"},
    verbose=True  # Shows detailed execution steps
)
```

### 5. Error Handling

```python
from configurable_agents.runtime import (
    run_workflow,
    ConfigLoadError,
    ConfigValidationError,
    StateInitializationError,
    WorkflowExecutionError
)

try:
    result = run_workflow("workflow.yaml", {"topic": "AI"})
except ConfigLoadError as e:
    print(f"File error: {e}")
except ConfigValidationError as e:
    print(f"Config error: {e}")
except StateInitializationError as e:
    print(f"Input error: {e}")
except WorkflowExecutionError as e:
    print(f"Execution error: {e}")
```

---

## 📖 Integration Points

### Uses From All Previous Tasks

**Phase 1 (Foundation)**:
- T-002: Config parser (`parse_config_file`)
- T-003: Config schema (`WorkflowConfig`)
- T-004: Config validator (`validate_config`)
- T-004.5: Runtime feature gating (`validate_runtime_support`)
- T-006: State schema builder (`build_state_model`)

**Phase 2 (Core Execution)**:
- T-012: Graph builder (`build_graph`)
- All Phase 2 components used transitively

### Used By Next Tasks

- T-014 (CLI Interface) - Wraps runtime executor
- Enables user-facing workflow execution

---

## 📖 Documentation Updated

- ✅ CHANGELOG.md (comprehensive entry created)
- ✅ docs/TASKS.md (T-013 marked DONE, progress updated to 14/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)
- ✅ examples/README.md (usage examples added)
- ✅ examples/simple_workflow.yaml (minimal example created)

---

## 📝 Git Commit Template

```bash
git add .
git commit -m "T-013: Runtime executor - Orchestrate config → execution

- Implemented runtime executor orchestrating complete pipeline
  - run_workflow(path, inputs, verbose) - Execute from file
  - run_workflow_from_config(config, inputs, verbose) - From config object
  - validate_workflow(path) - Validate without execution
  - 7-phase execution pipeline with granular error handling

- Phase-based execution pipeline
  1. Config Load: Parse YAML/JSON → dict
  2. Schema Validation: dict → Pydantic WorkflowConfig
  3. Config Validation: Cross-reference checks (T-004)
  4. Feature Gating: v0.1 compatibility (T-004.5)
  5. State Initialization: Build state model, initialize inputs
  6. Graph Build: Build and compile LangGraph (T-012)
  7. Execution: Execute graph, return final state

- Comprehensive error handling (6 exception types)
  - ExecutionError (base exception)
  - ConfigLoadError (Phase 1: file/parsing errors)
  - ConfigValidationError (Phase 2-4: validation errors)
  - StateInitializationError (Phase 5: invalid inputs)
  - GraphBuildError (Phase 6: graph construction)
  - WorkflowExecutionError (Phase 7: execution errors)
  - All errors preserve original exception

- Execution timing and metrics
  - Phase durations logged
  - Total execution time tracked
  - Performance monitoring enabled

- Verbose logging option
  - verbose=True enables DEBUG level
  - verbose=False uses INFO level (default)
  - Detailed execution traces for debugging

- Created 27 comprehensive tests
  - 23 unit tests (execution, validation, errors)
  - 4 integration tests (end-to-end workflows)

- Example workflows created
  - examples/simple_workflow.yaml (minimal)
  - examples/README.md (usage guide)

Verification:
  pytest tests/runtime/test_executor.py -v
  Expected: 23 passed

  pytest -v -m 'not integration'
  Expected: 406 passed (23 executor + 383 existing)

  pytest tests/runtime/test_executor_integration.py -v -m integration
  Expected: 4 integration tests

Progress: 14/20 tasks (70%) - Phase 2 (Core Execution) 6/6 COMPLETE ✅
Next: T-014 (CLI Interface)"
```

---

## 🔗 Related Documentation

- **[../../TASKS.md](../../TASKS.md)** - Task T-013 acceptance criteria
- **[../../SPEC.md](../../SPEC.md)** - Execution specification
- **[../../ARCHITECTURE.md](../../ARCHITECTURE.md)** - Runtime architecture
- **[../../PROJECT_VISION.md](../../PROJECT_VISION.md)** - Execution roadmap
- **[../../../examples/README.md](../../../examples/README.md)** - Usage examples

---

## 🚀 Next Steps for Users

### Run Your First Workflow

```bash
# Create a simple workflow
cat > hello.yaml << 'EOF'
state:
  fields:
    - name: message
      type: str
    - name: greeting
      type: str

nodes:
  - id: greet
    prompt: "Say hello to {message}"
    outputs:
      - greeting

edges:
  - from: START
    to: greet
  - from: greet
    to: END
EOF

# Execute workflow
python -c "
from configurable_agents.runtime import run_workflow
result = run_workflow('hello.yaml', {'message': 'World'})
print(result['greeting'])
"
```

### Validate Configs

```bash
# Validate before executing (no API calls)
python -c "
from configurable_agents.runtime import validate_workflow
try:
    validate_workflow('workflow.yaml')
    print('✅ Config is valid!')
except Exception as e:
    print(f'❌ Validation failed: {e}')
"
```

---

## 📊 Phase 2 Progress

**Phase 2 (Core Execution): 6/6 COMPLETE ✅ (100%)**
- ✅ T-008: Tool Registry
- ✅ T-009: LLM Provider
- ✅ T-010: Prompt Template Resolver
- ✅ T-011: Node Executor
- ✅ T-012: Graph Builder
- ✅ T-013: Runtime Executor

**🎉 Phase 2 Complete! Moving to Phase 3 (Polish & UX)**

---

*Implementation completed: 2026-01-26*
*Next task: T-014 (CLI Interface)*
