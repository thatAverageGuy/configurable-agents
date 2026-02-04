# T-004: Config Validator

**Status**: ✅ Complete
**Completed**: 2026-01-24
**Commit**: `e43c28b` - T-004: Config validator - Comprehensive validation
**Phase**: Phase 1 (Foundation)
**Progress After**: 4/20 tasks (20%)

---

## 🎯 What Was Done

- Implemented comprehensive config validation beyond Pydantic schema checks
- Cross-reference validation (node IDs, state fields, output types)
- Graph structure validation (connectivity, reachability)
- Linear flow enforcement (v0.1 constraints: no cycles, no conditional routing)
- Fail-fast error handling with helpful suggestions
- "Did you mean...?" suggestions for typos using edit distance
- Context-aware error messages with clear guidance
- 29 comprehensive validator tests
- Total: 153 tests passing (up from 124)

---

## 📦 Files Created

### Source Code

```
src/configurable_agents/config/
└── validator.py (validation engine with 8 validation stages)
```

### Tests

```
tests/config/
└── test_validator.py (29 comprehensive tests)
```

---

## 🔧 How to Verify

### 1. Test validation

```bash
pytest tests/config/test_validator.py -v
# Expected: 29 passed
```

### 2. Run full test suite

```bash
pytest -v
# Expected: 153 passed (18 parser + 67 schema + 31 types + 5 integration + 29 validator + 3 setup)
```

### 3. Validate a config programmatically

```python
from configurable_agents.config import parse_config_file, WorkflowConfig, validate_config

# Load and parse YAML/JSON
config_dict = parse_config_file("workflow.yaml")
config = WorkflowConfig(**config_dict)

# Validate (raises ValidationError if invalid)
validate_config(config)
print("Config is valid!")
```

### 4. Test error messages

```python
from configurable_agents.config import ValidationError

try:
    validate_config(invalid_config)
except ValidationError as e:
    print(f"Error: {e.message}")
    print(f"Context: {e.context}")
    print(f"Suggestion: {e.suggestion}")
```

---

## ✅ What to Expect

**Working**:
- ✅ Comprehensive validation catches common errors early
- ✅ Helpful error messages with context and suggestions
- ✅ "Did you mean 'process'?" for typos (edit distance ≤ 2)
- ✅ Fail-fast: stops at first error category
- ✅ Clear distinction between v0.1 features vs v0.2+ (with timeline info)
- ✅ Graph validation ensures all nodes reachable and can reach END
- ✅ Type safety: output types must match state field types
- ✅ No hidden surprises: placeholders validated at parse time

**Not Yet Working**:
- ❌ No runtime feature gating yet (T-004.5: reject unsupported features at runtime)
- ❌ Validation is parse-time only (no runtime state validation)

---

## 💻 Public API

### Main Validation Function

```python
from configurable_agents.config import validate_config, ValidationError

# Validate config (raises ValidationError if invalid)
try:
    validate_config(config)
except ValidationError as e:
    print(e)  # Includes message, context, and suggestion
```

### Custom Exception

```python
from configurable_agents.config import ValidationError

# ValidationError attributes:
# - message: Primary error message
# - context: Additional context (optional)
# - suggestion: Helpful suggestion (optional)
```

### Complete Public API

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

---

## 📚 Dependencies Used

- `pydantic >= 2.0` - Schema validation (inherited from T-003)
- Standard library only for validation logic

---

## 💡 Design Decisions

### Why 8 Validation Stages?

Validation is performed in fail-fast order to provide the most helpful error message first:

1. **Edge references** - Nodes must exist before checking outputs
2. **Node outputs** - State fields must exist before checking types
3. **Output schema alignment** - Schema fields must match outputs list
4. **Type alignment** - Output types must match state types
5. **Prompt placeholders** - Variables must reference valid fields
6. **State types** - All type strings must be valid
7. **Linear flow constraints** - v0.1 specific (no cycles, no conditionals)
8. **Graph structure** - Connectivity and reachability

### Why "Did you mean...?" suggestions?

- Uses edit distance (Levenshtein) to find typos
- Only suggests if distance ≤ 2 (too far = not helpful)
- Helps users fix common mistakes quickly
- Inspired by compiler error messages

### Why fail-fast?

- Show most helpful error first
- Avoid cascading errors (one fix may resolve many)
- Faster feedback loop for users
- Simpler error handling logic

### Why linear flow enforcement in validator?

- v0.1 only supports linear flows (no cycles, no conditional routing)
- Validation ensures configs are compatible with v0.1 runtime
- Clear error messages explain feature availability timeline
- Helps users understand what's supported now vs future

---

## 🧪 Tests Created

**File**: `tests/config/test_validator.py`

### Test Categories (29 tests total)

