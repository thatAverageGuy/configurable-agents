# T-011: Node Executor

**Status**: ✅ Complete
**Completed**: 2026-01-26
**Commit**: T-011: Node executor - Execute nodes with LLM + tools
**Phase**: Phase 2 (Core Execution)
**Progress After**: 12/20 tasks (60%)

---

## 🎯 What Was Done

- Implemented node executor that integrates all Phase 2 components
- Input mapping resolution from state
- Prompt template resolution with {state.field} preprocessing helper
- Tool loading and binding to LLM
- LLM configuration merging (node-level overrides global)
- Structured output enforcement using Pydantic models
- Copy-on-write state updates (immutable pattern)
- Comprehensive error handling with NodeExecutionError
- 23 comprehensive tests covering all scenarios
- Total: 367 tests passing (up from 344)

---

## 📦 Files Created

### Source Code

```
src/configurable_agents/core/
└── node_executor.py (execute_node, NodeExecutionError, _strip_state_prefix)
```

### Tests

```
tests/core/
└── test_node_executor.py (23 comprehensive tests)
```

---

## 🔧 How to Verify

### 1. Test node executor

```bash
pytest tests/core/test_node_executor.py -v
# Expected: 23 passed
```

### 2. Run full test suite

```bash
pytest -v -m "not integration"
# Expected: 367 passed (23 node executor + 344 existing)
```

### 3. Use node executor

```python
from configurable_agents.core import execute_node
from configurable_agents.config import NodeConfig, GlobalConfig, LLMConfig
from pydantic import BaseModel

# Define state
class State(BaseModel):
    topic: str
    article: str = ""

# Create node config
node_config = NodeConfig(
    id="write",
    prompt="Write about: {topic}",
    outputs=["article"]
)

# Execute node
state = State(topic="AI Safety")
updated_state = execute_node(node_config, state, None)
print(updated_state.article)
```

---

## ✅ What to Expect

**Working**:
- ✅ Execute workflow nodes with LLM + tools
- ✅ Resolve input mappings from state
- ✅ Resolve prompts with variable substitution
- ✅ Handle {state.field} syntax via preprocessing
- ✅ Load and bind tools to LLM
- ✅ Merge node-level and global LLM configurations
- ✅ Enforce output schema with Pydantic validation
- ✅ Update state immutably (copy-on-write)
- ✅ Retry logic via LLM provider
- ✅ Logging at INFO level
- ✅ All errors wrapped with node context

**Not Yet Working**:
- ❌ {state.field} handled via workaround (T-011.1 future improvement)
- ❌ No streaming support
- ❌ No parallel node execution

---

## 💻 Public API

### Main Execution Function

```python
from configurable_agents.core import (
    execute_node,              # Main execution function
    NodeExecutionError,        # Error type for node failures
)

# Execute a node
updated_state = execute_node(
    node_config,      # NodeConfig
    state,            # Current workflow state (Pydantic model)
    global_config,    # Optional[GlobalConfig]
)
# Returns: Updated state (new Pydantic instance)
```

### Error Handling

```python
from configurable_agents.core import NodeExecutionError

try:
    new_state = execute_node(node_config, state, global_config)
except NodeExecutionError as e:
    # NodeExecutionError: Node 'write_article': LLM API call failed
    # Context: node_id='write_article'
    # Original: LLMAPIError(...)
    print(f"Node {e.node_id} failed: {e}")
    print(f"Original error: {e.__cause__}")
```

### Complete Public API

```python
# From configurable_agents.core

# Node execution
from configurable_agents.core import (
    execute_node,              # Execute single node
    NodeExecutionError,        # Node execution error
)

# Template resolution (used internally)
from configurable_agents.core import (
    resolve_prompt,            # Resolve template variables
    TemplateResolutionError,   # Template error
)

# Usage
new_state = execute_node(node_config, state, global_config)
```

---

## 📚 Dependencies Used

### Existing Dependencies

- All Phase 2 components:
  - Template resolver (T-010)
  - LLM provider (T-009)
  - Tool registry (T-008)
  - Output schema builder (T-007)
- `pydantic >= 2.0` - State models
- `logging` - Execution logging

**Status**: No new dependencies required

---

## 💡 Design Decisions

### Why Copy-on-Write State Updates?

- Returns new state instance (immutable pattern)
- Prevents accidental state mutations
- Enables easier debugging and replay
- Matches functional programming principles
- LangGraph compatibility

### Why Input Mapping Semantics?

