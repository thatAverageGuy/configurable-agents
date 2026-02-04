# T-015: Example Configs

**Status**: ✅ Complete
**Completed**: 2026-01-27
**Commit**: T-015: Example configs - Working workflow examples
**Phase**: Phase 3 (Polish & UX)
**Progress After**: 16/20 tasks (80%)

---

## 🎯 What Was Done

- Created 4 comprehensive example workflow configs with full documentation
- Each example demonstrates different features and complexity levels
- All examples validated and working end-to-end
- Individual README files for each example with detailed explanations
- Updated main examples/README.md with organized examples catalog
- Complete learning path from beginner to advanced
- Total: 443 tests passing (no regressions)

---

## 📦 Files Created

### Example Workflows

```
examples/
├── echo.yaml (31 lines - minimal example)
├── article_writer.yaml (64 lines - multi-step with tools)
├── nested_state.yaml (52 lines - nested objects)
├── type_enforcement.yaml (78 lines - type system demo)
└── simple_workflow.yaml (existing, kept for compatibility)
```

### Documentation

```
examples/
├── echo_README.md (comprehensive beginner guide)
├── article_writer_README.md (detailed tool integration walkthrough)
├── nested_state_README.md (nested structure guide)
├── type_enforcement_README.md (type system reference)
└── README.md (updated with all examples, learning path)
```

---

## 🔧 How to Verify

### 1. Validate all examples

```bash
# All examples validate successfully
configurable-agents validate examples/echo.yaml  # ✅
configurable-agents validate examples/article_writer.yaml  # ✅
configurable-agents validate examples/nested_state.yaml  # ✅
configurable-agents validate examples/type_enforcement.yaml  # ✅
```

### 2. Run examples

```bash
# 1. Minimal (echo)
configurable-agents run examples/echo.yaml --input message="Hello!"

# 2. Multi-step with tools (article writer)
export SERPER_API_KEY="your-key"
configurable-agents run examples/article_writer.yaml --input topic="AI Safety"

# 3. Nested state (profile generator)
configurable-agents run examples/nested_state.yaml \
  --input name="Alice" \
  --input 'interests=["AI", "robotics", "philosophy"]'

# 4. Type enforcement (analysis)
configurable-agents run examples/type_enforcement.yaml \
  --input topic="Artificial Intelligence"
```

### 3. Full test suite

```bash
pytest -v -m "not integration"
# Expected: 443 passed (no regressions)
```

---

## ✅ What to Expect

**Working**:
- ✅ 4 validated example workflows
- ✅ Progressive complexity (minimal → advanced)
- ✅ Each example demonstrates specific features
- ✅ Comprehensive documentation for each
- ✅ Learning path from beginner to expert
- ✅ All examples tested and working
- ✅ Real-world relevant patterns

**Not Demonstrated**:
- ❌ Conditional routing (v0.2+ feature)
- ❌ Parallel execution (v0.2+ feature)
- ❌ Loops/cycles (v0.2+ feature)

---

## 📚 Examples Created

### 1. echo.yaml ⭐ (Minimal)

**Purpose**: Simplest possible workflow
**Complexity**: Beginner
**Lines**: 31
**Features**:
- 1 node, 1 input, 1 output
- Perfect for testing installation
- Understanding basic config structure
- No tools required

**Usage**:
```bash
configurable-agents run examples/echo.yaml --input message="Hello!"
```

**What You Learn**:
- Basic config structure
- Required fields (state, nodes, edges)
- Simple prompts
- Single output

**Config Snippet**:
```yaml
state:
  fields:
    - name: message
      type: str
    - name: response
      type: str

nodes:
  - id: echo
    prompt: "Repeat this message: {state.message}"
    outputs:
      - response

edges:
  - from: START
    to: echo
  - from: echo
    to: END
```

---

### 2. article_writer.yaml ⭐⭐⭐ (Intermediate)

**Purpose**: Multi-step workflow with tool integration
**Complexity**: Intermediate
**Lines**: 64
**Features**:
- 2 nodes (research → write)
- Tool integration (serper_search)
- State flowing between nodes
- Multiple typed outputs
- Global configuration (LLM, timeout, retries)

**Requirements**:
- SERPER_API_KEY environment variable

**Usage**:
```bash
export SERPER_API_KEY="your-key"
configurable-agents run examples/article_writer.yaml --input topic="AI Safety"
```

**What You Learn**:
- Multi-step workflows
- Tool integration and usage
- State passing between nodes
- Multiple outputs (article, word_count)
- Global LLM configuration
- Node-level LLM overrides

**Config Snippet**:
```yaml
config:
  llm:
    provider: google
    model: gemini-2.5-flash-lite
    temperature: 0.7
  timeout: 120
  max_retries: 3

nodes:
  - id: research
    prompt: "Research this topic: {state.topic}"
    tools:
      - serper_search
    outputs:
      - research

  - id: write
    prompt: "Write an article about {state.topic} using: {state.research}"
    outputs:
      - article
      - word_count
    output_schema:
      type: object
      fields:
        article:
          type: str
        word_count:
          type: int
```

