# ADR-001: Use LangGraph as Execution Engine

**Status**: Accepted
**Date**: 2026-01-24
**Deciders**: User, Claude Code

---

## Context

We need to choose an underlying framework to orchestrate agent workflow execution. The system must:

1. **Support DSPy optimization**: DSPy requires clean, unmanipulated access to prompts for optimization
2. **Handle state management**: Track state across multiple execution steps
3. **Enable control flow**: Support sequential execution (v0.1) and eventually conditionals/loops (v0.2+)
4. **Maintain transparency**: User should understand what's happening at each step
5. **Allow testing**: Must be able to mock/test execution without running actual LLMs
6. **Be production-grade**: Handle errors, retries, timeouts, observability

### The CrewAI Experience

Previous PoC used CrewAI, which hit a critical limitation:

**Problem**: CrewAI wraps user prompts with framework-specific augmentations:
```python
# User writes:
task_description = "Research {topic}"

# CrewAI actually sends:
actual_prompt = f"""
You are a {agent.role}.
Your goal is: {agent.goal}
Your backstory: {agent.backstory}

Tools available: {tools}

Current task:
{task_description}

[Additional CrewAI framework instructions...]
"""
```

**Impact on DSPy**:
- DSPy optimization requires control over the exact prompt sent to the LLM
- DSPy works by modifying prompts and few-shot examples to improve task performance
- With CrewAI's prompt wrapping, DSPy cannot optimize the actual prompt sent to the LLM
- Result: Optimization doesn't work, or works on wrong parts of the prompt

**Why This Matters**:
- One of our core features (Phase 3) is DSPy optimization
- Without DSPy, we're just another workflow orchestrator
- DSPy optimization is what makes configs "production-grade" without manual prompt engineering

---

## Decision

**Use LangGraph as the execution engine for v0.1 and beyond.**

---

## Rationale

### Why LangGraph?

#### 1. **No Prompt Manipulation**

LangGraph is fundamentally different from CrewAI:

```python
# LangGraph approach:
from langgraph.graph import StateGraph

def research_node(state: State) -> State:
    # YOU control the exact prompt
    prompt = f"Research the topic: {state.topic}"

    # YOU call the LLM however you want
    result = llm.invoke(prompt)  # Or use DSPy directly

    state.research = result
    return state

# LangGraph just orchestrates:
graph = StateGraph(State)
graph.add_node("research", research_node)
graph.add_edge("research", "write")
```

**Key point**: LangGraph calls your function. It doesn't wrap, inject, or modify anything. You have 100% control over what goes to the LLM.

#### 2. **DSPy Integration is Direct**

Because LangGraph doesn't manipulate prompts, DSPy modules can be used directly:

```python
import dspy

def research_node_with_dspy(state: State) -> State:
    # Define DSPy signature
    signature = dspy.Signature(
        "topic -> summary, sources",
        summary=str,
        sources=list[str]
    )

    # Use DSPy module directly
    module = dspy.ChainOfThought(signature)
    result = module(topic=state.topic)

    state.research = result.summary
    state.sources = result.sources
    return state

# LangGraph doesn't care - it just executes your function
graph.add_node("research", research_node_with_dspy)
```

**When we add DSPy optimization (v0.7+)**:
- DSPy can compile/optimize the modules
- Optimized prompts get used directly
- No framework interference

#### 3. **Explicit State Management**

LangGraph uses typed state objects:

```python
from typing import TypedDict

class State(TypedDict):
    topic: str
    research: str
    article: str
```

This aligns perfectly with our Pydantic state schemas. We can generate LangGraph-compatible state from config.

#### 4. **Simple Mental Model**

LangGraph is just a graph executor:
- Nodes = functions that transform state
- Edges = control flow between nodes
- Graph = sequence of transformations

This is transparent and debuggable. No hidden magic.

#### 5. **Well-Tested State Machine Logic**

LangGraph handles:
- Checkpointing (state snapshots)
- Error handling
- Conditional routing
- Parallel execution
- Human-in-the-loop

We can leverage these features as we grow (v0.2+) without rebuilding.

---

## Alternatives Considered

### Alternative 1: Build Custom State Machine

**Pros**:
- Zero dependencies
- Full control
- No surprises
- Exactly what we need, nothing more

**Cons**:
- 2-3 weeks extra development time
- Need to handle edge cases (cycles, error recovery, checkpointing)
- More code to test and maintain
- Delayed time to value

**Why rejected**:
- LangGraph is thin enough that it's not a liability
- Building our own is premature optimization
- We can always replace it later if needed

### Alternative 2: Continue with CrewAI

**Pros**:
- Already have working PoC
- High-level abstractions (agents, tasks, crews)
- Rich ecosystem

