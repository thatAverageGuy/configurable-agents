# T-012: Graph Builder

**Status**: ✅ Complete
**Completed**: 2026-01-26
**Commit**: T-012: Graph builder - Build LangGraph from config
**Phase**: Phase 2 (Core Execution)
**Progress After**: 13/20 tasks (65%)

---

## 🎯 What Was Done

- Implemented graph builder transforming WorkflowConfig to executable LangGraph
- Closure-based node function wrapping for clean config capture
- Direct Pydantic BaseModel integration with LangGraph (no TypedDict conversion)
- START/END entry/exit point handling (not identity nodes)
- Defensive validation for linear flows (v0.1 constraint)
- Comprehensive error handling with GraphBuilderError
- 18 comprehensive tests covering all scenarios (16 unit + 2 integration)
- Total: 383 tests passing (up from 367)

---

## 📦 Files Created

### Source Code

```
src/configurable_agents/core/
└── graph_builder.py (build_graph, make_node_function, GraphBuilderError)
```

### Tests

```
tests/core/
└── test_graph_builder.py (18 comprehensive tests: 16 unit + 2 integration)
```

---

## 🔧 How to Verify

### 1. Test graph builder

```bash
pytest tests/core/test_graph_builder.py -v -m "not integration"
# Expected: 16 passed
```

### 2. Run integration tests

```bash
pytest tests/core/test_graph_builder.py -v -m integration
# Expected: 2 passed
```

### 3. Run full test suite

```bash
pytest -v -m "not integration"
# Expected: 383 passed (16 graph builder + 367 existing)
```

### 4. Use graph builder

```python
from configurable_agents.core import build_graph, build_state_model
from configurable_agents.config import parse_config_file, WorkflowConfig

# Load config
config_dict = parse_config_file("workflow.yaml")
config = WorkflowConfig(**config_dict)

# Build state model
state_model = build_state_model(config.state)

# Build and compile graph
graph = build_graph(config, state_model, config.config)

# Execute
initial = state_model(topic="AI Safety")
final_dict = graph.invoke(initial)
print(final_dict["article"])
```

---

## ✅ What to Expect

**Working**:
- ✅ Build LangGraph StateGraph from validated WorkflowConfig
- ✅ Closure-based node functions capture config cleanly
- ✅ Direct Pydantic BaseModel integration (no conversion overhead)
- ✅ START/END as LangGraph entry/exit points
- ✅ Linear flow validation (v0.1 constraint)
- ✅ Compiled graph output (ready for immediate execution)
- ✅ Defensive validation (catches validator bugs)
- ✅ NodeExecutionError propagation with context
- ✅ Unexpected error wrapping with node_id
- ✅ Logging at INFO and DEBUG levels

**Not Yet Working**:
- ❌ No conditional routing (v0.1 constraint)
- ❌ No parallel execution (v0.2+ feature)
- ❌ No cycles/loops (v0.1 constraint)

---

## 💻 Public API

### Main Graph Functions

```python
from configurable_agents.core import (
    build_graph,          # Build compiled graph from config
    GraphBuilderError,    # Graph construction error
)

# Build compiled graph
state_model = build_state_model(config.state)
graph = build_graph(
    config=config,              # WorkflowConfig
    state_model=state_model,    # Pydantic BaseModel class
    global_config=config.config # Optional[GlobalConfig]
)

# Execute graph
initial = state_model(topic="AI Safety")
final_dict = graph.invoke(initial)  # Returns dict
print(final_dict["research"])
```

### Error Handling

```python
from configurable_agents.core import GraphBuilderError

try:
    graph = build_graph(config, state_model, global_config)
except GraphBuilderError as e:
    # GraphBuilderError: Failed to build graph: cycle detected
    # Original: ValidationError(...)
    print(e)
```

### Complete Public API

```python
# From configurable_agents.core

# Graph building
from configurable_agents.core import (
    build_graph,              # Build LangGraph from config
    GraphBuilderError,        # Graph construction error
)

# State building (T-006)
from configurable_agents.core import (
    build_state_model,        # Build Pydantic state model
)

# Usage
state_model = build_state_model(config.state)
graph = build_graph(config, state_model, config.config)
result = graph.invoke(initial_state)
```