---

### 3. nested_state.yaml ⭐⭐ (Intermediate)

**Purpose**: Demonstrate nested object types with schema
**Complexity**: Intermediate
**Lines**: 52
**Features**:
- Nested object types with schema
- List types (list[str])
- Complex state with multiple levels
- Object field access
- Input: name + list of interests
- Output: nested profile object

**Usage**:
```bash
configurable-agents run examples/nested_state.yaml \
  --input name="Alice" \
  --input 'interests=["AI", "robotics", "philosophy"]'
```

**What You Learn**:
- Nested object types
- List types with elements
- Complex state structures
- Object schema definition
- Accessing nested fields

**Config Snippet**:
```yaml
state:
  fields:
    - name: name
      type: str
    - name: interests
      type: list[str]
    - name: profile
      type: object
      schema:
        name:
          type: str
        interests:
          type: list[str]
        bio:
          type: str

nodes:
  - id: generate_profile
    prompt: "Create profile for {state.name} with interests: {state.interests}"
    outputs:
      - profile
    output_schema:
      type: object
      fields:
        name:
          type: str
        interests:
          type: list[str]
        bio:
          type: str
```

---

### 4. type_enforcement.yaml ⭐⭐⭐ (Advanced)

**Purpose**: Demonstrate all type system types
**Complexity**: Advanced
**Lines**: 78
**Features**:
- All type system types demonstrated
- int, bool, float, str, list[str], dict[str, int], object
- Multiple typed outputs from single node
- Type validation at multiple levels
- Automatic retry on type mismatches
- Lower temperature for type consistency

**Usage**:
```bash
configurable-agents run examples/type_enforcement.yaml \
  --input topic="Artificial Intelligence"
```

**What You Learn**:
- Complete type system
- Type validation
- Automatic retries
- Multiple outputs with types
- Output schema enforcement
- Type consistency patterns

**Config Snippet**:
```yaml
state:
  fields:
    - name: topic
      type: str
    - name: summary
      type: str
    - name: word_count
      type: int
    - name: is_technical
      type: bool
    - name: relevance_score
      type: float
    - name: keywords
      type: list[str]
    - name: category_scores
      type: dict[str, int]
    - name: metadata
      type: object
      schema:
        author:
          type: str
        version:
          type: int

nodes:
  - id: analyze
    llm:
      temperature: 0.3  # Lower for type consistency
    prompt: "Analyze this topic: {state.topic}"
    outputs:
      - summary
      - word_count
      - is_technical
      - relevance_score
      - keywords
      - category_scores
      - metadata
    output_schema:
      type: object
      fields:
        summary: {type: str}
        word_count: {type: int}
        is_technical: {type: bool}
        relevance_score: {type: float}
        keywords: {type: list[str]}
        category_scores: {type: dict[str, int]}
        metadata:
          type: object
          fields:
            author: {type: str}
            version: {type: int}
```

---

## 📖 Learning Path

### For Complete Beginners

1. **Start with `echo.yaml`**
   - Verify installation works
   - Understand basic config structure
   - See simple prompt → output flow

2. **Try `simple_workflow.yaml`**
   - Understand state management
   - See variable substitution
   - Learn about state fields

3. **Choose your path**:
   - Multi-step workflows → `article_writer.yaml`
   - Complex data structures → `nested_state.yaml`
   - Type mastery → `type_enforcement.yaml`

### For Intermediate Users

1. **Multi-Step Workflows**
   - Study `article_writer.yaml`
   - Understand tool integration
   - Learn sequential node execution
   - Master state passing between nodes

2. **Complex Data Structures**
   - Study `nested_state.yaml`
   - Learn nested objects
   - Understand list types
   - Master object schemas

3. **Type System Mastery**
   - Study `type_enforcement.yaml`
   - All types demonstrated
   - Validation patterns
   - Retry strategies

### For Advanced Users

- Combine patterns from all examples
- Build complex multi-step workflows
- Use all type system features
- Implement production patterns

---

## 💡 Design Decisions

### Why Progressive Complexity?

- Examples range from trivial to advanced
- Clear learning progression
- Users can start simple and advance
- Each level builds on previous

### Why Feature Focus?

- Each example demonstrates specific capabilities
- Clear purpose for each example
- Easy to find relevant patterns
- Reference implementation for features

### Why Comprehensive Docs?

- Every example has detailed README
- Usage examples provided
- Expected outputs shown
- Common issues addressed

### Why Real-World Relevant?

- Examples show production-like patterns
- Not toy examples
- Actual use cases
- Scalable patterns

### Why Validated?

- All configs pass validation
- No syntax errors
- Proven to work
- Safe to copy and modify

---

## 📖 What You Can Learn

### From echo.yaml
- Basic config structure
- Required fields
- Simple prompts
- Single output
- Minimal workflow