**Cons**:
- **Dealbreaker**: Incompatible with DSPy (prompt wrapping)
- Opinionated about agent structure
- Hard to understand what's actually sent to LLM
- Would need to maintain a fork to fix prompt issues

**Why rejected**:
- Fundamentally incompatible with DSPy optimization
- Too much hidden behavior

### Alternative 3: Use AutoGen

**Pros**:
- Mature multi-agent framework
- Good tooling

**Cons**:
- Similar prompt manipulation issues as CrewAI
- Complex abstractions (conversation patterns)
- Harder to integrate with DSPy

**Why rejected**:
- Same core problem as CrewAI

### Alternative 4: Raw LangChain (No Graph)

**Pros**:
- Direct LLM calls
- Simple

**Cons**:
- No state management
- No control flow abstractions
- Would need to build graph logic anyway

**Why rejected**:
- We'd end up rebuilding LangGraph

---

## Consequences

### Positive Consequences

1. **DSPy Integration Works**: Clean prompt access means DSPy optimization will work as designed

2. **Full Control**: We control exact prompts, LLM calls, and state updates

3. **Transparency**: Users can see exactly what's happening (no framework magic)

4. **Testability**: Easy to mock nodes and test graph execution

5. **Future-Proof**: LangGraph supports conditionals, loops, parallel execution (for v0.2+)

6. **Observability**: Can log/trace at node boundaries clearly

### Negative Consequences

1. **More Code**: We write more orchestration code than with high-level frameworks

2. **LangChain Dependency**: LangGraph depends on LangChain, which is a large dependency
   - **Mitigation**: We can vendor/fork if needed

3. **Learning Curve**: Team needs to understand LangGraph abstractions
   - **Mitigation**: LangGraph is simpler than alternatives

4. **Version Lock-in**: If LangGraph changes APIs, we need to migrate
   - **Mitigation**: LangGraph has stable API, backed by LangChain

### Risks

#### Risk 1: LangChain Chat Models Manipulate Prompts

**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Test in T-009 (LLM Provider) with direct API comparison
- If needed, bypass LangChain chat models and use raw API calls
- Document findings in ADR-009

#### Risk 2: Structured Outputs Incompatible with DSPy

**Likelihood**: Medium
**Impact**: High
**Mitigation**:
- Add T-019 (DSPy Integration Test) to validate compatibility
- Test structured outputs + DSPy optimization together
- Have fallback to raw outputs if needed

#### Risk 3: LangGraph Becomes Unmaintained

**Likelihood**: Very Low (backed by LangChain company)
**Impact**: Medium
**Mitigation**:
- LangGraph is open source, we can fork
- State machine logic is well-understood, can replace if needed
- Document escape strategy below

---

## Verification Steps

Before committing fully to LangGraph, we'll verify:

### T-009: LLM Provider Implementation
- [ ] Compare raw API call vs LangChain ChatModel
- [ ] Ensure prompts are identical
- [ ] Document any differences

### T-019: DSPy Integration Test (New Task)
- [ ] Create simple DSPy module
- [ ] Run in LangGraph node
- [ ] Verify optimization works
- [ ] Compare optimized vs non-optimized results

### T-020: Structured Output + DSPy Test (New Task)
- [ ] Combine Pydantic structured outputs with DSPy
- [ ] Ensure both work together
- [ ] Document any limitations

**Success Criteria**: If all three tests pass, LangGraph is confirmed as the right choice.

**Failure Path**: If tests fail, we revert to Alternative 1 (custom state machine) and document in ADR-001-SUPERSEDED.

---

## Escape Strategy

If LangGraph becomes problematic:

### Phase 1: Abstraction Layer (Immediate)
```python
# Abstract graph operations
class GraphExecutor(ABC):
    def add_node(self, name: str, func: Callable): ...
    def add_edge(self, from_node: str, to_node: str): ...
    def execute(self, initial_state: dict) -> dict: ...

class LangGraphExecutor(GraphExecutor):
    # LangGraph implementation

class CustomGraphExecutor(GraphExecutor):
    # Our own implementation if needed
```

### Phase 2: Replacement (If Needed)
- Implement `CustomGraphExecutor`
- Swap in config or at build time
- Maintain backwards compatibility

**Estimated effort**: 1-2 weeks to build custom executor if needed.

---

## References

- LangGraph docs: https://langchain-ai.github.io/langgraph/
- CrewAI prompt wrapping issue: Internal PoC findings
- DSPy optimization requirements: https://dspy-docs.vercel.app/

---

## Notes

This is a **critical decision** for the project. DSPy integration is a core differentiator. LangGraph's "just orchestration" philosophy aligns perfectly with our need for prompt control.

The key insight: **LangGraph orchestrates functions, CrewAI orchestrates agents.** Functions give us control; agents abstract it away.

---

## Superseded By

None (current)
