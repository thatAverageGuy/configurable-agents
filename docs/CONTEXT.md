# Development Context

> **Purpose**: Quick context for resuming development. Updated after each task completion.
>
> **For LLMs**: Read this first to understand current state, next action, and project standards.
> Fetch details from linked docs as needed during implementation.

**Last Updated**: 2026-01-31
**Current Phase**: Phase 4 (Observability & Docker Deployment)
**Latest Completion**: T-017 (Integration Tests) - 2026-01-28
**Next Action**: T-018 (MLFlow Integration Foundation)

---

## 🎯 Current State (What's Done, What Works)

### Progress Overview

- **Overall**: 18/27 tasks complete (67%)
- **Phase 1** (Foundation): ✅ 8/8 complete
- **Phase 2** (Core Execution): ✅ 6/6 complete
- **Phase 3** (Polish & UX): ✅ 4/4 complete
- **Phase 4** (Observability & Docker): 0/6 in progress
- **Phase 5** (Future): 3 tasks deferred to v0.2+

### What Works Right Now

```bash
# Complete end-to-end workflow execution
configurable-agents run article_writer.yaml --input topic="AI Safety"

# Config validation
configurable-agents validate workflow.yaml

# Python API
from configurable_agents.runtime import run_workflow
result = run_workflow("workflow.yaml", {"topic": "AI"})
```

**Key Capabilities**:
- ✅ YAML/JSON config parsing and validation
- ✅ Dynamic Pydantic state and output models
- ✅ Google Gemini LLM integration with structured outputs
- ✅ Tool registry (Serper web search)
- ✅ LangGraph execution engine
- ✅ CLI interface with smart input parsing
- ✅ 468 tests (449 unit + 19 integration)
- ✅ Complete user documentation

**What Doesn't Work Yet**:
- ❌ MLFlow observability (T-018-021)
- ❌ Docker deployment (T-022-024)
- ❌ Conditional routing (v0.2+)
- ❌ Multi-LLM support (v0.2+)

### Latest Completion: T-017 (Integration Tests)

**Completed**: 2026-01-28
**What**: 19 integration tests with real API calls (6 workflow + 13 error scenarios)
**Impact**:
- Validates end-to-end execution with real LLM/tools
- Cost tracking ($0.47 for full suite)
- Caught 2 critical bugs (tool binding order, default model)
- 468 tests total (up from 443)

**Key Files Modified**:
- `tests/integration/` - New test suite (1,066 lines)
- `src/configurable_agents/llm/provider.py` - Fixed tool binding bug
- `src/configurable_agents/llm/google.py` - Updated default model
- See: `implementation_logs/phase_3_polish_ux/T-017_integration_tests.md`

---

## 📋 Next Action (Start Here!)

### Task: T-018 - MLFlow Integration Foundation

**Goal**: Integrate MLFlow for tracking workflow executions, costs, and prompts.

**Acceptance Criteria**:
1. MLFlow dependency added and configured
2. Logging callback for LangGraph execution
3. Basic metrics: workflow name, duration, status
4. LLM metrics: model, tokens (input/output), estimated cost
5. Start/end run lifecycle management
6. Unit tests for MLFlow integration (mocked)
7. Integration test with real MLFlow backend
8. Documentation: setup instructions, usage examples

**Key Considerations**:
- Parse-time config validation (fail before MLFlow logging)
- Graceful degradation if MLFlow unavailable
- Zero performance overhead when disabled
- Cost estimation for Google Gemini (pricing constants)
- See ADR-011 (MLFlow Observability) for design decisions

**Key Files to Modify**:
- `src/configurable_agents/observability/` (new module)
  - `mlflow_tracker.py` (callback implementation)
  - `cost_estimator.py` (token → cost conversion)
- `src/configurable_agents/runtime/executor.py` (integrate callback)
- `src/configurable_agents/config/schema.py` (already has ObservabilityConfig)
- `tests/observability/` (new test suite)

**Dependencies**:
- `mlflow>=2.9.0` (add to pyproject.toml)
- Existing: T-013 (runtime executor), T-009 (LLM provider)

**Estimated Effort**: 4-6 hours

