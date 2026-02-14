# UI Redesign Analysis - Database & Naming Consolidation

**Status**: DRAFT - For Review Before Implementation
**Created**: 2026-02-13
**Related**: UI_ARCHITECTURE.md, ADR-020-agent-registry.md

---

## 1. Current State Analysis

### 1.1 Database Files (Current)

| DB File | Default Path | Used By | Tables |
|---------|--------------|---------|--------|
| `workflows.db` | `./workflows.db` | `run` command (via StorageConfig) | workflow_runs, execution_states, agents, chat_sessions, chat_messages, webhook_events, memory_records, workflow_registrations, orchestrators, session_state |
| `configurable_agents.db` | `./configurable_agents.db` | `ui`, `dashboard` commands | Same as above |
| `agent_registry.db` | `./agent_registry.db` | `workflow-registry` commands | agents, orchestrators |
| `mlflow.db` | `./mlflow.db` | MLflow (observability) | MLflow's own schema |
| `mlruns/` | `./mlruns/` | MLflow (legacy, deprecated in 3.9) | File-based artifact store |

**Problem**: Three different defaults for essentially the same data. User may end up with multiple scattered DB files.

### 1.2 ORM Models (Current)

| Model Class | Table Name | Purpose |
|-------------|------------|---------|
| `WorkflowRunRecord` | `workflow_runs` | Execution history records |
| `ExecutionStateRecord` | `execution_states` | State checkpoints per run |
| `AgentRecord` | `agents` | Deployed workflow containers |
| `ChatSession` | `chat_sessions` | ChatUI conversation sessions |
| `ChatMessage` | `chat_messages` | Individual chat messages |
| `WebhookEventRecord` | `webhook_events` | Webhook idempotency tracking |
| `MemoryRecord` | `memory_records` | Agent memory persistence |
| `WorkflowRegistrationRecord` | `workflow_registrations` | Webhook workflow configs |
| `OrchestratorRecord` | `orchestrators` | Orchestrator registrations |
| `SessionState` | `session_state` | ProcessManager crash detection |

### 1.3 Repository Classes (Current)

| Repository Class | Model Used | Purpose |
|------------------|------------|---------|
| `AbstractWorkflowRunRepository` | WorkflowRunRecord | Execution history CRUD |
| `AbstractExecutionStateRepository` | ExecutionStateRecord | State checkpoints |
| `AgentRegistryRepository` | AgentRecord | Deployed container management |
| `ChatSessionRepository` | ChatSession, ChatMessage | ChatUI persistence |
| `WebhookEventRepository` | WebhookEventRecord | Webhook deduplication |
| `MemoryRepository` | MemoryRecord | Agent memory |
| `WorkflowRegistrationRepository` | WorkflowRegistrationRecord | Webhook configs |
| `OrchestratorRepository` | OrchestratorRecord | Orchestrator management |

### 1.4 CLI Commands Using These (Current)

| Command | DB Default | Repositories Used |
|---------|------------|-------------------|
| `run` | `./workflows.db` | WorkflowRunRepository, ExecutionStateRepository, MemoryRepository |
| `validate` | None | None |
| `deploy` | None (generates artifacts) | None |
| `ui` | `configurable_agents.db` | All via dashboard |
| `dashboard` | `configurable_agents.db` | All via routes |
| `chat` | `configurable_agents.db` | ChatSessionRepository |
| `workflow-registry start` | `agent_registry.db` | AgentRegistryRepository |
| `workflow-registry list` | `agent_registry.db` | AgentRegistryRepository |
| `workflow-registry cleanup` | `agent_registry.db` | AgentRegistryRepository |
| `webhooks` | `configurable_agents.db` | WebhookEventRepository, WorkflowRegistrationRepository |

---

## 2. Proposed Changes

### 2.1 Database Consolidation

**Target**: Single app database `configurable_agents.db` + MLflow's `mlflow.db`

| DB File | Purpose | Status |
|---------|---------|--------|
| `configurable_agents.db` | All app data | KEEP (unified) |
| `mlflow.db` | MLflow observability | KEEP (separate, MLflow-owned) |

**Changes Required**:
1. Update `StorageConfig.path` default from `./workflows.db` to `./configurable_agents.db`
2. Remove `agent_registry.db` references - use `configurable_agents.db` for all commands
3. Update all CLI argument defaults to `configurable_agents.db`

### 2.2 Terminology Renaming

