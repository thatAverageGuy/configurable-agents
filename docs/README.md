# Documentation Index

> Complete index of all project documentation. Organized by audience and purpose.

---

## Quick Navigation

- [Getting Started](#getting-started) - New users start here
- [User Guides](#user-guides) - How to use the platform
- [Developer Documentation](#developer-documentation) - Internal development docs
- [API Reference](#api-reference) - API documentation

---

## Getting Started

| Document | Description | Link |
|----------|-------------|------|
| **QUICKSTART** | Get started in 5 minutes with your first workflow | [user/QUICKSTART.md](user/QUICKSTART.md) |
| **README** | Project overview, features, and installation (root) | [../README.md](../README.md) |

---

## User Guides

### Core Documentation

| Document | Description | Link |
|----------|-------------|------|
| **Config Reference** | Complete YAML config schema reference | [user/CONFIG_REFERENCE.md](user/CONFIG_REFERENCE.md) |
| **Troubleshooting** | Common issues and solutions | [user/TROUBLESHOOTING.md](user/TROUBLESHOOTING.md) |
| **Observability** | MLFlow setup, cost tracking, and monitoring | [user/OBSERVABILITY.md](user/OBSERVABILITY.md) |
| **Deployment** | Docker deployment guide | [user/DEPLOYMENT.md](user/DEPLOYMENT.md) |
| **Security Guide** | Security best practices | [user/SECURITY_GUIDE.md](user/SECURITY_GUIDE.md) |

### Advanced Topics

| Document | Description | Link |
|----------|-------------|------|
| **Advanced Topics** | Advanced features overview (control flow, memory, etc.) | [user/ADVANCED_TOPICS.md](user/ADVANCED_TOPICS.md) |
| **Performance Optimization** | A/B testing, quality gates, prompt optimization | [user/PERFORMANCE_OPTIMIZATION.md](user/PERFORMANCE_OPTIMIZATION.md) |
| **Production Deployment** | Production patterns and best practices | [user/PRODUCTION_DEPLOYMENT.md](user/PRODUCTION_DEPLOYMENT.md) |
| **Tool Development** | Creating custom tools | [user/TOOL_DEVELOPMENT.md](user/TOOL_DEVELOPMENT.md) |

---

## Developer Documentation

> Internal documentation for development and architecture decisions.

### Core Architecture

| Document | Description | Link |
|----------|-------------|------|
| **Project Vision** | Long-term vision, philosophy, and non-goals | [development/PROJECT_VISION.md](development/PROJECT_VISION.md) |
| **Architecture** | System design, components, and patterns | [development/ARCHITECTURE.md](development/ARCHITECTURE.md) |
| **Spec** | Technical specification and requirements | [development/SPEC.md](development/SPEC.md) |
| **TASKS** | Work breakdown and current status | [development/TASKS.md](development/TASKS.md) |
| **CONTEXT** | Development context and current state | [../CONTEXT.md](../CONTEXT.md) |

### Architecture Decision Records (ADRs)

| Directory | Description | Link |
|-----------|-------------|------|
| **ADRs** | 25+ architecture decision records with rationale | [development/adr/](development/adr/) |

**Key ADRs:**
- [ADR-001: LangGraph Execution Engine](development/adr/ADR-001-langgraph-execution-engine.md)
- [ADR-019: LiteLLM Integration](development/adr/ADR-019-litellm-integration.md)
- [ADR-020: Agent Registry](development/adr/ADR-020-agent-registry.md)
- [ADR-021: HTMX Dashboard](development/adr/ADR-021-htmx-dashboard.md)
- [ADR-022: RestrictedPython Sandbox](development/adr/ADR-022-restrictedpython-sandbox.md)
- [ADR-023: Memory Backend](development/adr/ADR-023-memory-backend.md)
- [ADR-024: Webhook Integration](development/adr/ADR-024-webhook-integration.md)
- [ADR-025: Optimization Architecture](development/adr/ADR-025-optimization-architecture.md)

### Implementation Logs

| Directory | Description | Link |
|-----------|-------------|------|
| **Implementation Logs** | Detailed task-by-task implementation records | [development/implementation_logs/](development/implementation_logs/) |

**Recent Logs:**
- [CL-001: Cleanup and Documentation Reorganization](development/implementation_logs/CL-001_cleanup_restoration.md)
- [CL-002: Documentation Index and Dead Link Cleanup](development/implementation_logs/CL-002_doc_index_cleanup.md)

**Phase 1 (Foundation):**
- [T-001: Project Setup](development/implementation_logs/phase_1_foundation/T-001_project_setup.md)
- [T-002: Config Parser](development/implementation_logs/phase_1_foundation/T-002_config_parser.md)
- [T-003: Config Schema](development/implementation_logs/phase_1_foundation/T-003_config_schema.md)
- [T-004: Config Validator](development/implementation_logs/phase_1_foundation/T-004_config_validator.md)
- [T-005: Type System](development/implementation_logs/phase_1_foundation/T-005_type_system.md)
- [T-006: State Schema Builder](development/implementation_logs/phase_1_foundation/T-006_state_schema_builder.md)
- [T-007: Output Schema Builder](development/implementation_logs/phase_1_foundation/T-007_output_schema_builder.md)

**Phase 2 (Core Execution):**
- [T-008: Tool Registry](development/implementation_logs/phase_2_core_execution/T-008_tool_registry.md)
- [T-009: LLM Provider](development/implementation_logs/phase_2_core_execution/T-009_llm_provider.md)
- [T-010: Prompt Template Resolver](development/implementation_logs/phase_2_core_execution/T-010_prompt_template_resolver.md)
- [T-011: Node Executor](development/implementation_logs/phase_2_core_execution/T-011_node_executor.md)
- [T-012: Graph Builder](development/implementation_logs/phase_2_core_execution/T-012_graph_builder.md)
- [T-013: Runtime Executor](development/implementation_logs/phase_2_core_execution/T-013_runtime_executor.md)

**Phase 3 (Polish & UX):**
- [T-014: CLI Interface](development/implementation_logs/phase_3_polish_ux/T-014_cli_interface.md)
- [T-015: Example Configs](development/implementation_logs/phase_3_polish_ux/T-015_example_configs.md)
- [T-016: Documentation](development/implementation_logs/phase_3_polish_ux/T-016_documentation.md)
- [T-017: Integration Tests](development/implementation_logs/phase_3_polish_ux/T-017_integration_tests.md)

**Phase 4 (Observability & Docker):**
- [T-018: MLFlow Integration Foundation](development/implementation_logs/phase_4_observability_docker/T-018_mlflow_integration_foundation.md)
- [T-019: MLFlow Instrumentation](development/implementation_logs/phase_4_observability_docker/T-019_mlflow_instrumentation.md)
- [T-020: Cost Tracking & Reporting](development/implementation_logs/phase_4_observability_docker/T-020_cost_tracking_reporting.md)
- [T-021: Observability Documentation](development/implementation_logs/phase_4_observability_docker/T-021_observability_documentation.md)
- [T-022: Docker Artifact Generator](development/implementation_logs/phase_4_observability_docker/T-022_docker_artifact_generator.md)
- [T-023: FastAPI Server Sync/Async](development/implementation_logs/phase_4_observability_docker/T-023_fastapi_server_sync_async.md)
- [T-024: CLI Deploy Command](development/implementation_logs/phase_4_observability_docker/T-024_cli_deploy_command.md)
- [T-028: MLFlow 3.9 Migration](development/implementation_logs/phase_4_observability_docker/T-028_mlflow_39_migration.md)

### Bug Records

| Directory | Description | Link |
|-----------|-------------|------|
| **Bugs** | Bug reports and resolutions | [development/bugs/](development/bugs/) |

---

## API Reference

| Document | Description | Link |
|----------|-------------|------|
| **API Index** | Complete API documentation (auto-generated) | [api/index.md](api/index.md) |
| **Config API** | Configuration module API | [api/config.md](api/config.md) |
| **Core API** | Core execution API | [api/core.md](api/core.md) |
| **LLM API** | LLM provider API | [api/llm.md](api/llm.md) |
| **Observability API** | Observability and metrics API | [api/observability.md](api/observability.md) |
| **Runtime API** | Runtime execution API | [api/runtime.md](api/runtime.md) |
| **Tools API** | Tool registry and tools API | [api/tools.md](api/tools.md) |

---

## Other Documentation

| Document | Description | Link |
|----------|-------------|------|
| **CHANGELOG** | Release notes and version history | [../CHANGELOG.md](../CHANGELOG.md) |
| **SETUP** | Development setup guide | [../SETUP.md](../SETUP.md) |
| **CLAUDE.md** | Project instructions for AI assistant | [../CLAUDE.md](../CLAUDE.md) |
| **Contributing** | Contribution guidelines | [../CONTRIBUTING.md](../CONTRIBUTING.md) |

---

## Documentation Structure

```
docs/
├── README.md                    # This file - documentation index
├── user/                        # User-facing documentation
│   ├── QUICKSTART.md
│   ├── CONFIG_REFERENCE.md
│   ├── TROUBLESHOOTING.md
│   ├── OBSERVABILITY.md
│   ├── DEPLOYMENT.md
│   ├── SECURITY_GUIDE.md
│   ├── ADVANCED_TOPICS.md
│   ├── PERFORMANCE_OPTIMIZATION.md
│   ├── PRODUCTION_DEPLOYMENT.md
│   └── TOOL_DEVELOPMENT.md
│
├── development/                 # Internal development docs
│   ├── PROJECT_VISION.md
│   ├── ARCHITECTURE.md
│   ├── SPEC.md
│   ├── TASKS.md
│   ├── adr/                    # Architecture Decision Records (25+ ADRs)
│   ├── bugs/                   # Bug reports
│   ├── implementation_logs/    # Task-by-task implementation records
│   │   ├── CL-001_cleanup_restoration.md
│   │   ├── CL-002_doc_index_cleanup.md
│   │   ├── phase_1_foundation/
│   │   ├── phase_2_core_execution/
│   │   ├── phase_3_polish_ux/
│   │   └── phase_4_observability_docker/
│   └── session_context/        # Archived session contexts
│
└── api/                         # API reference (auto-generated)
    ├── index.md
    ├── config.md
    ├── core.md
    ├── llm.md
    ├── observability.md
    ├── runtime.md
    └── tools.md
```

---

## Quick Reference

### For New Users
1. Read [README.md](../README.md) for project overview
2. Follow [QUICKSTART.md](user/QUICKSTART.md) for your first workflow
3. Check [CONFIG_REFERENCE.md](user/CONFIG_REFERENCE.md) for config syntax

### For Developers
1. Read [ARCHITECTURE.md](development/ARCHITECTURE.md) for system design
2. Check [TASKS.md](development/TASKS.md) for current work
3. Review [ADRs](development/adr/) for architectural decisions

### For Troubleshooting
1. Check [TROUBLESHOOTING.md](user/TROUBLESHOOTING.md) for common issues
2. Review [OBSERVABILITY.md](user/OBSERVABILITY.md) for debugging
3. Check [CONTEXT.md](../CONTEXT.md) for current project state

---

*Last Updated: 2026-02-06*