1. **Valid Configs** (3 tests)
   - Minimal valid config
   - Complex valid config with all features
   - Edge cases (single node, multiple outputs)

2. **Edge Reference Validation** (4 tests)
   - Invalid 'from' node reference
   - Invalid 'to' node reference
   - "Did you mean...?" suggestions for typos
   - Multiple invalid references

3. **Node Output Validation** (4 tests)
   - Output field not in state
   - Multiple missing output fields
   - "Did you mean...?" suggestions for field typos
   - Empty outputs list

4. **Output Schema Alignment** (4 tests)
   - Schema fields don't match outputs list
   - Extra fields in schema
   - Missing fields in schema
   - Object schema without fields

5. **Type Alignment** (3 tests)
   - Output type doesn't match state type
   - Multiple type mismatches
   - Collection type mismatches (list vs dict)

6. **Prompt Placeholder Validation** (3 tests)
   - Invalid placeholder reference
   - Multiple invalid placeholders
   - Nested placeholder syntax

7. **State Type Validation** (2 tests)
   - Invalid type string
   - Multiple invalid types

8. **Linear Flow Constraints** (3 tests)
   - Cycle detection
   - Conditional routing (v0.2+ feature)
   - Multiple outgoing edges from single node

9. **Graph Structure** (3 tests)
   - Orphaned nodes (unreachable from START)
   - Dead-end nodes (can't reach END)
   - Disconnected subgraphs

---

## ✅ Validation Features

### Edge Reference Validation
- ✅ Edge 'from' points to valid node
- ✅ Edge 'to' points to valid node
- ✅ Route 'to' points to valid node
- ✅ "Did you mean...?" suggestions for typos

### Node Output Validation
- ✅ All node outputs exist in state fields
- ✅ Output field names are valid
- ✅ "Did you mean...?" suggestions for field typos

### Output Schema Alignment
- ✅ Schema fields match outputs list (for object outputs)
- ✅ No extra fields in schema
- ✅ No missing fields in schema
- ✅ Object outputs must have fields

### Type Alignment
- ✅ Output types match state field types
- ✅ Basic type matching (str, int, float, bool)
- ✅ Collection type matching (list, dict)
- ✅ Helpful error messages for mismatches

### Prompt Placeholder Validation
- ✅ All {variable} references are valid state fields
- ✅ Placeholders validated in prompts and system messages
- ✅ Clear error messages with placeholder location

### State Type Validation
- ✅ All state field types are valid type strings
- ✅ Type strings validated using type system (T-003)

### Linear Flow Constraints (v0.1)
- ✅ No conditional routing (edge.routes)
- ✅ No cycles in graph
- ✅ Each node has at most one outgoing edge
- ✅ Single entry point from START

### Graph Structure
- ✅ START node connectivity
- ✅ All nodes reachable from START
- ✅ All nodes have path to END
- ✅ No orphaned nodes

---

## 📖 Example Error Messages

### Missing State Field

```
ValidationError: Node 'process': output 'missing_field' not found in state fields
Suggestion: Add 'missing_field' to state.fields or check spelling. Available fields: ['input', 'output']
```

### Typo in Node Reference

```
ValidationError: Edge 0: 'to' references unknown node 'proces'
Suggestion: Did you mean 'process'?
```

### Cycle Detected

```
ValidationError: Cycle detected in workflow: step1 -> step2 -> step1
Suggestion: Remove edges to break the cycle. Linear workflows cannot have loops (loops available in v0.2+)
Context: v0.1 supports linear flows only
```

### Conditional Routing (v0.2+ feature)

```
ValidationError: Edge 0: Conditional routing not supported in v0.1
Suggestion: Use linear edges (from/to) instead. Conditional routing available in v0.2+ (8-12 weeks)
Context: Edge: START -> routes. See docs/PROJECT_VISION.md for roadmap
```

### Type Mismatch

```
ValidationError: Node 'process': output 'result' has type 'int' but state field 'result' has type 'str'
Suggestion: Change output type to 'str' or change state field type to 'int'
```

---

## 📖 Documentation Updated

- ✅ CHANGELOG.md (comprehensive entry created)
- ✅ docs/TASKS.md (T-004 marked DONE, progress updated to 4/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated)

---

## 📝 Git Commit Template

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

## 🔗 Related Documentation

- **[../../TASKS.md](../../TASKS.md)** - Task T-004 acceptance criteria
- **[../../SPEC.md](../../SPEC.md)** - Validation requirements
- **[../../ARCHITECTURE.md](../../ARCHITECTURE.md)** - Validator component
- **[../../PROJECT_VISION.md](../../PROJECT_VISION.md)** - Feature roadmap (v0.1 vs v0.2+)

---

*Implementation completed: 2026-01-24*
*Next task: T-004.5 (Runtime Feature Gating)*
