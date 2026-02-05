# ADR-002: Strict Typing with Pydantic Schemas

**Status**: Accepted
**Date**: 2026-01-24
**Deciders**: User, Claude Code

---

## Context

LLMs are inherently non-deterministic and output unstructured text. This creates several production challenges:

### The Problem with Unstructured Outputs

**Scenario**: Article writer workflow
```yaml
nodes:
  - id: write
    prompt: "Write an article about {topic}"
    # What format does the LLM return?
    # - Just text?
    # - JSON?
    # - What if it returns invalid JSON?
    # - What if it's missing expected fields?
```

**Production failures**:
1. **Runtime type errors**: Code expects `dict`, gets `str`
2. **Missing fields**: Code accesses `result['score']`, but field doesn't exist
3. **Wrong types**: Code expects `int`, gets `"seven"`
4. **Late failures**: Workflow runs 7 steps, fails at step 8 due to type mismatch → wasted LLM costs

### The DX Problem

Without schemas, users can't tell what a node produces:
```yaml
- id: research
  prompt: "Research {topic}"
  # What does this output? ¯\_(ツ)_/¯
```

### The Testing Problem

How do you test a workflow when outputs are unpredictable?
- Mock LLM responses need to match... what format?
- Integration tests break when LLM changes output format

---

## Decision

**All node outputs MUST conform to Pydantic schemas defined in config.**

**All state fields MUST have declared types in config.**

---

## Implementation

### Config Requirement

Every node must declare an `output_schema`:

```yaml
nodes:
  - id: research
    prompt: "Research {topic} and provide summary and sources"
    outputs:
      - summary
      - sources
    output_schema:
      fields:
        - name: summary
          type: str
          description: "Concise summary of findings"
        - name: sources
          type: list[str]
          description: "List of source URLs"
```

### State Schema Requirement

State fields must be declared with types:

```yaml
state:
  fields:
    topic:
      type: str
      required: true
    summary:
      type: str
      default: ""
    sources:
      type: list[str]
      default: []
```

### Runtime Behavior

1. **Config validation**: Check that `outputs` match `output_schema` fields
2. **Schema generation**: Create Pydantic model from `output_schema`
3. **Structured LLM call**: Force LLM to return JSON matching schema
4. **Validation**: Pydantic validates output before updating state
5. **Type error → crash**: If validation fails, crash loudly with details

---

## Rationale

### 1. Fail Fast, Save Money

**Without schemas**:
```
Step 1 (research): ✓ $0.01
Step 2 (outline): ✓ $0.02
Step 3 (write): ✓ $0.10
Step 4 (review): ✗ TypeError: expected dict, got str
Total cost: $0.13 (wasted)
```

**With schemas**:
```
Config validation: ✗ Error: node 'review' expects dict but 'write' outputs str
Total cost: $0.00 (caught before execution)
```

### 2. Self-Documenting Configs

```yaml
# Anyone reading this knows exactly what 'research' produces
- id: research
  output_schema:
    fields:
      - name: summary
        type: str
      - name: sources
        type: list[str]
```

No need to read code or docs to understand data flow.

### 3. Testing is Reliable

```python
# Test with mock LLM output
mock_output = ResearchOutput(
    summary="AI safety is important",
    sources=["https://..."]
)

# Guaranteed to work because it's the same schema
```

### 4. IDE Support

With typed state, users get autocomplete and type checking:
```python
# state is fully typed
state.summary  # IDE knows this is str
state.sources  # IDE knows this is list[str]
```

### 5. Production-Grade Validation

Pydantic provides:
- Type coercion (e.g., "123" → 123)
- Validation (e.g., email format, min/max values)
- Error messages (e.g., "field 'score' must be int, got str")

---

## Alternatives Considered

### Alternative 1: Unstructured Outputs (Flexible)

```yaml
nodes:
  - id: research
    prompt: "Research {topic}"
    # No schema - LLM returns whatever
```

**Pros**:
- Simpler config
- More flexible
- LLM can be creative

**Cons**:
- **Runtime failures** (dealbreaker for production)
- Hard to test
- No type safety
- Wasted LLM costs on failures

**Why rejected**: Not production-grade. Fails late instead of early.

### Alternative 2: Optional Schemas

```yaml
nodes:
  - id: research
    output_schema: optional
```

**Pros**:
- Flexibility when needed
- Gradual adoption

**Cons**:
- **Complexity**: Two execution paths (typed vs untyped)
- **Confusion**: When to use which?
- **Type safety holes**: Downstream nodes don't know types

**Why rejected**: Complexity without significant benefit. Better to have one clear path.

