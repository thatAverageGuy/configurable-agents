# ADR-006: Linear Flows Only in v0.1

**Status**: Accepted
**Date**: 2026-01-24
**Deciders**: User, Claude Code

---

## Context

Agent workflows can have various execution patterns:

### 1. Linear (Sequential)
```
START → research → write → review → END
```

### 2. Conditional (Branching)
```
START → analyze →  [if sentiment > 0.5] → positive_response
                 ↓
                  [if sentiment ≤ 0.5] → negative_response
```

### 3. Loops (Iteration/Retry)
```
START → write → review → [if score < 7] → write (retry)
                       ↓
                        [if score ≥ 7] → END
```

### 4. Parallel (Concurrent Execution)
```
START → [research_academic, research_news, research_social] → synthesize → END
         (all three run in parallel)
```

### 5. Hierarchical (Sub-Workflows/Delegation)
```
START → manager_agent → [spawn worker_agents] → collect_results → END
```

---

## Decision

**v0.1 will support ONLY linear (sequential) flows.**

All other execution patterns are deferred to v0.2+.

---

## What This Means

### Allowed in v0.1

```yaml
edges:
  - from: START
    to: step1
  - from: step1
    to: step2
  - from: step2
    to: step3
  - from: step3
    to: END
```

**Execution**: START → step1 → step2 → step3 → END (always this order)

### NOT Allowed in v0.1

**Conditionals**:
```yaml
# NOT SUPPORTED
edges:
  - from: review
    condition: "{state.score} >= 7"
    to: END
  - from: review
    condition: "{state.score} < 7"
    to: write
```

**Loops**:
```yaml
# NOT SUPPORTED
edges:
  - from: write
    to: review
  - from: review
    to: write  # Cycle!
```

**Parallel execution**:
```yaml
# NOT SUPPORTED
edges:
  - from: START
    to: [research1, research2, research3]  # Parallel
  - from: [research1, research2, research3]
    to: synthesize  # Join
```

---

## Rationale

### 1. Simpler Implementation

**Linear flow complexity**:
- Graph validation: Check for cycles (simple topological sort)
- Execution: Just follow edges one by one
- Error handling: If node fails, stop execution
- Testing: Predictable execution order

**Estimated effort**: 2-3 weeks

**With conditionals + loops + parallel**:
- Graph validation: Complex (check for unreachable branches, infinite loops)
- Execution: Need conditional evaluation, loop detection, parallel coordination
- Error handling: Partial execution, rollback, retry logic
- Testing: Exponential test cases (every branch combination)

**Estimated effort**: 6-8 weeks

**Tradeoff**: Ship in 3 weeks vs 8 weeks.

### 2. Most Use Cases Are Linear

**Common workflows**:
1. **Data processing**: input → transform → validate → output
2. **Content generation**: research → outline → write → review
3. **Analysis**: collect → analyze → summarize → report
4. **Multi-step agents**: plan → execute → verify → report

**Estimate**: 60-70% of workflows are naturally sequential.

**Advanced patterns** (conditionals, loops) are needed for:
- Retry logic (if quality < threshold, retry)
- Dynamic routing (if type == X, go to flow Y)
- Parallel research (gather from multiple sources concurrently)

**These can wait for v0.2** after we validate core architecture.

### 3. Clear Scope

**v0.1 goal**: Validate config-driven architecture
- Can we generate graphs from YAML?
- Does state management work?
- Is validation helpful?
- Do users find configs intuitive?

**Linear flows are sufficient to answer these questions.**

Adding complexity (conditionals, loops) would:
- Delay feedback
- Add surface area for bugs
- Make testing harder

**Better approach**: Ship v0.1, learn, iterate.

### 4. Future-Proof Architecture

**LangGraph supports conditionals/loops/parallel out of the box.**

We're not painting ourselves into a corner. We're just not using these features yet.

**Adding them in v0.2 is straightforward**:

```python
# v0.1: Linear edges
graph.add_edge("research", "write")

# v0.2: Conditional edges
def should_retry(state):
    return state.score < 7

graph.add_conditional_edges(
    "review",
    should_retry,
    {
        True: "write",   # Retry
        False: END       # Done
    }
)
```

