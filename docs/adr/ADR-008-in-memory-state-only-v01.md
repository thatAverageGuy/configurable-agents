# ADR-008: In-Memory State Only (v0.1)

**Status**: Accepted
**Date**: 2026-01-24
**Deciders**: User, Claude Code

---

## Context

Workflows maintain state (data passed between nodes) during execution. State persistence strategies include:

### 1. In-Memory (Ephemeral)
```python
state = {"topic": "AI", "research": "", "article": ""}
# Exists only during execution
# Lost when process ends
```

### 2. File-Based Persistence
```python
# Save state to disk after each step
with open('state.json', 'w') as f:
    json.dump(state, f)
# Can resume if process crashes
```

### 3. Database Persistence
```python
# Save state to SQLite/Postgres
db.execute("INSERT INTO workflow_state ...")
# Queryable, shareable across processes
```

### 4. Distributed State (Redis, etc.)
```python
# Share state across multiple workers
redis.set(f"workflow:{id}:state", json.dumps(state))
# Enables distributed execution
```

---

## Decision

**v0.1 uses in-memory state only (ephemeral).**

State exists only during workflow execution and is lost when the process ends.

Persistence is deferred to v0.2+.

---

## What This Means

### Workflow Execution

```python
# Run workflow
result = run_workflow(config, inputs={"topic": "AI"})

# result = {"topic": "AI", "research": "...", "article": "..."}
# State is returned but not saved anywhere
```

**If process crashes mid-execution**:
- State is lost
- Workflow must be re-run from start
- LLM calls must be repeated (costs money)

**No resume capability**: Can't pick up where you left off.

---

## Rationale

### 1. Simplicity

**In-memory**:
```python
class State(BaseModel):
    topic: str
    research: str
    article: str

# Just instantiate
state = State(topic="AI", research="", article="")

# Update
state.research = "New value"
```

**Estimated effort**: Already done (part of core).

**With persistence**:
```python
class StatePersistence:
    def save(self, state: State, workflow_id: str):
        # Serialize state
        # Save to file/database
        # Handle errors

    def load(self, workflow_id: str) -> State:
        # Load from file/database
        # Deserialize
        # Handle missing/corrupt state

    def checkpoint(self, state: State, node_id: str):
        # Save intermediate state
        # Enable resume
```

**Additional complexity**:
- Serialization (Pydantic → JSON/bytes)
- Storage abstraction (files vs database)
- Resume logic (find last checkpoint, replay)
- State migrations (schema changes)

**Estimated effort**: 2-3 weeks.

**Tradeoff**: Ship v0.1 in 3 weeks, or v0.1 with persistence in 5-6 weeks.

### 2. Most v0.1 Workflows Are Short

**Typical v0.1 workflow**:
- 3-5 nodes
- 10-30 seconds total
- $0.01-$0.10 total cost

**If it crashes**:
- Re-run costs ~$0.05
- Re-run time ~20 seconds

**Not painful enough to need persistence.**

### 3. LangGraph Has Built-In Persistence

When we add persistence in v0.2, LangGraph provides it:

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# v0.1: No checkpointing
graph = build_graph(config)
result = graph.invoke(initial_state)

# v0.2: With checkpointing
checkpointer = SqliteSaver("checkpoints.db")
graph = build_graph(config).compile(checkpointer=checkpointer)
result = graph.invoke(initial_state, config={"thread_id": "workflow-123"})

# Resume after crash
result = graph.invoke(None, config={"thread_id": "workflow-123"})  # Picks up where it left off
```

**No architectural changes needed. Just add checkpointer.**

### 4. Persistence Needs Design Decisions

**Questions we can't answer yet**:
- Where to store state? (SQLite? Postgres? Files?)
- How long to keep state? (Forever? 30 days? Configurable?)
- How to handle schema migrations? (State schema changes)
- Should we version states?
- How to garbage collect old states?
- What about distributed execution? (Multiple workers)

**Better to defer these until we understand real usage patterns.**

### 5. YAGNI (You Aren't Gonna Need It)

**Persistence is only needed if**:
- Workflows are long-running (hours+)
- Failures are common (unreliable infrastructure)
- Resume is critical (expensive to re-run)

**v0.1 workflows likely don't meet these criteria.**

**If users request it → add in v0.2.**

---

## Alternatives Considered

### Alternative 1: File-Based Persistence

```python
# Save state to file after each node
def execute_node(node, state):
    result = node.run(state)
    state.update(result)

    # Save to disk
    with open(f'state_{workflow_id}.json', 'w') as f:
        json.dump(state.dict(), f)

    return state
