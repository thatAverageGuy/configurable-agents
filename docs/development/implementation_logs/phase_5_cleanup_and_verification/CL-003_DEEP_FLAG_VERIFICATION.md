# CL-003: Deep Flag-by-Flag CLI Verification

**Date**: 2026-02-09
**Purpose**: Systematic verification of every CLI flag to confirm it does what it claims.
**Approach**: Run commands, inspect output, trace code paths. Log all issues found.
**Follow-up**: Issues logged here will be fixed in a **separate fixing session** (not during verification).

---

## Verification Status

| # | Flag / Feature | Status | Issue ID |
|---|---------------|--------|----------|
| 1 | `run --input key=value` | PASS (user confirmed) | — |
| 2 | `run --verbose` | ~~FAIL~~ → **FIXED** | VF-001 ✅ |
| 3 | `run --enable-profiling` | ~~FAIL~~ → **FIXED** | VF-002 ✅ |
| 4 | `deploy --api-port` | **PASS** | — |
| 5 | `deploy --mlflow-port` | **PASS** | — |
| 6 | `deploy --no-mlflow` | ~~PARTIAL~~ → **FIXED** | VF-003 ✅ |
| 7 | `deploy --timeout` | **PASS** | — |
| 8 | `deploy --name` | **PASS** | — |
| 9 | Observability data flow | ~~FAIL~~ → **FIXED** | VF-004 ✅ |
| 10 | Filter flags (experiment, period, breakdown) | ~~PARTIAL~~ → **FIXED** | VF-004 ✅, VF-005 ✅ |

---

## Issues Found

### VF-001: `--verbose` does not produce DEBUG output

**Severity**: Medium
**Affected commands**: ALL commands that accept `--verbose` (run, validate, deploy, report costs, cost-report, profile-report, observability status, registry start/list/cleanup, dashboard, webhooks, chat, ui, optimization evaluate/apply/ab-test)

#### What was tested
```bash
# Without --verbose
configurable-agents run test_configs/01_basic_linear.yaml --input message="Hello"

# With --verbose
configurable-agents run test_configs/01_basic_linear.yaml --input message="Hello" --verbose
```

#### Expected behavior
With `--verbose`, DEBUG-level log lines should appear showing:
- Config loading details
- State model building
- Graph compilation steps
- Node execution details
- Storage operations
- 20+ logger.debug() calls in executor.py alone

#### Actual behavior
Output is nearly identical with and without `--verbose`. No DEBUG lines appear at all.

#### Root cause analysis

**Code path**:
1. `cli.py:2373` — defines `--verbose` flag with help text "Enable verbose logging (DEBUG level)"
2. `cli.py:241` — passes `verbose=args.verbose` to `run_workflow()`
3. `executor.py:110-111` — `if verbose: logging.getLogger("configurable_agents").setLevel(logging.DEBUG)`
4. `executor.py:182,184,194,...` — 20+ `logger.debug()` calls exist throughout execution

**The bug**: `logging_config.py:9` defines `setup_logging()` which calls `logging.basicConfig()` to register a `StreamHandler`. But **nothing in the CLI path ever calls `setup_logging()`**. Without `basicConfig()` being called, the root logger has no handlers. Python's default `lastResort` handler only emits WARNING+ to stderr, so all DEBUG and INFO messages are silently dropped.

The logger's *level* is correctly set to DEBUG, but there's no *handler* to emit the messages.

**What `--verbose` actually does today** (partial functionality):
- Error tracebacks: In every `except` block, `if args.verbose: traceback.format_exc()` — this WORKS because it uses `print()` directly, not the logger
- `ensure_initialized(verbose=True)` — also broken, uses `logger.debug()` which has no handler
- Server commands (dashboard, webhooks, registry): sets uvicorn `log_level="info"` vs `"warning"` — this WORKS because uvicorn configures its own handlers

#### Fix plan

**Approach**: Call `setup_logging()` at the right level in the CLI entry point.

**Option A (Recommended) — Single call in main():**
In `cli.py`, in the `main()` function (after arg parsing, before dispatching to `cmd_*`), add:
```python
from configurable_agents.logging_config import setup_logging
setup_logging("DEBUG" if args.verbose else "INFO")
```
This ensures every command gets proper logging. ~2 lines added.