**No architectural changes needed. Just expose more of LangGraph's features.**

---

## Alternatives Considered

### Alternative 1: Support Conditionals in v0.1

**Config example**:
```yaml
edges:
  - from: review
    routes:
      - condition: "{state.score} >= 7"
        to: END
      - condition: "{state.score} < 7"
        to: write
```

**Pros**:
- More powerful from day one
- Covers more use cases

**Cons**:
- **Complex validation**: Must check all branches are reachable
- **Runtime complexity**: Need expression evaluator for conditions
- **Security risk**: Evaluating user expressions (injection attacks)
- **3-4 weeks extra development**

**Why rejected**: Too complex for v0.1. Add in v0.2 with proper design.

### Alternative 2: Support Loops in v0.1

**Config example**:
```yaml
edges:
  - from: write
    to: review
  - from: review
    to: write
    max_iterations: 3
```

**Pros**:
- Useful for retry logic
- Common pattern

**Cons**:
- **Infinite loop risk**: What if condition never met?
- **Complex validation**: Detect cycles, ensure termination
- **State management**: Need to track iteration count
- **2-3 weeks extra development**

**Why rejected**: Not critical for v0.1. Can work around with multiple nodes in v0.1.

**Workaround for v0.1** (retry logic without loops):
```yaml
# Explicit retry attempts
nodes:
  - id: write_attempt_1
  - id: review_1
  - id: write_attempt_2
  - id: review_2
  - id: write_attempt_3

edges:
  - {from: write_attempt_1, to: review_1}
  - {from: review_1, to: write_attempt_2}
  - {from: write_attempt_2, to: review_2}
  - {from: review_2, to: write_attempt_3}
```

Not elegant, but works for v0.1.

### Alternative 3: Support All Patterns (Full Feature Set)

**Rationale**: Build it right the first time.

**Pros**:
- No v0.2 needed for execution patterns
- Users get full power immediately