```

**Pros**:
- Simple (just JSON files)
- Easy to inspect (cat state.json)
- No database needed

**Cons**:
- **File I/O overhead** (slower execution)
- **File cleanup** (when to delete?)
- **Concurrency issues** (multiple workflows → file conflicts)
- **Not production-grade** (files can be deleted, corrupt)

**Why rejected**: Not worth the complexity for v0.1.

### Alternative 2: SQLite Persistence

```python
# Use SQLite to store states
db = sqlite3.connect('workflow_states.db')
db.execute("""
    CREATE TABLE states (
        workflow_id TEXT,
        node_id TEXT,
        state JSON,
        timestamp DATETIME
    )
""")

def execute_node(node, state):
    result = node.run(state)
    state.update(result)

    # Save checkpoint
    db.execute(
        "INSERT INTO states VALUES (?, ?, ?, ?)",
        (workflow_id, node.id, json.dumps(state.dict()), datetime.now())
    )

    return state
```

**Pros**:
- Queryable (can inspect states)
- Atomic writes (safer than files)
- LangGraph supports this (SqliteSaver)

**Cons**:
- **Extra dependency** (SQLite, migrations)
- **Schema design** (how to structure tables?)
- **Cleanup logic** (garbage collection)
- **2-3 weeks extra development**

**Why rejected**: Overkill for v0.1. Add in v0.2 if needed.

### Alternative 3: Optional Persistence (Flag)

```yaml
config:
  persistence:
    enabled: true
    backend: sqlite
    path: checkpoints.db
```

**Pros**:
- Best of both worlds (users choose)
- Can start simple, opt-in later

**Cons**:
- **Two code paths** (in-memory vs persisted)
- **More testing** (test both modes)
- **Confusing for users** ("Should I enable this?")
- **Still need to implement persistence** (same effort)

**Why rejected**: Adds complexity without solving the core issue (persistence is still complex).

### Alternative 4: Memory + Logs (Replay)

**Approach**: Keep in-memory state, but log all inputs/outputs. If crash, replay logs.

```python
# Log every node execution
logger.info(f"Node {node_id} input: {state}")
logger.info(f"Node {node_id} output: {result}")

# On crash, replay from logs
def resume(workflow_id):
    logs = load_logs(workflow_id)
    state = initial_state
    for log in logs:
        state.update(log['output'])
    return state
```

**Pros**:
- No state storage needed
- Logs useful for debugging anyway

**Cons**:
- **Replay is slow** (re-execute all nodes)
- **Replay may not be deterministic** (LLM calls)
- **Complex to implement** (parse logs, reconstruct state)

**Why rejected**: Clever but fragile.

---

## Consequences

### Positive Consequences

1. **Simpler Implementation**
   - No persistence code
   - No state migrations
   - No garbage collection

2. **Faster Execution**
   - No file/DB writes
   - Lower latency per node

3. **Easier Testing**
   - No need to mock persistence layer
   - State is just Python objects

4. **Clear Scope**
   - v0.1 is intentionally limited
   - Users know it's not for long-running workflows

### Negative Consequences

1. **No Resume on Failure**
   - Crash → re-run from start
   - **Mitigation**: v0.1 workflows are short (~30s), re-run is cheap

2. **Can't Inspect State Mid-Execution**
   - State only available after workflow completes
   - **Mitigation**: Add logging for debugging

3. **Not Suitable for Long-Running Workflows**
   - Hours-long workflows risky without checkpoints
   - **Mitigation**: Document limitation, add persistence in v0.2

4. **Can't Resume Manually**
   - If step 5 fails, can't just fix and re-run step 5
   - **Mitigation**: v0.2 adds checkpointing

### Risks

#### Risk 1: Users Expect Persistence

**Likelihood**: Medium
**Impact**: Medium (user frustration)

**Mitigation**:
- Clearly document v0.1 limitation
- Explain why (simplicity, speed)
- Promise v0.2 persistence (with timeline)

**Documentation**:
```markdown
## State Management (v0.1)

