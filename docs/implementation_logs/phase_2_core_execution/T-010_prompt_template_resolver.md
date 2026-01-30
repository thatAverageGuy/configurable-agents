# T-010: Prompt Template Resolver

**Status**: ✅ Complete
**Completed**: 2026-01-25
**Commit**: T-010: Prompt template resolver - Variable substitution
**Phase**: Phase 2 (Core Execution)
**Progress After**: 11/20 tasks (55%)

---

## 🎯 What Was Done

- Implemented prompt template resolution with {variable} placeholder support
- Input mappings override state fields (explicit precedence)
- Support for nested state access ({metadata.author}, {metadata.flags.level})
- Comprehensive error handling with "Did you mean?" suggestions
- Edit distance algorithm for typo detection (max 2 edits)
- Automatic type conversion (int, bool, etc. → string)
- 44 comprehensive tests covering all scenarios
- Total: 344 tests passing (up from 300)

---

## 📦 Files Created

### Source Code

```
src/configurable_agents/core/
└── template.py (prompt template resolver)
```

### Tests

```
tests/core/
└── test_template.py (44 comprehensive tests)
```

---

## 🔧 How to Verify

### 1. Test template resolver

```bash
pytest tests/core/test_template.py -v
# Expected: 44 passed
```

### 2. Run full test suite

```bash
pytest -v -m "not integration"
# Expected: 344 passed (44 template + 300 existing)
```

### 3. Use template resolver

```python
from configurable_agents.core import resolve_prompt
from pydantic import BaseModel

class State(BaseModel):
    topic: str
    score: int

state = State(topic="AI Safety", score=95)
inputs = {"name": "Alice"}

# Simple resolution
result = resolve_prompt("Hello {name}", inputs, state)
assert result == "Hello Alice"

# State field
result = resolve_prompt("Topic: {topic}", {}, state)
assert result == "Topic: AI Safety"

# Input overrides state
inputs = {"topic": "Robotics"}
result = resolve_prompt("Topic: {topic}", inputs, state)
assert result == "Topic: Robotics"
```

---

## ✅ What to Expect

**Working**:
- ✅ Prompt templates resolve variables from inputs and state
- ✅ Input mappings override state fields (explicit precedence)
- ✅ Nested state access works (dot notation)
- ✅ Multiple variables in single template
- ✅ Type conversion automatic (int → "95", bool → "True")
- ✅ Helpful error messages with suggestions
- ✅ "Did you mean X?" for typos (edit distance ≤ 2)
- ✅ Available variables listed in error messages
- ✅ Fast and efficient (regex-based extraction)

**Not Yet Working**:
- ❌ Literal braces not escapable (v0.1 limitation)
- ❌ Format strings not supported (only {variable})
- ❌ No filters/transformations (v0.2+ feature)

---

## 💻 Public API

### Main Template Functions

```python
from configurable_agents.core import (
    resolve_prompt,             # Main resolution function
    extract_variables,          # Extract {variable} references
    TemplateResolutionError,    # Resolution error exception
)

# Resolve prompt template
resolved = resolve_prompt(
    prompt_template="Hello {name}, discuss {topic}",
    inputs={"name": "Alice"},  # Node-level inputs (override state)
    state=state_model,         # Workflow state (Pydantic model)
)
# Returns: "Hello Alice, discuss AI Safety"

# Extract variable references
variables = extract_variables("Author: {metadata.author}")
# Returns: {"metadata.author"}
```

### Error Handling

```python
from configurable_agents.core import TemplateResolutionError

# Missing variable
try:
    result = resolve_prompt("Hello {unknown}", {}, state)
except TemplateResolutionError as e:
    # Variable 'unknown' not found in inputs or state
    # Suggestion: Did you mean 'topic'?
    # Available inputs: []
    # Available state fields: ['topic', 'score']
    print(e)

# Nested variable not found
try:
    result = resolve_prompt("{metadata.author}", {}, state)
except TemplateResolutionError as e:
    # Variable 'metadata.author' not found in inputs or state
    # Available inputs: []
    # Available state fields: ['topic', 'score']
    print(e)
```

### Complete Public API

```python
# From configurable_agents.core

# Template resolution
from configurable_agents.core import (
    resolve_prompt,              # Resolve {variable} placeholders
    extract_variables,           # Extract variable references
    get_nested_value,            # Get value from nested path
)

# Exception
from configurable_agents.core import (
    TemplateResolutionError,     # Resolution error
)

# Usage
resolved = resolve_prompt("Hello {name}", {"name": "Bob"}, state)
variables = extract_variables("{a} and {b}")  # {"a", "b"}
```