---

## 📚 Dependencies Used

### Existing Dependencies

- `langgraph >= 0.0.20` - StateGraph, START, END
- Phase 2 components:
  - Node executor (T-011)
  - State schema builder (T-006)
- `pydantic >= 2.0` - State models

**Status**: No new dependencies required

---

## 💡 Design Decisions

### Why Pydantic BaseModel?

- Direct integration with LangGraph (no TypedDict conversion)
- Maintains type safety end-to-end
- Simpler implementation (no conversion overhead)
- Better error messages
- Familiar to users

### Why Closure Pattern?

- Node functions capture config cleanly
- Calls execute_node with captured context
- Avoids global state
- Clean separation of concerns
- Easy to test and debug

### Why START/END?

- LangGraph constants (entry/exit points)
- Not identity nodes (special semantics)
- Clear workflow boundaries
- Standard LangGraph pattern
- Simpler mental model

### Why Compiled Return?

- Returns `CompiledStateGraph` ready for execution
- No additional compilation step needed
- Immediate invocation possible
- Clear API boundary

### Why Minimal Validation?

- Trust T-004 validator for correctness
- Defensive checks only (catch validator bugs)
- Fail-fast on structural issues
- Keep graph builder focused

---

## 🧪 Tests Created

**File**: `tests/core/test_graph_builder.py` (18 tests total)

### Test Categories (16 unit + 2 integration)

#### Basic Graph Building (4 tests)

1. **Simple Graph** (2 tests)
   - Build graph with single node
   - Graph compiles successfully

2. **Multi-Node Graph** (2 tests)
   - Build graph with multiple nodes
   - Edges connect nodes correctly

#### Node Function Creation (3 tests)

1. **Closure Capture** (2 tests)
   - Node function captures config
   - Calls execute_node with correct args

2. **State Handling** (1 test)
   - Node function updates state

#### START/END Handling (3 tests)

1. **Entry Point** (1 test)
   - START connected to first node

2. **Exit Point** (1 test)
   - Last node connected to END

3. **Linear Flow** (1 test)
   - START → nodes → END sequence

#### Validation (4 tests)

1. **Linear Flow Check** (2 tests)
   - Reject cycles
   - Reject conditional routing

2. **Node References** (2 tests)
   - All node IDs valid
   - Edge references valid nodes

#### Error Handling (2 tests)

1. **Error Wrapping** (1 test)
   - GraphBuilderError wraps failures

2. **Context Preservation** (1 test)
   - Original exceptions preserved

#### Integration Tests (2 tests - marked)

1. **End-to-End Execution** (2 tests)
   - Complete workflow execution
   - Multi-step workflow with tools

---

## 🎨 Graph Builder Features

### Build Compiled Graph

```python
# Build from config
graph = build_graph(config, state_model, global_config)

# Returns CompiledStateGraph
assert isinstance(graph, CompiledStateGraph)

# Ready for execution
result = graph.invoke(initial_state)
```

### Closure-Based Node Functions

```python
# Internal: make_node_function creates closures
def make_node_function(node_config, global_config):
    def node_fn(state):
        return execute_node(node_config, state, global_config)
    return node_fn

# Each node function captures its config
# Clean separation, no global state
```

### START/END Points

```python
# Graph structure
# START → node1 → node2 → END

# START: Entry point (not a real node)
# END: Exit point (not a real node)
# Nodes: Actual processing steps
```

### Linear Flow Enforcement

```python
# Validates structure
# ✅ Linear: START → A → B → C → END
# ❌ Cycle: START → A → B → A → END
# ❌ Conditional: START → A → [route] → END
```

---

## 🔧 Implementation Details

### Graph Construction Flow

```
1. Validate linear flow (defensive)
2. Create StateGraph with state_model
3. For each node:
   - Create closure-based node function
   - Add node to graph
4. Add edges:
   - START to first node
   - Between nodes
   - Last node to END
5. Compile graph
6. Return CompiledStateGraph
```

### Node Function Signature