**Option B — Per-command setup:**
Call `setup_logging()` at the top of each `cmd_*` function. More invasive, no benefit.

**Recommendation**: Option A. LEVEL 1 change — ~2 lines in `cli.py` main().

**Secondary consideration**: The `logging_config.py` format string is `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"`. This will produce timestamp-prefixed lines that look different from the current CLI output (which uses `print_info`, `print_success` etc. with symbols). May want to consider whether DEBUG output should use a different format or if this is acceptable.

---

### VF-002: `--enable-profiling` is a complete no-op

**Severity**: High
**Affected commands**: `run`

#### What was tested
```bash
# With --enable-profiling
configurable-agents run test_configs/02_with_observability.yaml --input message="Hello" --enable-profiling

# Without --enable-profiling (identical behavior)
configurable-agents run test_configs/02_with_observability.yaml --input message="Hello"

# Checking profile-report after both
configurable-agents profile-report --mlflow-uri "sqlite:///mlflow_test.db"
```

#### Expected behavior
`--enable-profiling` should capture per-node timing data that `profile-report` can later display. The flag implies timing metrics are only captured when profiling is explicitly enabled.

#### Actual behavior
1. `--enable-profiling` sets `CONFIGURABLE_AGENTS_PROFILING=1` env var — but **nothing reads it**
2. `BottleneckAnalyzer` is **always** initialized unconditionally (`executor.py:299`)
3. Node timing IS recorded to the in-memory analyzer (`node_executor.py:589`) — but data is **discarded** after execution (not persisted anywhere queryable)
4. `profile-report` queries MLflow **runs** for `node_*_duration_ms` metrics — but no runs exist
5. Behavior with and without `--enable-profiling` is **identical**

#### Root cause analysis — 3 disconnected subsystems

**Subsystem A: The flag** (`cli.py:230-231`)
```python
os.environ["CONFIGURABLE_AGENTS_PROFILING"] = "1"
```
Sets env var. Nothing reads it. Dead code.

**Subsystem B: In-memory profiling** (`executor.py:299`, `node_executor.py:589`)
- `BottleneckAnalyzer` is always created and always records timing
- Summary is logged via `logger.info()` (also broken — see VF-001)
- Summary is stored in `workflows.db` as `bottleneck_info` JSON field in workflow run record
- But `profile-report` never queries `workflows.db` — it queries MLflow

**Subsystem C: MLflow metrics** (`node_executor.py:594-597`)
```python
if MLFLOW_AVAILABLE and mlflow.active_run():
    mlflow.log_metric(f"node_{node_id}_duration_ms", node_duration_ms)
```
Requires `mlflow.active_run()` to be not None. But the executor uses MLflow 3.9 **autolog/tracing** (creates traces, not runs). So `active_run()` is always None. Metrics never logged.

**Subsystem D: profile-report** (`cli.py:1000-1018`)
Queries MLflow runs for metrics matching `node_*_duration_ms`. Finds nothing because:
- No runs are created (only traces)
- No metrics are ever logged (active_run is None)

**Result**: The entire profiling pipeline is broken end-to-end. The three subsystems (flag, recording, reporting) are completely disconnected.

#### Fix plan

> **IMPORTANT**: Read `docs/development/OBSERVABILITY_REFERENCE.md` before fixing.
> We use MLflow 3.9 GenAI traces, NOT legacy ML runs. Never add `mlflow.start_run()`.

~~**Option A (WRONG — Legacy approach)**: Start explicit mlflow.start_run()~~ — This goes backwards to the ML paradigm. We use traces.

**Revised approach — LEVEL 2:**

1. **Remove dead code**: Delete `CONFIGURABLE_AGENTS_PROFILING` env var (cli.py:230-231). Remove `mlflow.active_run()` metric logging in node_executor.py:594-611 (dead path).

2. **Decide role of `--enable-profiling`**: Two options:
   - **Option A**: Remove the flag entirely. Profiling data is ALWAYS available in trace spans (duration via timestamps, tokens via `mlflow.chat.tokenUsage`). The `profile-report` command just reads it.
   - **Option B**: Keep the flag to control whether extra bottleneck analysis output is printed after execution (using BottleneckAnalyzer data which is already collected unconditionally).

