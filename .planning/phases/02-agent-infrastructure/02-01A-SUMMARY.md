---
phase: 02-agent-infrastructure
plan: 01A
subsystem: registry
tags: [fastapi, sqlalchemy, ttl-heartbeat, agent-registry, sqlite]

# Dependency graph
requires:
  - phase: 01-core-engine
    provides: Storage abstraction layer with Repository Pattern and SQLAlchemy 2.0 ORM
provides:
  - AgentRecord ORM model with TTL-based expiration checking
  - AgentRegistryRepository abstract interface for agent storage
  - SqliteAgentRegistryRepository implementation with async access
  - AgentRegistryServer FastAPI application with REST endpoints
  - Background cleanup task for expired agents
affects:
  - 02-01B: Registry Client + Generator Integration (uses this registry server)
  - 02-02A: Agent spawning and coordination (agents register with this server)

# Tech tracking
tech-stack:
  added: [fastapi, pydantic]
  patterns: [TTL-heartbeat, background cleanup loop, REST API with idempotent registration]

key-files:
  created:
    - src/configurable_agents/storage/models.py (AgentRecord)
    - src/configurable_agents/storage/base.py (AgentRegistryRepository)
    - src/configurable_agents/storage/sqlite.py (SqliteAgentRegistryRepository)
    - src/configurable_agents/registry/__init__.py
    - src/configurable_agents/registry/models.py (Pydantic models)
    - src/configurable_agents/registry/server.py (AgentRegistryServer)
  modified:
    - src/configurable_agents/storage/factory.py (returns agent registry repo)
    - src/configurable_agents/storage/__init__.py (exports agent registry types)

key-decisions:
  - "Used agent_metadata instead of metadata to avoid SQLAlchemy reserved attribute conflict"
  - "Custom __init__ in AgentRecord for default TTL and heartbeat timestamps"
  - "Registration is idempotent - re-registering updates existing record"
  - "Background cleanup runs every 60 seconds via asyncio.create_task()"

patterns-established:
  - "Pattern: TTL heartbeat - agents refresh their TTL by calling heartbeat endpoint"
  - "Pattern: Idempotent registration - POST /agents/register updates if exists"
  - "Pattern: Session management for SQLAlchemy async operations in FastAPI"
  - "Pattern: Background task lifecycle with FastAPI startup/shutdown events"

# Metrics
duration: 18min
completed: 2026-02-03
---

# Phase 2 Plan 01A: Agent Registry Storage and Server Summary

**TTL-based agent registry with SQLite storage, FastAPI REST endpoints, and background cleanup for distributed agent coordination**

## Performance

- **Duration:** 18 min
- **Started:** 2026-02-03T08:26:26Z
- **Completed:** 2026-02-03T08:44:54Z
- **Tasks:** 2
- **Files modified:** 7 (4 created, 3 modified)

## Accomplishments

- Agent registry storage layer with AgentRecord ORM model featuring TTL-based `is_alive()` method
- AgentRegistryRepository abstract interface with CRUD operations for agent management
- SqliteAgentRegistryRepository implementation using SQLAlchemy 2.0 patterns
- AgentRegistryServer FastAPI application with 6 REST endpoints
- Background cleanup task that removes expired agents every 60 seconds

## Task Commits

Each task was committed atomically:

1. **Task 1: Create agent registry storage layer** - `c15bc7f` (feat)
2. **Task 2: Create agent registry server (FastAPI)** - `e72420a` (feat)

**Plan metadata:** (to be committed with STATE.md update)

## Files Created/Modified

### Created

- `src/configurable_agents/storage/models.py` - Extended with AgentRecord ORM model
- `src/configurable_agents/storage/base.py` - Extended with AgentRegistryRepository interface
- `src/configurable_agents/storage/sqlite.py` - Extended with SqliteAgentRegistryRepository
- `src/configurable_agents/registry/__init__.py` - Registry module exports
- `src/configurable_agents/registry/models.py` - Pydantic request/response models
- `src/configurable_agents/registry/server.py` - AgentRegistryServer FastAPI application

### Modified

- `src/configurable_agents/storage/factory.py` - Updated to return agent registry repository
- `src/configurable_agents/storage/__init__.py` - Updated to export agent registry types

## Decisions Made

1. **SQLAlchemy reserved attribute conflict**: Changed field name from `metadata` to `agent_metadata` to avoid conflict with SQLAlchemy's reserved `metadata` attribute on DeclarativeBase classes.