| Current | Proposed | Rationale |
|---------|----------|-----------|
| **Pages/UI** | | |
| Workflows | Executions | Shows execution history, not workflow definitions |
| Agents | Deployments | These are deployed containers running workflows |
| Orchestrator | *(absorbed into Deployments)* | Register/execute/deregister belong there |
| **Tables** | | |
| `workflow_runs` | `executions` | One record per execution |
| `agents` | `deployments` | Deployed workflow containers |
| `orchestrators` | *(merge into `deployments` or remove)* | Redundant concept |
| **Models** | | |
| `WorkflowRunRecord` | `ExecutionRecord` | Matches table rename |
| `AgentRecord` | `DeploymentRecord` | Matches table rename |
| `OrchestratorRecord` | *(remove or merge)* | Redundant |
| **Repositories** | | |
| `AbstractWorkflowRunRepository` | `AbstractExecutionRepository` | Matches model rename |
| `AgentRegistryRepository` | `DeploymentRegistryRepository` | Matches model rename |
| `SQLiteWorkflowRunRepository` | `SQLiteExecutionRepository` | Matches model rename |
| `SqliteAgentRegistryRepository` | `SqliteDeploymentRegistryRepository` | Matches model rename |
| **CLI Commands** | | |
| `workflow-registry` | `deployments` | More accurate naming |
| **Variables/Fields** | | |
| `agent_id` | `deployment_id` | Consistency |
| `agent_name` | `deployment_name` | Consistency |
| `workflow_run_id` | `execution_id` | Consistency |

### 2.3 Table Schema Changes

#### `executions` (was `workflow_runs`)
```python
class ExecutionRecord(Base):
    __tablename__ = "executions"

    id: Mapped[str]  # execution_id (was run_id)
    workflow_name: Mapped[str]
    status: Mapped[str]
    config_snapshot: Mapped[Optional[str]]
    inputs: Mapped[Optional[str]]
    outputs: Mapped[Optional[str]]
    error_message: Mapped[Optional[str]]
    started_at: Mapped[datetime]
    completed_at: Mapped[Optional[datetime]]
    duration_seconds: Mapped[Optional[float]]
    total_tokens: Mapped[Optional[int]]
    total_cost_usd: Mapped[Optional[float]]
    bottleneck_info: Mapped[Optional[str]]
```

#### `deployments` (was `agents`)
```python
class DeploymentRecord(Base):
    __tablename__ = "deployments"

    deployment_id: Mapped[str]  # was agent_id
    deployment_name: Mapped[str]  # was agent_name
    host: Mapped[str]
    port: Mapped[int]
    last_heartbeat: Mapped[datetime]
    ttl_seconds: Mapped[int]
    deployment_metadata: Mapped[Optional[str]]  # was agent_metadata
    registered_at: Mapped[datetime]
```

#### `execution_states` (unchanged, but FK update)
```python
class ExecutionStateRecord(Base):
    __tablename__ = "execution_states"

    id: Mapped[int]
    execution_id: Mapped[str]  # was run_id, FK to executions.id
    node_id: Mapped[str]
    state_data: Mapped[str]
    created_at: Mapped[datetime]
```

---

## 3. Impact Radius Analysis

### 3.1 Files Requiring Changes

#### Core Storage Layer (HIGH IMPACT)
| File | Changes Required |
|------|------------------|
| `src/configurable_agents/storage/models.py` | Rename models, table names, field names |
| `src/configurable_agents/storage/base.py` | Rename abstract repository classes |
| `src/configurable_agents/storage/sqlite.py` | Rename concrete implementations |
| `src/configurable_agents/storage/factory.py` | Update class names, variable names |
| `src/configurable_agents/storage/__init__.py` | Update exports |

#### CLI (HIGH IMPACT)
| File | Changes Required |
|------|------------------|
| `src/configurable_agents/cli.py` | Rename commands, update defaults, update variable names |

#### Registry Module (HIGH IMPACT)
| File | Changes Required |
|------|------------------|
| `src/configurable_agents/registry/__init__.py` | Rename exports, add aliases |
| `src/configurable_agents/registry/server.py` | Rename class, update docstrings |
| `src/configurable_agents/client.py` | Rename class, update method names |
| `src/configurable_agents/registry/models.py` | Remove or update (models live in storage/) |

#### Dashboard/UI (MEDIUM IMPACT)
| File | Changes Required |
|------|------------------|
| `src/configurable_agents/ui/dashboard/app.py` | Update repository references |
| `src/configurable_agents/ui/dashboard/routes/agents.py` | Rename to `deployments.py`, update logic |
| `src/configurable_agents/ui/dashboard/routes/workflows.py` | Rename to `executions.py`, update logic |
| `src/configurable_agents/ui/dashboard/routes/orchestrator.py` | Merge into `deployments.py` |
| `src/configurable_agents/ui/dashboard/routes/metrics.py` | Update model references |
| `src/configurable_agents/ui/dashboard/routes/status.py` | Update model references |
| `src/configurable_agents/ui/dashboard/templates/*.html` | Rename files, update content |
| `src/configurable_agents/ui/gradio_chat.py` | Update references if any |

