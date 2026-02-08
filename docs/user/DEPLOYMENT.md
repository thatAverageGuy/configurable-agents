# Docker Deployment Guide

**Deploy workflows as production-ready microservices**

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [CLI Command Reference](#cli-command-reference)
- [Generated Artifacts](#generated-artifacts)
- [Environment Variables](#environment-variables)
- [Container Architecture](#container-architecture)
- [API Reference](#api-reference)
- [Streamlit UI Integration](#streamlit-ui-integration)
- [Container Management](#container-management)
- [Best Practices](#best-practices)
- [Advanced Topics](#advanced-topics)
- [Troubleshooting](#troubleshooting)

---

## Overview

### Why Docker Deployment?

Running workflows via CLI is great for development, but production requires:
- **API access**: Call workflows via HTTP (not just CLI)
- **Isolation**: Separate containers for each workflow
- **Scaling**: Run N containers behind a load balancer
- **CI/CD integration**: Docker images fit standard pipelines

### What You Get

```bash
configurable-agents deploy workflow.yaml
```

**Result**: A standalone Docker container with:
- **FastAPI server** (port 8000): HTTP API for workflow execution
- **MLFlow UI** (port 5000): Observability dashboard
- **Sync/async execution**: Fast workflows return immediately, slow ones return job_id
- **OpenAPI docs**: Auto-generated at `/docs`
- **Health checks**: For orchestration (k8s, ECS)

### Architecture

```
Workflow Config (YAML)
       ↓
[deploy command]
       ↓
Generated Artifacts:
├── Dockerfile (multi-stage, optimized)
├── server.py (FastAPI with sync/async)
├── requirements.txt (minimal deps)
├── docker-compose.yml
└── README.md (usage guide)
       ↓
[docker build]
       ↓
Docker Image (~180-200MB)
       ↓
[docker run]
       ↓
Running Container:
├── Port 8000: Workflow API
└── Port 5000: MLFlow UI
```

---

## Quick Start

### Prerequisites

1. **Docker installed**:
   ```bash
   docker --version
   # Docker version 20.10.0 or higher
   ```

2. **Workflow ready**:
   ```yaml
   # workflow.yaml (validated)
   schema_version: "1.0"
   flow:
     name: article_writer
   # ... rest of config ...
   ```

### Step 1: Deploy

```bash
configurable-agents deploy workflow.yaml
```

**Output**:
```
✓ Validating workflow... (0.5s)
✓ Checking Docker installation... (0.1s)
✓ Generating deployment artifacts... (0.3s)
  → ./deploy/Dockerfile
  → ./deploy/server.py
  → ./deploy/workflow.yaml
  → ./deploy/requirements.txt
  → ./deploy/docker-compose.yml
  → ./deploy/README.md
✓ Building Docker image... (45s)
  → Image: article_writer:latest (185 MB)
✓ Starting container... (2s)
  → Container ID: a3f9b2c1d4e5
  → Name: article_writer

🚀 Deployment successful!

Endpoints:
  Workflow API:  http://localhost:8000
  API Docs:      http://localhost:8000/docs
  MLFlow UI:     http://localhost:5000
  Health Check:  http://localhost:8000/health

Quick Start:
  # Run workflow
  curl -X POST http://localhost:8000/run \
    -H "Content-Type: application/json" \
    -d '{"topic": "AI Safety"}'

  # View traces
  open http://localhost:5000

Artifacts saved to: ./deploy
```

### Step 2: Call Workflow

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI Safety"}'
```

**Response (sync, <30s)**:
```json
{
  "status": "success",
  "execution_time_ms": 2340,
  "outputs": {
    "article": "AI Safety is a field of research focused on...",
    "word_count": 500
  }
}
```

**Response (async, >30s)**:
```json
{
  "status": "async",
  "job_id": "a3f9b2c1-d4e5-6789-0123-456789abcdef",
  "message": "Workflow exceeds 30s timeout. Poll /status/{job_id} for results."
}
```

### Step 3: View Traces (MLFlow UI)

```bash
open http://localhost:5000
```

---

## CLI Command Reference

### Basic Usage

```bash
configurable-agents deploy WORKFLOW_PATH [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--port` | int | 8000 | FastAPI server port |
| `--mlflow-port` | int | 5000 | MLFlow UI port (0 to disable) |
| `--output` | str | `./deploy` | Artifacts output directory |
| `--name` | str | `{workflow_name}` | Container/image name |
| `--timeout` | int | 30 | Sync/async threshold (seconds) |
| `--generate` | flag | False | Only generate artifacts (skip build/run) |
| `--no-mlflow` | flag | False | Disable MLFlow UI in container |
| `--env-file` | path | `.env` | Environment variables file |
| `--no-env-file` | flag | False | Skip env file (configure manually) |

### Examples

**Simple deployment**:
```bash
configurable-agents deploy workflow.yaml
```

**Custom ports**:
```bash
configurable-agents deploy workflow.yaml --port 9000 --mlflow-port 5001
```

**Generate artifacts only** (for manual build/deploy):
```bash
configurable-agents deploy workflow.yaml --generate --output ./my-deploy
```

**Disable MLFlow UI** (smaller image):
```bash
configurable-agents deploy workflow.yaml --no-mlflow
```

**Custom sync/async timeout**:
```bash
configurable-agents deploy workflow.yaml --timeout 60
# Workflows >60s will be async
```

**With environment variables**:
```bash
configurable-agents deploy workflow.yaml --env-file production.env
```

---

## Generated Artifacts

When you run `deploy`, the following files are created in `./deploy/`:

### 1. Dockerfile

Multi-stage optimized build:

```dockerfile
# ============================================
# Multi-Stage Build: Optimized for Size
# ============================================

# Stage 1: Builder (install dependencies)
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && rm -rf /var/lib/apt/lists/*

# Copy requirements and install to user site-packages
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ============================================
# Stage 2: Runtime (minimal, no build tools)
# ============================================
FROM python:3.10-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application files
COPY workflow.yaml server.py ./

# Environment
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Create data directory for MLflow SQLite DB
RUN mkdir -p /app

# Expose ports
EXPOSE 8000 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Start both FastAPI and MLFlow UI
CMD mlflow ui --host 0.0.0.0 --port 5000 --backend-store-uri sqlite:///app/mlflow.db & \
    python server.py
```

**Key optimizations**:
- Multi-stage build (~50MB savings)
- `--no-cache-dir` for pip
- Minimal base image (`python:3.10-slim`)
- Health check for orchestration

### 2. server.py

FastAPI server with sync/async logic:

```python
"""
FastAPI server for workflow execution.
Generated by configurable-agents deploy command.
"""
import asyncio
import uuid
from fastapi import FastAPI, BackgroundTasks
from configurable_agents.runtime import run_workflow_from_config

# Load workflow config at startup (fail-fast)
workflow_config = parse_config_file("workflow.yaml")

# Job store (in-memory for v0.1)
jobs = {}

# FastAPI app
app = FastAPI(title="article_writer API")

@app.post("/run")
async def run_workflow_endpoint(inputs: dict, background_tasks: BackgroundTasks):
    """Execute workflow (sync/async hybrid)"""
    try:
        # Attempt sync execution with timeout
        result = await asyncio.wait_for(
            asyncio.to_thread(run_workflow_from_config, workflow_config, inputs),
            timeout=30  # SYNC_TIMEOUT
        )
        return {"status": "success", "outputs": result}

    except asyncio.TimeoutError:
        # Fall back to async
        job_id = str(uuid.uuid4())
        jobs[job_id] = {"status": "pending", "created_at": ...}
        background_tasks.add_task(run_workflow_async, job_id, inputs)
        return {"status": "async", "job_id": job_id}

@app.get("/status/{job_id}")
def get_job_status(job_id: str):
    """Get async job status"""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[job_id]

@app.get("/health")
def health():
    """Health check"""
    return {"status": "healthy"}

@app.get("/schema")
def schema():
    """Return workflow input/output schema"""
    return {"inputs": ..., "outputs": ...}
```

**Features**:
- Sync/async hybrid (timeout-based)
- Job store for async executions
- Health check endpoint
- Schema introspection
- OpenAPI docs auto-generated

### 3. requirements.txt

Minimal runtime dependencies:

```txt
configurable-agents==0.1.0
fastapi==0.109.0
uvicorn[standard]==0.27.0
mlflow==2.10.0
```

### 4. docker-compose.yml

Optional: Easier local testing:

```yaml
version: '3.8'

services:
  workflow:
    build: .
    container_name: article_writer
    ports:
      - "8000:8000"
      - "5000:5000"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - SERPER_API_KEY=${SERPER_API_KEY}
    volumes:
      - ./mlflow.db:/app/mlflow.db  # Persist traces
    restart: unless-stopped
```

**Usage**:
```bash
cp .env.example .env  # Fill in API keys
docker-compose up -d
```

### 5. .env.example

Template for API keys:

```bash
# Google Gemini API Key (required)
# Get yours at: https://makersuite.google.com/app/apikey
GOOGLE_API_KEY=your_google_api_key_here

# Serper Search API Key (required if using serper_search tool)
# Get yours at: https://serper.dev/
SERPER_API_KEY=your_serper_api_key_here
```

### 6. README.md

Usage guide specific to this deployment (includes curl examples, management commands, etc.).

---

## Environment Variables

### CLI: File-Based

**Default behavior** (auto-detects `.env`):
```bash
configurable-agents deploy workflow.yaml
# Looks for .env in current directory
```

**Custom env file**:
```bash
configurable-agents deploy workflow.yaml --env-file production.env
```

**Skip env file**:
```bash
configurable-agents deploy workflow.yaml --no-env-file
# Configure later: docker run -e GOOGLE_API_KEY=xxx ...
```

### Streamlit UI: Upload or Paste

**Three options**:
1. **Upload .env file**: Drag & drop
2. **Paste variables**: Text area with KEY=value pairs
3. **Skip**: Configure manually later

**Streamlit interface**:
```python
env_method = st.radio("Environment Variables", [
    "Upload .env file",
    "Paste variables",
    "Skip (configure later)"
])

if env_method == "Upload .env file":
    uploaded_file = st.file_uploader(".env file", type=["env", "txt"])
    # Temp file created, passed to deploy command

elif env_method == "Paste variables":
    env_content = st.text_area("KEY=value (one per line)")
    # Temp file created, passed to deploy command
```

### Security Best Practices

❌ **NEVER bake secrets into images**:
```dockerfile
# BAD - Secret in image layer (persists forever)
ENV GOOGLE_API_KEY=AIzaSyC3x...
```

✅ **Pass at runtime**:
```bash
# GOOD - Injected at runtime
docker run --env-file .env my-workflow
docker run -e GOOGLE_API_KEY=xxx -e SERPER_API_KEY=yyy my-workflow
```

❌ **NEVER commit .env to Git**:
```gitignore
# .gitignore
.env
.env.*
*.env
!.env.example  # Template OK (no real keys)
```

✅ **Rotate keys regularly**:
```bash
# Update .env with new keys
docker stop my-workflow
docker rm my-workflow
configurable-agents deploy workflow.yaml  # Redeploy with new keys
```

### Production Secrets Management (v0.2+)

**AWS Secrets Manager**:
```bash
aws secretsmanager get-secret-value --secret-id prod/api-keys | \
  jq -r '.SecretString' > .env

configurable-agents deploy workflow.yaml
```

**HashiCorp Vault**:
```bash
vault kv get -format=json secret/api-keys | \
  jq -r '.data.data | to_entries | .[] | "\(.key)=\(.value)"' > .env

configurable-agents deploy workflow.yaml
```

---

## Container Architecture

### Persistent Server Model

**Not one-shot** (container stays running):
```
docker run -d ...
       ↓
FastAPI server starts (persistent)
       ↓
Accepts multiple HTTP requests
       ↓
Container keeps running until stopped
```

**Benefits**:
- Reuse LLM connections (faster)
- Standard microservice pattern
- Health checks for orchestration
- Multiple requests without cold start

### Sync/Async Hybrid Execution

**How it works**:

```python
# FastAPI endpoint logic
async def run_workflow_endpoint(inputs):
    try:
        # Attempt sync (with timeout)
        result = await asyncio.wait_for(
            asyncio.to_thread(run_workflow, config, inputs),
            timeout=SYNC_TIMEOUT  # Default: 30s
        )
        return {"status": "success", "outputs": result}

    except asyncio.TimeoutError:
        # Workflow too slow → switch to async
        job_id = str(uuid.uuid4())
        jobs[job_id] = {"status": "pending", ...}
        background_tasks.add_task(run_workflow_async, job_id, inputs)
        return {"status": "async", "job_id": job_id}
```

**Decision tree**:
```
POST /run
    ↓
Execute workflow
    ↓
Complete <30s? → Yes → Return outputs (200 OK)
    ↓
    No (timeout)
    ↓
Generate job_id
    ↓
Run in background
    ↓
Return job_id (202 Accepted)
```

### Job Store (In-Memory, v0.1)

**Structure**:
```python
jobs = {
    "a3f9b2c1-d4e5-...": {
        "status": "completed",  # pending, running, completed, failed
        "created_at": "2026-01-30T14:30:00Z",
        "completed_at": "2026-01-30T14:31:05Z",
        "execution_time_ms": 65000,
        "outputs": {"article": "...", "word_count": 500},
        "error": None
    }
}
```

**Limitation**: Jobs lost on container restart.

**Future** (v0.2): Redis or PostgreSQL for persistence.

### MLFlow UI Inside Container

**Startup command**:
```dockerfile
CMD mlflow ui --host 0.0.0.0 --port 5000 --backend-store-uri sqlite:///app/mlflow.db & \
    python server.py
```

**MLFlow UI runs in background**, FastAPI in foreground.

**Persistent traces** (volume mount):
```yaml
volumes:
  - ./mlflow.db:/app/mlflow.db  # Host file mapped to container
```

**Benefits**:
- View traces without separate MLFlow server
- Traces survive container restarts
- Self-contained deployment

---

## API Reference

### POST /run

Execute workflow (sync or async).

**Request**:
```http
POST /run
Content-Type: application/json

{
  "topic": "AI Safety",
  "count": 5
}
```

**Response (sync, <30s)**:
```json
{
  "status": "success",
  "execution_time_ms": 2340,
  "outputs": {
    "article": "...",
    "word_count": 500
  }
}
```

**Response (async, >30s)**:
```json
{
  "status": "async",
  "job_id": "a3f9b2c1-d4e5-6789-0123-456789abcdef",
  "message": "Workflow exceeds 30s timeout. Poll /status/{job_id} for results."
}
```

**Error responses**:
```json
// 400 Bad Request (invalid inputs)
{
  "status": "error",
  "error_type": "ValidationError",
  "message": "Missing required field: topic",
  "details": {...}
}

// 500 Internal Server Error (execution failed)
{
  "status": "error",
  "error_type": "ExecutionError",
  "message": "LLM API timeout"
}
```

### GET /status/{job_id}

Get async job status.

**Request**:
```http
GET /status/a3f9b2c1-d4e5-6789-0123-456789abcdef
```

**Response (pending)**:
```json
{
  "job_id": "a3f9b2c1-d4e5-6789-0123-456789abcdef",
  "status": "pending",
  "created_at": "2026-01-30T14:30:00Z"
}
```

**Response (running)**:
```json
{
  "job_id": "a3f9b2c1-d4e5-6789-0123-456789abcdef",
  "status": "running",
  "created_at": "2026-01-30T14:30:00Z"
}
```

**Response (completed)**:
```json
{
  "job_id": "a3f9b2c1-d4e5-6789-0123-456789abcdef",
  "status": "completed",
  "created_at": "2026-01-30T14:30:00Z",
  "completed_at": "2026-01-30T14:31:05Z",
  "execution_time_ms": 65000,
  "outputs": {
    "article": "...",
    "word_count": 500
  }
}
```

**Response (failed)**:
```json
{
  "job_id": "a3f9b2c1-d4e5-6789-0123-456789abcdef",
  "status": "failed",
  "created_at": "2026-01-30T14:30:00Z",
  "completed_at": "2026-01-30T14:30:45Z",
  "error": "LLM API timeout after 3 retries"
}
```

### GET /health

Health check for orchestration (k8s, ECS).

**Request**:
```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-30T14:35:00Z"
}
```

### GET /schema

Return workflow input/output schema.

**Request**:
```http
GET /schema
```

**Response**:
```json
{
  "workflow": "article_writer",
  "inputs": {
    "topic": {
      "type": "str",
      "required": true,
      "default": null,
      "description": "Topic to write about"
    }
  },
  "outputs": ["article", "word_count"]
}
```

### GET /docs

Interactive OpenAPI documentation (auto-generated by FastAPI).

**Access**: http://localhost:8000/docs

**Features**:
- Try API endpoints in browser
- View request/response schemas
- Download OpenAPI spec (JSON)

---

## Streamlit UI Integration

### Deploy Section

When you run `streamlit run streamlit_app.py`, a "Deploy to Docker" section is available:

**UI Elements**:
1. **Configuration**:
   - API Port (number input, default: 8000)
   - MLFlow Port (number input, default: 5000)
   - Container Name (text input, default: workflow name)

2. **Environment Variables**:
   - Radio: Upload .env / Paste variables / Skip
   - File uploader or text area
   - Preview with masked values

3. **Deploy Button**:
   - Executes `configurable-agents deploy` command
   - Shows real-time logs (subprocess output)
   - Displays success message with endpoints

4. **Container Management**:
   - List Containers button
   - Stop button (with container name input)
   - Remove button (with container name input)

**Example flow**:
```
1. Paste workflow YAML in editor
2. Select "Upload .env file"
3. Upload production.env
4. Click "Build & Deploy"
5. Wait ~60s (build + run)
6. Success: "🚀 Deployed to http://localhost:8000"
7. Click "List Containers" to see running containers
```

---

## Container Management

### View Running Containers

```bash
docker ps
```

**Output**:
```
CONTAINER ID   IMAGE                  PORTS                              NAMES
a3f9b2c1d4e5   article_writer:latest  0.0.0.0:8000->8000/tcp, 5000/tcp   article_writer
```

### View Logs

```bash
docker logs article_writer
docker logs -f article_writer  # Follow (live tail)
```

### Stop Container

```bash
docker stop article_writer
```

### Restart Container

```bash
docker restart article_writer
```

### Remove Container

```bash
docker rm -f article_writer  # -f to force stop if running
```

### Update Workflow

**Immutable deployment** (rebuild image):
```bash
# Edit workflow.yaml
vim workflow.yaml

# Redeploy (stops old container, builds new image, runs new container)
configurable-agents deploy workflow.yaml
```

**Alternative**: Volume mount (mutable):
```bash
docker run -d \
  -v ./workflow.yaml:/app/workflow.yaml \
  -p 8000:8000 \
  article_writer:latest
```

### View Resource Usage

```bash
docker stats article_writer
```

**Output**:
```
CONTAINER ID   NAME              CPU %   MEM USAGE / LIMIT   NET I/O
a3f9b2c1d4e5   article_writer    0.50%   120MiB / 2GiB       1.2kB / 0B
```

---

## Best Practices

### 1. Use Specific Image Tags

```bash
# BAD - :latest is ambiguous
docker run article_writer:latest

# GOOD - Semantic versioning
docker tag article_writer:latest article_writer:1.0.0
docker run article_writer:1.0.0
```

### 2. Set Resource Limits

```bash
docker run -d \
  --memory="512m" \
  --cpus="1.0" \
  -p 8000:8000 \
  article_writer:latest
```

### 3. Configure Restart Policy

```bash
docker run -d \
  --restart=unless-stopped \
  -p 8000:8000 \
  article_writer:latest
```

**Restart policies**:
- `no`: Don't restart (default)
- `always`: Always restart
- `unless-stopped`: Restart unless manually stopped
- `on-failure`: Restart only on error exit

### 4. Use Health Checks

Already included in generated Dockerfile:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"
```

**Check health**:
```bash
docker inspect --format='{{.State.Health.Status}}' article_writer
# Output: healthy
```

### 5. Persist MLFlow Traces

```bash
docker run -d \
  -v $(pwd)/mlflow.db:/app/mlflow.db \
  -p 8000:8000 -p 5000:5000 \
  article_writer:latest
```

**Backup traces**:
```bash
cp mlflow.db mlflow-backup-$(date +%Y%m%d).db
```

### 6. Use docker-compose for Production

```yaml
# docker-compose.yml
version: '3.8'

services:
  workflow:
    image: article_writer:1.0.0
    container_name: article_writer_prod
    ports:
      - "8000:8000"
      - "5000:5000"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    volumes:
      - ./mlflow.db:/app/mlflow.db
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
```

---

## Advanced Topics

### Custom Dockerfile

**Edit generated Dockerfile**:
```bash
configurable-agents deploy workflow.yaml --generate
cd deploy
vim Dockerfile
# Make changes (add dependencies, change base image, etc.)
docker build -t article_writer:custom .
docker run -d -p 8000:8000 article_writer:custom
```

### Load Balancing (Multiple Containers)

```bash
# Start 3 containers on different ports
configurable-agents deploy workflow.yaml --port 8001 --name workflow-1
configurable-agents deploy workflow.yaml --port 8002 --name workflow-2
configurable-agents deploy workflow.yaml --port 8003 --name workflow-3

# Use nginx for load balancing
# nginx.conf:
upstream workflow_backend {
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}

server {
    listen 8000;
    location / {
        proxy_pass http://workflow_backend;
    }
}
```

### Push to Registry

```bash
# Tag for registry
docker tag article_writer:latest myregistry.com/article_writer:1.0.0

# Login to registry
docker login myregistry.com

# Push
docker push myregistry.com/article_writer:1.0.0

# Pull on another machine
docker pull myregistry.com/article_writer:1.0.0
docker run -d -p 8000:8000 myregistry.com/article_writer:1.0.0
```

### Cloud Deployment (v0.2+)

**AWS ECS**:
```bash
# (Future) One-command deploy to ECS
configurable-agents deploy workflow.yaml --platform ecs --cluster my-cluster
```

**Google Cloud Run**:
```bash
# (Future) One-command deploy to Cloud Run
configurable-agents deploy workflow.yaml --platform cloudrun --region us-central1
```

---

## Troubleshooting

### Container Won't Start

**Check logs**:
```bash
docker logs article_writer
```

**Common issues**:
- Missing API keys: `GOOGLE_API_KEY not set`
- Invalid workflow config: `ValidationError: ...`
- Port already in use: `Error starting userland proxy: listen tcp 0.0.0.0:8000: bind: address already in use`

**Solutions**:
- Provide .env file: `--env-file .env`
- Validate workflow before deploy: `configurable-agents validate workflow.yaml`
- Use different port: `--port 9000`

### Workflow Fails at Runtime

**Check container logs**:
```bash
docker logs -f article_writer
```

**Check MLFlow UI**:
```bash
open http://localhost:5000
# View error traces, prompts, responses
```

### Port Already in Use

**Find process using port**:
```bash
# Linux/Mac
lsof -i :8000

# Windows
netstat -ano | findstr :8000
```

**Solution**: Use different port:
```bash
configurable-agents deploy workflow.yaml --port 9000
```

### MLFlow UI Not Accessible

**Check if MLFlow is running**:
```bash
docker exec article_writer ps aux | grep mlflow
```

**Check port binding**:
```bash
docker port article_writer
# Should show: 5000/tcp -> 0.0.0.0:5000
```

**Solution**: Ensure `--mlflow-port` is set and not 0:
```bash
configurable-agents deploy workflow.yaml --mlflow-port 5000
```

### Image Build Fails

**Check Docker daemon**:
```bash
docker info
```

**Check disk space**:
```bash
df -h
```

**Clean up old images**:
```bash
docker system prune -a
```

---

## Next Steps

- **Deploy your first workflow**: `configurable-agents deploy workflow.yaml`
- **Call the API**: `curl -X POST http://localhost:8000/run -d '...'`
- **View traces**: Open http://localhost:5000
- **Scale horizontally**: Run multiple containers behind load balancer
- **Plan for v0.2**: Cloud deployment (ECS, Cloud Run, Lambda)

---

## Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Docker Documentation**: https://docs.docker.com/
- **Docker Best Practices**: https://docs.docker.com/develop/dev-best-practices/
- **ADR-012**: Docker Deployment Architecture (internal design doc)
- **ADR-013**: Environment Variable Handling (internal design doc)

---

**Last Updated**: 2026-02-02
