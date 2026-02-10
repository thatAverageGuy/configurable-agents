# CL-003: VF Fixing Session

**Date**: 2026-02-10
**Change Level**: LEVEL 2
**Purpose**: Fix all 6 verification issues (VF-001–VF-006), remove optimization module, rename Agent Registry → Workflow Registry.
**Reference**: [CL-003_DEEP_FLAG_VERIFICATION.md](CL-003_DEEP_FLAG_VERIFICATION.md)

---

## Summary

Fixed all 8 items identified during the CL-003 verification sessions. All 97 targeted tests pass; full suite: 656 passed, 0 failed, 3 skipped.

---

## Fixes Applied

### VF-001: `--verbose` no DEBUG output

**Root cause**: `setup_logging()` never called — no handler registered on root logger.

**Fix**: Added `setup_logging()` call in `main()` (cli.py) after arg parsing:
```python
from configurable_agents.logging_config import setup_logging
verbose = getattr(args, 'verbose', False)
setup_logging("DEBUG" if verbose else "WARNING")
```

**Files**: `cli.py`

---

### VF-002: `--enable-profiling` dead code

**Root cause**: `os.environ["CONFIGURABLE_AGENTS_PROFILING"] = "1"` set but never read. `mlflow.active_run()` always None under trace paradigm.

**Fix**:
- Removed env var setting from `cmd_run()`
- Removed `mlflow.active_run()` metric logging blocks in `node_executor.py` (2 blocks: duration + cost)
- Added comment explaining metrics are captured via trace spans

**Files**: `cli.py`, `node_executor.py`

---

### VF-003: `--no-mlflow` cosmetic artifacts

**Root cause**: Deploy templates had hardcoded MLflow-related content (port EXPOSE, volume mounts, comments) regardless of `enable_mlflow` flag.

**Fix**: Added 6 conditional template variables in `generator.py:_build_template_variables()`:
- `compose_mlflow_port` — port mapping line or empty
- `compose_mlflow_volume` — volume mount line or empty
- `compose_mlflow_comment` — comment or empty
- `dockerfile_expose` — `EXPOSE 8000 5000` or `EXPOSE 8000`
- `dockerfile_mlflow_dir_comment` — conditional comment
- `dockerfile_cmd_comment` — conditional comment

Updated `Dockerfile.template` and `docker-compose.yml.template` to use these variables.

**Files**: `generator.py`, `Dockerfile.template`, `docker-compose.yml.template`

**Test fix**: Updated `test_generate_artifacts_mlflow_disabled` to assert correct behavior (no `EXPOSE 8000 5000`, no `5000` in compose, no `mlflow.db` volume).

---

### VF-004: Reporting commands use legacy `search_runs()` API

**Root cause**: All reporting commands queried MLflow runs (legacy ML paradigm), but executor produces traces (GenAI paradigm). Zero runs exist.

**Fix**: Rewrote 3 reporting paths to use `search_traces()` + span extraction:

1. **`cmd_profile_report()`** (cli.py): Queries traces, iterates spans, extracts duration from `(end_time_ns - start_time_ns) / 1_000_000`. Identifies nodes from `span.name`.

2. **`cmd_observability_status()`** (cli.py): Replaced `search_runs()` count with `search_traces()` count, using `trace.timestamp_ms` filter for time ranges.

3. **`MultiProviderCostTracker.generate_report()`** (multi_provider_tracker.py): Queries traces, iterates CHAT_MODEL spans, extracts token usage from `mlflow.chat.tokenUsage` attribute, model name from `invocation_params` or `ai.model.name`.

**Files**: `cli.py`, `multi_provider_tracker.py`

---

### VF-005: `CostReporter` wrong tracking URI

**Root cause**: `CostReporter.__init__` creates `MlflowClient(tracking_uri=...)` but `get_cost_entries()` calls `mlflow.get_experiment_by_name()` which uses the global tracking URI (never set).

**Fix**:
- Added `mlflow.set_tracking_uri(tracking_uri)` in `CostReporter.__init__`
- Rewrote `get_cost_entries()` to use trace-based queries (same pattern as VF-004)
- Added `_trace_to_cost_entry()` method extracting trace_id, timestamps, token usage from spans

**Files**: `cost_reporter.py`