**v0.1 uses in-memory state only.**

State is lost when workflow completes or crashes.
No resume capability.

**Use cases**:
- ✅ Short workflows (< 5 minutes)
- ✅ Cheap workflows (< $1)
- ✅ Development/testing
- ❌ Long-running production workflows
- ❌ Workflows that must resume on failure

**Coming in v0.2**: Persistent state with resume capability.
```

#### Risk 2: Workflow Failures Waste Money

**Scenario**: Workflow with 10 nodes, each $0.10. Node 9 fails. Re-run costs $1.00.

**Likelihood**: Low (v0.1 workflows are short)
**Impact**: Medium (user frustration + cost)

**Mitigation**:
- Encourage starting with small workflows
- Add validation to catch errors early (ADR-004)
- v0.2 adds checkpointing for expensive workflows

#### Risk 3: Hard to Debug

**Scenario**: Workflow crashes. No state saved. Can't see what went wrong.

**Likelihood**: Medium
**Impact**: Medium (poor DX)

**Mitigation**: Comprehensive logging

```python
# Log state before/after each node
logger.info(f"[{node_id}] Input state: {state.dict()}")
result = execute_node(node, state)
logger.info(f"[{node_id}] Output state: {state.dict()}")
logger.info(f"[{node_id}] Execution time: {elapsed}s")
```

**Users can inspect logs to see where it failed.**

---

## State Lifecycle (v0.1)

```python
# 1. Initialize state from config + inputs
state_schema = build_state_model(config['state'])
state = state_schema(**inputs)  # e.g., State(topic="AI")

# 2. Execute nodes, updating state
for node in nodes:
    result = execute_node(node, state)
    state = update_state(state, node.outputs, result)

# 3. Return final state
return state.dict()

# 4. State is garbage collected
# (Python deletes object when function returns)
```

**Total state lifetime**: Duration of `run_workflow()` function call.

---

## Logging Strategy (v0.1)

Since we don't persist state, logging is critical for debugging:

```python
import logging

logger = logging.getLogger('configurable_agents')

def execute_node(node_config, state):
    logger.info(f"Executing node: {node_config['id']}")
    logger.debug(f"Input state: {state.dict()}")

    try:
        result = call_llm(...)
        logger.debug(f"LLM output: {result}")

        state = update_state(state, node_config['outputs'], result)
        logger.debug(f"Updated state: {state.dict()}")

        return state

    except Exception as e:
        logger.error(f"Node failed: {e}", exc_info=True)
        logger.error(f"State at failure: {state.dict()}")
        raise
```

**Log levels**:
- `INFO`: Node execution, workflow start/end
- `DEBUG`: State snapshots, LLM calls
- `ERROR`: Failures with full context

**Example log output**:
```
INFO: Starting workflow: article_writer
INFO: Initial state: {'topic': 'AI'}
INFO: Executing node: research
DEBUG: Input state: {'topic': 'AI', 'research': ''}
DEBUG: LLM output: {'research': 'AI is...'}
DEBUG: Updated state: {'topic': 'AI', 'research': 'AI is...'}
INFO: Executing node: write
DEBUG: Input state: {'topic': 'AI', 'research': 'AI is...', 'article': ''}
DEBUG: LLM output: {'article': 'In recent years...'}
DEBUG: Updated state: {'topic': 'AI', 'research': 'AI is...', 'article': 'In recent years...'}
INFO: Workflow completed successfully
```

**Users can debug from logs without needing persisted state.**

---

## Migration Path to Persistence (v0.2)

### Step 1: Add Config Flag

```yaml
config:
  persistence:
    enabled: false  # Default to false (backwards compat)
