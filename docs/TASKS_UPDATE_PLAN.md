# TASKS.md Update Plan

**Date**: 2026-01-30
**Purpose**: Add Observability (T-018 to T-021) and Docker Deployment (T-022 to T-024) tasks

---

## Changes Summary

### Task Renumbering
- **OLD T-018** (Error Messages) → **NEW T-025**
- **OLD T-019** (DSPy Integration) → **NEW T-026**
- **OLD T-020** (DSPy Structured Output) → **NEW T-027**

### New Tasks (Inserted)
- **NEW T-018**: MLFlow Integration Foundation
- **NEW T-019**: MLFlow Instrumentation (Runtime & Nodes)
- **NEW T-020**: Cost Tracking & Reporting
- **NEW T-021**: Observability Documentation
- **NEW T-022**: Docker Artifact Generator & Templates
- **NEW T-023**: FastAPI Server with Sync/Async
- **NEW T-024**: CLI Deploy Command & Streamlit Integration

### Phase Changes
- **Phase 3** renamed: "Polish & UX" → "Polish & Production Readiness"
- **Phase 3** now includes: Observability (4 tasks) + Docker (3 tasks) + existing polish tasks
- **Phase 4** renamed: "DSPy Verification" → "Deferred Tasks"

---

## Detailed New Tasks

### T-018: MLFlow Integration Foundation
**Status**: TODO
**Priority**: P0
**Dependencies**: T-001 (Setup)
**Estimated Effort**: 2 days

**Description**:
Add MLFlow observability foundation - config schema, dependency installation, basic setup.

**Acceptance Criteria**:
- [ ] Add `mlflow` to dependencies (pyproject.toml)
- [ ] Extend config schema with `ObservabilityConfig` and `MLFlowConfig`
  - `enabled`: bool (default: False)
  - `tracking_uri`: str (default: "file://./mlruns")
  - `experiment_name`: str (default: "configurable_agents")
  - `run_name`: Optional[str] (template support)
  - `log_artifacts`: bool (default: True)
  - Enterprise hooks: `retention_days`, `redact_pii` (not enforced)
- [ ] Validate observability config in validator
- [ ] Create `src/configurable_agents/observability/` package
- [ ] Create `src/configurable_agents/observability/mlflow_tracker.py` (setup utilities)
- [ ] Unit tests for config schema extensions (12 tests)
- [ ] Unit tests for MLFlow initialization (8 tests)
- [ ] Document config schema in SPEC.md

**Files Created**:
- `src/configurable_agents/observability/__init__.py`
- `src/configurable_agents/observability/mlflow_tracker.py`
- `tests/observability/__init__.py`
- `tests/observability/test_mlflow_config.py`
- `tests/observability/test_mlflow_tracker.py`

**Files Modified**:
- `src/configurable_agents/config/schema.py` (add ObservabilityConfig)
- `src/configurable_agents/config/validator.py` (validate observability config)
- `pyproject.toml` (add mlflow dependency)
- `docs/SPEC.md` (document observability config)

**Tests**: 20 tests (12 config + 8 tracker)

**Interface**:
```python
from configurable_agents.observability import init_mlflow, is_mlflow_enabled

# Initialize MLFlow if enabled
if config.observability and config.observability.mlflow:
    init_mlflow(config.observability.mlflow)

# Check if active
if is_mlflow_enabled():
    # Log metrics
    pass
```

**Related ADRs**: ADR-011 (MLFlow Observability)

---

### T-019: MLFlow Instrumentation (Runtime & Nodes)
**Status**: TODO
**Priority**: P0
**Dependencies**: T-018, T-013 (Runtime Executor)
**Estimated Effort**: 3 days

**Description**:
Instrument runtime executor and node executor to log params, metrics, and artifacts to MLFlow.