2. **Default value handling**: Implemented custom `__init__` method in AgentRecord to provide default values for `ttl_seconds`, `last_heartbeat`, and `registered_at` since SQLAlchemy 2.0's `mapped_column` defaults only apply to database operations, not Python object construction.

3. **Idempotent registration**: Registration endpoint updates existing records instead of failing, allowing agents to re-register without errors.

4. **Background cleanup interval**: Set to 60 seconds as a reasonable balance between prompt cleanup and resource usage.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed SQLAlchemy reserved attribute conflict**

- **Found during:** Task 1 (AgentRecord model creation)
- **Issue:** Field name `metadata` conflicts with SQLAlchemy's reserved `metadata` attribute on DeclarativeBase classes, causing `InvalidRequestError`
- **Fix:** Renamed field to `agent_metadata` throughout the codebase
- **Files modified:** src/configurable_agents/storage/models.py, src/configurable_agents/storage/sqlite.py, src/configurable_agents/registry/server.py
- **Verification:** Import test passes, agents table created successfully
- **Committed in:** `c15bc7f` (part of Task 1 commit)

**2. [Rule 2 - Missing Critical] Added default value handling for AgentRecord**

- **Found during:** Task 1 (verification testing)
- **Issue:** Creating AgentRecord without explicit `ttl_seconds` or `last_heartbeat` caused TypeError in `is_alive()` method due to None values
- **Fix:** Implemented custom `__init__` method with default values for `ttl_seconds` (60), `last_heartbeat` (datetime.utcnow()), and `registered_at` (datetime.utcnow())
- **Files modified:** src/configurable_agents/storage/models.py
- **Verification:** Agent creation works without all parameters, is_alive() returns correct result
- **Committed in:** `c15bc7f` (part of Task 1 commit)

**3. [Rule 1 - Bug] Fixed SQLAlchemy DetachedInstanceError in register_agent**

- **Found during:** Task 2 (server testing)
- **Issue:** After calling `repo.add()`, the AgentRecord becomes detached from the session, causing DetachedInstanceError when accessing attributes
- **Fix:** Use Session context manager directly for SQLite repo, refresh the record after commit, and re-fetch from repository
- **Files modified:** src/configurable_agents/registry/server.py
- **Verification:** Registration endpoint works, agent info returned correctly
- **Committed in:** `e72420a` (part of Task 2 commit)

**4. [Rule 1 - Bug] Fixed list_agents method signature**

- **Found during:** Task 2 (server testing)
- **Issue:** Method had `self` parameter shadowing issue due to incorrect Query decorator usage
- **Fix:** Added `self` as first parameter and moved Query decorator to correct position
- **Files modified:** src/configurable_agents/registry/server.py
- **Verification:** List agents endpoint works correctly
- **Committed in:** `e72420a` (part of Task 2 commit)

---

**Total deviations:** 4 auto-fixed (1 bug, 1 missing critical, 2 bugs)
**Impact on plan:** All auto-fixes necessary for correctness and functionality. No scope creep.

## Issues Encountered

- **httpx 0.28 / starlette 0.35 incompatibility**: The installed versions of httpx (0.28.1) and starlette (0.35.1) have a TestClient compatibility issue. Worked around by testing server methods directly via asyncio instead of using TestClient.

## User Setup Required

None - no external service configuration required.

## Verification Results

### Storage Verification

- Import test: PASSED - `from configurable_agents.storage import create_storage_backend`
- AgentRecord has is_alive(): PASSED
- agents table created in SQLite: PASSED

### Server Verification

- Import test: PASSED - `from configurable_agents.registry import AgentRegistryServer`
- Server instance creation: PASSED
- FastAPI app creation: PASSED
- 10 routes registered: PASSED

### Endpoint Verification

- POST /agents/register: PASSED - Creates/updates agent records
- POST /agents/{id}/heartbeat: PASSED - Updates timestamp
- GET /agents: PASSED - Lists agents with filtering
- GET /agents/{id}: PASSED - Returns agent info
- DELETE /agents/{id}: PASSED - Removes agent
- GET /health: PASSED - Returns status and counts
- Background cleanup: PASSED - Removes expired agents

## Next Phase Readiness

- Registry server is ready for agent registration
- Registry client implementation needed in 02-01B for agents to self-register
- Generator integration needed in 02-01B for workflow-aware agent spawning
- Agent spawning and coordination (02-02A) will use this registry server

---
*Phase: 02-agent-infrastructure*
*Completed: 2026-02-03*
