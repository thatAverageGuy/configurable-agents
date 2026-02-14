# CLI Reference Guide

> **Source**: `src/configurable_agents/cli.py` (single file, ~2975 lines)
>
> **Entry points**:
> - `configurable-agents` (installed via `pip install -e .`)
> - `python -m configurable_agents` (module invocation)
>
> **Last verified**: 2026-02-14
>
> **Note**: Updated for UI Redesign (2026-02-13). Commands renamed:
> - `workflow-registry` → `deployments`
> - Dashboard routes: `/workflows` → `/executions`, `/agents` → `/deployments`

---

## Quick Overview

| Command | Description | Category |
|---------|-------------|----------|
| `run` | Execute a workflow from a YAML/JSON config | Core |
| `validate` | Validate a workflow config without executing | Core |
| `deploy` | Deploy workflow as a Docker container | Deployment |
| `ui` | Launch complete UI (Dashboard + Chat + MLFlow) | UI |
| `dashboard` | Launch orchestration dashboard only | UI |
| `chat` | Launch Gradio Chat UI only | UI |
| `webhooks` | Launch webhook server (WhatsApp/Telegram/Generic) | Integration |
| `report costs` | Generate cost reports from MLFlow data | Observability |
| `cost-report` | Unified cost report by provider | Observability |
| `profile-report` | Profiling report with bottleneck analysis | Observability |
| `observability status` | Show MLFlow connection & recent activity | Observability |
| `observability cost-report` | Alias for `cost-report` | Observability |
| `observability profile-report` | Alias for `profile-report` | Observability |
| `deployments start` | Start the deployment registry server | Registry |
| `deployments list` | List registered deployments | Registry |
| `deployments cleanup` | Clean up expired deployments | Registry |

---

## Global Flags

```
configurable-agents --version    Show version (0.1.0-dev)
configurable-agents --help       Show help with all commands and examples
```

---

## Core Commands

### `run` - Execute Workflow

Runs a workflow defined in a YAML/JSON config file. Auto-initializes the SQLite database before execution.