### From simple_workflow.yaml
- State management
- Variable substitution ({state.field})
- Input/output flow
- Basic node execution

### From article_writer.yaml
- Multi-node workflows
- Tool integration (serper_search)
- Sequential execution
- State passing between nodes
- Global configuration
- Node-level overrides
- Multiple outputs
- Object output schemas

### From nested_state.yaml
- Nested objects
- List inputs (list[str])
- Complex state structures
- Object schemas
- Nested field access

### From type_enforcement.yaml
- Complete type system
- All basic types (str, int, float, bool)
- Collection types (list, dict)
- Object types with schemas
- Type validation
- Automatic retries
- Output schema enforcement
- Type consistency patterns

---

## 📖 Documentation Updated

- ✅ CHANGELOG.md (comprehensive entry created)
- ✅ docs/TASKS.md (T-015 marked DONE, progress updated to 16/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated, examples section added)
- ✅ examples/README.md (comprehensive catalog with learning path)
- ✅ examples/echo_README.md (beginner guide created)
- ✅ examples/article_writer_README.md (tool integration guide created)
- ✅ examples/nested_state_README.md (nested state guide created)
- ✅ examples/type_enforcement_README.md (type system reference created)

---

## 📝 Git Commit Template

```bash
git add .
git commit -m "T-015: Example configs - Working workflow examples

- Created 4 comprehensive example workflows
  1. echo.yaml (⭐ Minimal) - Simplest possible workflow
  2. article_writer.yaml (⭐⭐⭐ Intermediate) - Multi-step with tools
  3. nested_state.yaml (⭐⭐ Intermediate) - Nested objects
  4. type_enforcement.yaml (⭐⭐⭐ Advanced) - Type system demo

- Individual README files for each example
  - echo_README.md - Beginner guide
  - article_writer_README.md - Tool integration walkthrough
  - nested_state_README.md - Nested structure guide
  - type_enforcement_README.md - Type system reference

- Updated main examples/README.md
  - Organized examples catalog
  - Learning path from beginner to advanced
  - Usage examples for each workflow
  - Feature matrix

- All examples validated and working
  - No syntax errors
  - Pass validation
  - Tested end-to-end
  - Real-world relevant patterns

- Progressive complexity
  - Minimal → Intermediate → Advanced
  - Clear learning progression
  - Feature-focused demonstrations
  - Production-like patterns

Verification:
  # Validate all examples
  configurable-agents validate examples/echo.yaml
  configurable-agents validate examples/article_writer.yaml
  configurable-agents validate examples/nested_state.yaml
  configurable-agents validate examples/type_enforcement.yaml

  # Full test suite (no regressions)
  pytest -v -m 'not integration'
  Expected: 443 passed

Progress: 16/20 tasks (80%) - Phase 3 (Polish & UX) 2/5 complete
Next: T-016 (Documentation - User-facing guides)"
```

---

## 🔗 Related Documentation

- **[../../TASKS.md](../../TASKS.md)** - Task T-015 acceptance criteria
- **[../../../examples/README.md](../../../examples/README.md)** - Examples catalog
- **[../../../examples/echo_README.md](../../../examples/echo_README.md)** - Minimal example guide
- **[../../../examples/article_writer_README.md](../../../examples/article_writer_README.md)** - Tool integration guide
- **[../../../examples/nested_state_README.md](../../../examples/nested_state_README.md)** - Nested state guide
- **[../../../examples/type_enforcement_README.md](../../../examples/type_enforcement_README.md)** - Type system reference

---

## 🚀 Next Steps for Users

### Run All Examples

```bash
# 1. Minimal (echo)
configurable-agents run examples/echo.yaml --input message="Hello!"

# 2. Simple workflow
configurable-agents run examples/simple_workflow.yaml --input name="Alice"

# 3. Multi-step with tools (requires SERPER_API_KEY)
export SERPER_API_KEY="your-key"
configurable-agents run examples/article_writer.yaml --input topic="AI Safety"

# 4. Nested state
configurable-agents run examples/nested_state.yaml \
  --input name="Alice" \
  --input 'interests=["AI", "robotics"]'

# 5. Type enforcement
configurable-agents run examples/type_enforcement.yaml \
  --input topic="Artificial Intelligence"
```

### Modify Examples

```bash
# Copy an example to start your own workflow
cp examples/echo.yaml my_workflow.yaml

# Edit the config
vim my_workflow.yaml

# Validate your changes
configurable-agents validate my_workflow.yaml

# Run your workflow
configurable-agents run my_workflow.yaml --input message="Test"
```

---

## 📊 Phase 3 Progress

**Phase 3 (Polish & UX): 2/5 complete (40%)**
- ✅ T-014: CLI Interface
- ✅ T-015: Example Configs
- ⏳ T-016: Documentation
- ⏳ T-017: Integration Tests
- ⏳ T-018: Error Message Improvements (future)

---

*Implementation completed: 2026-01-27*
*Next task: T-016 (Documentation - User-facing guides)*