3. **Rewrite `profile-report`**: Query `search_traces()` + extract span durations instead of `search_runs()` + `node_*_duration_ms` metrics. Reference: `MLFlowTracker.get_workflow_cost_summary()` already does trace-based span extraction correctly.

4. **BottleneckAnalyzer**: Keep as-is for in-memory analysis (already unconditional). Its data also persists to `workflows.db` `bottleneck_info`.

#### Additional discovery: `workflows.db`

The run created `workflows.db` (default SQLite storage). It stores:
- Workflow run records (with bottleneck_info JSON)
- Execution state per node
- Memory persistence

This file is created by ANY `run` command — it's the storage backend, not specific to profiling. The `--db-url` flag on other commands can customize its location.

---

### VF-003: `--no-mlflow` has cosmetic issues in generated artifacts

**Severity**: Low
**Affected commands**: `deploy`

#### What was tested
```bash
# Generate artifacts with --no-mlflow
configurable-agents deploy test_configs/01_basic_linear.yaml --generate --no-mlflow --output-dir deploy_no_mlflow

# Generate artifacts with mlflow enabled (default)
configurable-agents deploy test_configs/01_basic_linear.yaml --generate --api-port 9090 --mlflow-port 6060 --timeout 45 --name my-custom-agent
```

#### Verified deploy flags (4 PASS, 1 PARTIAL)

**PASS — `--api-port 9090`**: docker-compose.yml has `"9090:8000"`, server.py uses internal 8000. Correct.

**PASS — `--mlflow-port 6060`**: docker-compose.yml has `"6060:5000"`. Correct.

**PASS — `--timeout 45`**: server.py has `SYNC_TIMEOUT = 45`. Correct.

**PASS — `--name my-custom-agent`**: docker-compose.yml `container_name: my-custom-agent`, docker build tags `my-custom-agent:latest`. Correct.

**PARTIAL — `--no-mlflow`**: Core functionality works, cosmetic issues remain.

#### What works correctly with `--no-mlflow`
- Dockerfile CMD: `CMD python server.py` (no `mlflow ui &` prefix) — correct
- requirements.txt: `# mlflow disabled` instead of `mlflow>=3.9.0` — correct
- server.py: MLflow gated by `MLFLOW_TRACKING_URI` env var at runtime — correct (if env var not set, MLflow code is never executed)

#### Issues (cosmetic, not functional)
1. **docker-compose.yml** still has `"0:5000"` port mapping — should omit the port line entirely when MLflow disabled. Port 0 mapping is technically a bind to a random host port.
2. **docker-compose.yml** still has `# Persist MLFlow data` volume comment and `./mlflow.db:/app/mlflow.db` volume mount — unnecessary when MLflow disabled
3. **Dockerfile** still has `EXPOSE 8000 5000` — should only expose 8000 when MLflow disabled
4. **Dockerfile** still has comment `# Create data directory for MLflow SQLite DB` and `# Start server (MLFlow UI in background if enabled, FastAPI in foreground)` — misleading when MLflow disabled

#### Fix plan

**LEVEL 1** — Template generation in `generator.py` needs conditional blocks for docker-compose.yml and Dockerfile:
- When `enable_mlflow=False`: omit 5000 port, omit mlflow volume, clean up comments
- Affects `_build_template_vars()` to produce different compose/dockerfile fragments

**Not critical** — the container will work correctly because:
- server.py is properly gated by env var
- The `"0:5000"` port is harmless if nothing listens inside
- But it's confusing for users inspecting the generated files

---

### VF-004: Observability data flow is broken end-to-end (traces vs runs mismatch)

**Severity**: High
**Affected commands**: `cost-report`, `profile-report`, `observability status`, `report costs`