#### Orchestrator Module (MEDIUM IMPACT)
| File | Changes Required |
|------|------------------|
| `src/configurable_agents/orchestrator/__init__.py` | Update terminology |
| `src/configurable_agents/orchestrator/client.py` | Update terminology |
| `src/configurable_agents/orchestrator/service.py` | Update terminology |

#### Tests (HIGH IMPACT)
| File | Changes Required |
|------|------------------|
| `tests/storage/test_factory.py` | Update class names |
| `tests/storage/test_agent_registry_repository.py` | Rename file, update tests |
| `tests/registry/test_server.py` | Update class names |
| `tests/registry/test_client.py` | Update class names |
| `tests/registry/test_ttl_expiry.py` | Update class names |
| `tests/ui/test_dashboard.py` | Update references |
| `tests/ui/test_dashboard_e2e.py` | Update references |
| `tests/ui/test_dashboard_integration.py` | Update references |
| `tests/orchestrator/*.py` | Update references |

#### Documentation (MEDIUM IMPACT)
| File | Changes Required |
|------|------------------|
| `docs/user/cli_guide.md` | Update command names, terminology |
| `docs/development/ARCHITECTURE.md` | Update terminology |
| `docs/development/UI_ARCHITECTURE.md` | Update page names, terminology |
| `docs/development/adr/ADR-020-agent-registry.md` | Update or supersede |
| `CHANGELOG.md` | Add entry for breaking changes |
| `README.md` | Update examples |

#### Config/Schema (LOW IMPACT)
| File | Changes Required |
|------|------------------|
| `src/configurable_agents/config/schema.py` | Update `StorageConfig.path` default |

### 3.2 Breaking Changes

| Change | Impact | Migration Required |
|--------|--------|-------------------|
| Table `workflow_runs` → `executions` | Existing DBs will have old table | YES - migration script or new DB |
| Table `agents` → `deployments` | Existing DBs will have old table | YES - migration script or new DB |
| `AgentRecord` → `DeploymentRecord` | Code using this class directly | YES - update imports |
| `workflow-registry` command → `deployments` | Scripts, docs, muscle memory | YES - alias old command? |
| DB default changes | Multiple DB files may exist | Manual cleanup |

### 3.3 Backward Compatibility Options

**Option A: Clean Break (Recommended for v1.0)**
- Remove all old names
- Require fresh database
- Clear migration path in docs

**Option B: Aliases + Deprecation**
- Keep old class names as aliases
- Add deprecation warnings
- Remove in v2.0

**Option C: Database Migration**
- Alembic migration script
- Rename tables, columns
- Preserve existing data

---

## 4. Recommended Implementation Order

### Phase 1: Core Storage Layer
1. Update `StorageConfig.path` default
2. Rename models in `models.py`
3. Rename abstract classes in `base.py`
4. Rename implementations in `sqlite.py`
5. Update `factory.py` and `__init__.py`

### Phase 2: CLI Updates
1. Update all `--db-url` defaults
2. Rename `workflow-registry` → `deployments`
3. Update variable names throughout
4. Add backward-compatible aliases if needed

### Phase 3: Registry Module
1. Rename classes
2. Add public aliases for backward compat
3. Update docstrings

### Phase 4: Dashboard/UI
1. Rename route files
2. Merge orchestrator into deployments
3. Update templates
4. Update template names

### Phase 5: Tests
1. Update all test files
2. Rename test files to match new naming
3. Verify all tests pass

### Phase 6: Documentation
1. Update all docs
2. Create ADR for this change
3. Update CHANGELOG

---

## 5. Open Questions

1. **Orchestrator table**: Keep or merge into deployments?
   - Current: `OrchestratorRecord` tracks orchestrators separately
   - Proposed: Remove if redundant, or clarify distinction

2. **Backward compatibility**: Clean break or aliases?
   - v1.0 can break, but need clear migration docs

3. **Session state table**: Keep as `session_state` or rename?
   - Currently singleton pattern for crash detection
   - Low impact, could leave as-is

4. **Memory/WorkflowRegistration tables**: Any renaming needed?
   - `memory_records` - agent memory, could become `deployment_memory`?
   - `workflow_registrations` - for webhooks, name is accurate

---

## 6. Summary

| Metric | Value |
|--------|-------|
| Files to modify | ~45 files |
| Breaking changes | Yes (table names, class names, CLI command) |
| Migration required | Yes (new DB or Alembic migration) |
| Estimated effort | 2-3 implementation sessions |
| Risk level | Medium (lots of changes, but systematic) |

---

*This document is for review. No code changes should be made until approved.*
