# CLI Reference Guide

> **Source**: `src/configurable_agents/cli.py` (single file, ~2975 lines)
>
> **Entry points**:
> - `configurable-agents` (installed via `pip install -e .`)
> - `python -m configurable_agents` (module invocation)
>
> **Last verified**: 2026-02-09

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
| `workflow-registry start` | Start the workflow registry server | Registry |
| `workflow-registry list` | List registered workflows | Registry |
| `workflow-registry cleanup` | Clean up expired workflows | Registry |

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
| `--enable-profiling` | | off | Capture node timing data in MLFlow |

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
configurable-agents run workflow.yaml --verbose --enable-profiling
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
- `/workflows` - Workflow listing
- `/agents` - Agent listing
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

**Note**: Workflow must have been run with `--enable-profiling` to capture timing data.

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

## Workflow Registry Commands

### `workflow-registry start` - Start Registry Server

Starts the workflow registry FastAPI server for distributed workflow coordination.

```
configurable-agents workflow-registry start [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--host` | | `0.0.0.0` | Host to bind to |
| `--port` | | `9000` | Port to listen on |
| `--db-url` | | `sqlite:///agent_registry.db` | Database URL |
| `--verbose` | `-v` | off | Enable verbose output |

---

### `workflow-registry list` - List Workflows

Lists all registered workflows from the registry database.

```
configurable-agents workflow-registry list [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--db-url` | | `sqlite:///agent_registry.db` | Database URL |
| `--include-dead` | | off | Include expired/dead workflows |
| `--verbose` | `-v` | off | Enable verbose output |

**Output columns**: Workflow ID, Name, Host:Port, Last Heartbeat, Status (Alive/Dead)

---

### `workflow-registry cleanup` - Remove Expired Workflows

Manually triggers deletion of expired workflows from the registry.

```
configurable-agents workflow-registry cleanup [OPTIONS]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--db-url` | | `sqlite:///agent_registry.db` | Database URL |
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
| Workflow Registry | 9000 | `workflow-registry start` |

---

## CLI Verification Status

> Manually tested on 2026-02-09 (Windows, Python 3.x, dev branch @ `3ce357c`).

| Command | Tested | Works | Notes |
|---------|--------|-------|-------|
| `--version` | 2026-02-09 | YES | Shows `0.1.0-dev` |
| `--help` | 2026-02-09 | YES | Lists all 13 commands with examples |
| `run` | 2026-02-09 | YES | Tested: basic, multi-node, conditional, parallel, loop. All pass. Error handling correct for missing files, bad inputs, missing required fields |
| `validate` | 2026-02-09 | YES | Valid configs pass, missing file caught, malformed YAML gives clear error with fix guidance |
| `deploy --generate` | 2026-02-09 | YES | Generates 10 artifacts. `--no-mlflow`, `--name` flags work. Missing file caught |
| `deploy` (full Docker) | 2026-02-09 | YES | Full Docker build+run works. Container health, /docs, /schema, /run all respond correctly. See BF-008 below |
| `ui` | - | SKIP | UI phase — requires long-running server |
| `dashboard` | - | SKIP | UI phase — requires long-running server |
| `chat` | - | SKIP | UI phase — requires Gradio + long-running server |
| `webhooks` | 2026-02-09 | YES | Fixed (was BF-007). Server starts, `/` and `/webhooks/health` respond correctly |
| `report costs` | 2026-02-09 | YES | Works with filters, empty result handled gracefully |
| `cost-report` | 2026-02-09 | YES | Rich table renders correctly, shows $0 when no cost data |
| `profile-report` | 2026-02-09 | YES | Correctly reports "No runs found" when no profiling data |
| `observability status` | 2026-02-09 | YES | Shows connection status, experiment count, recent activity |
| `observability cost-report` | 2026-02-09 | YES | Alias works, identical output to `cost-report` |
| `observability profile-report` | 2026-02-09 | YES | Alias works, identical output to `profile-report` |
| `workflow-registry start` | 2026-02-09 | YES | Server starts, listens on configured port (renamed from agent-registry) |
| `workflow-registry list` | 2026-02-09 | YES | Shows "No workflows found" on empty DB |
| `workflow-registry cleanup` | 2026-02-09 | YES | Shows "No expired workflows found" on empty DB |
| ~~`optimization *`~~ | 2026-02-10 | REMOVED | Optimization module removed — redesign planned with MLflow 3.9 GenAI + DSPy |

### All `--help` subcommands verified

All 13 top-level commands and their subcommands produce correct `--help` output (2026-02-09).

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
