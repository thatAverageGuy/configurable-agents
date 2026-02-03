---
phase: 02-agent-infrastructure
plan: 02C
subsystem: observability
tags: [cli, rich, mlflow, cost-tracking, profiling, bottleneck-analysis]

# Dependency graph
requires:
  - phase: 02-02A
    provides: MultiProviderCostTracker and generate_cost_report function
  - phase: 02-02B
    provides: BottleneckAnalyzer and profiling decorator
provides:
  - CLI commands for cost-report, profile-report, and observability status
  - Rich-formatted table output for cost and profiling data
  - --enable-profiling flag on run command for ad-hoc performance investigation
affects: [03-interfaces-triggers]

# Tech tracking
tech-stack:
  added: [rich>=13.0.0]
  patterns: [CLI command groups, Rich table formatting, MLFlow query via CLI]

key-files:
  created: [tests/observability/test_cli_commands.py]
  modified: [pyproject.toml, src/configurable_agents/cli.py]

key-decisions:
  - "Rich library for formatted table output - provides visually appealing CLI tables with highlighting"
  - "Lazy MLFlow import in CLI functions - allows CLI to work without MLFlow installed for help/argument parsing"
  - "Environment variable pattern for --enable-profiling - enables runtime profiling control without code changes"

patterns-established:
  - "CLI command groups: observability command with status/cost-report/profile-report subcommands"
  - "Rich table highlighting: most expensive (yellow), slowest node (red), bottlenecks (>50% in yellow)"
  - "CLI alias pattern: observability subcommands reuse main command functions"

# Metrics
duration: 18min
completed: 2026-02-03
---

# Phase 2 Plan 2C: Observability CLI Commands Summary

**Cost and profiling CLI commands with Rich-formatted tables, bottleneck highlighting, and MLFlow integration**

## Performance

- **Duration:** 18 min
- **Started:** 2026-02-03T08:55:18Z
- **Completed:** 2026-02-03T08:73:00Z
- **Tasks:** 2/2 complete
- **Files modified:** 3

## Accomplishments

- Added `cost-report` CLI command with provider/model breakdown and most expensive highlighting
- Added `profile-report` CLI command with bottleneck analysis and slowest node highlighting
- Added `observability` command group with status, cost-report, and profile-report subcommands
- Added `--enable-profiling` flag to `run` command for ad-hoc performance investigation
- Created comprehensive CLI command tests (24 tests, 614 lines)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add CLI commands for cost and profiling reports** - `13b899f` (feat)
2. **Task 2: Add CLI command tests** - `0c37577` (test)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified

- `pyproject.toml` - Added rich>=13.0.0 dependency
- `src/configurable_agents/cli.py` - Added cost-report, profile-report, observability commands and --enable-profiling flag
- `tests/observability/test_cli_commands.py` - Created comprehensive CLI test suite (614 lines)

## CLI Commands Added

### cost-report
```bash
configurable-agents cost-report --experiment <name> [--mlflow-uri <uri>]
```
- Displays unified cost breakdown by provider/model
- Shows Provider/Model, Tokens, Cost USD, Calls columns
- Highlights most expensive provider in bold/yellow
- Shows totals row (Total Cost, Total Tokens)

### profile-report
```bash
configurable-agents profile-report [--run-id <id>] [--mlflow-uri <uri>]
```
- Displays bottleneck analysis for workflow runs
- Shows Node ID, Avg Duration, Total Duration, Calls, % of Total, Cost USD
- Highlights slowest node in bold/red
- Highlights bottlenecks (>50%) in yellow
- Defaults to latest run if --run-id not specified

### observability command group
```bash
configurable-agents observability status [--mlflow-uri <uri>]
configurable-agents observability cost-report --experiment <name>
configurable-agents observability profile-report [--run-id <id>]
```
- `status`: Shows MLFlow connection state, URI, and recent run count
- `cost-report`: Alias to main cost-report command
- `profile-report`: Alias to main profile-report command

### --enable-profiling flag
```bash
configurable-agents run workflow.yaml --enable-profiling
```
- Sets CONFIGURABLE_AGENTS_PROFILING=1 environment variable
- Enables BottleneckAnalyzer for the workflow run
- Useful for ad-hoc performance investigation

## Decisions Made

- Used Rich library for formatted table output - provides visually appealing tables with color highlighting
- Lazy MLFlow import in CLI functions - allows CLI help to work without MLFlow installed
- Environment variable pattern for profiling flag - enables runtime control without code changes
- Command alias pattern via observability subcommands - provides logical grouping while reusing implementation

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

### Command Help Verification
- `python -m configurable_agents cost-report --help` - OK
- `python -m configurable_agents profile-report --help` - OK
- `python -m configurable_agents observability --help` - OK
- `python -m configurable_agents observability status --help` - OK
- `python -m configurable_agents run --help | grep -i profiling` - OK (shows --enable-profiling flag)

### Test Results
- All 24 CLI command tests pass
- Test file: 614 lines (exceeds 100 minimum)
- Tests cover: command registration, argument parsing, MLFlow mocking, table output, error handling

## Phase 2 Completion Summary

This plan (02-02C) completes the **Observability** sub-wave of Phase 2 (Agent Infrastructure). All Phase 2 plans are now complete:

**Phase 2 Plans Completed:**
- 02-01A: Agent Registry - Multi-process agent coordination
- 02-01B: Registry Client - FastAPI client for agent operations
- 02-01C: Agent Lifecycle - Heartbeat and cleanup mechanisms
- 02-02A: Multi-Provider Cost Tracking - Unified cost reporting across LLM providers
- 02-02B: Performance Profiling - Bottleneck detection and node timing
- 02-02C: Observability CLI Commands - Cost and profiling reports via CLI

**Phase 2 Deliverables:**
- Agent registry for multi-process coordination
- FastAPI client for registry operations
- Heartbeat-based lifecycle management
- Multi-provider cost tracking with MLFlow integration
- Performance profiling with bottleneck detection
- CLI commands for observability reports

## Next Phase Readiness

Phase 3 (Interfaces and Triggers) is ready to begin:
- Agent infrastructure is complete with registry, lifecycle, and observability
- Cost tracking and profiling are integrated with MLFlow
- CLI provides user-friendly access to observability data
- No blockers or concerns

**Next phase link:** [Phase 3: Interfaces and Triggers](../03-interfaces-triggers/)

---
*Phase: 02-agent-infrastructure*
*Completed: 2026-02-03*
