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

## Superseded By

None (current)