- Template strings resolved against state
- Allows state field transformations
- Node inputs override state values
- Clear data flow from state to inputs

### Why State Prefix Preprocessing?

- `_strip_state_prefix` converts {state.X} → {X}
- Validator (T-004) and SPEC.md use {state.field} syntax
- Template resolver (T-010) expects {field} without prefix
- Workaround until T-011.1 (native support)
- Low impact (preprocessing works fine, just not elegant)

### Why Error Wrapping?

- All failures wrapped in NodeExecutionError
- Preserves original exception as __cause__
- Adds node_id context for debugging
- Makes error handling consistent

### Why Retry Delegation?

- LLM provider handles retries (max_retries from global config)
- Keeps node executor simple
- Centralized retry logic
- Exponential backoff handled by provider

### Why Logging Strategy?

- INFO for success/failure (high-level)
- DEBUG for detailed steps (verbose mode)
- Execution timing logged
- Node ID always included

---

## 🧪 Tests Created

**File**: `tests/core/test_node_executor.py` (23 tests)

### Test Categories (23 tests total)

#### Basic Execution (5 tests)

1. **Simple Node** (2 tests)
   - Execute node with prompt and outputs
   - State updated with LLM result

2. **Multiple Outputs** (2 tests)
   - Node produces multiple outputs
   - All outputs written to state

3. **No Tools** (1 test)
   - Node execution without tools

#### Input Mapping (5 tests)

1. **Input Resolution** (3 tests)
   - Inputs resolved from state
   - Template variables in inputs
   - Nested state access in inputs

2. **Input Override** (2 tests)
   - Node inputs override state values
   - Inputs used in prompt resolution

#### Tool Integration (4 tests)

1. **Tool Loading** (2 tests)
   - Tools loaded from registry
   - Tools bound to LLM

2. **Tool Execution** (2 tests)
   - LLM can use tools
   - Multiple tools available

#### LLM Configuration (4 tests)

1. **Config Merging** (2 tests)
   - Node config overrides global config
   - Global config used as default

2. **Model Selection** (2 tests)
   - Node specifies different model
   - Temperature override

#### Output Schema (3 tests)

1. **Schema Enforcement** (2 tests)
   - Output schema enforced
   - Pydantic validation applied

2. **Type Validation** (1 test)
   - Output types validated

#### Error Handling (2 tests)

1. **Wrapped Errors** (2 tests)
   - NodeExecutionError wraps all failures
   - Original exception preserved

---

## 🎨 Node Executor Features

### Execute Node

```python
# Basic execution
updated_state = execute_node(
    node_config=NodeConfig(
        id="write",
        prompt="Write about: {topic}",
        outputs=["article"]
    ),
    state=State(topic="AI"),
    global_config=None
)
# → New State instance with article field populated
```

### Input Mapping

```python
# Node config with input mappings
node_config = NodeConfig(
    id="process",
    inputs={
        "author": "{metadata.author}",  # Resolve from state
        "topic": "AI Safety"             # Literal value
    },
    prompt="Author {author} writes about {topic}",
    outputs=["result"]
)

# Inputs resolved before prompt resolution
updated_state = execute_node(node_config, state, global_config)
```

### Tool Binding

```python
# Node with tools
node_config = NodeConfig(
    id="search",
    prompt="Search for: {query}",
    tools=["serper_search"],  # Tools from registry
    outputs=["results"]
)

# Tools automatically loaded and bound to LLM
updated_state = execute_node(node_config, state, global_config)
```

### LLM Config Merging

```python
# Global config
global_config = GlobalConfig(
    llm=LLMConfig(temperature=0.5, model="gemini-2.5-flash-lite")
)

# Node overrides
node_config = NodeConfig(
    id="creative",
    llm=LLMConfig(temperature=0.9),  # Override temperature only
    prompt="Be creative: {topic}",
    outputs=["creative_text"]
)

# Merged: temperature=0.9, model="gemini-2.5-flash-lite"
updated_state = execute_node(node_config, state, global_config)
```

### Output Schema Enforcement

```python
# Node with output schema
node_config = NodeConfig(
    id="analyze",
    prompt="Analyze: {text}",
    outputs=["summary", "score"],
    output_schema={
        "type": "object",
        "fields": {
            "summary": {"type": "str"},
            "score": {"type": "int"}
        }
    }
)

# Pydantic validation enforced automatically
updated_state = execute_node(node_config, state, global_config)
```

---

## 🔧 Implementation Details

### State Prefix Preprocessing