---

## 📚 Dependencies Used

### Standard Library Only

- `re` - Regular expressions for variable extraction
- `typing` - Type hints

**Status**: No new dependencies required

---

## 💡 Design Decisions

### Why Input Priority?

- Inputs override state (node-level control)
- Allows per-node customization
- State provides defaults
- Clear and predictable precedence

### Why Dot Notation?

- Nested access via {a.b.c} syntax
- Matches common template patterns
- Works with Pydantic models and dicts
- Supports arbitrary nesting depth

### Why Type Conversion?

- Automatic str() conversion for all values
- Prevents type errors in prompts
- Simplifies template usage
- Predictable string concatenation

### Why Fail-Fast?

- Error on first missing variable encountered
- Clear error messages
- Prevents partial template resolution
- Easy to debug

### Why Edit Distance?

- Max 2 edits for suggestions (Levenshtein distance)
- Catches common typos (transpositions, insertions, deletions)
- Not too aggressive (avoids silly suggestions)
- Helpful for users

### Why Simple Syntax?

- Only {variable} supported (no format strings yet)
- Easy to understand and use
- Sufficient for v0.1 needs
- Can extend in v0.2+ if needed

### Why No Escaping?

- Literal braces not supported in v0.1 (can add if needed)
- Simpler implementation
- Rare use case for LLM prompts
- Can be added later if requested

---

## 🧪 Tests Created

**File**: `tests/core/test_template.py` (44 tests)

### Test Categories (44 tests total)

#### Simple Variable Resolution (8 tests)

1. **Input Resolution** (3 tests)
   - Resolve variable from inputs
   - Multiple variables from inputs
   - Empty template

2. **State Resolution** (3 tests)
   - Resolve variable from state
   - Multiple variables from state
   - No variables in template

3. **Priority** (2 tests)
   - Input overrides state
   - State used when input missing

#### Nested State Access (8 tests)

1. **Single Level Nesting** (3 tests)
   - Resolve {metadata.author}
   - Multiple nested variables
   - Nested dict access

2. **Deep Nesting** (3 tests)
   - Three-level nesting ({a.b.c})
   - Four-level nesting ({a.b.c.d})
   - Mixed nested and flat variables

3. **Nested with Pydantic** (2 tests)
   - Pydantic model nested fields
   - Nested BaseModel instances

#### Type Conversion (6 tests)

1. **Numeric Types** (2 tests)
   - Int to string (95 → "95")
   - Float to string (3.14 → "3.14")

2. **Boolean Types** (2 tests)
   - True to "True"
   - False to "False"

3. **Collection Types** (2 tests)
   - List to string representation
   - Dict to string representation

#### Error Cases (10 tests)

1. **Missing Variables** (4 tests)
   - Variable not in inputs or state
   - Multiple missing variables
   - Nested variable not found
   - Error message includes available fields

2. **Typo Suggestions** (4 tests)
   - Edit distance 1 (did you mean "topic"?)
   - Edit distance 2 (transposition)
   - Edit distance 3 (no suggestion)
   - Multiple candidates (closest one suggested)

3. **Edge Cases** (2 tests)
   - Empty variable name {  }
   - Malformed placeholders

#### Helper Functions (8 tests)

1. **extract_variables** (4 tests)
   - Extract single variable
   - Extract multiple variables
   - Extract nested variables
   - No variables returns empty set

2. **get_nested_value** (4 tests)
   - Get value from dict
   - Get nested value from dict
   - Get value from Pydantic model
   - Get nested from Pydantic model

#### Integration Scenarios (4 tests)

1. **Real Workflow Patterns** (4 tests)
   - Article writer prompt with {topic}
   - Multi-step with {previous_output}
   - Nested metadata access
   - Complex mixed variables

---

## 🎨 Template Resolver Features

### Variable Resolution

```python
# Resolve from inputs
resolve_prompt("Hello {name}", {"name": "Alice"}, state)
# → "Hello Alice"

# Resolve from state
resolve_prompt("Topic: {topic}", {}, state)
# → "Topic: AI Safety"

# Input overrides state
resolve_prompt("{topic}", {"topic": "Robotics"}, state)
# → "Robotics" (not "AI Safety" from state)
```

### Nested State Access

```python
# Single level nesting
resolve_prompt("{metadata.author}", {}, state)
# → state.metadata.author value

# Deep nesting
resolve_prompt("{config.llm.model}", {}, state)
# → state.config.llm.model value

# Mixed nested and flat
resolve_prompt("{topic} by {metadata.author}", {}, state)
# → "AI Safety by Alice"
```

