# ADR-012: Docker Deployment Architecture

**Status**: Accepted
**Date**: 2026-01-30
**Deciders**: Product team
**Related**: ADR-011 (MLFlow Observability)

---

## Context

Users need to deploy workflows as standalone microservices for:
1. **Production readiness**: Isolated, reproducible deployments
2. **API access**: Call workflows via HTTP (not just CLI)
3. **Horizontal scaling**: Run multiple containers behind load balancer
4. **CI/CD integration**: Docker images fit standard deployment pipelines

Requirements:
- Single CLI command to deploy (`configurable-agents deploy workflow.yaml`)
- Workflow config baked into image (validated at build time, immutable)
- Persistent HTTP server (not one-shot execution)
- Sync/async execution (fast workflows return immediately, slow ones return job_id)
- MLFlow UI included (view traces at `http://localhost:5000`)
- Ultra-optimized image (<200MB target)
- Local-only for v0.1 (cloud deployment in v0.2+)

---

## Decision

**We will generate optimized Docker containers with FastAPI servers for workflow deployment.**

### Architecture Overview

```
User Workflow (workflow.yaml)
         ↓
[configurable-agents deploy] CLI Command
         ↓
Generated Artifacts:
├── Dockerfile (multi-stage, optimized)
├── server.py (FastAPI with sync/async)
├── workflow.yaml (validated, baked in)
├── requirements.txt (minimal runtime deps)
├── docker-compose.yml (optional)
├── .env.example (API keys template)
└── README.md (usage guide)

         ↓
[Auto-build] docker build -t workflow:latest .
         ↓
[Auto-run] docker run -d -p 8000:8000 -p 5000:5000 workflow:latest
         ↓
Running Container:
├── Port 8000: FastAPI server (workflow API)
│   ├── POST /run (sync/async execution)
│   ├── GET /status/{job_id} (async job polling)
│   ├── GET /health (health check)
│   └── GET /schema (input/output schema)
├── Port 5000: MLFlow UI (observability)
└── Volume: /app/mlruns (persistent traces)
```

### Key Design Decisions

#### 1. Persistent Server (Not One-Shot)

**Decision**: Container runs a persistent FastAPI server, not one-shot execution.

**Rationale**:
- Reuse LLM connections (faster, lower latency)
- Support multiple requests without restart
- Standard microservice pattern (fits k8s, ECS, etc.)
- Health checks for orchestration

**Trade-off**: More memory (server overhead) vs one-shot simplicity
- **Accepted**: Persistent is production-ready

#### 2. Sync/Async Hybrid Execution

**Decision**: Workflows attempt sync execution with timeout, fall back to async.

**Behavior**:
- If workflow completes within `SYNC_TIMEOUT` (default: 30s) → return outputs immediately
- If exceeds timeout → return `job_id`, client polls `/status/{job_id}`

**Example**:
```python
# Fast workflow (<30s): Synchronous
POST /run {"topic": "AI"}
→ 200 OK {"status": "success", "outputs": {...}, "execution_time_ms": 2340}

# Slow workflow (>30s): Asynchronous
POST /run {"topic": "Write 50-page report"}
→ 202 Accepted {"status": "async", "job_id": "abc-123", "message": "Poll /status/abc-123"}

GET /status/abc-123
→ 200 OK {"status": "running", ...}
→ 200 OK {"status": "completed", "outputs": {...}}
```

**Rationale**:
- Best of both worlds (simple API for fast workflows, scalable for slow ones)
- No client-side timeout issues (30s HTTP timeout is standard)
- Background task execution (FastAPI `BackgroundTasks`)

**Alternative considered**: Always async (return job_id immediately)
- **Rejected**: Adds complexity for simple/fast workflows

#### 3. Build-on-Demand (Primary) + Artifact Generation (Optional)

**Decision**: `deploy` command validates, builds, and runs by default. `--generate` flag for artifacts only.

**Default behavior**:
```bash
configurable-agents deploy workflow.yaml
# → Validates, builds image, runs container (detached)
```

**Artifacts only**:
```bash
configurable-agents deploy workflow.yaml --generate --output ./my-deploy
# → Generates Dockerfile, server.py, etc. (no build/run)
```

