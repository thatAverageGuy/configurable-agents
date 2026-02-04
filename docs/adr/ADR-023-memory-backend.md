# ADR-023: Memory Backend Design

**Status**: Accepted
**Date**: 2026-02-04
**Deciders**: thatAverageGuy, Claude Code

---

## Context

The system needs persistent, long-term memory storage for agents. State is transient (cleared after each workflow execution), but memory should persist across executions.

### Requirements

- **RT-07**: User can configure persistent memory per node, agent, or workflow (context survives across executions)
- **ARCH-06**: Long-term memory has dedicated storage backend (per-agent context storage)

### Constraints

- Must support namespace isolation (agent/workflow/node level)
- Must support wildcard queries (get all memory for agent)
- Must work with existing storage abstraction (SQLite/PostgreSQL)
- Must be simple API (dict-like read, explicit write)

---

## Decision

**Use SQLAlchemy ORM with namespace pattern `{agent_id}:{workflow_id}:{node_id}:{key}`. Dict-like read API with explicit write for clarity.**

---

## Rationale

### Why Namespace Pattern?

1. **Hierarchical**: Natural scoping (agent → workflow → node → key)
2. **Flexible**: Wildcards enable broad queries (`*:*:*:key`)
3. **Queryable**: SQL LIKE queries for namespace matching
4. **Clear**: Explicit hierarchy in keys

### Why Dict-Like Read + Explicit Write?

1. **Pythonic**: Familiar API (`memory['key']` to read)
2. **Explicit**: `memory.write('key', value)` makes persistence clear
3. **Asymmetric**: Read is convenient (dict), write is intentional (method)
4. **Prevents Accidents**: Can't accidentally persist with `memory['key'] = value`

### Why SQL ORM?

1. **Existing Infrastructure**: Already using SQLAlchemy for storage (ADR-020)
2. **Queryable**: Complex queries (wildcards, ranges)
3. **Transactional**: ACID guarantees for concurrent access
4. **Pluggable**: SQLite (local) → PostgreSQL (production)

---

## Implementation

### Data Model

```python
class MemoryEntry(Base):
    """Long-term memory entry"""
    __tablename__ = "memory"

    id: Mapped[int] = mapped_column(primary_key=True)
    namespace: Mapped[str] = mapped_column(String(500), index=True)
    key: Mapped[str] = mapped_column(String(255), index=True)
    value: Mapped[JSON] = mapped_column(JSON)  # Any JSON-serializable value

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=datetime.utcnow)

    # Composite unique constraint
    __table_args__ = (
        UniqueConstraint("namespace", "key", name="uq_namespace_key"),
    )
```

### Namespace Pattern

```python
NAMESPACE_PATTERN = "{agent_id}:{workflow_id}:{node_id}:{key}"

# Examples:
"research_agent:*:*:user_style"        # All workflows/nodes for agent
"research_agent:article_gen:*:topic"  # Any node in this workflow
"research_agent:article_gen:v2:cache"  # Specific node
"*:*:*:shared_config"                  # Global (all agents/workflows/nodes)
```

### Memory API

```python
class AgentMemory:
    """Long-term memory with dict-like read and explicit write"""

    def __init__(self, agent_id: str, workflow_id: str = "*", node_id: str = "*"):
        self.agent_id = agent_id
        self.workflow_id = workflow_id or "*"
        self.node_id = node_id or "*"
        self._namespace = f"{agent_id}:{self.workflow_id}:{self.node_id}"

    def __getitem__(self, key: str) -> Any:
        """Dict-like read: memory['key']"""
        return self._read(key, self._namespace)

    def read(self, key: str, namespace: str = None) -> Any:
        """Explicit read with optional namespace override"""
        ns = namespace or self._namespace
        entry = self.repository.get(ns, key)
        return entry.value if entry else None

    def write(self, key: str, value: Any, namespace: str = None) -> None:
        """Explicit write (persist to storage)"""
        ns = namespace or self._namespace
        self.repository.upsert(ns, key, value)

    def list_keys(self, namespace: str = None) -> List[str]:
        """List all keys in namespace"""
        ns = namespace or self._namespace
        return self.repository.list_keys(ns)
```

### Repository Operations

```python
class MemoryRepository(ABC):
    """Abstract repository for memory operations"""

    @abstractmethod
    def get(self, namespace: str, key: str) -> Optional[MemoryEntry]: ...

    @abstractmethod
    def upsert(self, namespace: str, key: str, value: Any) -> None: ...

    @abstractmethod
    def list_keys(self, namespace: str) -> List[str]: ...

    @abstractmethod
    def delete(self, namespace: str, key: str) -> bool: ...

class SQLMemoryRepository(MemoryRepository):
    """SQLAlchemy implementation"""

    def get(self, namespace: str, key: str) -> Optional[MemoryEntry]:
        with Session(self.session_factory) as session:
            return session.query(MemoryEntry).filter(
                MemoryEntry.namespace == namespace,
                MemoryEntry.key == key
            ).first()

    def upsert(self, namespace: str, key: str, value: Any) -> None:
        with Session(self.session_factory) as session:
            entry = session.query(MemoryEntry).filter(
                MemoryEntry.namespace == namespace,
                MemoryEntry.key == key
            ).first()

            if entry:
                entry.value = value
                entry.updated_at = datetime.utcnow()
            else:
                entry = MemoryEntry(namespace=namespace, key=key, value=value)
                session.add(entry)

            session.commit()
```

