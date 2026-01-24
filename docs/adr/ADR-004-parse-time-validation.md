# ADR-004: Parse-Time Validation

**Status**: Accepted
**Date**: 2026-01-24
**Deciders**: User, Claude Code

---

## Context

Config validation can happen at three different times:

### 1. Parse Time (Config Load)
```python
config = load_config("workflow.yaml")  # ← Validate here?
validate_config(config)  # Check structure, references, types
```

### 2. Build Time (Graph Construction)
```python
config = load_config("workflow.yaml")
graph = build_graph(config)  # ← Validate here?
# Check if nodes/edges can actually be built
```

### 3. Runtime (During Execution)
```python
config = load_config("workflow.yaml")
graph = build_graph(config)
result = graph.invoke(inputs)  # ← Validate here?
# Discover errors as they happen
```

---

## The Problem

**Scenario**: User creates a workflow config:

```yaml
state:
  fields:
    topic: {type: str, required: true}
    research: {type: str, default: ""}

nodes:
  - id: research
    prompt: "Research {state.topic}"
    outputs: [research_summary]  # ← BUG: should be 'research'
    output_schema:
      fields:
        - name: research_summary
          type: str

  - id: write
    prompt: "Write about {state.research}"  # ← Uses 'research'
    outputs: [article]
    output_schema:
      fields:
        - name: article
          type: str

edges:
  - {from: START, to: research}
  - {from: research, to: write}
  - {from: write, to: END}
```

**Bug**: `research` node outputs to `research_summary`, but state expects `research`.

**When should we catch this?**

### Option A: Runtime Validation

```
$ python -m configurable_agents run workflow.yaml --input topic="AI"

Executing node: research...
Calling LLM... ($0.01)
Received output: {"research_summary": "..."}
Updating state...
✗ Error: field 'research_summary' not found in state schema

Total cost: $0.01 (wasted)
```

### Option B: Build-Time Validation

```
$ python -m configurable_agents run workflow.yaml --input topic="AI"

Building graph...
✗ Error: node 'research' outputs to 'research_summary' but state has no such field

Total cost: $0.00
```

### Option C: Parse-Time Validation

```
$ python -m configurable_agents run workflow.yaml --input topic="AI"

Loading config...
✗ Error: node 'research' outputs to 'research_summary' but state schema only defines: topic, research

Total cost: $0.00
Time wasted: 0 seconds
```

---

## Decision

**Validate everything possible at parse time, before any execution begins.**

**Validation happens immediately after YAML parsing, before graph construction or LLM calls.**

---

## What Gets Validated at Parse Time

### 1. YAML Syntax
```yaml
flow:
  name: "test
  # ← Missing closing quote
```
**Error**: Invalid YAML syntax at line 2

### 2. Required Fields
```yaml
flow: {}  # Missing 'name'
state: {}
nodes: []
edges: []
```
**Error**: `flow.name` is required

### 3. Type Validity
```yaml
state:
  fields:
    score:
      type: invalid_type  # ← Not a valid type
```
**Error**: Invalid type 'invalid_type'. Supported: str, int, float, bool, list, dict, list[str], ...

### 4. Node ID Uniqueness
```yaml
nodes:
  - id: research
  - id: research  # ← Duplicate
```
**Error**: Duplicate node ID 'research'

### 5. Edge References
```yaml
edges:
  - from: START
    to: research
  - from: research
    to: nonexistent  # ← Node doesn't exist
```
**Error**: Edge references unknown node 'nonexistent'

### 6. State Field References
```yaml
nodes:
  - id: research
    prompt: "{state.nonexistent_field}"  # ← Field doesn't exist
```
**Error**: Prompt references unknown state field 'nonexistent_field'. Available: topic, research

### 7. Output/Schema Consistency
```yaml
nodes:
  - id: research
    outputs: [summary]
    output_schema:
      fields:
        - name: result  # ← Mismatch
```
**Error**: Node 'research' declares output 'summary' but schema only defines: result

### 8. Graph Structure
```yaml
edges:
  - from: START
    to: research
  - from: research
    to: write
  # Missing edge to END
```
**Error**: No edge to END. All workflows must end at END.

### 9. Circular Dependencies (v0.1: Linear Only)
```yaml
edges:
  - from: A
    to: B
  - from: B
    to: A  # ← Cycle
```
**Error**: Circular dependency detected: A → B → A

### 10. Tool Availability
```yaml
nodes:
  - id: research
    tools: [nonexistent_tool]  # ← Tool doesn't exist
```
**Error**: Unknown tool 'nonexistent_tool'. Available: serper_search

### 11. Required Inputs
```yaml
state:
  fields:
    topic: {type: str, required: true}
```

```python
# User runs without required input
run_workflow(config, inputs={})  # ← Missing 'topic'
```
**Error**: Required field 'topic' not provided in inputs

---

## Rationale

### 1. Fail Fast, Save Money