**Cons**:
- **8-10 weeks development** (vs 3 weeks for linear)
- **High complexity** (more bugs)
- **Harder to test** (combinatorial explosion)
- **Delayed user feedback** (can't validate assumptions)

**Why rejected**: Violates "start simple, add complexity" principle.

### Alternative 4: No Constraints (Let Users Define Anything)

**Approach**: Don't validate graph structure, just execute whatever user provides.

**Pros**:
- Maximum flexibility
- No validation needed

**Cons**:
- **Infinite loops crash system**
- **Unreachable nodes waste money**
- **Poor error messages** (fails at runtime)
- **Not production-grade**

**Why rejected**: Fails our "fail fast" principle (ADR-004).

---

## Consequences

### Positive Consequences

1. **Faster Development**
   - 3 weeks vs 8-10 weeks
   - Simpler codebase
   - Less testing surface

2. **Easier to Understand**
   - Users know execution order from config
   - No surprises (no hidden conditionals)
   - Predictable behavior

3. **Simpler Validation**
   - Just check for cycles
   - Ensure all nodes reachable
   - No complex condition analysis

4. **Clearer Scope**
   - v0.1 is intentionally limited
   - Sets user expectations
   - Focuses on core value proposition

5. **Learn Before Complexifying**
   - Get user feedback on basics
   - Understand actual needs for conditionals
   - Design v0.2 based on real use cases, not assumptions

### Negative Consequences

1. **Limited Use Cases**
   - Can't express retry logic elegantly
   - Can't do dynamic routing
   - Can't parallelize work

   **Mitigation**: Document workarounds for v0.1, promise v0.2 support.

2. **Some Users Frustrated**
   - "Why can't I add a simple if statement?"

   **Mitigation**: Clear roadmap showing v0.2 timeline, explain benefits of staged approach.

3. **Workarounds Are Ugly**
   - Retry logic requires duplicating nodes
   - Feels inefficient

   **Mitigation**: v0.2 comes quickly (4-6 weeks after v0.1).

### Risks

#### Risk 1: Users Abandon Due to Limitations

**Likelihood**: Low-Medium
**Impact**: Medium

**Mitigation**:
- Clearly document v0.1 limitations in README
- Show roadmap with v0.2 conditional/loop support
- Provide workarounds in docs
- Ship v0.2 quickly after v0.1 (8-12 weeks total)

#### Risk 2: Workarounds Create Bad Patterns

**Example**: Users might duplicate nodes instead of using loops
```yaml
# Bad pattern that users might adopt
nodes:
  - id: attempt_1
  - id: attempt_2
  - id: attempt_3
  # Copy-paste everywhere
```

**Mitigation**:
- Document as temporary workaround
- Provide migration guide to v0.2 syntax
- Auto-migrate configs when v0.2 released

#### Risk 3: Hard to Add Conditionals Later

**Likelihood**: Very Low
**Impact**: High (architectural rework)

**Why unlikely**: LangGraph already supports this
```python
# LangGraph already has conditional edges
graph.add_conditional_edges(source, condition_func, mapping)
```

We just need to:
1. Add condition syntax to config
2. Parse and evaluate conditions
3. Build conditional edges

**No architecture changes needed.**

---

## Implementation

### Graph Validation (v0.1)

```python
def validate_graph_structure(config):
    """Validate graph is linear (no cycles, no branches)"""

    # Build adjacency list
    edges = build_edge_map(config['edges'])

    # 1. Check for cycles
    if has_cycle(edges):
        raise ValidationError("Graph contains cycle. v0.1 supports linear flows only.")

    # 2. Check each node has at most one outgoing edge
    for node, destinations in edges.items():
        if len(destinations) > 1:
            raise ValidationError(
                f"Node '{node}' has {len(destinations)} outgoing edges. "
                "v0.1 supports linear flows only (one edge per node)."
            )

    # 3. Check reachability
    if not all_nodes_reachable(edges):
        raise ValidationError("Some nodes are unreachable from START")

    # 4. Check all paths lead to END
    if not all_paths_reach_end(edges):
        raise ValidationError("Some nodes have no path to END")
```

### Error Messages

```
Error in workflow.yaml:15
  Graph contains cycle: write → review → write

  v0.1 supports linear flows only.

  For retry logic, see: docs/workarounds/retry.md
  Or wait for v0.2 (with loop support): docs/../TASKS.md

  To fix temporarily, unroll the loop:
    write_attempt_1 → review_1 → write_attempt_2 → review_2 → END
```

---

## Migration Path to v0.2

### v0.2: Add Conditional Edges

**Config syntax**:
```yaml
edges:
  # Linear edge (v0.1 style)
  - from: research
    to: write

  # Conditional edge (v0.2 new)
  - from: review
    routes:
      - condition:
          type: expression
          logic: "{state.score} >= 7"
        to: END
      - condition:
          type: expression
          logic: "{state.score} < 7"
        to: write
```

**Implementation**:
```python
def build_edge(edge_config):
    if 'routes' in edge_config:
        # v0.2: Conditional edge
        return build_conditional_edge(edge_config)
    else:
        # v0.1: Linear edge
        return build_linear_edge(edge_config)
```

**Backwards compatible**: v0.1 configs still work.

### v0.3: Add Loop Constructs

**Config syntax**:
```yaml
edges:
  - from: review
    to: write
    loop:
      max_iterations: 3
      break_condition: "{state.score} >= 7"
```

**Or use conditionals** (already supported in v0.2):
```yaml
edges:
  - from: review
    routes:
      - condition: "{state.score} >= 7 or state.iteration >= 3"
        to: END
      - condition: "{state.score} < 7 and state.iteration < 3"
        to: write
```

### v0.4: Add Parallel Execution

**Config syntax**:
```yaml
edges:
  - from: START
    to_parallel: [research_academic, research_news, research_social]

  - from_parallel: [research_academic, research_news, research_social]
    to: synthesize
```

**Implementation**: LangGraph's `add_fanout` and `add_join`.

---

## Workarounds for v0.1

### Workaround 1: Retry Logic (Explicit Unrolling)

**Want**:
```yaml
# NOT SUPPORTED IN v0.1
edges:
  - from: write
    to: review
  - from: review
    to: write
    max_iterations: 3
```

**v0.1 workaround**:
```yaml
nodes:
  - id: write_1
    prompt: "Write article (attempt 1)"
  - id: review_1
    prompt: "Review article"
  - id: write_2
    prompt: "Write article (attempt 2)"
  - id: review_2
    prompt: "Review article"
  - id: write_3
    prompt: "Write article (attempt 3, final)"

edges:
  - {from: START, to: write_1}
  - {from: write_1, to: review_1}
  - {from: review_1, to: write_2}
  - {from: write_2, to: review_2}
  - {from: review_2, to: write_3}
  - {from: write_3, to: END}
```

**Note**: Ugly but functional. v0.2 will have proper loops.

### Workaround 2: Conditional Routing (Pre-Computed)

**Want**:
```yaml
# NOT SUPPORTED IN v0.1
edges:
  - from: classify
    routes:
      - condition: "{state.category} == 'technical'"
        to: technical_handler
      - condition: "{state.category} == 'general'"
        to: general_handler
```

**v0.1 workaround**: Use LLM to route
```yaml
nodes:
  - id: classify_and_handle
    prompt: |
      Topic: {state.topic}
      Category: {state.category}

      If technical: [detailed technical response]
      If general: [simple general response]

      Determine category and generate appropriate response.
```

**Note**: Less clean, but works. v0.2 will have proper routing.

---

## Documentation

### README.md

```markdown
## Execution Patterns

**v0.1 supports linear (sequential) workflows only.**

Example:
```yaml
edges:
  - {from: START, to: step1}
  - {from: step1, to: step2}
  - {from: step2, to: END}
```

**Not supported in v0.1:**
- Conditional branching (if/else)
- Loops (retry logic)
- Parallel execution

**Coming in v0.2+:**
See [../TASKS.md](../TASKS.md) for timeline.

**Workarounds:**
See [docs/workarounds/](docs/workarounds/) for v0.1 patterns.
```

### ../TASKS.md

```markdown
## Roadmap

### v0.1 (Current)
- ✅ Linear workflows
- ✅ State management
- ✅ Structured outputs
- ✅ Tool integration (single tool)

### v0.2 (4-6 weeks)
- 🔄 Conditional edges (if/else routing)
- 🔄 Loop constructs (retry logic)
- 🔄 Multiple LLM providers (OpenAI, Anthropic, Ollama)

### v0.3 (8-12 weeks)
- 🔄 Parallel execution
- 🔄 DSPy optimization
- 🔄 Config generator chatbot
```

---

## Testing Strategy

### Validation Tests
- ✅ Linear graphs pass validation
- ✅ Cyclic graphs fail validation
- ✅ Branching graphs fail validation
- ✅ Unreachable nodes fail validation

### Execution Tests
- ✅ Execute simple 2-node linear flow
- ✅ Execute complex 10-node linear flow
- ✅ State propagates correctly through steps

---

## References

- LangGraph conditional edges: https://langchain-ai.github.io/langgraph/how-tos/branching/
- LangGraph loops: https://langchain-ai.github.io/langgraph/how-tos/persistence/

---

## Notes

**Philosophy**: Simplicity first, complexity later.

Linear flows cover the majority of use cases and validate the core architecture. Conditionals and loops are valuable, but not critical for proving the concept.

**Quote**: "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away." - Antoine de Saint-Exupéry

v0.1 is the minimum viable product. v0.2+ adds back complexity where needed.

---

## Implementation Status

**Status**: 2705 Implemented in v0.1
**Related Tasks**: T-009 (LLM Provider), T-012 (Graph Builder), T-013 (Runtime Executor)
**Enforcement**: Feature gating (T-004.5) blocks unsupported features
**Date Implemented**: 2026-01-26 to 2026-01-27

This design constraint is enforced by:
1. Config validator - Rejects unsupported features at parse time
2. Feature gating - Hard blocks for v0.2+ features
3. Limited implementation - Only v0.1 features implemented

---

## Superseded By

None (current)