```
configurable-agents run <config_file> [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `config_file` | (positional) | *required* | Path to workflow config file (YAML/JSON) |
| `--input` | `-i` | none | Workflow inputs as `key=value` (repeatable) |
| `--verbose` | `-v` | off | Enable DEBUG-level logging |

**Input parsing rules**:
- Strings: `--input topic="AI Safety"` or `--input topic=AI Safety`
- Numbers: `--input count=5` (auto-parsed via JSON)
- Booleans: `--input enabled=true`
- JSON values: `--input items='["a","b"]'`

**Exit codes**: 0 = success, 1 = error (config load, validation, state init, graph build, execution)

**Examples**:
```bash
configurable-agents run workflow.yaml
configurable-agents run workflow.yaml -i topic="AI Safety" -i count=5
configurable-agents run workflow.yaml --verbose
```

---

### `validate` - Validate Config

Validates a workflow config file without executing it. Checks YAML syntax and schema compliance.

```
configurable-agents validate <config_file> [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `config_file` | (positional) | *required* | Path to workflow config file (YAML/JSON) |
| `--verbose` | `-v` | off | Show full tracebacks on error |

**Examples**:
```bash
configurable-agents validate workflow.yaml
configurable-agents validate workflow.yaml --verbose
```

---

## Deployment

### `deploy` - Deploy as Docker Container

Generates deployment artifacts (Dockerfile, docker-compose, FastAPI server, etc.) and optionally builds + runs the Docker container.

```
configurable-agents deploy <config_file> [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `config_file` | (positional) | *required* | Path to workflow config (YAML/JSON) |
| `--output-dir` | | `./deploy` | Directory for generated artifacts |
| `--api-port` | | `8000` | FastAPI server port |
| `--mlflow-port` | | `5000` | MLFlow UI port |
| `--name` | | workflow name | Container name |
| `--timeout` | | `30` | Sync/async threshold in seconds |
| `--generate` | | off | Generate artifacts only, skip Docker build/run |
| `--no-mlflow` | | off | Disable MLFlow UI in container |
| `--env-file` | | `.env` | Environment variables file |
| `--no-env-file` | | off | Skip environment file entirely |
| `--verbose` | `-v` | off | Enable verbose output |

**Pipeline** (without `--generate`):
1. Validate config
2. Generate deployment artifacts
3. Check Docker availability
4. Check port availability
5. Handle `.env` file
6. `docker build`
7. `docker run` (detached)
8. Print endpoints and management commands

**Examples**:
```bash
# Generate artifacts only (no Docker needed)
configurable-agents deploy workflow.yaml --generate --output-dir ./my_deploy

# Full deploy
configurable-agents deploy workflow.yaml --api-port 8000 --name my-workflow

# Deploy without MLFlow
configurable-agents deploy workflow.yaml --no-mlflow
```

---

## UI Commands

### `ui` - Launch Complete UI

Starts **all** UI services via `ProcessManager` (fork-join pattern):
- Dashboard (uvicorn/FastAPI)
- Chat UI (Gradio) - unless `--no-chat`
- MLFlow UI (subprocess) - if mlflow is installed

```
configurable-agents ui [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--host` | | `0.0.0.0` | Host to bind all services to |
| `--dashboard-port` | | `7861` | Dashboard port |
| `--chat-port` | | `7860` | Chat UI port |
| `--db-url` | | `sqlite:///configurable_agents.db` | Database URL |
| `--mlflow-uri` | | auto (localhost:5000 if mlflow installed) | MLFlow tracking URI |
| `--mlflow-port` | | `5000` | MLFlow UI port (ignored if `--mlflow-uri` set) |
| `--no-chat` | | off | Start Dashboard only, skip Chat UI |
| `--verbose` | `-v` | off | Enable verbose output |

**Behavior**:
- Checks for previous dirty shutdown (crash recovery)
- Auto-starts MLFlow if installed (no `--mlflow-uri` needed)
- Uses `ProcessManager` for child process lifecycle
- Ctrl+C stops all services gracefully
- Windows-specific: uses job objects for reliable MLFlow cleanup

**Examples**:
```bash
configurable-agents ui
configurable-agents ui --no-chat --dashboard-port 8080
configurable-agents ui --mlflow-uri http://remote-mlflow:5000
```

---

### `dashboard` - Launch Dashboard Only

Starts the orchestration dashboard (FastAPI + uvicorn) as a standalone service.

```
configurable-agents dashboard [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--host` | | `0.0.0.0` | Host to bind to |
| `--port` | | `7861` | Port to listen on |
| `--db-url` | | `sqlite:///configurable_agents.db` | Database URL |
| `--mlflow-uri` | | none | MLFlow tracking URI (optional) |
| `--verbose` | `-v` | off | Enable verbose output |

**Endpoints served**:
- `/` - Dashboard home
- `/executions` - Execution listing
- `/deployments` - Deployment listing
- `/mlflow` - Embedded MLFlow UI (if `--mlflow-uri` set)

**Examples**:
```bash
configurable-agents dashboard
configurable-agents dashboard --port 9000 --mlflow-uri http://localhost:5000
```

---

### `chat` - Launch Gradio Chat UI

Starts the Gradio-based chat interface for interactive workflow config generation.

```
configurable-agents chat [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--host` | | `0.0.0.0` | Host to bind to |
| `--port` | | `7860` | Port to listen on |
| `--dashboard-url` | | `DASHBOARD_URL` env or `http://localhost:7861` | Dashboard URL link |
| `--share` | | off | Create a public Gradio share link |
| `--verbose` | `-v` | off | Enable verbose output |

**Requires**: `pip install gradio>=4.0.0` (optional dependency group `chat`)

**Examples**:
```bash
configurable-agents chat
configurable-agents chat --share --port 8080
```

---

## Integration

### `webhooks` - Launch Webhook Server

Starts a FastAPI server with webhook endpoints for WhatsApp, Telegram, and generic workflow triggers.

```
configurable-agents webhooks [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--host` | | `0.0.0.0` | Host to bind to |
| `--port` | | `7862` | Port to listen on |
| `--verbose` | `-v` | off | Enable verbose output |

**Endpoints served**:
- `/webhooks/health` - Health check
- `/webhooks/generic` - Generic workflow trigger
- `/webhooks/whatsapp` - WhatsApp webhook
- `/webhooks/telegram` - Telegram webhook
- `/docs` - Swagger API docs

**Environment variables for platform config**:
- WhatsApp: `WHATSAPP_PHONE_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_VERIFY_TOKEN`
- Telegram: `TELEGRAM_BOT_TOKEN`

**Examples**:
```bash
configurable-agents webhooks
configurable-agents webhooks --port 9000 --verbose
```

---

## Observability Commands

### `report costs` - Cost Reports from MLFlow

Queries MLFlow tracking data to generate cost summaries with filtering and export.

```
configurable-agents report costs [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--tracking-uri` | | `sqlite:///mlflow.db` | MLFlow tracking URI |
| `--experiment` | | none | Filter by experiment name |
| `--workflow` | | none | Filter by workflow name |
| `--period` | | none | Predefined period: `today`, `yesterday`, `last_7_days`, `last_30_days`, `this_month` |
| `--start-date` | | none | Filter after date (ISO: `YYYY-MM-DD`) |
| `--end-date` | | none | Filter before date (ISO: `YYYY-MM-DD`) |
| `--status` | | none | Filter by status: `success` or `failure` |
| `--breakdown` | | off | Show breakdown by workflow and model |
| `--aggregate-by` | | none | Aggregate by: `daily`, `weekly`, `monthly` |
| `--output` | `-o` | none | Export to file path |
| `--format` | | `json` | Export format: `json` or `csv` |
| `--include-summary` | | `true` | Include summary in JSON export |
| `--verbose` | `-v` | off | Enable verbose output |

**Output fields**: Total cost, total runs, successful/failed runs, total tokens, avg cost/run, avg tokens/run, breakdowns by workflow and model.

**Examples**:
```bash
configurable-agents report costs --period last_7_days --breakdown
configurable-agents report costs --experiment my_exp --aggregate-by daily
configurable-agents report costs --output costs.csv --format csv
```

---

### `cost-report` - Unified Provider Cost Report

Generates a Rich-formatted table showing cost breakdown by LLM provider and model from MLFlow experiment data.

```
configurable-agents cost-report --experiment <name> [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--experiment` | | *required* | MLFlow experiment name |
| `--mlflow-uri` | | config default / `sqlite:///mlflow.db` | MLFlow tracking URI |
| `--verbose` | `-v` | off | Enable verbose output |

**Requires**: `rich>=13.0.0`

**Examples**:
```bash
configurable-agents cost-report --experiment my_experiment
configurable-agents cost-report --experiment my_experiment --mlflow-uri http://mlflow:5000
```

---

### `profile-report` - Profiling & Bottleneck Analysis

Analyzes node-level execution timing from MLFlow run metrics. Highlights slowest nodes and bottlenecks (>50% of total time).

```
configurable-agents profile-report [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--run-id` | | latest run | Specific MLFlow run ID to analyze |
| `--mlflow-uri` | | config default / `sqlite:///mlflow.db` | MLFlow tracking URI |
| `--verbose` | `-v` | off | Enable verbose output |

**Requires**: `rich>=13.0.0`, `mlflow>=3.9.0`

**Note**: Timing data is automatically captured via MLflow 3.9 autolog for all runs.

**Examples**:
```bash
configurable-agents profile-report
configurable-agents profile-report --run-id abc123def456
```

---

### `observability status` - MLFlow Status

Shows MLFlow connection status, experiment count, and recent activity (last 24 hours).

```
configurable-agents observability status [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--mlflow-uri` | | config default | MLFlow tracking URI |
| `--verbose` | `-v` | off | Enable verbose output |

**Requires**: `rich>=13.0.0`, `mlflow>=3.9.0`

**Examples**:
```bash
configurable-agents observability status
configurable-agents observability status --mlflow-uri http://mlflow:5000
```

---

### `observability cost-report` / `observability profile-report`

These are **aliases** to the top-level `cost-report` and `profile-report` commands with identical flags. Provided for organizational convenience under the `observability` namespace.

---

## Deployment Registry Commands

### `deployments start` - Start Registry Server

Starts the deployment registry FastAPI server for distributed deployment coordination.

```
configurable-agents deployments start [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--host` | | `0.0.0.0` | Host to bind to |
| `--port` | | `9000` | Port to listen on |
| `--db-url` | | `sqlite:///configurable_agents.db` | Database URL |
| `--verbose` | `-v` | off | Enable verbose output |

---

### `deployments list` - List Deployments

Lists all registered deployments from the registry database.

```
configurable-agents deployments list [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--db-url` | | `sqlite:///configurable_agents.db` | Database URL |
| `--include-dead` | | off | Include expired/dead deployments |
| `--verbose` | `-v` | off | Enable verbose output |

**Output columns**: Deployment ID, Name, Host:Port, Last Heartbeat, Status (Alive/Dead)

---

### `deployments cleanup` - Remove Expired Deployments

Manually triggers deletion of expired deployments from the registry.

```
configurable-agents deployments cleanup [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--db-url` | | `sqlite:///configurable_agents.db` | Database URL |
| `--verbose` | `-v` | off | Enable verbose output |

---

## Default Port Map

| Service | Port | Command |
|---------|------|---------|
| Chat UI (Gradio) | 7860 | `chat`, `ui` |
| Dashboard (FastAPI) | 7861 | `dashboard`, `ui` |
| Webhooks (FastAPI) | 7862 | `webhooks` |
| MLFlow UI | 5000 | `ui`, `deploy` |
| Deploy API (FastAPI) | 8000 | `deploy` |
| Deployment Registry | 9000 | `deployments start` |

---

## CLI Verification Status

> **Last comprehensive test**: 2026-02-14 (Windows, Python 3.12, UI Redesign branch)
>
> All 12 test configs in `test_configs/` validated and tested.

### Core Commands

| Command | Tested | Works | Notes |
|---------|--------|-------|-------|
| `--version` | 2026-02-14 | YES | Shows `0.1.0-dev` |
| `--help` | 2026-02-14 | YES | Lists all 13 commands with examples |
| `run` | 2026-02-14 | YES | All test configs work. Flags tested: `--input`, `--verbose`. Data persisted to database verified. |
| `run --verbose` | 2026-02-14 | YES | DEBUG-level logging enabled |
| `run --input key=value` | 2026-02-14 | YES | Multiple inputs supported |
| `validate` | 2026-02-14 | YES | All 12 test configs validate successfully |
| `validate --verbose` | 2026-02-14 | YES | Verbose output shows validation steps |

### Deploy Commands

| Command | Tested | Works | Notes |
|---------|--------|-------|-------|
| `deploy --generate` | 2026-02-14 | YES | Generates 10 artifacts (Dockerfile, server.py, requirements.txt, docker-compose.yml, .env.example, README.md, .dockerignore, workflow.yaml, src/, pyproject.toml) |
| `deploy --output-dir` | 2026-02-14 | YES | Custom output directory works |
| `deploy --name` | 2026-02-14 | YES | Custom container name works |
| `deploy --no-mlflow` | 2026-02-14 | YES | MLFlow disabled in generated artifacts |
| `deploy --no-env-file` | 2026-02-14 | YES | Skips .env file handling |
| `deploy --verbose` | 2026-02-14 | YES | Verbose output during generation |
| `deploy` (full Docker) | 2026-02-09 | YES | Full Docker build+run works. See BF-008 below |

### Deployment Registry Commands

| Command | Tested | Works | Notes |
|---------|--------|-------|-------|
| `deployments start` | 2026-02-14 | YES | Server starts on configurable port (default 9000) |
| `deployments start --port` | 2026-02-14 | YES | Custom port works |
| `deployments list` | 2026-02-14 | YES | Shows "No deployments found" on empty DB |
| `deployments list --include-dead` | 2026-02-14 | YES | Flag recognized |
| `deployments cleanup` | 2026-02-14 | YES | Shows "No expired deployments found" on empty DB |

### Observability Commands

| Command | Tested | Works | Notes |
|---------|--------|-------|-------|
| `observability status` | 2026-02-14 | YES | Shows MLFlow connection, experiment count, recent activity |
| `cost-report --experiment` | 2026-02-14 | YES | Validates experiment name |
| `profile-report` | 2026-02-14 | YES | Shows "No traces found" when no data |
| `profile-report --run-id` | 2026-02-14 | YES | Custom run ID supported |
| `report costs` | 2026-02-14 | YES | Query MLFlow for cost data |
| `report costs --period` | 2026-02-14 | YES | Periods: today, yesterday, last_7_days, last_30_days, this_month |
| `report costs --breakdown` | 2026-02-14 | YES | Cost breakdown by workflow and model |
| `report costs --output` | 2026-02-14 | YES | Export to JSON/CSV (when data exists) |

### Server Commands

| Command | Tested | Works | Notes |
|---------|--------|-------|-------|
| `dashboard --help` | 2026-02-14 | YES | Shows all flags |
| `webhooks` | 2026-02-14 | YES | Server starts on configurable port (default 7862) |
| `webhooks --port` | 2026-02-14 | YES | Custom port works |
| `chat --help` | 2026-02-14 | YES | Shows all flags including --share |
| `ui --help` | 2026-02-14 | YES | Shows all flags including --no-chat |
| `ui --no-chat` | 2026-02-14 | YES | Skip chat UI flag recognized |

### Test Configs Verified

All 12 test configs in `test_configs/` validated and executed:

| Config | Description | Status |
|--------|-------------|--------|
| `01_basic_linear.yaml` | Minimal single-node workflow | PASS |
| `02_with_observability.yaml` | MLFlow tracking enabled | PASS |
| `03_multi_node_linear.yaml` | Multi-node linear flow | PASS |
| `04_with_tools.yaml` | Tool integration | PASS |
| `05_conditional_branching.yaml` | Conditional edge routing | PASS |
| `06_loop_iteration.yaml` | Loop with max iterations | PASS |
| `07_parallel_execution.yaml` | Fork-join parallel execution | PASS |
| `08_multi_llm.yaml` | Multi-LLM provider support | PASS |
| `09_with_memory.yaml` | Memory backend integration | PASS |
| `10_with_sandbox.yaml` | Sandbox execution | PASS |
| `11_with_storage.yaml` | Storage backend integration | PASS |
| `12_full_featured.yaml` | All features combined | PASS |

### Database Verification

Execution records are properly persisted to SQLite database:
- Executions table: Records created with workflow_name, status, duration
- Execution states table: Node-level state tracking
- Verified: 4+ execution records from test runs

### All `--help` subcommands verified

All 13 top-level commands and their subcommands produce correct `--help` output (2026-02-14).

### Removed Commands

| Command | Status | Notes |
|---------|--------|-------|
| ~~`optimization *`~~ | REMOVED | Optimization module removed — redesign planned with MLflow 3.9 GenAI + DSPy |

---

## Bugs Found and Fixed During CLI Verification

### BF-007: `webhooks` command fails — wrong router import (FIXED)

**Severity**: Command non-functional
**File**: `src/configurable_agents/cli.py:1998`
**Error**: `module 'configurable_agents.webhooks.router' has no attribute 'routes'`

**Root cause**: `from configurable_agents.webhooks import router` imported the `router` **module** (`webhooks/router.py`), not the `APIRouter` instance inside it.

**Fix**: Changed to `from configurable_agents.webhooks.router import router as webhook_router`

### BF-008: Docker deploy — build failure and port mismatch (FIXED)

**Severity**: Deploy non-functional (two sub-issues)

**BF-008a: Invalid pyproject.toml scripts break Docker build**
- **Error**: `ValueError: invalid pyproject.toml config: project.scripts.docs:build`
- **Root cause**: `pyproject.toml` has `docs:build`, `docs:serve`, `docs:clean` entries that are shell commands, not valid Python entry points
- **File**: `src/configurable_agents/deploy/generator.py` (`_copy_pyproject_toml()`)
- **Fix**: Rewrote method to filter out invalid script entries (entries with spaces or missing `module:attr` format)

**BF-008b: Container port mismatch**
- **Error**: Health endpoint unreachable — server listened on user port (e.g., 8099) but Docker mapped `host:8099 → container:8000`
- **Root cause**: `server.py.template` used `port=${api_port}` but Dockerfile `EXPOSE 8000` and health check both use 8000
- **Files**: `src/configurable_agents/deploy/templates/server.py.template`, `docker-compose.yml.template`
- **Fix**: Hardcoded container internal port to 8000 (`port=8000`), updated compose port mappings to `${api_port}:8000` and `${mlflow_port}:5000`

### Minor: Deploy endpoint documentation mismatch

The CLI prints "API: http://localhost:{port}/execute" but the actual endpoint is `/run`. Cosmetic only — the `/docs` Swagger page shows the correct endpoint.