**Cost comparison**:

| Validation Time | Cost of Error Discovery |
|----------------|------------------------|
| Parse time | $0.00 (instant) |
| Build time | $0.00 (seconds) |
| Runtime (step 1) | $0.01-$0.10 (wasted LLM call) |
| Runtime (step 5) | $0.10-$1.00 (5 wasted LLM calls) |

**With multi-step workflows**:
```
Without parse-time validation:
  Step 1: ✓ $0.02
  Step 2: ✓ $0.05
  Step 3: ✓ $0.10
  Step 4: ✓ $0.15
  Step 5: ✗ Error (config bug)
  Total wasted: $0.32

With parse-time validation:
  Validation: ✗ Error (config bug)
  Total wasted: $0.00
```

### 2. Better Developer Experience

**Immediate feedback**:
```
$ python -m configurable_agents run workflow.yaml

Error: node 'research' outputs to 'summary' but state has no such field
  in workflow.yaml:12

Did you mean 'research'?
```

**No waiting for LLM calls to discover config bugs.**

### 3. Local Testing

**Users can validate configs without API keys**:
```bash
# Validate structure without running
$ python -m configurable_agents validate workflow.yaml

✓ Config is valid
  - 3 nodes
  - 4 edges
  - 5 state fields
  - Uses tools: serper_search
```

**No LLM costs for config development.**

### 4. CI/CD Integration

**In CI pipeline**:
```yaml
# .github/workflows/validate.yml
- name: Validate workflow configs
  run: |
    for config in workflows/*.yaml; do
      python -m configurable_agents validate $config
    done
```

**Catch config errors before deployment.**

### 5. Prevents Runtime Surprises

**Config validation guarantees**:
- All referenced nodes exist
- All state fields are defined
- All tools are available
- Graph structure is valid
- Types are correct

**Runtime can focus on**:
- LLM errors (timeout, rate limit)
- Tool errors (API failure)
- Unexpected output formats

**No need to handle config errors at runtime.**

---

## Alternatives Considered

### Alternative 1: Lazy Validation (Runtime Only)

**Approach**: Validate as you encounter errors during execution.

**Pros**:
- Simpler validator (less upfront work)
- Faster config load time

**Cons**:
- **Wasted LLM costs** (dealbreaker)
- Poor developer experience (slow feedback)
- Hard to debug (errors are far from root cause)

**Example**:
```python
# User gets error at step 5
# Has to trace back to find config bug
# Already spent money on steps 1-4
```

**Why rejected**: Wastes money and time.

### Alternative 2: Build-Time Validation

**Approach**: Validate when constructing LangGraph.

**Pros**:
- Still catches errors before LLM calls
- Some checks can't be done without graph context

**Cons**:
- Slower than parse-time (need to build graph)
- Couples validation to graph builder
- Can't validate without building

**Why rejected**: Parse-time catches 95% of errors. Build-time can handle the 5%.

### Alternative 3: Two-Phase Validation

**Approach**: Basic checks at parse-time, advanced checks at build-time.

**Example**:
```python
# Parse time: Syntax, required fields, basic structure
validate_config_basic(config)

# Build time: Graph validity, circular dependencies
graph = build_graph(config)  # Validates during build
```

**Pros**:
- Balanced approach
- Some checks genuinely need graph context

**Cons**:
- More complex (two validation layers)
- Users don't know which errors are caught when

**Why rejected (for v0.1)**:
- v0.1 is linear flows only (no complex graph validation needed)
- Can add build-time validation in v0.2 if needed

### Alternative 4: Type-Checked Configs (Static Analysis)

**Approach**: Use JSON Schema or similar to validate configs.

**Example**:
```bash
# Validate against schema
jsonschema -i workflow.yaml workflow-schema.json
```

**Pros**:
- Standard tooling
- IDE integration (autocomplete)
- Can validate in editor

**Cons**:
- JSON Schema can't express all our rules (e.g., "outputs match output_schema")
- Still need custom validation for semantics
- Extra step (users must run jsonschema)

**Why rejected**: Can add as enhancement (IDE integration), but not a replacement for parse-time validation.

---

## Consequences

### Positive Consequences

1. **Zero Wasted LLM Costs**
   - Config errors caught before execution
   - No partial workflow runs

2. **Fast Feedback Loop**
   - Edit config → validate → fix → repeat
   - No waiting for LLM calls

3. **Better Error Messages**
   - Errors include line numbers, context
   - Can suggest fixes ("Did you mean...?")

4. **Confidence**
   - If validation passes, config will run
   - No runtime surprises from config bugs

5. **Offline Development**
   - Validate configs without API keys
   - Develop workflows without internet

6. **CI/CD Friendly**
   - Validate all configs in repo
   - Catch errors before merge

### Negative Consequences

1. **Slower Config Load**
   - Validation adds ~100-500ms
   - **Mitigation**: Acceptable for 1-10 second LLM calls