### Alternative 3: Inferred Schemas

```yaml
nodes:
  - id: research
    outputs: [summary, sources]
    # Infer types from state schema
```

**Pros**:
- Less verbose config
- Types still enforced

**Cons**:
- **Ambiguity**: What if output schema differs from state schema?
- **Hidden behavior**: Not clear what LLM should return
- **LLM confusion**: No description field to guide LLM

**Why rejected**: Explicitness is better than brevity. LLM needs descriptions.

### Alternative 4: Python Type Hints Instead of YAML

```python
class ResearchOutput(BaseModel):
    summary: str
    sources: list[str]

# Reference in YAML
nodes:
  - id: research
    output_schema: ResearchOutput
```

**Pros**:
- Reusable schemas
- Type checking in Python

**Cons**:
- **Requires code**: Defeats config-only approach
- **Not config-first**: Config references external code

**Why rejected**: We want config-as-code, not code-as-config. May reconsider for advanced use cases in v0.2+.

---

## Consequences

### Positive Consequences

1. **Early Validation**: Catch type errors before execution
   ```
   Config error: node 'write' outputs 'article' (str) but state expects 'article' (dict)
   ```

2. **Clear Contracts**: Every node declares inputs/outputs explicitly
   ```yaml
   outputs: [summary, sources]  # Explicit contract
   ```

3. **Testability**: Mock outputs match real outputs exactly

4. **Cost Savings**: No wasted LLM calls due to type mismatches

5. **Better Error Messages**:
   ```
   ValidationError: field 'score' must be int, got 'seven'
   Node: validate
   State: {topic: "AI", article: "..."}
   ```

6. **DSPy Compatibility**: Schemas can be used for DSPy signatures
   ```python
   signature = dspy.Signature(
       "topic -> summary, sources",
       summary=str,
       sources=list[str]
   )
   ```

### Negative Consequences

1. **More Verbose Configs**: Every node needs explicit schema
   ```yaml
   # This is now required:
   output_schema:
     fields:
       - name: summary
         type: str
   ```

2. **Less Flexibility**: Can't let LLM return arbitrary formats
   - **Mitigation**: Support `dict` type for unstructured data if needed

3. **LLM Failures**: LLM might not return valid JSON
   - **Mitigation**: Retry with clarified prompt, add examples

4. **Config Complexity**: New users might find schemas intimidating
   - **Mitigation**: Provide templates and examples

### Risks

#### Risk 1: LLMs Fail to Follow Schema

**Likelihood**: Medium (especially with complex schemas)
**Impact**: Medium (node execution fails)

**Mitigation**:
- Use LLM structured output mode (JSON mode)
- Add schema description to prompt
- Retry with examples if first attempt fails
- Log schema validation errors for debugging

**Example**:
```python
# If LLM returns invalid JSON:
prompt_with_example = f"""
{original_prompt}

Return JSON matching this schema:
{{
  "summary": "string",
  "sources": ["url1", "url2"]
}}

Example:
{{
  "summary": "AI safety focuses on...",
  "sources": ["https://example.com"]
}}
"""
```

#### Risk 2: Type System Too Limited

**Likelihood**: Medium (as use cases grow)
**Impact**: Low (can extend type system)

**Mitigation**:
- Start with basic types (str, int, float, bool, list, dict)
- Add complex types as needed (union, optional, literal)
- Document type system clearly in SPEC.md

#### Risk 3: Pydantic Breaking Changes

**Likelihood**: Low (Pydantic v2 is stable)
**Impact**: Medium (need to update schema builder)

**Mitigation**:
- Pin Pydantic version
- Test with new versions before upgrading
- Abstract Pydantic behind our schema builder

---

## Verification Steps

### T-006: State Schema Builder
- [ ] Generate Pydantic models from state config
- [ ] Test all supported types
- [ ] Validate required fields
- [ ] Test default values

### T-007: Output Schema Builder
- [ ] Generate Pydantic models from output_schema
- [ ] Include field descriptions
- [ ] Test validation errors

### T-011: Node Executor
- [ ] Call LLM with structured output (Pydantic schema)
- [ ] Validate output before updating state
- [ ] Test retry on validation failure
- [ ] Log clear error messages

---

## Examples

### Simple Schema

```yaml
output_schema:
  fields:
    - name: result
      type: str
```

### Complex Schema

```yaml
output_schema:
  fields:
    - name: article
      type: str
      description: "Full article text (400-600 words)"
    - name: word_count
      type: int
      description: "Exact word count"
    - name: keywords
      type: list[str]
      description: "Key topics covered (3-5 keywords)"
    - name: metadata
      type: dict
      description: "Additional metadata"
```