```

### Step 2: Integrate LangGraph Checkpointing

```python
from langgraph.checkpoint.sqlite import SqliteSaver

def run_workflow(config, inputs):
    # Build graph
    graph = build_graph(config)

    # Add checkpointer if enabled
    if config.get('persistence', {}).get('enabled'):
        checkpointer = SqliteSaver("checkpoints.db")
        graph = graph.compile(checkpointer=checkpointer)
    else:
        graph = graph.compile()

    # Execute
    result = graph.invoke(inputs)
    return result
```

### Step 3: Add Resume API

```python
# Resume workflow from checkpoint
def resume_workflow(workflow_id: str):
    checkpointer = SqliteSaver("checkpoints.db")
    graph = build_graph(...).compile(checkpointer=checkpointer)

    # Resume from last checkpoint
    result = graph.invoke(None, config={"thread_id": workflow_id})
    return result
```

### Step 4: Cleanup API

```python
# Delete old checkpoints
def cleanup_checkpoints(older_than_days: int = 30):
    checkpointer = SqliteSaver("checkpoints.db")
    checkpointer.delete_old(older_than_days)
```

---

## Future: Advanced State Management (v0.3+)

### Long-Term Memory

```yaml
config:
  memory:
    type: vector_db
    provider: chroma
    collection: article_facts
```

**Use case**: Remember facts across workflow runs.

### Shared State (Multi-User)

```yaml
config:
  state:
    backend: redis
    ttl: 3600  # Expire after 1 hour
```

**Use case**: Multiple users accessing same workflow state.

### State Versioning

```yaml
config:
  versioning:
    enabled: true
    keep_history: 10  # Keep last 10 states
```

**Use case**: Time-travel debugging, rollback.

---

## Testing Strategy

### T-006: State Builder Tests

**Tests**:
- Create state from config
- Initialize with inputs
- Validate required fields
- Handle defaults
- Type validation

**No persistence tests** (nothing to persist).

### T-011: Node Executor Tests

**Tests**:
- Update state after node execution
- Validate output against schema
- State immutability (don't mutate original)

**No checkpoint tests** (no checkpoints in v0.1).

---

## Documentation

### README.md

```markdown
## State Management

**v0.1 uses in-memory state.**

State is:
- Created at workflow start
- Updated as nodes execute
- Returned at workflow end
- Lost after execution

**No persistence or resume capability.**

**Best for**:
- Short workflows (< 5 minutes)
- Development and testing
- Low-cost experimentation

**Not suitable for**:
- Long-running workflows (> 1 hour)
- Production systems requiring resume
- Workflows with expensive steps

**Persistence coming in v0.2.**
```

### Logging Guide

```markdown
## Debugging Workflows

Since v0.1 doesn't persist state, use logs to debug:

```bash
# Run with debug logging
LOG_LEVEL=DEBUG python -m configurable_agents run workflow.yaml

# Logs show state at each step:
DEBUG: Input state: {'topic': 'AI'}
DEBUG: Output: {'research': '...'}
DEBUG: Updated state: {'topic': 'AI', 'research': '...'}
```

**Logs include**:
- Input state per node
- LLM outputs
- Updated state
- Execution times
- Errors with full context
```

---

## References

- LangGraph checkpointing: https://langchain-ai.github.io/langgraph/how-tos/persistence/
- SQLite for state: https://docs.python.org/3/library/sqlite3.html

---

## Notes

**Philosophy**: Start simple, add complexity when needed.

In-memory state is the simplest possible implementation. It's sufficient for v0.1's short, cheap workflows.

When users need persistence (long workflows, expensive steps, production deployments), we'll add it in v0.2 with proper design.

**Key insight**: Premature persistence is premature optimization. Let real usage guide the design.

**Quote**: "Make it work, make it right, make it fast" - Kent Beck

v0.1: Make it work (in-memory)
v0.2: Make it right (persistence, resume)
v0.3: Make it fast (distributed, caching)

---

## Superseded By

None (current)