**Acceptance Criteria**:
- [ ] Workflow-level tracking in `runtime/executor.py`:
  - [ ] Start MLFlow run on workflow start
  - [ ] Log params: workflow_name, version, schema_version, global_model, global_temperature
  - [ ] Log metrics: duration_seconds, total_input_tokens, total_output_tokens, node_count, retry_count, status (1=success, 0=failure)
  - [ ] Log artifacts: inputs.json, outputs.json, error.txt (if failed)
  - [ ] End run on workflow completion
- [ ] Node-level tracking in `core/node_executor.py`:
  - [ ] Start nested run per node
  - [ ] Log params: node_id, node_model, tools
  - [ ] Log metrics: node_duration_ms, input_tokens, output_tokens, retries
  - [ ] Log artifacts: prompt.txt, response.txt
  - [ ] End nested run
- [ ] Handle MLFlow disabled gracefully (no-op if not enabled)
- [ ] Token tracking from LLM responses
- [ ] Error tracking (exception details)
- [ ] Unit tests (mocked MLFlow, 25 tests)
- [ ] Integration test with real MLFlow (1 slow test)

**Files Modified**:
- `src/configurable_agents/runtime/executor.py` (workflow-level tracking)
- `src/configurable_agents/core/node_executor.py` (node-level tracking)

**Files Created**:
- `tests/observability/test_mlflow_instrumentation.py` (25 unit tests)
- `tests/observability/test_mlflow_integration.py` (1 integration test)

**Tests**: 26 tests (25 unit + 1 integration)

**Example**:
```python
# Workflow-level
with mlflow.start_run(run_name=config.observability.mlflow.run_name):
    mlflow.log_param("workflow_name", config.flow.name)
    mlflow.log_metric("duration_seconds", duration)
    mlflow.log_dict(inputs, "inputs.json")

    # Node-level (nested)
    with mlflow.start_run(run_name=f"node_{node_id}", nested=True):
        mlflow.log_metric("node_duration_ms", node_duration)
        mlflow.log_text(prompt, "prompt.txt")
```

**Related ADRs**: ADR-011

---

### T-020: Cost Tracking & Reporting
**Status**: TODO
**Priority**: P1
**Dependencies**: T-019
**Estimated Effort**: 2 days

**Description**:
Implement token-to-cost calculation and cost tracking in MLFlow.

**Acceptance Criteria**:
- [ ] Create `llm/cost_tracker.py` with pricing tables:
  - `PRICING` dict with model → {input, output} $/1K tokens
  - Support: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-lite
  - Placeholder for future: OpenAI, Anthropic, etc.
- [ ] `calculate_cost(model, input_tokens, output_tokens)` function
- [ ] Log cost metrics in MLFlow:
  - `cost_usd` (per run, cumulative)
  - `cost_per_node_avg` (average cost per node)
- [ ] Create example cost reporting notebook:
  - Query MLFlow API for all runs
  - Aggregate costs (total, per workflow, per model)
  - Export to CSV
  - Visualize trends (matplotlib/seaborn)
- [ ] Unit tests for cost calculation (15 tests)
- [ ] Integration test with MLFlow (1 test)
- [ ] Document pricing tables in OBSERVABILITY.md

**Files Created**:
- `src/configurable_agents/llm/cost_tracker.py`
- `examples/notebooks/cost_report.ipynb` (Jupyter notebook)
- `tests/llm/test_cost_tracker.py`

**Files Modified**:
- `src/configurable_agents/core/node_executor.py` (log costs)
- `src/configurable_agents/runtime/executor.py` (aggregate costs)

**Tests**: 16 tests (15 unit + 1 integration)

**Interface**:
```python
from configurable_agents.llm import calculate_cost

cost = calculate_cost("gemini-1.5-flash", input_tokens=150, output_tokens=500)
# Returns: 0.000075 (USD)

mlflow.log_metric("cost_usd", cost)
```

**Related ADRs**: ADR-011

---

### T-021: Observability Documentation
**Status**: TODO
**Priority**: P1
**Dependencies**: T-018, T-019, T-020
**Estimated Effort**: 2 days