**Rationale**:
- **Build-on-demand**: Fastest path to deployment (one command)
- **Artifact generation**: Allows customization (edit Dockerfile, add auth, etc.)
- Default optimizes for speed (most users want instant deploy)

**Alternative considered**: Generate-only as default
- **Rejected**: Adds friction (users must manually build/run)

#### 4. Always Detached Mode

**Decision**: Containers always run in detached mode (`docker run -d`). No foreground option.

**Rationale**:
- Detached is production standard (background service)
- Foreground mode confusing (CLI would block indefinitely)
- Users can view logs via `docker logs -f` if needed

**Alternative considered**: `--detach` / `--no-detach` flags
- **Rejected**: No use case for foreground mode in deployment context

#### 5. MLFlow UI Included in Container

**Decision**: MLFlow UI runs inside container on port 5000 (unless `--no-mlflow` flag).

**Rationale**:
- Observability accessible even when workflow containerized
- No external dependencies (self-contained)
- Traces persist across container restarts (volume mount)

**Implementation**:
```dockerfile
CMD mlflow ui --host 0.0.0.0 --port 5000 --backend-store-uri file:///app/mlruns & \
    python server.py
```

**Alternative considered**: Separate MLFlow container (docker-compose)
- **Rejected**: Adds complexity for v0.1 (single container simpler)

#### 6. Multi-Stage Dockerfile (Optimization)

**Decision**: Use multi-stage build to minimize image size.

**Dockerfile structure**:
```dockerfile
# Stage 1: Builder (install dependencies)
FROM python:3.10-slim AS builder
RUN pip install --user -r requirements.txt

# Stage 2: Runtime (copy installed packages, no build tools)
FROM python:3.10-slim
COPY --from=builder /root/.local /root/.local
COPY workflow.yaml server.py ./
CMD mlflow ui ... & python server.py
```