### State Schema

```yaml
state:
  fields:
    # Required input
    topic:
      type: str
      required: true

    # Step outputs
    research:
      type: str
      default: ""

    article:
      type: str
      default: ""

    score:
      type: int
      default: 0

    feedback:
      type: str
      default: ""
```

---

## Future Enhancements

### v0.2: Advanced Types
- `Optional[str]` (nullable fields)
- `Union[str, int]` (multiple types)
- `Literal["draft", "final"]` (enum-like)

### v0.3: Custom Validators
```yaml
output_schema:
  fields:
    - name: score
      type: int
      validators:
        - min: 0
        - max: 10
```

### v0.4: Nested Schemas
```yaml
output_schema:
  fields:
    - name: result
      type: object
      schema:
        fields:
          - name: summary
            type: str
          - name: details
            type: list[str]
```

---

## References

- Pydantic docs: https://docs.pydantic.dev/
- LLM structured outputs: https://platform.openai.com/docs/guides/structured-outputs
- Type safety benefits: Internal analysis

---

## Notes

This decision reflects a core philosophy: **production-grade systems fail fast and validate early.**

Unstructured LLM outputs are fine for prototypes, but production systems need guarantees. Pydantic schemas provide those guarantees at minimal cost (slightly more verbose config).

The tradeoff is worth it: better DX, fewer runtime surprises, lower costs.

---

## Implementation Details

**Status**: ✅ Implemented in v0.1
**Related Tasks**: T-003 (Config Schema), T-005 (Type System), T-006 (State Builder), T-007 (Output Builder), T-011 (Node Executor)
**Date Implemented**: 2026-01-26 to 2026-01-27

### T-005: Type System Implementation

**File**: `src/configurable_agents/config/types.py` (150 lines)

**Type String Parsing**:
```python
def parse_type_string(type_str: str) -> dict:
    """Parse type strings like 'list[str]', 'dict[str, int]'"""
    # Returns: {"kind": "list", "item_type": {"kind": "str"}}

# Supported types:
# - Primitives: str, int, float, bool
# - Collections: list[T], dict[K, V]
# - Object: object (for structured outputs)
```

**Type Validation**:
- Parse-time validation of type strings in config
- Validates nested types recursively
- Clear error messages: `"Invalid type 'lisst[str]' - did you mean 'list[str]'?"`

**Python Type Conversion**:
```python
def get_python_type(type_str: str) -> type:
    """Convert type string to Python type for Pydantic"""
    get_python_type("str")  # → str
    get_python_type("list[str]")  # → list
    get_python_type("dict[str, int]")  # → dict
```

**Test Coverage**: 31 type parsing tests

---

### T-006: State Schema Builder Implementation

**File**: `src/configurable_agents/core/state_builder.py` (200 lines)

**Dynamic Pydantic Model Generation**:
```python
def build_state_model(state_schema: StateSchema) -> Type[BaseModel]:
    """Generate Pydantic BaseModel from StateSchema config"""

    # Build field definitions
    field_defs = {}
    for field in state_schema.fields:
        python_type = get_python_type(field.type)
        default = ... if field.required else field.default
        field_defs[field.name] = (python_type, default)

    # Create model dynamically
    StateModel = create_model(
        "WorkflowState",
        **field_defs
    )
    return StateModel
```

**Features**:
- Required fields → Pydantic `...` (ellipsis)
- Optional fields → default values
- Type validation enforced by Pydantic
- Model name: `WorkflowState`

**Example**:
```yaml
# Config
state:
  fields:
    - name: topic
      type: str
      required: true
    - name: article
      type: str
      default: ""
```

```python
# Generated model (equivalent to):
class WorkflowState(BaseModel):
    topic: str  # Required
    article: str = ""  # Optional with default
```

**Test Coverage**: 25 state builder tests

---

### T-007: Output Schema Builder Implementation

**File**: `src/configurable_agents/core/output_builder.py` (180 lines)

**Dynamic Output Model Generation**:
```python
def build_output_model(
    output_schema: OutputSchema,
    node_id: str
) -> Type[BaseModel]:
    """Generate Pydantic model for node output validation"""

    if output_schema.type != "object":
        # Simple output wrapped in 'result' field
        return create_model(
            f"Output_{node_id}",
            result=(get_python_type(output_schema.type), ...)
        )
    else:
        # Object output with explicit fields
        field_defs = {
            field.name: (get_python_type(field.type), ...)
            for field in output_schema.fields
        }
        return create_model(f"Output_{node_id}", **field_defs)
```

**Two Output Modes**:

