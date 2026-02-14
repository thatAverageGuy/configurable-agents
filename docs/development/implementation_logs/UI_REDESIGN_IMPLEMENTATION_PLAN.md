# UI Redesign Implementation Plan

**Status**: ✅ COMPLETE (All 6 Phases)
**Created**: 2026-02-13
**Completed**: 2026-02-13
**Related**: UI_DESIGN_SPEC.md, UI_REDESIGN_ANALYSIS.md, UI_PAGES_DESIGN.md

---

## Overview

This document provides a detailed implementation plan for the UI redesign. The work is organized into **6 phases** with clear dependencies, file changes, and testing strategies.

### Summary

| Phase | Focus | Files Changed | Risk | Status |
|-------|-------|---------------|------|--------|
| 1 | Storage Layer | 5 | High | ✅ COMPLETE |
| 2 | CLI Updates | 2 | Medium | ✅ COMPLETE |
| 3 | Registry Module | 4 | Medium | ✅ COMPLETE |
| 4 | Dashboard/UI | 10 | High | ✅ COMPLETE |
| 5 | Tests | 10 | Medium | ✅ COMPLETE |
| 6 | Documentation | 6 | Low | ✅ COMPLETE |

**Total Files Modified**: ~45 files

---

## Phase 1: Storage Layer (Foundation) ✅ COMPLETE

**Goal**: Rename all models, tables, and repositories to match new terminology.

**Completed**: 2026-02-13

### 1.1 Files to Modify

| File | Changes |
|------|---------|
| `src/configurable_agents/storage/models.py` | Rename models and table names |
| `src/configurable_agents/storage/base.py` | Rename abstract repository classes |
| `src/configurable_agents/storage/sqlite.py` | Rename concrete implementations |
| `src/configurable_agents/storage/factory.py` | Update class references |
| `src/configurable_agents/storage/__init__.py` | Update exports |

### 1.2 Model Renaming Details

```python
# OLD → NEW
WorkflowRunRecord → Execution
    __tablename__ = "workflow_runs" → "executions"
    # Add field: deployment_id: Mapped[Optional[str]]  # FK to deployments

ExecutionStateRecord → ExecutionState
    __tablename__ = "execution_states" (unchanged)
    run_id → execution_id  # FK field rename

AgentRecord → Deployment
    __tablename__ = "agents" → "deployments"
    agent_id → deployment_id
    agent_name → deployment_name
    agent_metadata → deployment_metadata
    # Add field: workflow_name: Mapped[str]

OrchestratorRecord → REMOVE (absorbed into Deployments)
```

### 1.3 Repository Renaming Details

```python
# OLD → NEW
AbstractWorkflowRunRepository → AbstractExecutionRepository
SQLiteWorkflowRunRepository → SQLiteExecutionRepository

AgentRegistryRepository → DeploymentRepository
SqliteAgentRegistryRepository → SqliteDeploymentRepository

OrchestratorRepository → REMOVE
```

### 1.4 Schema Changes

#### executions table (was workflow_runs)
```sql
-- New field
deployment_id VARCHAR(36)  -- FK to deployments.deployment_id, nullable
```

#### deployments table (was agents)
```sql
-- Renamed fields
deployment_id VARCHAR(255) PRIMARY KEY  -- was agent_id
deployment_name VARCHAR(256)             -- was agent_name
deployment_metadata VARCHAR(4000)        -- was agent_metadata

-- New field
workflow_name VARCHAR(256)  -- workflow this deployment runs
```

#### execution_states table
```sql
-- Renamed field
execution_id VARCHAR(36)  -- was run_id, FK to executions.id
```

### 1.5 Implementation Steps

1. **Backup existing databases** (manual step)
2. Update `models.py`:
   - Rename `WorkflowRunRecord` to `Execution`, update `__tablename__`
   - Add `deployment_id` field to `Execution`
   - Rename `ExecutionStateRecord.run_id` to `execution_id`
   - Rename `AgentRecord` to `Deployment`, update `__tablename__`
   - Add `workflow_name` field to `Deployment`
   - Rename field names (agent_id → deployment_id, etc.)
   - Remove `OrchestratorRecord` class
3. Update `base.py`:
   - Rename abstract classes
   - Update method signatures
4. Update `sqlite.py`:
   - Rename concrete implementations
   - Update SQL queries and field references
5. Update `factory.py`:
   - Update class name references