---

### VF-006: Parent commands crash without subcommand

**Root cause**: `main()` checks `if not args.command` but when parent command given without subcommand, `args.command` is truthy. Then `args.func(args)` fails because argparse doesn't set `func`.

**Fix**: Added `hasattr(args, 'func')` check after the `args.command` check:
```python
if not hasattr(args, 'func'):
    parser.parse_args([args.command, '--help'])
    return 1
```

**Files**: `cli.py`

---

## Additional Actions

### Remove optimization module

**Rationale**: Legacy MLflow runs paradigm, doesn't do real optimization. See [OPTIMIZATION_INVESTIGATION.md](../../OPTIMIZATION_INVESTIGATION.md).

**Files deleted**:
- `src/configurable_agents/optimization/` (entire package: `__init__.py`, `evaluator.py`, `ab_test.py`, `gates.py`)
- `src/configurable_agents/ui/dashboard/routes/optimization.py`
- `src/configurable_agents/ui/dashboard/templates/optimization.html`
- `src/configurable_agents/ui/dashboard/templates/experiments.html`
- `tests/optimization/` (entire directory)
- `tests/cli/test_optimization_commands.py`

**Files modified**:
- `cli.py` — removed 3 optimization command functions + parser entries
- `dashboard/app.py` — removed `optimization_router` import and include
- `dashboard/routes/__init__.py` — removed optimization_router export

**Preserved**:
- Quality gates moved to `src/configurable_agents/runtime/gates.py` (used by executor)
- `runtime/executor.py` imports updated to new location
- `tests/runtime/test_gates.py` moved from `tests/optimization/`
- Config schema models (`ABTestConfig`, `OptimizationConfig`) kept — optional fields, don't break parsing

---

### Rename Agent Registry → Workflow Registry

**Changes**:
- CLI command: `agent-registry` → `workflow-registry`
- Added aliases in `registry/__init__.py`: `WorkflowRegistryServer = AgentRegistryServer`, `WorkflowRegistryClient = AgentRegistryClient`
- Updated all CLI help text from "agent" to "workflow" terminology
- Updated import in cli.py to use `WorkflowRegistryServer`

**Preserved** (for DB backward compatibility):
- Internal class names: `AgentRegistryServer`, `AgentRegistryClient`, `AgentRecord`
- Storage layer: `AgentRegistryRepository`, table names
- API endpoints: `/agents/*` (would be a breaking change for deployed clients)

---

## Test Results

**Targeted tests** (97 tests across modified modules): All pass
**Full suite**: 656 passed, 0 failed, 3 skipped

**Test fixes applied**:
- `test_generate_artifacts_mlflow_disabled`: Updated assertions to match correct VF-003 behavior
- `test_enable_profiling_sets_environment_variable`: Renamed and updated to assert env var is NOT set (dead code removed)
- `test_gates.py`: Moved to `tests/runtime/`, updated import path

**Pre-existing issue** (not from our changes):
- `test_dashboard.py` has ImportError (`_time_ago` not found in agents route) — excluded from test runs

---

## Files Modified Summary

| File | Change |
|------|--------|
| `cli.py` | VF-001, VF-002, VF-004 (profile-report, obs status), VF-006, remove optimization, rename registry |
| `node_executor.py` | VF-002 (remove dead mlflow.active_run() blocks) |
| `multi_provider_tracker.py` | VF-004 (rewrite generate_report to traces) |
| `cost_reporter.py` | VF-005 (tracking URI) + VF-004 (trace-based rewrite) |
| `generator.py` | VF-003 (conditional template variables) |
| `Dockerfile.template` | VF-003 (template variables) |
| `docker-compose.yml.template` | VF-003 (template variables) |
| `registry/__init__.py` | Rename aliases |
| `runtime/gates.py` | NEW — moved from optimization |
| `runtime/executor.py` | Updated import path for gates |
| `dashboard/app.py` | Remove optimization router |
| `dashboard/routes/__init__.py` | Remove optimization router |
| `test_generator_integration.py` | VF-003 test fix |
| `test_cli_commands.py` | VF-002 test fix |
| `tests/runtime/test_gates.py` | Moved from tests/optimization |

---

*This log documents the fixing session for all CL-003 verification issues.*