**Description**:
Comprehensive observability documentation covering MLFlow usage, setup, and future roadmap.

**Acceptance Criteria**:
- [ ] Create `docs/OBSERVABILITY.md`:
  - [ ] Overview (why observability matters)
  - [ ] MLFlow quick start (install, enable, view UI)
  - [ ] Configuration reference (all options explained)
  - [ ] What gets tracked (workflow-level, node-level, costs)
  - [ ] Docker integration (MLFlow UI in container)
  - [ ] Cost tracking guide (query API, export CSV)
  - [ ] DSPy integration (future, v0.3+)
  - [ ] Enterprise features (retention, PII redaction, multi-tenancy)
  - [ ] OpenTelemetry integration (future, v0.2+) - detailed guide
  - [ ] Prometheus integration (future, v0.3+) - detailed guide
  - [ ] Comparison matrix (MLFlow vs OTEL vs Prometheus)
  - [ ] Best practices (when to use what)
  - [ ] Troubleshooting
- [ ] Create example workflow with MLFlow enabled:
  - `examples/article_writer_mlflow.yaml`
- [ ] Update `docs/CONFIG_REFERENCE.md` (add observability section)
- [ ] Update `docs/QUICKSTART.md` (mention observability)
- [ ] Update `README.md` (add observability features)

**Files Created**:
- `docs/OBSERVABILITY.md` (comprehensive guide, ~800 lines)
- `examples/article_writer_mlflow.yaml`

**Files Modified**:
- `docs/CONFIG_REFERENCE.md`
- `docs/QUICKSTART.md`
- `README.md`

**Related ADRs**: ADR-011, ADR-014

---

### T-022: Docker Artifact Generator & Templates
**Status**: TODO
**Priority**: P0
**Dependencies**: T-013 (Runtime Executor), T-021 (Observability)
**Estimated Effort**: 2 days

**Description**:
Implement artifact generation for Docker deployment - Dockerfile, FastAPI server, requirements, etc.

**Acceptance Criteria**:
- [ ] Create `src/configurable_agents/deploy/` package
- [ ] Create `src/configurable_agents/deploy/generator.py`:
  - [ ] `generate_deployment_artifacts(config, output_dir, timeout, enable_mlflow, mlflow_port)`
  - [ ] Template engine (Jinja2 or string.Template)
  - [ ] Variable substitution (workflow_name, ports, timeout)
- [ ] Create `src/configurable_agents/deploy/templates/` directory:
  - [ ] `Dockerfile.template` (multi-stage, optimized)
  - [ ] `server.py.template` (FastAPI with sync/async)
  - [ ] `requirements.txt.template` (minimal runtime deps)
  - [ ] `docker-compose.yml.template`
  - [ ] `.env.example.template`
  - [ ] `README.md.template`
  - [ ] `.dockerignore`
- [ ] Dockerfile optimizations:
  - [ ] Multi-stage build (builder + runtime)
  - [ ] `python:3.10-slim` base image
  - [ ] `--no-cache-dir` for pip
  - [ ] Health check
  - [ ] MLFlow UI startup (if enabled)
- [ ] Unit tests (artifact generation, 20 tests)
- [ ] Integration test (generate → validate files exist, 3 tests)

**Files Created**:
- `src/configurable_agents/deploy/__init__.py`
- `src/configurable_agents/deploy/generator.py`
- `src/configurable_agents/deploy/templates/Dockerfile.template`
- `src/configurable_agents/deploy/templates/server.py.template`
- `src/configurable_agents/deploy/templates/requirements.txt.template`
- `src/configurable_agents/deploy/templates/docker-compose.yml.template`
- `src/configurable_agents/deploy/templates/.env.example.template`
- `src/configurable_agents/deploy/templates/README.md.template`
- `src/configurable_agents/deploy/templates/.dockerignore`
- `tests/deploy/__init__.py`
- `tests/deploy/test_generator.py`