```python
# LangGraph expects: state -> dict
def node_function(state: StateModel) -> dict:
    """
    Execute node and return state updates as dict.

    Args:
        state: Current Pydantic state model instance

    Returns:
        Dict with updated fields
    """
    updated = execute_node(node_config, state, global_config)
    return updated.model_dump()
```

### Error Propagation

```python
# NodeExecutionError from execute_node
# → Propagates through graph execution
# → Includes node_id context
# → Original exception preserved

# GraphBuilderError for construction failures
# → Wraps validation errors
# → Includes helpful messages
```

---

## 📖 Integration Points

### Uses From Previous Tasks

- `execute_node` from T-011 (node execution)
- `WorkflowConfig` from T-003 (config schema)
- `build_state_model` from T-006 (state building)
- `validate_config` from T-004 (used before building)

### Used By Next Tasks

- T-013 (Runtime Executor) - orchestrates config → execution
- Wraps graph building in complete pipeline

---

## 📖 Documentation Updated

- ✅ CHANGELOG.md (comprehensive entry created)
- ✅ docs/TASKS.md (T-012 marked DONE, progress updated to 13/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)

---

## 📝 Git Commit Template

```bash
git add .
git commit -m "T-012: Graph builder - Build LangGraph from config

- Implemented graph builder transforming config to executable graph
  - build_graph(config, state_model, global_config) - Main function
  - Returns CompiledStateGraph ready for execution
  - Direct Pydantic BaseModel integration (no TypedDict)
  - START/END as LangGraph entry/exit points

- Closure-based node function wrapping
  - make_node_function creates closures capturing config
  - Clean separation without global state
  - Calls execute_node with captured context

- Defensive validation for linear flows
  - Catch validator bugs at runtime
  - Reject cycles and conditional routing
  - v0.1 constraint enforcement

- Comprehensive error handling
  - GraphBuilderError wraps all failures
  - NodeExecutionError propagation with context
  - Unexpected errors wrapped with node_id
  - Helpful error messages

- Logging at INFO and DEBUG levels
  - High-level graph construction logged
  - Detailed steps in DEBUG mode
  - Node additions and edge creation tracked

- Created 18 comprehensive tests
  - 16 unit tests (building, validation, errors)
  - 2 integration tests (end-to-end execution)

Verification:
  pytest tests/core/test_graph_builder.py -v -m 'not integration'
  Expected: 16 passed

  pytest -v -m 'not integration'
  Expected: 383 passed (16 graph builder + 367 existing)

Progress: 13/20 tasks (65%) - Phase 2 (Core Execution) 5/6 complete
Next: T-013 (Runtime Executor)"
```

---

## 🔗 Related Documentation

- **[../../TASKS.md](../../TASKS.md)** - Task T-012 acceptance criteria
- **[../../SPEC.md](../../SPEC.md)** - Graph structure specification
- **[../../ARCHITECTURE.md](../../ARCHITECTURE.md)** - Graph builder architecture
- **[../../PROJECT_VISION.md](../../PROJECT_VISION.md)** - Execution roadmap
- **[../adr/](../adr/)** - Architecture decisions

---

## 🚀 Next Steps for Users

### Build and Execute Graph

```python
from configurable_agents.core import build_graph, build_state_model
from configurable_agents.config import parse_config_file, WorkflowConfig

# Load and validate config
config_dict = parse_config_file("workflow.yaml")
config = WorkflowConfig(**config_dict)

# Build state model
state_model = build_state_model(config.state)

# Build graph
graph = build_graph(config, state_model, config.config)

# Execute
initial = state_model(topic="AI Safety")
result = graph.invoke(initial)
print(result)
```

---

## 📊 Phase 2 Progress

**Phase 2 (Core Execution): 5/6 complete (83%)**
- ✅ T-008: Tool Registry
- ✅ T-009: LLM Provider
- ✅ T-010: Prompt Template Resolver
- ✅ T-011: Node Executor
- ✅ T-012: Graph Builder
- ⏳ T-013: Runtime Executor

**Almost done with Phase 2! Just Runtime Executor left.**

---

*Implementation completed: 2026-01-26*
*Next task: T-013 (Runtime Executor)*
