# Remaining Documentation Updates

**Date**: 2026-01-30
**Status**: In Progress

---

## Completed ✅

1. ✅ **ADRs Created** (4 files):
   - ADR-011: MLFlow for Observability
   - ADR-012: Docker Deployment Architecture
   - ADR-013: Environment Variable Handling
   - ADR-014: Three-Tier Observability Strategy

2. ✅ **TASKS.md Updated**:
   - Inserted T-018 to T-024 (7 new tasks with full acceptance criteria)
   - Renamed old T-018 → T-025, T-019 → T-026, T-020 → T-027
   - Updated Progress Tracker (18/27 tasks, 67%)
   - Updated Task Dependencies
   - Updated Work Estimates
   - Updated Notes section

3. ✅ **ROADMAP.md Updated**:
   - Updated Version Overview table
   - Added observability + Docker to v0.1
   - Updated status (67% complete, 18/27 tasks)
   - Added "What's Coming Next" section
   - Updated Core Features (added MLFlow & Docker sections)
   - Updated Limitations
   - Updated Remaining Work (7 tasks listed)
   - Updated Feature Availability Matrix
   - Updated Timeline Summary
   - Updated Release Criteria checklist

---

## Remaining (To Complete) ⏳

### 3. ARCHITECTURE.md Updates Needed
**File**: `docs/ARCHITECTURE.md`

**Add new sections**:
- After Component Architecture, add "Observability Layer (MLFlow)"
- Add "Deployment Architecture (Docker Containers)"
- Update System Overview diagram to include observability

**Content to add**:
```markdown
### 8. Observability Layer (MLFlow) - v0.1

**Responsibility**: Track workflow execution, costs, and performance

**Architecture**:
- MLFlow tracking (file-based or remote)
- Workflow-level metrics (duration, tokens, cost)
- Node-level nested runs (prompts, responses)
- Artifacts storage (inputs, outputs, errors)

**Integration Points**:
- Runtime Executor: Start/end workflow runs
- Node Executor: Log per-node metrics
- LLM Provider: Extract token counts

### 9. Deployment Architecture (Docker) - v0.1

**Responsibility**: Package workflows as standalone containers

**Architecture**:
- Artifact Generator: Creates Dockerfile, FastAPI server, requirements
- Multi-stage Docker build (optimized <200MB)
- FastAPI server with sync/async execution
- MLFlow UI embedded in container (port 5000)
- Environment variable injection (secrets management)

**Flow**:
CLI deploy command → Generate artifacts → Build image → Run container (detached)
```

---

### 4. SPEC.md Updates Needed
**File**: `docs/SPEC.md`

**Add new section** (after existing config sections):
```markdown
## Observability Configuration

### ObservabilityConfig

Optional configuration for workflow observability and monitoring.

```yaml
config:
  observability:
    mlflow:
      enabled: true                    # Enable MLFlow tracking (default: false)
      tracking_uri: "file://./mlruns"  # Storage backend
      experiment_name: "my_workflows"  # Experiment grouping
      run_name: null                   # Template for run names (optional)
      log_artifacts: true              # Log inputs/outputs (default: true)

      # Enterprise hooks (not enforced in v0.1)
      retention_days: null             # Auto-cleanup (future)
      redact_pii: false                # PII sanitization (future)
```

**Fields**:
- `enabled` (bool): Enable MLFlow tracking
- `tracking_uri` (str): Backend URI (file://, postgresql://, s3://, databricks://)
- `experiment_name` (str): Group related runs
- `run_name` (str, optional): Custom run naming template
- `log_artifacts` (bool): Whether to save inputs/outputs as artifacts

**Enterprise Hooks** (v0.2+):
- `retention_days`: Automatic cleanup of old runs
- `redact_pii`: Sanitize sensitive data before logging
```

---

### 5. Create docs/OBSERVABILITY.md
**File**: `docs/OBSERVABILITY.md` (NEW, ~800 lines)

**Structure** (based on ADR-011 and ADR-014):
- Overview (why observability matters)
- Quick Start (install, enable, view UI)
- MLFlow Integration (v0.1)
  - Configuration reference
  - What gets tracked
  - Workflow-level metrics
  - Node-level traces
  - Cost tracking
  - Docker integration
- OpenTelemetry Integration (v0.2) - detailed guide
- Prometheus Integration (v0.3) - detailed guide
- Comparison Matrix (MLFlow vs OTEL vs Prometheus)
- Best Practices
- Troubleshooting
- Enterprise Features (retention, PII, multi-tenancy)

**Note**: Already detailed in ADR-011 and ADR-014, needs conversion to user-facing guide.

---

### 6. Create docs/DEPLOYMENT.md
**File**: `docs/DEPLOYMENT.md` (NEW, ~600 lines)

**Structure** (based on ADR-012 and ADR-013):
- Overview (Docker deployment architecture)
- Quick Start
  - `configurable-agents deploy workflow.yaml`
  - Access endpoints
- CLI Command Reference
  - All flags explained
  - Examples
- Generated Artifacts
  - Dockerfile structure
  - FastAPI server
  - docker-compose.yml
- Environment Variables
  - CLI (--env-file)
  - Streamlit UI (upload/paste)
  - Security best practices
- Container Management
  - Start, stop, restart
  - Logs, health checks
  - Updating workflows
- API Reference
  - POST /run (sync/async)
  - GET /status/{job_id}
  - GET /health
  - GET /schema
- Streamlit UI Integration
- Troubleshooting
- Advanced Topics
  - Custom Dockerfile
  - Image optimization
  - Production deployment

**Note**: Already detailed in ADR-012 and ADR-013, needs conversion to user-facing guide.

---

### 7. README.md Updates Needed
**File**: `README.md` (root)

**Updates**:
1. Update status badge: `v0.1.0-dev` → include "67% complete"
2. Add new features section:
   - **Observability**: MLFlow tracking, cost monitoring
   - **Docker Deployment**: One-command containerization
3. Update progress: "17/20 tasks" → "18/27 tasks (67%)"
4. Add quick examples for observability and deployment
5. Update "What's Next" section (T-018 to T-024)

**Example additions**:
```markdown
### 🔍 Observability (v0.1)

Track costs, prompts, and performance:
```yaml
config:
  observability:
    mlflow:
      enabled: true
```

View traces:
```bash
mlflow ui  # http://localhost:5000
```

### 🐳 Docker Deployment (v0.1)

Deploy workflows as microservices:
```bash
configurable-agents deploy workflow.yaml
# → http://localhost:8000 (API)
# → http://localhost:5000 (MLFlow UI)
```
```

---

## Estimated Time to Complete Remaining

- ARCHITECTURE.md: 30 minutes (add 2 sections)
- SPEC.md: 20 minutes (add observability config)
- OBSERVABILITY.md: 2-3 hours (convert ADRs to user guide, ~800 lines)
- DEPLOYMENT.md: 2-3 hours (convert ADRs to user guide, ~600 lines)
- README.md: 20 minutes (update features, progress)

**Total**: ~5-7 hours of focused writing

---

## Notes

- Most content already exists in ADRs (ADR-011, ADR-012, ADR-013, ADR-014)
- Conversion task: Technical ADR → User-facing documentation
- OBSERVABILITY.md and DEPLOYMENT.md are the largest pieces
- Can be done incrementally (ARCHITECTURE, SPEC, README first, then guides)

---

## User Feedback

> "Once the documentation updates are complete, I think we might need to revisit the documentation structures and the number of docs we are maintaining and optimize that."

**Action**: After completing these updates, create a proposal for documentation consolidation/optimization.

---

**Status**: Paused for user review and continuation approval