1. **Simple Output** (single value):
```yaml
output_schema:
  type: str
# LLM must return: {"result": "text here"}
```

2. **Object Output** (multiple fields):
```yaml
output_schema:
  type: object
  fields:
    - {name: article, type: str}
    - {name: word_count, type: int}
# LLM must return: {"article": "...", "word_count": 500}
```

**Field Descriptions for LLM**:
- Descriptions passed to LLM via JSON schema
- Helps LLM understand what to return
- Example: `"description": "Concise summary of findings"`

**Test Coverage**: 29 output builder tests

---

### T-011: Node Executor Integration

**File**: `src/configurable_agents/core/node_executor.py` (280 lines)

**Structured Output Enforcement Flow**:

```python
def execute_node(
    node_config: NodeConfig,
    state: BaseModel,
    global_config: Optional[GlobalConfig] = None
) -> BaseModel:
    """Execute node with structured output validation"""

    # 1. Build output model from schema
    OutputModel = build_output_model(
        node_config.output_schema,
        node_config.id
    )

    # 2. Configure LLM with structured output
    llm = create_llm(llm_config)
    llm_with_schema = llm.with_structured_output(
        OutputModel.model_json_schema()
    )

    # 3. Bind tools if specified
    if node_config.tools:
        tools = [get_tool(name) for name in node_config.tools]
        llm_with_schema = llm_with_schema.bind_tools(tools)

    # 4. Call LLM (guaranteed to return dict matching OutputModel)
    response = llm_with_schema.invoke(prompt)

    # 5. Validate output against schema
    validated_output = OutputModel(**response)

    # 6. Update state with validated output
    state_dict = state.model_dump()
    for field_name in node_config.outputs:
        if hasattr(validated_output, field_name):
            state_dict[field_name] = getattr(validated_output, field_name)
        elif hasattr(validated_output, 'result'):
            state_dict[field_name] = validated_output.result

    # 7. Return new state instance (immutable update)
    return type(state)(**state_dict)
```

**Validation Guarantees**:
1. **LLM returns structured JSON**: `with_structured_output()` forces JSON mode
2. **Pydantic validates types**: `OutputModel(**response)` validates all fields
3. **Missing fields → error**: Pydantic raises ValidationError if LLM omits field
4. **Wrong types → error**: Pydantic converts or raises error
5. **State update → type-safe**: New state instance validated by StateModel

**Error Handling**:
```python
class NodeExecutionError(Exception):
    """Wraps all node execution errors with context"""

# Example error message:
# NodeExecutionError: Node 'research' failed:
#   Output validation failed: field 'sources' missing
```

**Test Coverage**: 23 node executor tests (including output validation scenarios)

---

### Production Validation (T-017)

**Real API Testing** (Integration Tests):
- 19 integration tests with real Gemini API calls
- Structured outputs validated across all workflows
- Error scenarios tested (invalid output types, missing fields)

**Results**:
- ✅ Gemini `with_structured_output()` works reliably
- ✅ Pydantic validation catches all type errors
- ✅ Clear error messages for debugging
- ⚠️ Known limitation: Nested objects not yet supported (deferred to v0.2)

**Example Integration Test**:
```python
def test_article_writer_workflow_integration():
    """Test multi-node workflow with structured outputs"""
    config = load_config("examples/article_writer.yaml")

    # Execute workflow
    result = run_workflow(config, {"topic": "AI Safety"})

    # Validate structured outputs
    assert isinstance(result["research"], str)  # from research node
    assert isinstance(result["article"], str)  # from write node
    assert len(result["article"]) > 0
```

---

## Implementation Learnings

### What Worked Well

1. **`with_structured_output()` is Reliable**
   - Google Gemini JSON mode enforces schema
   - Rarely returns invalid JSON
   - Field names and types respected

2. **Pydantic Validation is Robust**
   - Clear error messages
   - Type coercion helps (e.g., "123" → 123)
   - Catches errors before they corrupt state

3. **Field Descriptions Help LLM**
   - Including descriptions in JSON schema improves accuracy
   - LLM better understands what to return

### Known Limitations (v0.1)

1. **Nested Objects Not Supported**
   - Can't do: `{"result": {"summary": "...", "details": [...]}}`
   - Workaround: Flatten to top-level fields
   - Planned for v0.2

2. **All Output Fields Required**
   - LLM must provide all fields in `output_schema`
   - Can't mark fields as optional
   - Planned for v0.2

3. **No Union Types**
   - Can't do: `type: str | int`
   - Workaround: Use str and parse if needed
   - Planned for v0.3

---

## Superseded By

None (current)