#### What was tested
```bash
# Run workflow with observability enabled
configurable-agents run test_configs/02_with_observability.yaml --input message="Hello for cost test"

# Then test all observability reporting commands
configurable-agents cost-report --experiment test_02_observability --mlflow-uri "sqlite:///mlflow_test.db"
configurable-agents profile-report --mlflow-uri "sqlite:///mlflow_test.db"
configurable-agents observability status --mlflow-uri "sqlite:///mlflow_test.db"
configurable-agents report costs --tracking-uri "sqlite:///mlflow_test.db" --experiment test_02_observability
```

#### Results per command

| Command | Connects? | Finds experiment? | Shows data? | Detail |
|---------|-----------|------------------|-------------|--------|
| `cost-report` | Yes | Yes | **No** — 0 tokens, $0, 0 calls | Queries runs, finds none |
| `profile-report` | Yes | Yes | **No** — "No runs found" | Queries runs for `node_*_duration_ms` metrics |
| `observability status` | Yes | Yes (2 experiments) | **No** — "No runs in last 24 hours" | Queries runs, finds none |
| `report costs` | Yes | **No** — experiment not found | **No** — crashes | See VF-005 |

#### Root cause

Same as VF-002: The executor uses MLflow 3.9 autolog/tracing which creates **traces**, not **runs**. All reporting commands query for **runs** with metrics. Zero runs exist.

**Data verified in DB**:
```python
client.search_runs(experiment_ids=["1"])  # 0 runs
client.search_traces(experiment_ids=["1"])  # 1 trace (with data)
```

The trace data IS there — it's just in the wrong table for the reporting commands to find.

#### Fix plan

> **IMPORTANT**: Read `docs/development/OBSERVABILITY_REFERENCE.md` before fixing.

~~Original plan: Fix VF-002 to start mlflow.start_run()~~ — WRONG, legacy approach.

**Correct fix — LEVEL 2**: Rewrite all reporting commands to use trace APIs:

1. **`cost-report`** (`cmd_cost_report` + `MultiProviderCostTracker.generate_report()`):
   - Replace `search_runs()` with `search_traces()`
   - Extract token/cost from CHAT_MODEL spans via `mlflow.chat.tokenUsage`
   - Reference implementation: `MLFlowTracker.get_workflow_cost_summary()` already does this correctly for a single trace

2. **`profile-report`** (`cmd_profile_report`):
   - Replace run metrics query with trace span duration extraction
   - Duration = `(span.end_time_ns - span.start_time_ns) / 1_000_000`
   - Node identity from `span.name` + `metadata.langgraph_node`

3. **`observability status`** (`cmd_observability_status`):
   - Replace `search_runs()` count with `search_traces()` count

4. **`report costs`** (`CostReporter`):
   - Full rewrite to trace-based queries, or deprecate in favor of `cost-report`

---

### VF-005: `report costs` uses wrong MLflow API for experiment lookup

**Severity**: Medium
**Affected commands**: `report costs` (older command)

#### What was tested
```bash
configurable-agents report costs --tracking-uri "sqlite:///mlflow_test.db" --experiment test_02_observability
```

#### Expected behavior
Should find the experiment and show cost data (even if zero).

#### Actual behavior
```
x Invalid input: Failed to get experiment 'test_02_observability': Experiment not found
```
The experiment DOES exist (verified by `cost-report` and `observability status`).

#### Root cause

`CostReporter.__init__` (`cost_reporter.py:94`):
```python
self.client = MlflowClient(tracking_uri=tracking_uri)
```

`CostReporter.get_cost_entries` (`cost_reporter.py:123`):
```python
experiment = mlflow.get_experiment_by_name(experiment_name)
```

The `MlflowClient` is initialized with the correct URI, but `mlflow.get_experiment_by_name()` uses the **global** `mlflow` tracking URI (defaults to `./mlruns/`). The global URI is never set.

In contrast, the newer `cost-report` command calls `mlflow.set_tracking_uri(mlflow_uri)` before creating its client, which is why it works.

#### Fix plan

**LEVEL 1** — In `CostReporter.__init__`, add:
```python
mlflow.set_tracking_uri(tracking_uri)
```
Or change `get_cost_entries` to use `self.client.get_experiment_by_name()` instead of `mlflow.get_experiment_by_name()`.