**Tests**: 23 tests (20 unit + 3 integration)

**Interface**:
```python
from configurable_agents.deploy import generate_deployment_artifacts

generate_deployment_artifacts(
    config=workflow_config,
    output_dir=Path("./deploy"),
    timeout=30,
    enable_mlflow=True,
    mlflow_port=5000
)
# Generates: Dockerfile, server.py, requirements.txt, etc.
```

**Related ADRs**: ADR-012, ADR-013

---

### T-023: FastAPI Server with Sync/Async
**Status**: TODO
**Priority**: P0
**Dependencies**: T-022
**Estimated Effort**: 3 days

**Description**:
Create FastAPI server template with sync/async hybrid execution, job store, and MLFlow integration.

**Acceptance Criteria**:
- [ ] FastAPI server template (`server.py.template`):
  - [ ] Endpoints: POST /run, GET /status/{job_id}, GET /health, GET /schema, GET /
  - [ ] Sync/async hybrid logic (timeout-based fallback)
  - [ ] Job store (in-memory dict for v0.1)
  - [ ] Input validation (against workflow schema)
  - [ ] OpenAPI auto-docs (FastAPI built-in)
  - [ ] MLFlow integration (logging within container)
  - [ ] Error handling (ValidationError, ExecutionError, etc.)
  - [ ] Background task execution (FastAPI BackgroundTasks)
- [ ] Sync execution (if < timeout):
  - [ ] Use `asyncio.wait_for()` with timeout
  - [ ] Return outputs immediately (200 OK)
- [ ] Async execution (if > timeout):
  - [ ] Generate job_id (UUID)
  - [ ] Store job metadata (status, created_at, inputs)
  - [ ] Run in background task
  - [ ] Return job_id (202 Accepted)
- [ ] Job status endpoint:
  - [ ] Query job store by job_id
  - [ ] Return status: pending, running, completed, failed
  - [ ] Include outputs (if completed) or error (if failed)
- [ ] Health check endpoint (for orchestration)
- [ ] Schema introspection endpoint (returns input/output schema)
- [ ] Unit tests (mocked workflow execution, 30 tests)
- [ ] Integration test (real FastAPI server, 5 tests)

**Files Modified**:
- `src/configurable_agents/deploy/templates/server.py.template`

**Files Created**:
- `tests/deploy/test_server_template.py` (30 unit tests)
- `tests/deploy/test_server_integration.py` (5 integration tests)

**Tests**: 35 tests (30 unit + 5 integration)

**API Example**:
```bash
# Sync execution (<30s)
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI"}'
→ 200 OK {"status": "success", "execution_time_ms": 2340, "outputs": {...}}

# Async execution (>30s)
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"topic": "Write 50-page report"}'
→ 202 Accepted {"status": "async", "job_id": "abc-123", "message": "..."}

# Poll status
curl http://localhost:8000/status/abc-123
→ 200 OK {"status": "completed", "outputs": {...}}
```

**Related ADRs**: ADR-012

---

### T-024: CLI Deploy Command & Streamlit Integration
**Status**: TODO
**Priority**: P0
**Dependencies**: T-022, T-023
**Estimated Effort**: 3 days

**Description**:
Implement `deploy` CLI command and integrate with Streamlit UI for Docker deployment.

**Acceptance Criteria**:
- [ ] CLI `deploy` command in `src/configurable_agents/cli.py`:
  - [ ] Arguments: workflow_path, --port, --mlflow-port, --output, --name, --timeout, --generate, --no-mlflow, --env-file, --no-env-file
  - [ ] Step 1: Validate workflow (fail-fast)
  - [ ] Step 2: Check Docker installed (`docker version`, fail-fast)
  - [ ] Step 3: Generate artifacts (call T-022 generator)
  - [ ] Step 4: If --generate, exit (artifacts only)
  - [ ] Step 5: Build Docker image (`docker build`)
  - [ ] Step 6: Run container detached (`docker run -d`)
  - [ ] Step 7: Print success message (endpoints, curl examples, management commands)
