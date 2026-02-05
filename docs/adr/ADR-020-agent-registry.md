# ADR-020: Agent Registry Architecture

**Status**: Accepted
**Date**: 2026-02-04
**Deciders**: thatAverageGuy, Claude Code

---

## Context

The system needs a way to track and manage multiple agent containers dynamically. As users deploy workflows as agents, the orchestrator needs to:

1. Discover available agents
2. Track agent health and availability
3. Enable agent lifecycle management (registration, heartbeat, deregistration)
4. Provide query interfaces for dashboard and CLI tools

### Requirements

- **ARCH-01**: Agent containers are minimal (~50-100MB) with MLFlow UI decoupled
- **ARCH-02**: Agents support bidirectional registration (agent-initiated and orchestrator-initiated)
- **ARCH-03**: Agent registry tracks active agents with heartbeat and TTL-based expiration

### Constraints

- Registry must be lightweight (don't add heavy dependencies like etcd/Consul)
- Must support dynamic agent addition/removal
- Must handle network partitions gracefully (agents restart, registry restart)
- Must support local development (no external services required)

---

## Decision

**Use SQLAlchemy 2.0 with Repository Pattern for storage, heartbeat/TTL pattern for lifecycle management, and FastAPI for registry server.**

---

## Rationale

### Why SQLAlchemy 2.0?

1. **Type Safety**: DeclarativeBase with Mapped/mapped_column provides compile-time validation
2. **Pluggable Backend**: SQLite for local dev, PostgreSQL for production (same API)
3. **Mature**: Well-documented, battle-tested, excellent Python integration
4. **Async Support**: Can add async engine later if needed (for high scale)
5. **Migration Path**: Easy to migrate to PostgreSQL/Redis later

### Why Repository Pattern?

1. **Abstraction**: Swappable storage backends without changing business logic
2. **Testing**: Easy to mock repositories for unit tests
3. **Transaction Management**: Clear boundaries for database operations
4. **Separation of Concerns**: Business logic separate from data access

### Why Heartbeat/TTL Pattern?

1. **Self-Healing**: Stale agents automatically expire without explicit deregistration
2. **Simplicity**: Agents only need to send periodic heartbeat requests
3. **Robustness**: Handles agent crashes (heartbeat stops, TTL expires)
4. **No Coordination**: No distributed consensus required

### Why FastAPI?

1. **Async**: Built-in async support for concurrent heartbeat requests
2. **Type Safety**: Automatic Pydantic validation for request/response
3. **OpenAPI**: Auto-generated API docs
4. **Lightweight**: Minimal overhead, perfect for registry service

---

## Implementation

### Data Model

```python
from sqlalchemy import Mapped, mapped_column
from datetime import datetime

class AgentRecord(Base):
    """Agent registry record"""
    __tablename__ = "agent_registry"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(255))
    agent_version: Mapped[str] = mapped_column(String(50))
    capabilities: Mapped[JSON] = mapped_column(JSON)  # List[str]
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="active")

    # Heartbeat/TTL
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ttl_seconds: Mapped[int] = mapped_column(Integer, default=60)

    # Metadata
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    agent_metadata: Mapped[JSON] = mapped_column(JSON)  # Dict[str, Any]
```

### Repository Pattern

```python
class AgentRegistryRepository(ABC):
    """Abstract repository for agent registry operations"""

    @abstractmethod
    def register_agent(self, agent: AgentRecord) -> int: ...

    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[AgentRecord]: ...

    @abstractmethod
    def heartbeat(self, agent_id: str) -> bool: ...

    @abstractmethod
    def expire_stale_agents(self) -> int: ...  # Cleanup

    @abstractmethod
    def list_active_agents(self) -> List[AgentRecord]: ...

class SQLAgentRegistryRepository(AgentRegistryRepository):
    """SQLAlchemy implementation"""

    def __init__(self, session_factory):
        self.session_factory = session_factory
```

### Registry Server (FastAPI)

```python
@app.post("/api/v1/agents/register")
async def register_agent(agent: AgentRegistration):
    """Register or update agent"""
    with Session(session_factory) as session:
        record = AgentRecord(**agent.dict())
        session.add(record)
        session.commit()
        return {"status": "registered", "agent_id": agent.agent_id}

@app.post("/api/v1/agents/{agent_id}/heartbeat")
async def send_heartbeat(agent_id: str):
    """Update agent heartbeat"""
    with Session(session_factory) as session:
        agent = session.get(AgentRecord, agent_id)
        if agent:
            agent.last_heartbeat = datetime.utcnow()
            session.commit()
            return {"status": "ok"}
        return {"status": "not_found"}

@app.get("/api/v1/agents")
async def list_agents():
    """List all active agents"""
    with Session(session_factory) as session:
        agents = session.query(AgentRecord).filter(
            AgentRecord.last_heartbeat > datetime.utcnow() - timedelta(seconds=60)
        ).all()
        return {"agents": [agent.dict() for agent in agents]}
```

### Background Cleanup

```python
async def cleanup_stale_agents():
    """Background task to expire stale agents"""
    while True:
        with Session(session_factory) as session:
            cutoff = datetime.utcnow() - timedelta(seconds=60)
            expired = session.query(AgentRecord).filter(
                AgentRecord.last_heartbeat < cutoff
            ).all()
            for agent in expired:
                session.delete(agent)
            session.commit()
        await asyncio.sleep(60)  # Run every 60 seconds
```

### Agent Client (Heartbeat Loop)

```python
class AgentRegistryClient:
    """Client for agent self-registration and heartbeat"""

    async def register_and_heartbeat(self, agent_config: AgentConfig):
        """Register agent and start heartbeat loop"""
        # Initial registration
        await self._register(agent_config)

        # Heartbeat loop
        while True:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(20)  # 20s interval (~1/3 of TTL)
            except CancelledError:
                break  # Shutdown
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
                await asyncio.sleep(5)  # Retry delay
```

---

## Configuration

### Agent Config

```yaml
config:
  agent:
    id: "research_agent"
    name: "Research Agent"
    version: "1.0.0"
    capabilities:
      - "web_search"
      - "summarization"
    registry_url: "http://localhost:8001"
    heartbeat_interval: 20  # Seconds between heartbeats
    ttl: 60  # Time-to-live in seconds
```

### Environment Variables

- `AGENT_HOST`: Agent host address (default: auto-detect)
- `AGENT_PORT`: Agent port (default: auto-detect)
- `REGISTRY_URL`: Registry server URL (default: http://localhost:8001)

---

## Lifecycle Management

### Registration Flow

```
Agent Startup
    ↓
Generate Agent ID (or use config)
    ↓
POST /api/v1/agents/register
    ↓
Store in database with registered_at timestamp
    ↓
Start heartbeat loop (20s interval)
```

### Heartbeat Flow

```
Every 20 seconds:
    ↓
POST /api/v1/agents/{agent_id}/heartbeat
    ↓
Update last_heartbeat timestamp
    ↓
Return {"status": "ok"}
```

### Expiration Flow

```
Every 60 seconds (registry background task):
    ↓
Query agents where (now - last_heartbeat) > ttl
    ↓
Delete stale agents
    ↓
Log expirations
```

---

## Alternatives Considered

### Alternative 1: etcd or Consul

**Pros**:
- Built-in service discovery
- Distributed consensus
- Production-grade

**Cons**:
- Heavy dependencies (etcd requires 3-5 node cluster)
- Overkill for local development
- Complex setup
- Adds operational complexity

**Why rejected**: Violates local-first principle. Too heavy for v1.0.

### Alternative 2: In-Memory Registry

**Pros**:
- Zero dependencies
- Fast
- Simple

**Cons**:
- Not persistent (registry restart loses all agents)
- No horizontal scaling
- Single point of failure

**Why rejected**: Doesn't survive registry restart. No durability.

### Alternative 3: Redis

**Pros**:
- Fast key-value store
- Built-in TTL (EXPIRE command)
- Pub/sub for events

**Cons**:
- External dependency (requires Redis server)
- More complex than SQLite for local dev
- Overkill for <100 agents

**Why rejected**: Adds operational complexity. SQLite is sufficient for v1.0.

---

## Consequences

### Positive Consequences

1. **Self-Healing**: Stale agents auto-expire without manual intervention
2. **Simple Deployment**: No external services required (SQLite file)
3. **Production-Ready**: Can upgrade to PostgreSQL without code changes
4. **Testable**: Repository pattern enables easy mocking
5. **Observable**: All agents tracked in queryable database

### Negative Consequences

1. **Polling**: Registry queries database every 60s (cleanup loop)
2. **No Push Notifications**: Agents don't know when registry expires them
3. **Single Point of Failure**: Registry server crash stops heartbeat processing ( mitigated by fast restart)

### Risks

#### Risk 1: Heartbeat Storm (Many Agents)

**Likelihood**: Medium (at scale, >100 agents)
**Impact**: Low
**Mitigation**: Cleanup runs every 60s, heartbeat every 20s. Can optimize with batch updates if needed.

#### Risk 2: Network Partitions

**Likelihood**: Low (local deployment)
**Impact**: Medium
**Mitigation**: Agents retry heartbeat with backoff. Registry auto-expires stale agents.

#### Risk 3: Clock Skew

**Likelihood**: Low (single machine or same datacenter)
**Impact**: Low
**Mitigation**: Use UTC timestamps everywhere. TTL is generous (60s vs 20s heartbeat).

---

## Deferred Features

### ~~ARCH-02: Orchestrator-Initiated Registration~~ ✅ COMPLETE

**Status**: ~~Deferred to post-v1.0~~ **Completed 2026-02-06**

**Previous Reason**: Agent-initiated registration is sufficient for v1.0. Orchestrator-initiated requires agent discovery mechanism (port scanning, mDNS, or explicit configuration). Can add later without breaking changes.

**Implementation**: Manual registration via dashboard UI (no auto-discovery, as designed). Orchestrator is embedded in dashboard (not separate service).

**Files**:
- `src/configurable_agents/ui/dashboard/routes/orchestrator.py` - Complete rewrite (467 lines)
- `src/configurable_agents/ui/dashboard/templates/orchestrator.html` - Complete rewrite (489 lines)
- `src/configurable_agents/ui/dashboard/app.py` - Orchestrator initialization
- Test agent: `test_agent.py` (237 lines)

**Testing**: 14/14 integration tests passing

**Impact**: Low - agents can self-register on startup, no manual discovery needed.

---

## Related Decisions

- [ADR-012](ADR-012-docker-deployment-architecture.md): Docker deployment for agents
- [ADR-021](ADR-021-htmx-dashboard.md): Dashboard displays registered agents

---

## Implementation Status

**Status**: ✅ Complete (v1.0 + ARCH-02 completed 2026-02-06)

**Files**:
- `src/configurable_agents/registry/models.py` - AgentRecord ORM
- `src/configurable_agents/registry/repository.py` - Repository pattern implementation
- `src/configurable_agents/registry/server.py` - FastAPI registry server
- `src/configurable_agents/registry/client.py` - Agent client with heartbeat loop
- `src/configurable_agents/ui/dashboard/routes/orchestrator.py` - Orchestrator routes (467 lines)
- `src/configurable_agents/ui/dashboard/templates/orchestrator.html` - Orchestrator UI (489 lines)

**Testing**: 22 tests for registry + 14 integration tests for orchestrator

**ARCH-02 (Orchestrator-Initiated Registration)**: Complete
- Manual agent registration via dashboard UI
- Live health monitoring (HTMX polling every 10s)
- Execute workflows on remote agents
- Execution history integration
- Orchestrator embedded in dashboard (not separate service)

---

## Superseded By

None (current)
