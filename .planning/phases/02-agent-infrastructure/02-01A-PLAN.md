---
phase: 02-agent-infrastructure
plan: 01A
type: execute
wave: 1
depends_on: []
files_modified:
  - src/configurable_agents/storage/models.py
  - src/configurable_agents/storage/base.py
  - src/configurable_agents/storage/sqlite.py
  - src/configurable_agents/registry/__init__.py
  - src/configurable_agents/registry/models.py
  - src/configurable_agents/registry/server.py
autonomous: true

must_haves:
  truths:
    - "Registry server starts on specified port with SQLite backend"
    - "Registry exposes /agents/register endpoint for agent self-registration"
    - "Registry exposes POST /agents/{agent_id}/heartbeat endpoint for TTL refresh"
    - "Registry exposes GET /agents endpoint to list all registered agents"
    - "Registry exposes GET /health endpoint for health checks"
    - "Registry runs background cleanup task every 60 seconds to remove expired agents"
  artifacts:
    - path: "src/configurable_agents/storage/models.py"
      provides: "Agent registry ORM models"
      contains: "class AgentRecord"
      min_lines: 50
    - path: "src/configurable_agents/storage/base.py"
      provides: "Agent registry repository interface"
      contains: "class AgentRegistryRepository(abc.ABC)"
    - path: "src/configurable_agents/storage/sqlite.py"
      provides: "Agent registry repository implementation"
      contains: "class SqliteAgentRegistryRepository"
    - path: "src/configurable_agents/registry/server.py"
      provides: "Agent registry FastAPI server"
      exports: ["app", "AgentRegistryServer"]
      min_lines: 150
  key_links:
    - from: "src/configurable_agents/registry/server.py"
      to: "src/configurable_agents/storage/base.py"
      via: "AgentRegistryRepository interface"
      pattern: "class AgentRegistryRepository"
---

<objective>
Implement agent registry storage layer and FastAPI server.

**Purpose:** Create the central registry server that agents will register with. This includes the storage layer (ORM models and SQLite repository) and the FastAPI server with registration, heartbeat, listing, and health endpoints. This is the foundation of the agent registry system.

**Output:**
- AgentRecord ORM model with TTL-based expiration check
- AgentRegistryRepository abstract interface
- SqliteAgentRegistryRepository implementation with async access
- AgentRegistryServer FastAPI application
- Registration, heartbeat, listing, and health endpoints
- Background cleanup task for expired agents
</objective>

<execution_context>
@C:\Users\ghost\.claude\get-shit-done/workflows/execute-plan.md
@C:\Users\ghost\.claude\get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02-agent-infrastructure/02-RESEARCH.md

# Existing infrastructure from Phase 1
@src/configurable_agents/storage/models.py
@src/configurable_agents/storage/base.py
@src/configurable_agents/storage/sqlite.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create agent registry storage layer</name>
  <files>src/configurable_agents/storage/models.py, src/configurable_agents/storage/base.py, src/configurable_agents/storage/sqlite.py</files>
  <action>
Add agent registry models and repository:

1. **Extend storage/models.py**:
   - Add `AgentRecord` ORM model with fields:
     - agent_id (String(255), primary key)
     - agent_name (String(256))
     - host (String(256))
     - port (Integer)
     - last_heartbeat (DateTime, indexed)
     - ttl_seconds (Integer, default=60)
     - metadata (String(4000), JSON blob)
     - registered_at (DateTime)
   - Add `is_alive()` method that checks: `datetime.utcnow() < last_heartbeat + timedelta(seconds=ttl_seconds)`

2. **Extend storage/base.py**:
   - Add `AgentRegistryRepository(abc.ABC)` abstract interface with methods:
     - `add(agent: AgentRecord) -> None`
     - `get(agent_id: str) -> Optional[AgentRecord]`
     - `list_all(include_dead: bool = False) -> list[AgentRecord]`
     - `update_heartbeat(agent_id: str) -> None`
     - `delete(agent_id: str) -> None`
     - `delete_expired() -> int` (returns count deleted)

3. **Extend storage/sqlite.py**:
   - Implement `AgentRegistryRepository` using aiosqlite for async access
   - Use repository pattern from existing WorkflowRunRepository
   - For `update_heartbeat`: update `last_heartbeat = datetime.utcnow()`
   - For `delete_expired`: DELETE WHERE `datetime.utcnow() > last_heartbeat + ttl_seconds`
   - Create `agents` table in `initialize_db()`

Reference: Phase 1 storage patterns (WorkflowRunRepository), RESEARCH.md Pattern 2 (TTL heartbeat), Pattern 7 (SQLite schema).
  </action>
  <verify>
