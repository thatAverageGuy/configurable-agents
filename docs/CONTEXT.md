# Development Context

> **Purpose**: Quick context for resuming development. Updated after each task completion.
>
> **For LLMs**: Read this first to understand current state, next action, and project standards.
> Fetch details from linked docs as needed during implementation.

---

## ⚠️ CRITICAL: Post-Task Documentation Updates

**MANDATORY**: After completing ANY task, you MUST update ALL relevant documentation. This is non-negotiable.

**Minimum Required Updates** (4-6 files):
1. **TASKS.md**: Mark task as DONE ✅, update progress percentage, update "Last Updated" date
2. **CONTEXT.md** (this file): Update "Latest Completion", "Next Action", "Current State", progress stats
3. **CHANGELOG.md**: Add entry to `[Unreleased]` section with key features (5-10 lines)
4. **README.md**: Update progress badges, test counts, roadmap table, "Next up" section
5. **Implementation log**: Create `docs/implementation_logs/phase_X/T-XXX_task_name.md` with comprehensive details
6. **Commit message**: Use format "T-XXX: Task description with Co-Authored-By"

**Search and Update** (if applicable):
- **SPEC.md**: If config schema, pricing, or specifications changed
- **ADRs**: Update "Current State" or "Implementation Planning" sections in relevant ADRs
- **Module files**: Update supported models, pricing tables, or feature lists
- **User docs**: QUICKSTART.md, CONFIG_REFERENCE.md, TROUBLESHOOTING.md if user-visible changes
- **ARCHITECTURE.md**: If system design or components changed

**Search Strategy**:
1. Grep for old values (e.g., test counts, percentages, "Next up")
2. Check related ADRs for sections that reference your task
3. Verify all cross-references are updated
4. Use "Find All" to catch missed occurrences

**Why This Matters**:
- Documentation is the source of truth for the project
- Outdated docs lead to confusion and wasted time
- Progress tracking depends on accurate updates
- Implementation logs preserve critical context

**If you skip documentation updates, the task is NOT complete!**

---

**Last Updated**: 2026-02-01
**Current Phase**: Phase 4 (Observability & Docker Deployment)
**Latest Completion**: T-023 (FastAPI Server with Sync/Async) - 2026-02-01
**Next Action**: T-024 (CLI Deploy Command & Streamlit Integration)

---

## 🎯 Current State (What's Done, What Works)

### Progress Overview

- **Overall**: 23/27 tasks complete (85%)
- **Phase 1** (Foundation): ✅ 8/8 complete
- **Phase 2** (Core Execution): ✅ 6/6 complete
- **Phase 3** (Polish & UX): ✅ 4/4 complete
- **Phase 4** (Observability): ✅ 4/4 complete
- **Phase 4** (Docker Deployment): 2/3 complete
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
- ✅ MLFlow observability foundation (cost tracking, workflow metrics)
- ✅ Automatic node-level tracking (token extraction, prompt/response logging)
- ✅ Cost reporting utilities with CLI commands (JSON/CSV export)
- ✅ Docker artifact generation (Dockerfile, FastAPI server, docker-compose, etc.)
- ✅ FastAPI server with input validation and MLFlow integration
- ✅ 616 unit tests passing (100% pass rate)
- ✅ Complete user documentation

**What Doesn't Work Yet**:
- ❌ Docker deployment CLI command (T-024)
- ❌ Conditional routing (v0.2+)
- ❌ Multi-LLM support (v0.2+)

### Latest Completion: T-023 (FastAPI Server with Sync/Async)

**Completed**: 2026-02-01
**What**: Enhanced FastAPI server template with input validation and MLFlow integration, plus comprehensive test coverage
**Impact**:
- Deployed workflows now validate all inputs automatically (clear 422 errors for invalid data)
- Optional MLFlow tracking for production observability
- Comprehensive test coverage ensures template correctness
- Users get type-safe APIs with OpenAPI documentation

**Key Features**:
- **Input Validation**: Dynamic Pydantic model generation from workflow schema
- **MLFlow Integration**: Conditional tracking based on `MLFLOW_TRACKING_URI` env var
- **Test Suite**: 35 tests (30 unit + 5 integration) - all passing
- **Graceful Degradation**: MLFlow errors don't crash server

**Enhancements**:
- `_build_input_model()` - generates WorkflowInput Pydantic model from state schema
- Type mapping (str, int, float, bool, list, dict) to Python types
- Required/optional field handling with defaults
- MLFlow logging for sync and async executions (params, metrics, errors)
- POST /run validates inputs against schema before execution

**Files Modified**: 1 (server.py.template: 223 → 320 lines)
**Files Created**: 2 test files (328 + 209 lines)
**Tests Added**: 35 (30 unit + 5 integration) - Total: 603 tests passing

**Implementation Log**: `implementation_logs/phase_4_observability_docker/T-023_fastapi_server_sync_async.md`

---