6. Update `__init__.py`:
   - Export new class names
   - Add backward-compatible aliases (optional)

### 1.6 Testing Strategy

- [ ] Unit tests for all renamed models
- [ ] Unit tests for all renamed repositories
- [ ] Test FK relationships (executions.deployment_id → deployments)
- [ ] Test fresh database creation with new schema
- [ ] Run existing storage tests with updated imports

### 1.7 Backward Compatibility

**Decision**: Clean break (no aliases)
- This is v1.0 pre-release
- Users will need fresh database
- Document migration path clearly

---

## Phase 2: CLI Updates ✅ COMPLETE

**Goal**: Update CLI commands to use new terminology and database defaults.

**Completed**: 2026-02-13

### 2.1 Files Modified

| File | Changes |
|------|---------|
| `src/configurable_agents/cli.py` | Renamed commands, updated terminology |
| `src/configurable_agents/config/schema.py` | Updated `StorageConfig.path` default |

### 2.2 Changes Made

- Command renamed: `workflow-registry` → `deployments`
- Functions renamed: `cmd_workflow_registry_*` → `cmd_deployments_*`
- Import renamed: `WorkflowRegistryServer` → `DeploymentRegistryServer`
- Variables renamed: `agent` → `deployment`, `agents` → `deployments`
- Fields renamed: `agent_id` → `deployment_id`, `agent_name` → `deployment_name`
- Default DB path: `workflows.db` → `configurable_agents.db`
- Storage tuple unpacking: 8 values → 7 (removed orchestrator)

### 2.3 Testing Strategy

- [ ] Test `deployments start` command
- [ ] Test `deployments list` command
- [ ] Test `deployments cleanup` command
- [ ] Verify database default is correct
- [ ] Test `run` command with new DB path

---

## Phase 3: Registry Module Updates ✅ COMPLETE

**Goal**: Update registry module classes to use new terminology.

**Completed**: 2026-02-13

### 3.1 Files Modified

| File | Changes |
|------|---------|
| `src/configurable_agents/registry/__init__.py` | Updated exports with backward-compatible aliases |
| `src/configurable_agents/registry/server.py` | Renamed `AgentRegistryServer` → `DeploymentRegistryServer` |
| `src/configurable_agents/registry/client.py` | Renamed `AgentRegistryClient` → `DeploymentClient` |
| `src/configurable_agents/registry/models.py` | Updated Pydantic models for API layer |

### 3.2 Changes Made

- Routes: `/agents/*` → `/deployments/*`
- `AgentRegistrationRequest` → `DeploymentRegistrationRequest`
- `AgentInfo` → `DeploymentInfo`
- Added `workflow_name` field to track which workflow a deployment runs
- Removed orchestrator-related models
- Storage tuple: 8 → 7 values

---

## Phase 4: Dashboard/UI Updates ✅ COMPLETE

**Goal**: Restructure dashboard routes and templates to match new 4-page design.

**Completed**: 2026-02-13

### 4.1 Files Modified

| File | Action |
|------|--------|
| `src/configurable_agents/ui/dashboard/routes/workflows.py` | Renamed to `executions.py` |
| `src/configurable_agents/ui/dashboard/routes/agents.py` | Renamed to `deployments.py` |
| `src/configurable_agents/ui/dashboard/routes/orchestrator.py` | **DELETED** (merged into deployments.py) |
| `src/configurable_agents/ui/dashboard/routes/__init__.py` | Updated imports |
| `src/configurable_agents/ui/dashboard/routes/metrics.py` | Updated model references |
| `src/configurable_agents/ui/dashboard/routes/status.py` | Updated model references |
| `src/configurable_agents/ui/dashboard/app.py` | Updated route imports, navigation |

### 4.2 Route Changes

```python
# OLD → NEW routes
/workflows/* → /executions/*
/agents/* → /deployments/*
/orchestrator/* → REMOVED (merged into /deployments/*)
```

### 4.3 App State Changes

- `workflow_repo` → `execution_repo`
- `agent_registry_repo` → `deployment_repo`

---

## Phase 5: Test Updates ✅ COMPLETE

**Goal**: Update all test files to use new class/model names.

**Completed**: 2026-02-13

### 5.1 Files Updated