- [ ] Environment variable handling:
  - [ ] Auto-detect `.env` in current directory
  - [ ] Custom path via `--env-file`
  - [ ] Skip with `--no-env-file`
  - [ ] Validate env file format (KEY=value)
- [ ] Streamlit integration (`streamlit_app.py`):
  - [ ] Add "Deploy to Docker" section
  - [ ] Environment variable upload/paste/skip options
  - [ ] Port configuration (API, MLFlow)
  - [ ] Container name input
  - [ ] Deploy button (executes CLI command)
  - [ ] Real-time logs (subprocess output)
  - [ ] Success message (show endpoints, curl examples)
  - [ ] Container management (list, stop, remove buttons)
- [ ] Unit tests (CLI deploy command, 25 tests)
- [ ] Integration tests (full deploy flow, 3 slow tests)

**Files Modified**:
- `src/configurable_agents/cli.py` (add deploy command)
- `streamlit_app.py` (add deploy section)

**Files Created**:
- `tests/test_cli_deploy.py` (25 unit tests)
- `tests/test_deploy_integration.py` (3 integration tests)

**Tests**: 28 tests (25 unit + 3 integration)

**CLI Usage**:
```bash
# Simple deployment
configurable-agents deploy workflow.yaml

# With options
configurable-agents deploy workflow.yaml \
  --port 8000 \
  --mlflow-port 5000 \
  --name my-workflow \
  --timeout 30 \
  --env-file .env

# Generate artifacts only
configurable-agents deploy workflow.yaml --generate --output ./my-deploy
```

**Streamlit UI**:
- Radio: Upload .env / Paste variables / Skip
- Number inputs: API port, MLFlow port
- Text input: Container name
- Button: "Build & Deploy"
- Buttons: List Containers, Stop, Remove

**Related ADRs**: ADR-012, ADR-013

---

## Progress Tracker Updates

### Old (Before Changes)
```
v0.1 Progress: 17/20 tasks complete (85%)

Phase 3: Polish & UX (2/5 complete)
- ✅ T-014: CLI
- ✅ T-015: Examples
- ⏳ T-016: Documentation
- ⏳ T-017: Integration Tests
- ⏳ T-018: Error Messages

Phase 4: DSPy Verification (0/2 complete)
- ⏳ T-019: DSPy Integration Test
- ⏳ T-020: Structured Output + DSPy Test
```

### New (After Changes)
```
v0.1 Progress: 18/27 tasks complete (67%)

Phase 3: Polish & Production Readiness (4/11 complete)
- ✅ T-014: CLI
- ✅ T-015: Examples
- ✅ T-016: Documentation
- ✅ T-017: Integration Tests
- ⏳ T-018: MLFlow Integration Foundation
- ⏳ T-019: MLFlow Instrumentation (Runtime & Nodes)
- ⏳ T-020: Cost Tracking & Reporting
- ⏳ T-021: Observability Documentation
- ⏳ T-022: Docker Artifact Generator & Templates
- ⏳ T-023: FastAPI Server with Sync/Async
- ⏳ T-024: CLI Deploy Command & Streamlit Integration

Phase 4: Deferred Tasks (0/3 complete)
- ⏳ T-025: Error Message Improvements (was T-018)
- ⏳ T-026: DSPy Integration Test (was T-019)
- ⏳ T-027: Structured Output + DSPy Test (was T-020)
```

---

## Task Dependencies (Updated)