**Implementation Sequence**:
1. Read ADR-011 (MLFlow Observability) for design decisions
2. Read `docs/SPEC.md` section on `config.observability.mlflow`
3. Implement `CostEstimator` class (Gemini pricing constants)
4. Implement `MLFlowCallback` (LangGraph callback interface)
5. Integrate callback in `runtime/executor.py`
6. Write unit tests (mock MLFlow)
7. Write integration test (real MLFlow backend)
8. Update documentation
9. Create implementation log: `implementation_logs/phase_4_observability_docker/T-018_mlflow_integration_foundation.md`
10. Update CHANGELOG.md (add to [Unreleased])
11. Update this file (CONTEXT.md)

**Related Documentation**:
- `adr/ADR-011-mlflow-observability.md` - Design rationale
- `SPEC.md` lines 450-480 - Config schema for MLFlow
- `ARCHITECTURE.md` - Observability patterns
- `OBSERVABILITY.md` - User-facing MLFlow guide (update after T-018-021)

---

## 📚 Documentation Map (Where to Find What)

### Core Technical Docs (Stable, Reference)

| Document | Purpose | When to Read |
|----------|---------|--------------|
| **PROJECT_VISION.md** | Long-term vision, philosophy, non-goals | Understanding "why" and project direction |
| **ARCHITECTURE.md** | System design, patterns, components | Understanding "how" the system works |
| **SPEC.md** | Schema v1.0 specification (complete config reference) | Implementing config-related features |
| **TASKS.md** | Work breakdown, dependencies, acceptance criteria | Planning work, checking task details |
| **CLAUDE.md** | Development workflow, change control policy | **READ FIRST** - How to work with this codebase |

### Implementation Records (Historical, Detailed)