**Note**: The `--period` and `--breakdown` flags on `report costs` couldn't be fully tested due to this bug blocking execution. The code logic for those filters (lines 687-756) looks correct but is untestable without the experiment lookup fix.

---

## File Artifact Tracking

| File | Created by | Purpose | Pre-existing? |
|------|-----------|---------|---------------|
| `mlflow.db` | BF-005 migration | MLflow tracking store (SQLite) | Yes — baseline |
| `workflows.db` | `run` command (storage factory) | Default SQLite storage for workflow runs, execution state, memory | Created on first `run` |
| `mlflow_test.db` | `02_with_observability.yaml` config | MLflow tracking for observability-enabled workflows | Created when config has `observability.mlflow.tracking_uri: "sqlite:///mlflow_test.db"` — cleaned up after test |

*Updated as new files are discovered during verification.*

---

---

## Round 2: Extended CLI Verification (2026-02-09)

Testing remaining CLI commands: `validate`, `webhooks`, `optimization`, `agent-registry`.

### Verification Status (Round 2)

| # | Command / Feature | Status | Issue ID |
|---|-------------------|--------|----------|
| 11 | `validate` (all paths) | **PASS** | — |
| 12 | `webhooks` (server, endpoints, CRUD) | **PASS** | — |
| 13 | `optimization` | **REMOVED** | Module deleted ✅ |
| 14 | `workflow-registry` (no subcommand) | ~~CRASH~~ → **FIXED** | VF-006 ✅ |
| 14 | `workflow-registry start/list/cleanup` | **PASS** | Renamed from agent-registry ✅ |

---

### Validate Command — PASS

**Tested**: Valid configs (basic + full-featured), missing file, broken YAML, schema-invalid config, `--verbose` on error.

| Test | Result |
|------|--------|
| `validate test_configs/01_basic_linear.yaml` | PASS — "Config is valid!" |
| `validate test_configs/12_full_featured.yaml` | PASS |
| `validate nonexistent_file.yaml` | PASS — Clear error + guidance |
| `validate broken.yaml` (bad YAML syntax) | PASS — Error with fix suggestions |
| `validate minimal.yaml` (schema-invalid) | PASS — Pydantic errors with field details |
| `validate broken.yaml --verbose` | PASS — Full traceback printed |

**Note**: `--strict` and `--format` flags listed in CONTEXT.md don't exist in the parser. The command only accepts `config_file` (positional) + `--verbose`. These were never implemented.

---

### Webhooks Command — PASS

**Tested**: Server startup with `--port`, all HTTP endpoints, platform detection, idempotency.

| Test | Result |
|------|--------|
| `webhooks --port 7899` | PASS — Binds to specified port |
| `GET /` (root) | PASS — Returns endpoint directory |
| `GET /webhooks/health` | PASS — Status + platform detection |
| `GET /docs` | PASS — Swagger UI loads |
| `POST /webhooks/generic` (with workflow) | PASS — Executes workflow, returns result |
| `POST /webhooks/generic` (missing workflow_name) | PASS — 400 error |
| `POST /webhooks/generic` (duplicate webhook_id) | PASS — 409 idempotency rejection |
| `POST /webhooks/whatsapp` (unconfigured) | PASS — 503 "not configured" |
| `POST /webhooks/telegram` (unconfigured) | PASS — 503 "not configured" |
| `POST /webhooks/register` (create) | PASS — Returns registration + secret |
| `GET /webhooks/registrations` (list) | PASS — Lists all registrations |
| `POST /webhooks/register` (duplicate) | PASS — 409 "already registered" |
| `DELETE /webhooks/registrations/{name}` | PASS — Deletes registration |

**Note**: Generated webhook URLs use `WEBHOOK_BASE_URL` env var (default `http://localhost:7862`), not the actual listening port. By design.

---

### Optimization Command — PARTIAL (module to be removed)

**Decision**: Remove entire optimization module. Current A/B test system uses legacy MLflow runs, doesn't do actual prompt optimization. Will redesign using MLflow 3.9 GenAI evaluation and potentially DSPy. See [OPTIMIZATION_INVESTIGATION.md](../../OPTIMIZATION_INVESTIGATION.md).