```
Phase 3 Dependencies:

Observability (Sequential):
T-018 (MLFlow Foundation)
  ↓
T-019 (Instrumentation) [also depends on T-013 Runtime]
  ↓
T-020 (Cost Tracking)
  ↓
T-021 (Docs)

Docker Deployment (Sequential):
T-022 (Artifact Generator) [depends on T-013 Runtime, T-021 Observability]
  ↓
T-023 (FastAPI Server)
  ↓
T-024 (CLI + Streamlit) [depends on T-022, T-023]

Deferred (No dependencies):
T-025 (Error Messages) [depends on T-004, T-013]
T-026 (DSPy Integration) [depends on T-009, T-011]
T-027 (DSPy + Structured Output) [depends on T-026]
```

---

## Timeline Estimates (Updated)

### Phase 3: Polish & Production Readiness (11 tasks)

**Observability** (4 tasks):
- T-018: MLFlow Foundation (2 days)
- T-019: MLFlow Instrumentation (3 days)
- T-020: Cost Tracking (2 days)
- T-021: Observability Docs (2 days)
- **Subtotal**: 9 days (~2 weeks)

**Docker Deployment** (3 tasks):
- T-022: Artifact Generator (2 days)
- T-023: FastAPI Server (3 days)
- T-024: CLI + Streamlit (3 days)
- **Subtotal**: 8 days (~1.5 weeks)

**Phase 3 Total**: 17 days (~3.5 weeks)

### Phase 4: Deferred Tasks (3 tasks)
- T-025: Error Messages (1 week) - **Deferred to v0.2**
- T-026: DSPy Integration Test (1 week) - **Deferred to v0.3**
- T-027: DSPy + Structured Output (3-4 days) - **Deferred to v0.3**

---

## v0.1 Release Criteria (Updated)

**Must Complete** (23 tasks):
- ✅ Phase 1: Foundation (8/8)
- ✅ Phase 2: Core Execution (6/6)
- ⏳ Phase 3: Polish & Production (4/11) - **7 remaining**
  - ✅ T-014, T-015, T-016, T-017 (done)
  - ⏳ T-018, T-019, T-020, T-021 (Observability)
  - ⏳ T-022, T-023, T-024 (Docker)

**Deferred to v0.2+** (4 tasks):
- T-025: Error Message Improvements
- T-026: DSPy Integration Test
- T-027: DSPy + Structured Output Test

**New v0.1 Scope**: 23 tasks (was 20)
**Rationale**: Observability and Docker deployment are production-essential features for first public release.

---

## Documentation Updates Needed

1. **TASKS.md** (this file):
   - Insert T-018 to T-024 (new tasks)
   - Renumber T-018 → T-025, T-019 → T-026, T-020 → T-027
   - Update Phase 3 description
   - Update Progress Tracker
   - Update Timeline Estimates

2. **ROADMAP.md**:
   - Update v0.1 features (add Observability + Docker)
   - Update timeline (6-8 weeks → 8-10 weeks)
   - Update feature availability matrix
   - Update release checklist

3. **ARCHITECTURE.md**:
   - Add Observability layer (MLFlow integration)
   - Add Deployment architecture (Docker containers)
   - Update system diagram

4. **SPEC.md**:
   - Add observability config schema
   - Document deployment artifacts

5. **CREATE NEW**:
   - `docs/OBSERVABILITY.md` (comprehensive guide)
   - `docs/DEPLOYMENT.md` (deployment guide)

6. **README.md**:
   - Add Observability features section
   - Add Docker Deployment section
   - Update progress tracker

---

## Review Checklist

Before making changes to TASKS.md, verify:
- [ ] All task numbers correctly renumbered (T-018 old → T-025 new)
- [ ] All new tasks (T-018 to T-024) have complete acceptance criteria
- [ ] Dependencies are correct (no circular dependencies)
- [ ] Progress tracker reflects new totals (18/27 = 67%)
- [ ] Timeline estimates are realistic (3.5 weeks for Phase 3)
- [ ] No tasks orphaned or duplicated
- [ ] Related ADRs referenced (ADR-011, ADR-012, ADR-013, ADR-014)

---

**Status**: Ready for review and implementation
**Next Step**: Get approval, then systematically update all docs