| Document | Purpose | When to Read |
|----------|---------|--------------|
| **CHANGELOG.md** | Release notes (standard format, user-facing) | Understanding what changed per release |
| **implementation_logs/** | Detailed task implementation notes (dev-facing) | Deep dive into how a task was implemented |
| **adr/** | Architecture Decision Records (16 ADRs) | Understanding why a design choice was made |

### User-Facing Docs (External)

| Document | Purpose | Audience |
|----------|---------|----------|
| **QUICKSTART.md** | 5-minute tutorial | New users |
| **CONFIG_REFERENCE.md** | Config schema guide | Config authors |
| **TROUBLESHOOTING.md** | Common errors and fixes | Users debugging issues |
| **OBSERVABILITY.md** | MLFlow setup and usage | Users tracking costs (T-018-021) |
| **DEPLOYMENT.md** | Docker deployment | Users deploying workflows (T-022-024) |

### Living Documents (Updated Frequently)

| Document | Purpose | Update Frequency |
|----------|---------|------------------|
| **CONTEXT.md** (this file) | Current state, next action, dev context | After every task |
| **TASKS.md** | Task status (TODO/IN_PROGRESS/DONE) | After every task |
| **README.md** | Project overview, progress, quickstart | Weekly or per milestone |

---

## 🔧 Implementation Standards (How We Work)

### Code Principles (from PROJECT_VISION.md)

**Philosophy**:
- **Local-First**: Runs on user's machine, data stays local
- **Strict Typing**: All inputs/outputs are Pydantic models
- **Fail Fast, Fail Loud**: Validate at parse time, clear errors, no silent failures
- **Boring Technology**: Explicit > implicit, composition > abstraction
- **Production-Grade**: Testing non-negotiable, observability built in

**Key Mantras**:
1. "Does this add complexity or remove it?" (Prefer removal)
2. "Can a user understand this by reading the config?" (Prefer transparency)
3. "Will this break existing configs?" (Avoid breaking changes)
4. "Is this testable?" (If not, rethink)
5. "Does this fail fast?" (Catch errors early)

### Testing Requirements (from ADR-017)

**Test Strategy**:
- **Unit tests** (mocked LLM/APIs): Required for all components
- **Integration tests** (real APIs): Required for critical paths only
- **Cost tracking**: Integration tests must track and report API costs

**Test Requirements**:
- Every new module needs unit tests (>80% coverage)
- Critical user paths need integration tests
- All tests in `tests/` pass before marking task DONE
- Integration tests run on PR only (cost control)

**Running Tests**:
```bash
# Unit tests (fast, free)
pytest tests/ --ignore=tests/integration/

# Integration tests (slow, costs $0.50)
pytest tests/integration/ -v

# All tests
pytest -v
```

### Change Control (from CLAUDE.md)

**CRITICAL**: All changes must declare a CHANGE LEVEL.

| Level | Scope | Requirements |
|-------|-------|--------------|
| **LEVEL 0** | Read only (questions, analysis) | Default mode, no file modifications |
| **LEVEL 1** | Surgical edits (~20 lines, existing files only) | No new files, no refactoring |
| **LEVEL 2** | Local changes (single logical area) | Public interfaces stable, typical for tasks |
| **LEVEL 3** | Structural changes (multi-file, architectural) | **Requires ADR** or updating ARCHITECTURE.md |

**For T-018 (MLFlow Integration)**:
- **Declared Level**: CHANGE LEVEL 2
- **Rationale**: New module (`observability/`), existing runtime integration, no public API changes
- **No ADR needed**: ADR-011 already exists with design decisions

### Documentation Requirements (After Task Completion)

**MUST UPDATE** (4 files):
1. **TASKS.md**: Change task status to DONE, update progress percentage
2. **Implementation log**: Create `implementation_logs/phase_X/T-XXX_task_name.md` with details
3. **CHANGELOG.md**: Add entry to `[Unreleased]` section (5-10 lines)
4. **CONTEXT.md** (this file): Update "Latest Completion", "Next Action", "Current State"

**MAY UPDATE** (if applicable):
- **README.md**: If major milestone or user-facing feature (update "What Works Now")
- **ADRs**: Create new ADR if CHANGE LEVEL 3 (structural changes)
- **User docs**: Update QUICKSTART.md, CONFIG_REFERENCE.md, etc. if user-visible changes

### File Naming Conventions

**Source Code**:
- Modules: `snake_case.py` (e.g., `mlflow_tracker.py`)
- Classes: `PascalCase` (e.g., `MLFlowCallback`)
- Functions: `snake_case` (e.g., `estimate_cost`)

**Tests**:
- Test files: `test_<module_name>.py` (e.g., `test_mlflow_tracker.py`)
- Test functions: `test_<scenario>` (e.g., `test_mlflow_callback_logs_metrics`)
- Integration tests: `tests/integration/test_*.py` with `@pytest.mark.integration`

**Documentation**:
- Core docs: `SCREAMING_SNAKE.md` (e.g., `ARCHITECTURE.md`)
- Implementation logs: `T-XXX_task_name.md` (e.g., `T-018_mlflow_integration_foundation.md`)
- ADRs: `ADR-NNN-title.md` (e.g., `ADR-011-mlflow-observability.md`)

---

## 🚦 Common Patterns & Gotchas

### Pattern: Parse-Time Validation

```python
# ALWAYS validate config before runtime execution
config = WorkflowConfig(**config_dict)  # Pydantic validation
validate_config(config)                  # Cross-reference validation
validate_runtime_support(config)         # Feature gating

# THEN execute (never execute invalid config)
graph = build_graph(config, state_model, global_config)
```

### Pattern: Fail-Fast Error Handling

```python
# Custom error types with helpful messages
from configurable_agents.core import NodeExecutionError

try:
    result = execute_node(node, state)
except LLMAPIError as e:
    raise NodeExecutionError(
        node_id=node.id,
        message=f"LLM call failed: {e}",
        suggestion="Check GOOGLE_API_KEY environment variable",
        original_error=e
    )
```

### Pattern: Cost Tracking (Integration Tests)

```python
# Always track costs in integration tests
def test_workflow_integration(cost_tracker):
    result = run_workflow("workflow.yaml", {"topic": "AI"})

    # Track estimated cost
    cost_tracker.add_gemini_call(input_tokens=150, output_tokens=500)

    assert "result" in result
    # Cost printed at end: ~$0.02
```

### Gotcha: LangGraph Returns Dict, Not BaseModel

```python
# Graph invocation returns dict, NOT Pydantic model
state_model = build_state_model(config.state)
graph = build_graph(config, state_model)

initial = state_model(topic="AI")  # BaseModel instance
final = graph.invoke(initial)       # Returns dict, not BaseModel!

# Access as dict
print(final["article"])  # NOT final.article
```

### Gotcha: Tool Binding Order

```python
# Tools MUST be bound BEFORE .with_structured_output()
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite")

# CORRECT order
llm_with_tools = llm.bind_tools(tools)
llm_structured = llm_with_tools.with_structured_output(schema)

# WRONG order (AttributeError)
llm_structured = llm.with_structured_output(schema)
llm_with_tools = llm_structured.bind_tools(tools)  # ❌ Error!
```

---

## 🎯 Quick Commands (Copy-Paste Ready)

```bash
# Run tests
pytest tests/ --ignore=tests/integration/  # Unit only (fast)
pytest tests/integration/ -v                # Integration only (slow, $$)
pytest -v                                   # All tests

# Run workflow
configurable-agents run examples/article_writer.yaml --input topic="AI"
configurable-agents validate examples/article_writer.yaml

# Check code
ruff check src/                             # Linting
mypy src/                                   # Type checking (when added)

# Documentation
grep "TODO" -r src/                         # Find TODOs
grep "FIXME" -r src/                        # Find FIXMEs

# Git
git log --oneline -10                       # Recent commits
git diff main                               # Changes since main
```

---

## 📌 Key Files Reference

### Most Frequently Modified

- `src/configurable_agents/runtime/executor.py` - Workflow execution orchestration
- `src/configurable_agents/config/schema.py` - Pydantic models for config
- `tests/runtime/test_executor.py` - Runtime tests
- `docs/TASKS.md` - Task status tracking
- `docs/CONTEXT.md` - This file (update after every task)

### Key Entry Points

- `src/configurable_agents/runtime/executor.py:run_workflow()` - Main execution function
- `src/configurable_agents/cli.py:main()` - CLI entry point
- `src/configurable_agents/config/validator.py:validate_config()` - Validation logic

### Configuration

- `pyproject.toml` - Dependencies, project metadata
- `.env.example` - Required environment variables (GOOGLE_API_KEY, SERPER_API_KEY)
- `pytest.ini` - Test configuration

---

## 🔗 Implementation Logs Quick Reference

### Phase 1 (Foundation) - Complete

- `implementation_logs/phase_1_foundation/T-001_project_setup.md`
- `implementation_logs/phase_1_foundation/T-002_config_parser.md`
- `implementation_logs/phase_1_foundation/T-003_config_schema.md`
- `implementation_logs/phase_1_foundation/T-004_config_validator.md`
- `implementation_logs/phase_1_foundation/T-004.5_runtime_feature_gating.md`
- `implementation_logs/phase_1_foundation/T-005_type_system.md`
- `implementation_logs/phase_1_foundation/T-006_state_schema_builder.md`
- `implementation_logs/phase_1_foundation/T-007_output_schema_builder.md`

### Phase 2 (Core Execution) - Complete

- `implementation_logs/phase_2_core_execution/T-008_tool_registry.md`
- `implementation_logs/phase_2_core_execution/T-009_llm_provider.md`
- `implementation_logs/phase_2_core_execution/T-010_prompt_template_resolver.md`
- `implementation_logs/phase_2_core_execution/T-011_node_executor.md`
- `implementation_logs/phase_2_core_execution/T-012_graph_builder.md`
- `implementation_logs/phase_2_core_execution/T-013_runtime_executor.md`

### Phase 3 (Polish & UX) - Complete

- `implementation_logs/phase_3_polish_ux/T-014_cli_interface.md`
- `implementation_logs/phase_3_polish_ux/T-015_example_configs.md`
- `implementation_logs/phase_3_polish_ux/T-016_documentation.md`
- `implementation_logs/phase_3_polish_ux/T-017_integration_tests.md`

### Phase 4 (Observability & Docker) - Next

- `implementation_logs/phase_4_observability_docker/T-018_mlflow_integration_foundation.md` (create after completion)

---

*Last Updated: 2026-01-31 | Next Update: After T-018 completion*