| Test | Result |
|------|--------|
| `optimization` (no subcommand) | **CRASH** — VF-006 |
| `optimization --help` | PASS — Lists 3 subcommands |
| `optimization evaluate --experiment nonexistent` | PASS — Clear error |
| `optimization evaluate --verbose` | PASS — Full traceback |
| `optimization apply-optimized --dry-run` | PASS — Error handling works |
| `optimization ab-test` (no ab_test in config) | PASS — Clear error + config example |

**Architecture note**: The optimization module is intentionally run-based (uses `mlflow.start_run()`), separate from the executor's trace-based paradigm. This is a design mismatch — the evaluator queries runs that only exist if A/B tests were run through the CLI, not from regular workflow executions.

---

### Agent Registry Command — PASS

**Decision**: Rename "Agent Registry" → "Workflow Registry" (what gets registered is deployed workflow containers, not LLM agents). Rename to be done during fixing session.

| Test | Result |
|------|--------|
| `agent-registry` (no subcommand) | **CRASH** — VF-006 |
| `agent-registry start --port 9100 --db-url` | PASS — Server starts, binds to port |
| `GET /health` | PASS — Returns agent counts |
| `POST /agents/register` | PASS — Creates record with timestamps |
| Re-register same agent (idempotent) | PASS — Updates fields, preserves `registered_at` |
| `GET /agents` (default: alive only) | PASS — Only alive agents |
| `GET /agents?include_dead=true` | PASS — Shows dead agents with `is_alive: false` |
| `GET /agents/{id}` | PASS — Returns full details |
| `POST /agents/{id}/heartbeat` | PASS — Updates `last_heartbeat` |
| TTL expiry (2s TTL agent) | PASS — Correctly marked dead after TTL |
| `DELETE /agents/{id}` | PASS — Removes from DB |
| 404 for nonexistent agent | PASS — Heartbeat, get, delete all return 404 |
| Orchestrator CRUD (register, list) | PASS |
| CLI `agent-registry list` | PASS — Rich table output |
| CLI `agent-registry list --include-dead` | PASS — Shows dead agents |
| CLI `agent-registry cleanup` | PASS — Deletes expired agents |

---

### VF-006: Parent commands with subparsers crash when no subcommand given

**Severity**: Low
**Affected commands**: `optimization`, `agent-registry`

#### What was tested
```bash
configurable-agents optimization
configurable-agents agent-registry
```

#### Expected behavior
Should display help text showing available subcommands.

#### Actual behavior
```
AttributeError: 'Namespace' object has no attribute 'func'
```

#### Root cause
`main()` in `cli.py:2966` checks `if not args.command` to show help. But when a parent command with subparsers is used without a subcommand, `args.command = "optimization"` (truthy), so it passes the check. Then `args.func(args)` fails because argparse doesn't set `func` when no subcommand is selected.

#### Fix plan
**LEVEL 1** — Add `hasattr(args, 'func')` check in `main()`:
```python
if not args.command:
    parser.print_help()
    return 1

if not hasattr(args, 'func'):
    # Parent command without subcommand — show subcommand help
    parser.parse_args([args.command, '--help'])
    return 1
```

---

## Summary

**Round 1**: 10 items verified — 5 PASS, 2 FAIL, 2 PARTIAL, 1 CRASH → **ALL FIXED** (2026-02-10)
**Round 2**: 4 commands verified — 2 PASS, 1 REMOVED, 1 PASS + VF-006 → **ALL FIXED** (2026-02-10)
**Round 3** (pending): 3 commands remaining — `dashboard`, `chat`, `ui`

**Total issues**: 6 (VF-001 through VF-006) — **ALL 6 FIXED** (2026-02-10)

**Additional actions completed** (2026-02-10):
- Optimization module removed entirely
- Agent Registry renamed to Workflow Registry

**Reference**: [UI_ARCHITECTURE.md](../../UI_ARCHITECTURE.md) — Read before Round 3 testing.

**Fixing details**: [CL-003_VF_FIXING_SESSION.md](CL-003_VF_FIXING_SESSION.md)

---

*This document is the single source of truth for all CLI verification. All Round 1 + 2 issues fixed. Round 3 (UI commands) pending.*