## 📋 Next Action (Start Here!)

### Task: T-024 - CLI Deploy Command & Streamlit Integration

**Goal**: Implement `deploy` CLI command for one-command Docker deployment

**Acceptance Criteria**:
1. CLI `deploy` command in `src/configurable_agents/cli.py`:
   - Arguments: workflow_path, --port, --mlflow-port, --output, --name, --timeout, --generate, --no-mlflow, --env-file, --no-env-file
   - Step 1: Validate workflow (fail-fast)
   - Step 2: Check Docker installed (`docker version`, fail-fast)
   - Step 3: Generate artifacts (call T-022 generator)
   - Step 4: Build Docker image (`docker build`)
   - Step 5: Run container (`docker-compose up -d`)
   - Step 6: Print success message with API URL
2. Generate artifacts only (--generate flag, skip build/run)
3. Error handling:
   - Invalid workflow config
   - Docker not installed
   - Port already in use
   - Build failures
4. Unit tests (20 tests)
5. Integration test (1 end-to-end test)

**Dependencies**:
- ✅ T-022 (Docker Artifact Generator) - COMPLETE
- ✅ T-023 (FastAPI Server) - COMPLETE

**Estimated Effort**: 3 days

**Related Documentation**:
- `docs/DEPLOYMENT.md` (Docker deployment guide)
- `docs/adr/ADR-012-docker-deployment.md` (Docker architecture)

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

**CRITICAL RULES**:
⚠️ **NEVER RENAME FILES WITHOUT EXPLICIT PERMISSION** ⚠️
- Do NOT change file case (CONTEXT.md ≠ Context.md)
- Do NOT move files to different directories without asking
- Do NOT rename implementation logs or documentation files
- If unsure, ASK FIRST before making any file naming changes

**MUST UPDATE** (minimum 4 files, possibly more):
1. **TASKS.md**: Change task status to DONE, update progress percentage, update "Last Updated" date
2. **CONTEXT.md** (this file): Update "Latest Completion", "Next Action", "Current State", "What Works Now"
3. **CHANGELOG.md**: Add entry to `[Unreleased]` section (5-10 lines with key features)
4. **README.md**: Update progress badges, test counts, roadmap table, "Next up" section
5. **Implementation log**: Create `docs/implementation_logs/phase_X/T-XXX_task_name.md` with comprehensive details

**MUST SEARCH AND UPDATE** (if applicable):
After completing core updates above, SEARCH for and update:
- **SPEC.md**: If config schema, pricing, or specifications changed
- **ADRs**: Update "Current State" section in relevant ADRs (e.g., ADR-011 for observability)
- **Module files**: Update supported models, pricing tables, or feature lists (e.g., `google.py`)
- **User docs**: QUICKSTART.md, CONFIG_REFERENCE.md, TROUBLESHOOTING.md if user-visible changes
- **ARCHITECTURE.md**: If system design or components changed

**Search Strategy**:
1. Grep for old values (e.g., task counts, test counts, percentages)
2. Check related ADRs for "Current State" or "Implementation Planning" sections
3. Check SPEC.md for schema/pricing that might reference your changes
4. Verify all cross-references are updated

**NEW ADR** (if CHANGE LEVEL 3):
- Create new ADR for structural/architectural changes
- Update ARCHITECTURE.md to reference new ADR

### File Naming Conventions

⚠️ **CRITICAL: DO NOT RENAME EXISTING FILES WITHOUT EXPLICIT PERMISSION** ⚠️
- Existing documentation files use specific naming conventions
- Case matters: `CONTEXT.md` ≠ `Context.md` (different files on case-sensitive systems)
- Locations matter: `docs/implementation_logs/` ≠ `implementation_logs/`
- **ALWAYS ASK before renaming or moving ANY file**
- When creating NEW files, follow conventions below

**Source Code**:
- Modules: `snake_case.py` (e.g., `mlflow_tracker.py`)
- Classes: `PascalCase` (e.g., `MLFlowCallback`)
- Functions: `snake_case` (e.g., `estimate_cost`)

**Tests**:
- Test files: `test_<module_name>.py` (e.g., `test_mlflow_tracker.py`)
- Test functions: `test_<scenario>` (e.g., `test_mlflow_callback_logs_metrics`)
- Integration tests: `tests/integration/test_*.py` with `@pytest.mark.integration`

**Documentation** (for NEW files only):
- Core docs: `SCREAMING_SNAKE.md` in `docs/` (e.g., `ARCHITECTURE.md`, `CONTEXT.md`, `TASKS.md`)
- Implementation logs: `T-XXX_task_name.md` in `docs/implementation_logs/phase_X/` (e.g., `T-018_mlflow_integration_foundation.md`)
- ADRs: `ADR-NNN-title.md` in `docs/adr/` (e.g., `ADR-011-mlflow-observability.md`)

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

*Last Updated: 2026-02-01 | Next Update: After T-024 completion*