```python
# Current workaround (_strip_state_prefix)
prompt = "Topic: {state.topic}"  # From config
preprocessed = "Topic: {topic}"   # After stripping

# Future T-011.1: Template resolver handles natively
# No preprocessing needed
```

### Copy-on-Write Pattern

```python
# Original state unchanged
original = State(topic="AI", article="")

# New state returned
updated = execute_node(node_config, original, global_config)

# Original unchanged
assert original.article == ""
assert updated.article != ""
```

### Error Context

```python
try:
    execute_node(node_config, state, global_config)
except NodeExecutionError as e:
    print(e.node_id)         # "write_article"
    print(e.message)         # "Node 'write_article': ..."
    print(e.__cause__)       # Original exception
```

---

## 📖 Known Technical Debt

### T-011.1: Native {state.field} Support

**Current State**:
- Validator (T-004) and SPEC.md use `{state.field}` syntax
- Template resolver (T-010) expects `{field}` without prefix
- Workaround: `_strip_state_prefix` helper preprocesses prompts/inputs

**Impact**: Low (preprocessing works fine, just not elegant)

**Resolution**: Update template resolver in v0.2+ to accept both syntaxes

**Files Affected**:
- `src/configurable_agents/core/node_executor.py` (uses workaround)
- `src/configurable_agents/core/template.py` (needs update)

---

## 📖 Documentation Updated

- ✅ CHANGELOG.md (comprehensive entry created)
- ✅ docs/TASKS.md (T-011 marked DONE, progress updated to 12/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)

---

## 📝 Git Commit Template

```bash
git add .
git commit -m "T-011: Node executor - Execute nodes with LLM + tools

- Implemented node executor integrating Phase 2 components
  - execute_node(node, state, global_config) - Main function
  - Input mapping resolution from state
  - Prompt template resolution
  - Tool loading and binding to LLM
  - LLM configuration merging
  - Structured output enforcement

- Copy-on-write state updates
  - Returns new Pydantic instance
  - Original state unchanged
  - Immutable pattern for safety

- State prefix preprocessing helper
  - _strip_state_prefix converts {state.X} → {X}
  - Workaround until T-011.1 (native support)
  - TODO: Update template resolver in v0.2+

- Comprehensive error handling
  - NodeExecutionError wraps all failures
  - Preserves original exception
  - Includes node_id context
  - Helpful error messages

- Logging at INFO and DEBUG levels
  - Execution success/failure logged
  - Detailed steps in DEBUG mode
  - Execution timing tracked

- Created 23 comprehensive tests
  - Basic execution (5 tests)
  - Input mapping (5 tests)
  - Tool integration (4 tests)
  - LLM configuration (4 tests)
  - Output schema (3 tests)
  - Error handling (2 tests)

Verification:
  pytest -v -m 'not integration'
  Expected: 367 passed (23 node executor + 344 existing)

Progress: 12/20 tasks (60%) - Phase 2 (Core Execution) 4/6 complete
Next: T-012 (Graph Builder)"
```

---

## 🔗 Related Documentation

- **[../../TASKS.md](../../TASKS.md)** - Task T-011 acceptance criteria
- **[../../SPEC.md](../../SPEC.md)** - Node execution specification
- **[../../ARCHITECTURE.md](../../ARCHITECTURE.md)** - Executor architecture
- **[../../PROJECT_VISION.md](../../PROJECT_VISION.md)** - Execution roadmap

---

## 🚀 Next Steps for Users

### Use in Workflow

```yaml
nodes:
  - id: write_article
    prompt: "Write about: {state.topic}"
    tools:
      - serper_search
    outputs:
      - article
    llm:
      temperature: 0.7
```

### Test Node Execution

```python
from configurable_agents.core import execute_node
from configurable_agents.config import NodeConfig
from pydantic import BaseModel

class State(BaseModel):
    topic: str
    article: str = ""

node = NodeConfig(
    id="write",
    prompt="Write about: {topic}",
    outputs=["article"]
)

state = State(topic="AI Safety")
new_state = execute_node(node, state, None)
print(new_state.article)
```

---

## 📊 Phase 2 Progress

**Phase 2 (Core Execution): 4/6 complete (67%)**
- ✅ T-008: Tool Registry
- ✅ T-009: LLM Provider
- ✅ T-010: Prompt Template Resolver
- ✅ T-011: Node Executor
- ⏳ T-012: Graph Builder
- ⏳ T-013: Runtime Executor

---

*Implementation completed: 2026-01-26*
*Next task: T-012 (Graph Builder)*