**Optimizations**:
- ✅ Remove build tools (gcc, g++) from final image (~50MB savings)
- ✅ `--no-cache-dir` for pip (smaller layers)
- ✅ Minimal base image (`python:3.10-slim` ~120MB vs alpine's compatibility issues)
- ✅ User site-packages (avoids root install)

**Result**: Target image size ~180-200MB (acceptable for v0.1)

**Alternative considered**: Alpine Linux (`python:3.10-alpine`)
- **Rejected**: Compiled dependencies (LangChain, Pydantic) fail on Alpine (musl libc issues)

#### 7. Workflow Baked into Image (Immutable)

**Decision**: Workflow config validated and embedded in image at build time.

**Rationale**:
- ✅ Fail-fast (invalid configs rejected before image built)
- ✅ Immutable deployments (image = specific workflow version)
- ✅ Reproducible (same image → same workflow)
- ✅ No runtime config loading errors

**Alternative considered**: Volume-mounted workflow (mutable)
- **Deferred**: Advanced option for v0.2 (documented but not default)

---

## CLI Command Design

### Primary Command: `deploy`

```bash
configurable-agents deploy workflow.yaml [OPTIONS]

Options:
  --port INT              FastAPI server port (default: 8000)
  --mlflow-port INT       MLFlow UI port (default: 5000, 0 to disable)
  --output DIR            Artifacts output directory (default: ./deploy)
  --name TEXT             Container/image name (default: workflow name)
  --timeout INT           Sync/async threshold in seconds (default: 30)
  --generate              Only generate artifacts (skip build/run)
  --no-mlflow             Disable MLFlow UI in container
  --env-file PATH         Environment variables file (default: .env if exists)
  --no-env-file           Skip env file (configure manually later)
```

### Execution Flow

```
1. Validate workflow (fail-fast)
   └─ Parse YAML → validate schema → check runtime support
2. Check Docker installed (fail-fast)
   └─ Run `docker version` → exit if missing
3. Generate artifacts
   └─ Dockerfile, server.py, requirements.txt, docker-compose.yml, README.md
4. If --generate flag: EXIT (artifacts only)
5. Build Docker image
   └─ docker build -t {name}:latest {output_dir}
6. Run container (detached)
   └─ docker run -d -p {port}:8000 -p {mlflow_port}:5000 --env-file {env_file} {name}
7. Print success message
   └─ Show endpoints, curl examples, management commands
```

---

## FastAPI Server Design

### Endpoints

| Endpoint | Method | Description | Response Time |
|----------|--------|-------------|---------------|
| `/` | GET | API info, links to docs | Instant |
| `/run` | POST | Execute workflow (sync/async) | 0-30s (sync) or instant (async) |
| `/status/{job_id}` | GET | Check async job status | Instant |
| `/health` | GET | Container health check | Instant |
| `/schema` | GET | Workflow input/output schema | Instant |
| `/docs` | GET | OpenAPI interactive docs | Instant |

### Sync/Async Implementation

```python
@app.post("/run", response_model=RunResponse)
async def run_workflow_endpoint(inputs: Dict[str, Any], background_tasks: BackgroundTasks):
    """Execute workflow with sync/async fallback"""
    start_time = time.time()

    try:
        # Attempt sync execution with timeout
        result = await asyncio.wait_for(
            asyncio.to_thread(run_workflow_from_config, workflow_config, inputs),
            timeout=SYNC_TIMEOUT  # Default: 30s
        )

        return RunResponse(
            status="success",
            execution_time_ms=int((time.time() - start_time) * 1000),
            outputs=result
        )

    except asyncio.TimeoutError:
        # Workflow too slow → async mode
        job_id = str(uuid.uuid4())
        jobs[job_id] = {"status": "pending", "created_at": datetime.utcnow().isoformat()}
        background_tasks.add_task(run_workflow_async, job_id, inputs)

        return RunResponse(
            status="async",
            job_id=job_id,
            message=f"Workflow exceeds {SYNC_TIMEOUT}s. Poll /status/{job_id}"
        )
```

### Job Store (v0.1: In-Memory)

```python
# In-memory job store (simple, stateless OK for v0.1)
jobs: Dict[str, Dict[str, Any]] = {}

# Structure:
{
    "abc-123": {
        "status": "completed",  # pending, running, completed, failed
        "created_at": "2026-01-30T14:30:00Z",
        "completed_at": "2026-01-30T14:31:05Z",
        "execution_time_ms": 65000,
        "outputs": {"article": "...", "word_count": 500},
        "error": None
    }
}
```

**Trade-off**: Jobs lost on container restart
- **v0.1**: Acceptable (stateless microservices)
- **v0.2**: Add Redis/PostgreSQL for persistence

---

## Environment Variable Handling

**Decision**: Dual interface for environment variables (CLI vs UI).

### CLI: File-Based

```bash
# Default: Auto-detect .env in current directory
configurable-agents deploy workflow.yaml

# Custom env file
configurable-agents deploy workflow.yaml --env-file /path/to/secrets.env

# Skip (configure manually later)
configurable-agents deploy workflow.yaml --no-env-file
```

### Streamlit UI: Upload or Paste

```python
# Streamlit interface
env_method = st.radio("Environment Variables", [
    "Upload .env file",
    "Paste variables",
    "Skip (configure later)"
])

if env_method == "Upload .env file":
    uploaded_file = st.file_uploader(".env file", type=["env", "txt"])
    # Save to temp file, pass to deploy command

elif env_method == "Paste variables":
    env_content = st.text_area("KEY=value (one per line)")
    # Save to temp file, pass to deploy command
```

**Security**:
- ❌ Never bake API keys into image (insecure, leak risk)
- ✅ Pass via `--env-file` or `docker run -e` (runtime injection)
- ✅ `.env` never committed to Git (documented, `.gitignore`)
- ✅ Streamlit UI masks values in preview

**Related**: See ADR-013 for detailed environment variable security.

---

## Streamlit Integration

**Decision**: Add "Deploy" button to existing Streamlit UI.

**Features**:
- Paste workflow config → click "Deploy" → container runs
- Environment variable upload/paste
- Container management (list, stop, remove)
- Real-time deployment logs

**Implementation**:
```python
# streamlit_app.py
if st.button("🐳 Build & Deploy"):
    # Save config to temp file
    temp_config = Path("/tmp/workflow_temp.yaml")
    temp_config.write_text(config_text)

    # Run deploy command
    subprocess.run([
        "configurable-agents", "deploy", str(temp_config),
        "--port", str(port), "--name", container_name
    ])
```

**Trade-off**: Requires Docker installed on Streamlit host
- **Acceptable**: Streamlit is development/demo tool (not production)

---

## Alternatives Considered

### 1. One-Shot Execution (Container Exits After Request)

**Approach**: `docker run workflow:latest '{"topic": "AI"}'` → outputs → container exits

**Pros**:
- Simpler (no server, no persistence)
- True isolation (each request = new container)

**Cons**:
- ❌ Slow (cold start every request, ~5-10s)
- ❌ Can't reuse LLM connections
- ❌ No health checks (orchestration harder)
- ❌ Doesn't fit standard microservice patterns

**Rejected**: Persistent server is production-ready.

### 2. Always Async (No Sync Mode)

**Approach**: All `/run` requests return `job_id` immediately, always poll for results.

**Pros**:
- Simpler implementation (no timeout logic)
- Uniform API (always same response shape)

**Cons**:
- ❌ Adds complexity for fast workflows (extra polling)
- ❌ Poor UX for simple cases (2-second workflow requires polling)

**Rejected**: Sync/async hybrid provides better UX.

### 3. Separate MLFlow Container (docker-compose Multi-Container)

**Approach**: `docker-compose.yml` with two services (workflow + mlflow).

**Pros**:
- Cleaner separation of concerns
- Can scale MLFlow independently

**Cons**:
- ❌ More complex for users (two containers to manage)
- ❌ Networking setup (container-to-container communication)
- ❌ Overkill for v0.1 (single workflow deployment)

**Deferred**: Single container for v0.1, multi-container for v0.2+ (distributed deployments).

### 4. Cloud Deployment in v0.1 (ECS, Cloud Run, Lambda)

**Approach**: `--platform ecs` flag to deploy to AWS directly.

**Pros**:
- One-command cloud deployment

**Cons**:
- ❌ Scope creep (large feature, many providers)
- ❌ Requires AWS/GCP credentials management
- ❌ Each platform has unique constraints (Lambda 15min timeout, etc.)

**Deferred**: Local-only for v0.1, cloud deployment in v0.2+ with ADR.

### 5. Workflow Updates via API (Mutable Deployments)

**Approach**: `POST /update_workflow` endpoint to reload config without rebuild.

**Pros**:
- Faster iteration (no rebuild)

**Cons**:
- ❌ Breaks immutability (same image, different behavior)
- ❌ Config drift (hard to track which version running)
- ❌ No validation at build time (runtime errors)

**Rejected**: Immutable deployments are best practice. Rebuild is fast enough (<1min).

---

## Consequences

### Positive

1. **One-command deployment**: `deploy` handles everything (validate, build, run)
2. **Production-ready**: Persistent server, health checks, observability
3. **Sync/async flexibility**: Fast workflows instant, slow workflows scalable
4. **Observability included**: MLFlow UI accessible in container
5. **Optimized images**: Multi-stage build keeps size <200MB
6. **Immutable deployments**: Workflow validated and baked in (reproducible)
7. **CI/CD friendly**: Docker images fit standard pipelines
8. **Horizontal scaling**: Run N containers behind load balancer (v0.2+)

### Negative

1. **Docker dependency**: Users must install Docker (fail-fast with clear error)
2. **Job store in-memory**: Lost on container restart (v0.1 limitation)
   - *Mitigation*: Document Redis/PostgreSQL migration in v0.2
3. **Image size ~200MB**: Larger than minimal Alpine images
   - *Acceptable*: Python + FastAPI + LangChain = unavoidable overhead
4. **No cloud deployment**: Local-only for v0.1
   - *Roadmap*: AWS ECS, Cloud Run in v0.2
5. **No autoscaling**: Users must manage scaling manually
   - *Roadmap*: k8s HPA, ECS autoscaling in v0.3

### Neutral

1. **Generated artifacts**: Users can customize (Dockerfile, server.py) but must rebuild
2. **MLFlow UI exposed**: Port 5000 open (security consideration for production)
   - *Mitigation*: Document reverse proxy setup (nginx + basic auth)
3. **Sync timeout hardcoded**: 30s default (configurable via `--timeout`)
4. **Container naming conflicts**: Fails if name exists (explicit user control)

---

## Implementation Plan

### Phase 1: Artifact Generator (T-022)
- Template engine for Dockerfile, server.py, etc.
- Variable substitution (ports, workflow name, timeout)
- Generate requirements.txt, docker-compose.yml, README.md

### Phase 2: FastAPI Server Template (T-023)
- Sync/async execution logic
- Job store (in-memory)
- Endpoints: `/run`, `/status`, `/health`, `/schema`, `/docs`
- MLFlow integration (logging within container)
- OpenAPI auto-docs

### Phase 3: CLI Deploy Command (T-024)
- Argument parsing (ports, output, generate, etc.)
- Validation (workflow, Docker installed)
- Artifact generation (call T-022)
- Image build (`docker build`)
- Container run (`docker run -d`)
- Success message with endpoints

### Phase 4: Streamlit Integration (T-024)
- Deploy button with env var upload/paste
- Container management (list, stop, remove)
- Real-time logs

---

## Future Enhancements (v0.2+)

1. **Persistent job store**: Redis, PostgreSQL, or DynamoDB
2. **Cloud deployment**: ECS, Cloud Run, Lambda (via `--platform` flag)
3. **Multi-container**: Separate MLFlow container, Redis sidecar
4. **Autoscaling**: k8s HPA, ECS service autoscaling
5. **Registry push**: `--push` to DockerHub, ECR, GCR
6. **CI/CD templates**: GitHub Actions, GitLab CI, CircleCI configs
7. **Advanced networking**: API Gateway, load balancer integration
8. **Security**: TLS, API authentication, rate limiting

---

## References

- FastAPI Documentation: https://fastapi.tiangolo.com/
- Docker Multi-Stage Builds: https://docs.docker.com/build/building/multi-stage/
- Docker Best Practices: https://docs.docker.com/develop/dev-best-practices/
- MLFlow in Docker: https://mlflow.org/docs/latest/docker.html
- 12-Factor App (Stateless Processes): https://12factor.net/processes

---

## Supersedes

None (first deployment decision)

---

## Implementation Planning

**Status**: ⏳ Planned for v0.1 (not yet implemented)
**Related Tasks**: T-022 (Docker Artifacts), T-023 (FastAPI Server), T-024 (CLI Deploy Command)
**Target Date**: February 2026
**Estimated Effort**: 7 days (2+3+2)

### Implementation Tasks

**T-022: Docker Artifact Generator & Templates** (2 days):
- Template system for generating Dockerfile, server.py, etc.
- Multi-stage Dockerfile (builder + runtime)
- docker-compose.yml with MLFlow UI
- requirements.txt generation
- README.md for deployment

**T-023: FastAPI Server with Sync/Async** (3 days):
- POST /run endpoint with timeout-based fallback
- GET /status/{job_id} for async tracking
- GET /health for container orchestration
- GET /schema for workflow introspection
- In-memory job store (v0.1), Redis/PostgreSQL (v0.2+)
- Background task execution
- Input validation against workflow schema

**T-024: CLI Deploy Command & Streamlit Integration** (2 days):
- `configurable-agents deploy workflow.yaml` command
- Docker detection and validation
- Build and run container
- Environment variable handling (CLI --env-file)
- Streamlit UI: upload .env, paste variables
- Container management utilities

### Current State

**Completed**:
- ✅ Architecture designed (this ADR)
- ✅ Documentation drafted (docs/DEPLOYMENT.md - 1,165 lines)
- ✅ Sync/async strategy defined
- ✅ Environment variable approach decided (ADR-013)
- ✅ MLFlow UI integration planned (ADR-011)

**Not Started**:
- ⏳ Artifact generator code
- ⏳ FastAPI server template
- ⏳ CLI deploy command
- ⏳ Dockerfile templates

**Next Steps**: Begin T-022 after observability implementation (T-018-021) complete

---

## Related Decisions

- **ADR-011**: MLFlow observability (UI included in container)
- **ADR-013**: Environment variable handling (CLI vs UI)
- **Future ADR**: Cloud deployment strategy (v0.2)
- **Future ADR**: Container orchestration (k8s, ECS) (v0.3)