### Wildcard Queries

```python
def list_keys(self, namespace: str) -> List[str]:
    """List keys using SQL LIKE for wildcard matching"""
    with Session(self.session_factory) as session:
        # Convert "*" wildcard to SQL LIKE syntax
        pattern = namespace.replace("*", "%")
        results = session.query(MemoryEntry.key).filter(
            MemoryEntry.namespace.like(pattern)
        ).all()
        return [r.key for r in results]
```

---

## Configuration

### Node-Level Memory Config

```yaml
nodes:
  - id: personalization_node
    memory:
      read:
        - key: "user_style"
          namespace: "*:*:*:preferences"
      write:
        - key: "last_topic"
          value: "{state.topic}"
          namespace: "agent:*:*:history"
    prompt: |
      User prefers: {user_style}
      Last topic was: {last_topic}
```

### Global Memory Config

```yaml
config:
  memory:
    backend: "sqlite"  # or "postgresql"
    connection_string: "sqlite:///memory.db"
    default_namespace: "agent:*:*:default"
```

---

## Usage Examples

### Simple Read/Write

```python
memory = AgentMemory(agent_id="research_agent")

# Write (persist)
memory.write("user_preference", "formal")

# Read (dict-like)
style = memory["user_preference"]  # Returns "formal"
```

### Namespace Override

```python
memory = AgentMemory(agent_id="research_agent", workflow_id="article_gen")

# Write to specific namespace
memory.write("cache", data, namespace="research_agent:article_gen:v2:cache")

# Read from broad namespace
all_styles = memory.read("user_style", namespace="research_agent:*:*:preferences")
```

### Wildcard Queries

```python
memory = AgentMemory(agent_id="research_agent")

# List all keys for this agent (any workflow/node)
keys = memory.list_keys("research_agent:*:*:*")

# List all preferences across workflows
prefs = memory.list_keys("research_agent:*:*:user_*")
```

---

## Alternatives Considered

### Alternative 1: Redis

**Pros**:
- Fast key-value store
- Built-in TTL
- Pub/sub for events

**Cons**:
- External dependency (requires Redis server)
- Overkill for local development
- Another service to deploy

**Why rejected**: Violates local-first principle. SQLite is sufficient for v1.0.

### Alternative 2: Vector Database (RAG)

**Pros**:
- Semantic search
- Embedding-based retrieval

**Cons**:
- Heavy dependency (ChromaDB, Pinecone, etc.)
- Overkill for simple key-value storage
- Adds complexity

**Why deferred**: Can add in v1.1 for semantic memory. v1.0 needs simple KV store.

### Alternative 3: File System (JSON/YAML)

**Pros**:
- Simple (no database)
- Human-readable

**Cons**:
- Slow (file I/O)
- No transactions
- No concurrent access
- No querying (wildcards)

**Why rejected**: Doesn't scale. SQL provides better abstraction.

---

## Consequences

### Positive Consequences

1. **Persistent Context**: Agents learn across executions
2. **Flexible Scoping**: Namespace pattern supports hierarchical isolation
3. **Simple API**: Dict-like reads are familiar
4. **Queryable**: Wildcards enable broad queries
5. **Pluggable**: SQLite (local) → PostgreSQL (production)

### Negative Consequences

1. **Asymmetric API**: Dict read but not dict write (must use `write()`)
2. **Namespace Complexity**: Users must understand pattern syntax
3. **Storage Overhead**: Every write is a database transaction
4. **No TTL**: Entries don't auto-expire (can add later)

### Risks

#### Risk 1: Namespace Conflicts

**Likelihood**: Low (clear pattern)
**Impact**: Low
**Mitigation**: Unique constraint on (namespace, key). Agent IDs are unique.

#### Risk 2: Memory Bloat

**Likelihood**: Medium (no auto-expire)
**Impact**: Medium
**Mitigation**: Can add TTL or manual cleanup commands in v1.1.

#### Risk 3: Concurrent Access

**Likelihood**: Low (single agent per workflow)
**Impact**: Low
**Mitigation**: SQL transactions handle concurrent writes (last write wins).

---

## Related Decisions

- [ADR-020](ADR-020-agent-registry.md): Agent registry (uses same storage backend)
- Phase 1 (01-01-PLAN.md): Storage abstraction layer

---

## Implementation Status

**Status**: ✅ Complete (v1.0)

**Files**:
- `src/configurable_agents/memory/memory.py` - AgentMemory class
- `src/configurable_agents/memory/models.py` - MemoryEntry ORM
- `src/configurable_agents/memory/repository.py` - MemoryRepository implementation

**Features**:
- Namespace pattern with wildcard support
- Dict-like read API (`memory['key']`)
- Explicit write API (`memory.write('key', value)`)
- SQL repository with upsert
- Integration with node executor

**Testing**: 20 tests covering read/write, wildcards, and isolation

---

## Superseded By

None (current)