2. **Complex Validator**
   - Need to check many rules
   - **Mitigation**: Comprehensive test suite (T-004)

3. **False Positives Possible**
   - Validator might be too strict
   - **Mitigation**: Allow escape hatches where needed

4. **Maintenance Burden**
   - As schema evolves, validator must too
   - **Mitigation**: Keep validator logic modular

### Risks

#### Risk 1: Validator Has Bugs

**Likelihood**: Medium (validation is complex)
**Impact**: High

**Scenarios**:
- **False negative**: Invalid config passes validation → runtime failure
- **False positive**: Valid config fails validation → user frustrated

**Mitigation**:
- Comprehensive test suite
- Test with real-world configs
- Collect edge cases and add to tests
- Clear error messages so users can override if needed

#### Risk 2: Can't Validate Everything at Parse Time

**Likelihood**: High (some checks need runtime info)
**Impact**: Low

**Example**:
```yaml
# Can we validate this prompt will work?
prompt: "Research {state.topic} and return JSON"
# We can check {state.topic} exists, but not if LLM will return JSON
```

**Mitigation**:
- Validate structure (syntax, references)
- Runtime handles LLM behavior (output format, errors)
- Document what's validated vs what's runtime

#### Risk 3: Validation is Too Slow

**Likelihood**: Low
**Impact**: Medium

**Mitigation**:
- Optimize hot paths
- Cache validation results (if config unchanged)
- Profile and benchmark

---

## Implementation Strategy

### T-004: Config Validator

**Validation order** (fail fast on first error):

1. YAML syntax
2. Required top-level keys
3. Type validity
4. Node ID uniqueness
5. Edge references
6. State field references
7. Output/schema consistency
8. Graph structure (reachability, cycles)
9. Tool availability

**Error reporting**:
```python
class ValidationError(Exception):
    def __init__(self, message: str, line: int = None, suggestion: str = None):
        self.message = message
        self.line = line
        self.suggestion = suggestion

# Usage
raise ValidationError(
    message="Unknown node 'researc' referenced in edge",
    line=15,
    suggestion="Did you mean 'research'?"
)
```

**Output**:
```
Error in workflow.yaml:15
  Unknown node 'researc' referenced in edge

  14: edges:
  15:   - from: researc
           ^^^^^^^^
  16:     to: write

  Did you mean 'research'?
```

---

## Testing Strategy

### Unit Tests
- Test each validation rule independently
- Test error message quality
- Test suggestion logic ("Did you mean...?")

### Integration Tests
- Test with complete valid configs (should pass)
- Test with invalid configs (should fail with helpful errors)
- Test edge cases (empty configs, minimal configs, large configs)

### Adversarial Testing
- Malformed YAML
- Circular references
- Missing required fields
- Type mismatches
- Deep nesting

---

## Error Message Philosophy

**Bad error message**:
```
Error: Invalid config
```

**Good error message**:
```
Error in workflow.yaml:12
  Node 'research' outputs to 'summary' but state schema has no such field

  State schema defines:
    - topic (str, required)
    - research (str)
    - article (str)

  Did you mean 'research'?

  To fix:
    Change line 12 from:
      outputs: [summary]
    to:
      outputs: [research]
```

**Principles**:
1. **Location**: File name + line number
2. **Context**: Show surrounding lines
3. **Explanation**: Why it's an error
4. **Suggestion**: How to fix
5. **Examples**: Show correct syntax if helpful

---

## Future Enhancements

### v0.2: Warnings (Non-Fatal)

```
Warning: Node 'research' has no description
  Consider adding a description for documentation

Warning: Tool 'serper_search' requires SERPER_API_KEY environment variable
  This will fail at runtime if not set
```

### v0.3: Linter Mode

```bash
# Check for style issues, best practices
python -m configurable_agents lint workflow.yaml

Issues:
  - Prompt in node 'research' is very long (>500 chars). Consider splitting.
  - Node 'write' uses high temperature (0.9). Is this intentional?
  - State field 'unused_field' is never read or written.
```

### v0.4: Fix Suggestions

```bash
# Auto-fix common issues
python -m configurable_agents fix workflow.yaml

Fixed:
  - Renamed output 'summary' to 'research' (matched state schema)
  - Removed unused state field 'old_field'
  - Sorted edges by execution order
```

---

## References

- Fail-fast principle: https://en.wikipedia.org/wiki/Fail-fast
- Error message design: https://elm-lang.org/news/compiler-errors-for-humans

---

## Notes

Parse-time validation is a **quality-of-life feature** that becomes a **cost-saving feature** at scale.

For one workflow: Saves a few cents and seconds.
For 100 workflows/day: Saves dollars and hours.

**Key principle**: Catch errors as early as possible in the development cycle.

```
Parse time < Build time < Runtime
   ($0)        ($0)        ($$$)
```

---

## Superseded By

None (current)