| File | Changes |
|------|---------|
| `tests/storage/test_factory.py` | Updated class names, 8 → 7 repos |
| `tests/storage/test_sqlite.py` | Renamed models (Execution, ExecutionState) |
| `tests/storage/test_base.py` | Updated abstract class names |
| `tests/storage/test_deployment_repository.py` | **RENAMED** from test_agent_registry_repository.py |
| `tests/storage/test_agent_registry_repository.py` | **DELETED** |
| `tests/registry/test_server.py` | Bulk replace all names |
| `tests/registry/test_ttl_expiry.py` | Bulk replace all names |
| `tests/ui/test_dashboard.py` | Bulk replace all names |
| `tests/ui/test_dashboard_e2e.py` | Bulk replace all names |
| `tests/ui/test_dashboard_integration.py` | Bulk replace all names |
| `tests/runtime/test_executor_storage.py` | Bulk replace all names |

### 5.2 Bulk Replacements Applied

- `WorkflowRunRecord` → `Execution`
- `AgentRecord` → `Deployment`
- `ExecutionStateRecord` → `ExecutionState`
- `agent_id` → `deployment_id`
- `agent_name` → `deployment_name`
- Storage tuple: 8 → 7 values

---

## Phase 6: Documentation Updates ✅ COMPLETE

**Goal**: Update all documentation to reflect new terminology.

**Completed**: 2026-02-13

### 6.1 Files Updated

| File | Status |
|------|--------|
| `CHANGELOG.md` | ✅ Updated with complete 6-phase changelog entry |
| `CONTEXT.md` | ✅ Updated with final status and commit message |
| `docs/development/TASKS.md` | ✅ Marked UI-REDESIGN complete |
| `docs/development/ARCHITECTURE.md` | ✅ Updated all terminology |
| `docs/development/adr/ADR-XXX-ui-redesign-terminology.md` | ✅ Created new ADR |
| `docs/development/implementation_logs/UI_REDESIGN_IMPLEMENTATION_PLAN.md` | ✅ This file |

### 6.2 User Documentation

User docs (`docs/user/`) may need updates if they reference old command names or routes. These can be updated in a follow-up pass if needed.

---

## Implementation Order

### Recommended Sequence

```
Phase 1 (Storage) ──────► Phase 2 (CLI) ──────► Phase 3 (Registry)
         │                       │                      │
         └───────────────────────┼──────────────────────┘
                                 │
                                 ▼
                         Phase 4 (Dashboard)
                                 │
                                 ▼
                         Phase 5 (Tests)
                                 │
                                 ▼
                       Phase 6 (Documentation)
```

### Critical Path

1. **Phase 1 MUST complete first** - All other phases depend on storage layer changes
2. **Phases 2, 3, 4 can run in parallel** after Phase 1 (with coordination)
3. **Phase 5 MUST wait** for Phases 1-4 to complete
4. **Phase 6 can start anytime** but should complete last

---

## Breaking Changes Summary

| Change | Impact | Migration |
|--------|--------|-----------|
| `workflow_runs` → `executions` | Table rename | Fresh DB required |
| `agents` → `deployments` | Table rename | Fresh DB required |
| `AgentRecord` → `Deployment` | Class rename | Update imports |
| `workflow-registry` → `deployments` | CLI rename | Update scripts |
| `/workflows` → `/executions` | Route rename | Update bookmarks |
| `/agents` → `/deployments` | Route rename | Update bookmarks |
| `/orchestrator/*` removed | Route removal | Use `/deployments/*` |

---

## Rollback Plan

If issues arise during implementation:

1. **Phase 1-3**: Can rollback via git revert (no DB migration yet)
2. **Phase 4**: Template/route issues are isolated to UI
3. **Phase 5**: Test failures don't affect runtime
4. **Fresh DB**: Always an option to delete and recreate

---

## Success Criteria

Implementation is complete when:

1. [x] All storage models renamed and tested
2. [x] All repositories renamed and tested
3. [x] CLI `deployments` command works
4. [x] Dashboard shows 4 pages (Chat, Executions, Deployments, MLflow)
5. [x] All routes work with new names
6. [x] All tests pass
7. [x] Documentation updated
8. [x] CONTEXT.md reflects completion

---

## Decisions Made

1. **Rename to `DeploymentRegistryServer`** - Full consistency with "Deployment" terminology
2. **Clean break for database** - No migration script, fresh database required
3. **Local commit only** - No push to GitHub (local experiment)

---

*Implementation completed 2026-02-13. Ready for local commit.*