Run: `python -c "from configurable_agents.storage import create_storage_backend; repo, _ = create_storage_backend(); print('Agent registry repo:', type(repo).__name__)"`

Verify: Check that `AgentRecord` model exists with `is_alive()` method in models.py
  </verify>
  <done>
Agent registry ORM model created with TTL-based expiration check, repository interface defined, SQLite async implementation complete, agents table created on initialization.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create agent registry server (FastAPI)</name>
  <files>src/configurable_agents/registry/__init__.py, src/configurable_agents/registry/models.py, src/configurable_agents/registry/server.py</files>
  <action>
Create new registry module with FastAPI server:

1. **Create src/configurable_agents/registry/__init__.py**:
   - Export: AgentRegistryServer, AgentRegistryClient (stub), AgentRecord

2. **Create src/configurable_agents/registry/models.py**:
   - Re-export AgentRecord from storage.models for convenience
   - Add Pydantic request/response models:
     - `AgentRegistrationRequest(agent_id, agent_name, host, port, ttl_seconds, metadata)`
     - `AgentInfo(agent_id, agent_name, host, port, is_alive, last_heartbeat, registered_at)`

3. **Create src/configurable_agents/registry/server.py**:
   - `AgentRegistryServer` class with:
     - `__init__(self, registry_url: str, repo: AgentRegistryRepository)`
     - `create_app() -> FastAPI` - returns FastAPI application
   - FastAPI endpoints:
     - `POST /agents/register` - Agent self-registration (idempotent: update if exists)
     - `POST /agents/{agent_id}/heartbeat` - Refresh TTL
     - `GET /agents` - List all agents (filter dead via `include_dead` query param)
     - `GET /agents/{agent_id}` - Get specific agent info
     - `DELETE /agents/{agent_id}` - Manual deregistration
     - `GET /health` - Registry health check
   - Background cleanup task: Delete expired agents every 60 seconds
   - Use FastAPI's `@app.on_event("startup")` to start cleanup loop via `asyncio.create_task()`

**Note:** Orchestrator-initiated registration (pushing agent config from orchestrator to agent) is deferred to Phase 3. This plan implements agent-initiated registration only (agent pulls config on startup).

Reference: RESEARCH.md Pattern 3 (FastAPI health endpoints), Pattern 7 (registry endpoints code example).
  </action>
  <verify>
Run: `python -c "from configurable_agents.registry import AgentRegistryServer; print('Registry server imported successfully')"`

Run: `python -c "from fastapi.testclient import TestClient; from configurable_agents.registry import AgentRegistryServer; server = AgentRegistryServer('sqlite:///test.db'); app = server.create_app(); client = TestClient(app); print('Health:', client.get('/health').json())"`
  </verify>
  <done>
AgentRegistryServer created with FastAPI app, registration/heartbeat/list/deregister endpoints implemented, background cleanup task running, health endpoint functional. Orchestrator-initiated registration deferred to Phase 3.
  </done>
</task>

</tasks>

<verification>
After completing all tasks:

1. **Storage Verification**:
   - Import test: `from configurable_agents.storage import create_storage_backend`
   - Verify `AgentRecord` has `is_alive()` method
   - Verify `agents` table is created in SQLite database

2. **Server Verification**:
   - Import test: `from configurable_agents.registry import AgentRegistryServer`
   - Create server instance: `server = AgentRegistryServer('sqlite:///test.db')`
   - Create app: `app = server.create_app()`
   - Test health endpoint: `TestClient(app).get('/health').json()` returns 200

3. **Endpoint Verification**:
   - POST /agents/register creates new agent
   - POST /agents/{id}/heartbeat updates timestamp
   - GET /agents lists agents
   - Background cleanup task runs without errors
</verification>

<success_criteria>
**Plan Success Criteria Met:**
1. AgentRecord ORM model exists with TTL-based `is_alive()` method
2. AgentRegistryRepository interface is defined with all required methods
3. SqliteAgentRegistryRepository implements the interface correctly
4. AgentRegistryServer FastAPI application starts without errors
5. All endpoints (register, heartbeat, list, get, delete, health) are accessible
6. Background cleanup task removes expired agents every 60 seconds
</success_criteria>

<output>
After completion, create `.planning/phases/02-agent-infrastructure/02-01A-SUMMARY.md` with:
- Frontmatter (phase, plan, wave, status, completed_at, tech_added, patterns_established, key_files)
- Summary of changes (storage layer, registry server)
- Verification results (storage, server endpoints, background cleanup)
- Next steps link (02-01B: Registry Client + Generator Integration)
</output>