### Multiple Variables

```python
resolve_prompt("Hello {name}, discuss {topic}", inputs, state)
# → "Hello Alice, discuss AI Safety"
```

### Type Conversion

```python
# Int to string
resolve_prompt("Score: {score}", {}, State(score=95))
# → "Score: 95"

# Bool to string
resolve_prompt("Enabled: {enabled}", {}, State(enabled=True))
# → "Enabled: True"
```

### Extract Variables

```python
variables = extract_variables("Hello {name}, {greeting}")
# → {"name", "greeting"}

variables = extract_variables("{metadata.author} wrote {article}")
# → {"metadata.author", "article"}
```

---

## 📖 Error Messages

### Missing Variable

```
TemplateResolutionError: Variable 'unknown' not found in inputs or state
Suggestion: Did you mean 'topic'?
Available inputs: []
Available state fields: ['topic', 'score']
```

### Nested Variable Not Found

```
TemplateResolutionError: Variable 'metadata.author' not found in inputs or state
Available inputs: []
Available state fields: ['topic', 'score', 'metadata']

Note: 'metadata' exists but 'author' field not found within it
```

### No Suggestion (Edit Distance > 2)

```
TemplateResolutionError: Variable 'completely_wrong' not found in inputs or state
Available inputs: []
Available state fields: ['topic', 'score']
```

---

## 📖 Documentation Updated

- ✅ CHANGELOG.md (comprehensive entry created)
- ✅ docs/TASKS.md (T-010 marked DONE, progress updated to 11/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)

---

## 📝 Git Commit Template

```bash
git add .
git commit -m "T-010: Prompt template resolver - Variable substitution

- Implemented prompt template resolution with {variable} placeholders
  - resolve_prompt(template, inputs, state) - Main resolution function
  - extract_variables(template) - Extract variable references
  - Input mappings override state fields (explicit precedence)
  - Fail loudly if variable not found

- Support for nested state access
  - Dot notation: {metadata.author}, {metadata.flags.level}
  - Works with Pydantic models and dicts
  - Deeply nested access (3+ levels)
  - Automatic type conversion (int, bool → string)

- Comprehensive error handling
  - \"Did you mean?\" suggestions for typos (edit distance ≤ 2)
  - Available inputs and state fields listed
  - Clear error messages with context
  - TemplateResolutionError exception

- Created 44 comprehensive tests
  - Simple variable resolution (inputs, state)
  - Input override priority
  - Nested state access (1 level, 3+ levels)
  - Multiple variables, type conversion
  - Error cases with suggestions
  - Helper functions (extract, get_nested_value)
  - Edit distance algorithm
  - Integration scenarios

Verification:
  pytest -v -m 'not integration'
  Expected: 344 passed (44 template + 300 existing)

Progress: 11/20 tasks (55%) - Phase 2 (Core Execution) 3/6 complete
Next: T-011 (Node Executor)"
```

---

## 🔗 Related Documentation

- **[../../TASKS.md](../../TASKS.md)** - Task T-010 acceptance criteria
- **[../../SPEC.md](../../SPEC.md)** - Template syntax specification
- **[../../ARCHITECTURE.md](../../ARCHITECTURE.md)** - Template resolver architecture
- **[../../PROJECT_VISION.md](../../PROJECT_VISION.md)** - Template enhancement roadmap

---

## 🚀 Next Steps for Users

### Use in Workflow Configs

```yaml
nodes:
  - id: greet
    prompt: "Hello {name}, discuss {topic}"
    inputs:
      name: "{state.user_name}"  # Mapped from state
```

### Test Template Resolution

```python
from configurable_agents.core import resolve_prompt, extract_variables
from pydantic import BaseModel

class State(BaseModel):
    topic: str
    metadata: dict

state = State(topic="AI", metadata={"author": "Alice"})

# Simple resolution
result = resolve_prompt("Topic: {topic}", {}, state)
# → "Topic: AI"

# Nested resolution
result = resolve_prompt("By {metadata.author}", {}, state)
# → "By Alice"

# Extract variables
vars = extract_variables("{topic} by {metadata.author}")
# → {"topic", "metadata.author"}
```

---

## 📊 Phase 2 Progress

**Phase 2 (Core Execution): 3/6 complete (50%)**
- ✅ T-008: Tool Registry
- ✅ T-009: LLM Provider
- ✅ T-010: Prompt Template Resolver
- ⏳ T-011: Node Executor
- ⏳ T-012: Graph Builder
- ⏳ T-013: Runtime Executor

---

*Implementation completed: 2026-01-25*
*Next task: T-011 (Node Executor)*
