# ADR-026: UI Redesign Terminology Changes

**Status**: Accepted
**Date**: 2026-02-13
**Supersedes**: ADR-020 (partially - renamed from "Agent Registry" to "Deployment Registry")

---

## Context

The project is implementing a new 4-page UI design (Chat UI, Executions, Deployments, MLflow). The existing terminology was inconsistent with this design:

- `WorkflowRunRecord` / `workflow_runs` → Used for individual executions but named "runs"
- `AgentRecord` / `agents` → Used for deployments but named "agents"
- `OrchestratorRecord` / `orchestrators` → Redundant with deployments
- Routes: `/workflows/*`, `/agents/*`, `/orchestrator/*` → Fragmented

The new UI design requires clean, consistent terminology that maps 1:1 to the 4 pages.

---

## Decision

We will rename all models, tables, routes, and classes to match the new 4-page UI design.

### Model/Table Renaming

| Old Name | New Name | Table |
|----------|----------|-------|
| `WorkflowRunRecord` | `Execution` | `executions` |
| `AgentRecord` | `Deployment` | `deployments` |
| `OrchestratorRecord` | *(removed)* | *(removed)* |
| `ExecutionStateRecord` | `ExecutionState` | `execution_states` |

### Repository Renaming

| Old Name | New Name |
|----------|----------|
| `AbstractWorkflowRunRepository` | `AbstractExecutionRepository` |
| `SQLiteWorkflowRunRepository` | `SQLiteExecutionRepository` |
| `AgentRegistryRepository` | `DeploymentRepository` |
| `SqliteAgentRegistryRepository` | `SqliteDeploymentRepository` |
| `OrchestratorRepository` | *(removed)* |

### Registry Module Renaming

| Old Name | New Name |
|----------|----------|
| `AgentRegistryServer` | `DeploymentRegistryServer` |
| `AgentRegistryClient` | `DeploymentClient` |
| `AgentRegistrationRequest` | `DeploymentRegistrationRequest` |

### Route Renaming

| Old Route | New Route |
|-----------|-----------|
| `/workflows/*` | `/executions/*` |
| `/agents/*` | `/deployments/*` |
| `/orchestrator/*` | *(merged into `/deployments/*`)* |

### CLI Renaming

| Old Command | New Command |
|-------------|-------------|
| `workflow-registry` | `deployments` |

### Storage Factory Changes

- Return tuple: 8 values → 7 values (removed orchestrator repository)

---

## Consequences

### Positive

1. **Consistency**: All terminology maps cleanly to the 4-page UI
2. **Simplicity**: Removed `OrchestratorRecord` reduces complexity
3. **Clarity**: "Execution" is clearer than "WorkflowRun" for individual runs
4. **Discovery**: "Deployment" better describes long-running services vs "Agent"
5. **Navigation**: Routes match page names directly

### Negative

1. **Breaking Change**: Requires fresh database (tables renamed)
2. **Import Changes**: All class imports must be updated
3. **Route Changes**: API clients must update endpoint URLs
4. **CLI Changes**: Scripts using `workflow-registry` command must update

### Migration Path

**No migration script provided**. This is a clean break for v1.0 pre-release.

Users should:
1. Export any needed data from old database
2. Delete old database file
3. Restart application (tables created automatically with new schema)
4. Re-import data if needed (manual process)

### Backward Compatibility

Backward-compatible aliases are provided in `__init__.py` files for:
- `AgentRegistryServer` → `DeploymentRegistryServer`
- `AgentRegistryClient` → `DeploymentClient`
- `WorkflowRegistryServer` → `DeploymentRegistryServer`
- `WorkflowRegistryClient` → `DeploymentClient`

These aliases will be removed in a future version.

---

## Implementation

6 phases completed on 2026-02-13:

1. **Phase 1**: Storage Layer (5 files)
2. **Phase 2**: CLI Updates (2 files)
3. **Phase 3**: Registry Module (4 files)
4. **Phase 4**: Dashboard/UI (10 files)
5. **Phase 5**: Tests (10 files)
6. **Phase 6**: Documentation (6 files)

**Total**: ~45 files modified

---

## Related

- [UI_DESIGN_SPEC.md](../UI_DESIGN_SPEC.md) - New 4-page UI design
- [UI_REDESIGN_IMPLEMENTATION_PLAN.md](../implementation_logs/UI_REDESIGN_IMPLEMENTATION_PLAN.md) - Detailed implementation plan
- [ADR-020](ADR-020-agent-registry.md) - Original Agent Registry ADR (superseded)
- [CHANGELOG.md](../../../CHANGELOG.md) - Breaking changes entry
