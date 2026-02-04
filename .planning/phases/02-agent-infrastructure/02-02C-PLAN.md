---
phase: 02-agent-infrastructure
plan: 02C
type: execute
wave: 2
depends_on: ["02-02A", "02-02B"]
files_modified:
  - src/configurable_agents/cli.py
  - tests/observability/test_cli_commands.py
autonomous: true

must_haves:
  truths:
    - "CLI command 'configurable-agents cost-report' displays unified cost breakdown by provider"
    - "cost-report shows Provider/Model, Tokens, Cost USD, and Calls columns"
    - "cost-report highlights most expensive provider in output"
    - "CLI command 'configurable-agents profile-report' displays bottleneck analysis"
    - "profile-report shows Node ID, Avg Duration, Total Duration, Calls, and % of Total"
    - "profile-report highlights slowest node and bottlenecks (>50%)"
    - "CLI command 'configurable-agents observability status' shows MLFlow connection"
    - "'run' command accepts --enable-profiling flag for ad-hoc performance investigation"
  artifacts:
    - path: "src/configurable_agents/cli.py"
      provides: "CLI commands for cost and profiling reports"
      contains: "cost-report, profile-report, observability command groups"
    - path: "tests/observability/test_cli_commands.py"
      provides: "CLI command tests"
      min_lines: 100
  key_links:
    - from: "src/configurable_agents/cli.py"
      to: "src/configurable_agents/observability/multi_provider_tracker.py"
      via: "generate_cost_report import for cost-report command"
      pattern: "from configurable_agents.observability.multi_provider_tracker import generate_cost_report"
    - from: "src/configurable_agents/cli.py"
      to: "src/configurable_agents/runtime/profiler.py"
      via: "BottleneckAnalyzer import for profile-report command"
      pattern: "from configurable_agents.runtime.profiler import BottleneckAnalyzer"
---

<objective>
Add CLI commands for cost and profiling reports.

**Purpose:** Provide user-friendly CLI commands for viewing multi-provider cost breakdowns and performance profiling data. Users can run cost-report to see expenses by provider and profile-report to identify bottlenecks. Also adds --enable-profiling flag to run command for ad-hoc performance investigation.

**Output:**
- cost-report CLI command with formatted table output
- profile-report CLI command with bottleneck analysis
- observability command group for status/check subcommands
- --enable-profiling flag on run command
- Comprehensive CLI command tests
</objective>

<execution_context>
@C:\Users\ghost\.claude\get-shit-done/workflows/execute-plan.md
@C:\Users\ghost\.claude\get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02-agent-infrastructure/02-RESEARCH.md
@.planning/phases/02-agent-infrastructure/02-02A-SUMMARY.md
@.planning/phases/02-agent-infrastructure/02-02B-SUMMARY.md

# Existing infrastructure
@src/configurable_agents/observability/multi_provider_tracker.py
@src/configurable_agents/runtime/profiler.py
@src/configurable_agents/cli.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add CLI commands for cost and profiling reports</name>
  <files>src/configurable_agents/cli.py</files>
  <action>
Add CLI commands for observability reports:

**Update cli.py**:

1. Add `cost-report` command:
   ```bash
   configurable-agents cost-report --experiment <name> [--mlflow-uri <uri>]
   ```
   - Arguments: `--experiment` (required), `--mlflow-uri` (optional, default from config)
   - Calls `generate_cost_report(experiment_name, mlflow_uri)`
   - Prints formatted table using Rich library
   - Table columns: Provider/Model, Tokens, Cost USD, Calls
   - Shows totals at bottom (Total Cost, Total Tokens)
   - Highlights most expensive provider with bold/yellow
   - Example output:
     ```
     Cost Report: experiment-name
     ┏━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━┓
     ┃ Provider/Model ┃ Tokens  ┃ Cost USD  ┃ Calls┃
     ┡━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━┩
     │ openai/gpt-4o   │ 6,000   │ $0.30     │ 5    │
     │ anthropic/claude │ 4,000   │ $0.20     │ 3    │
     ├─────────────────┼─────────┼───────────┼──────┤
     │ TOTAL           │ 10,000  │ $0.50     │ 8    │
     └─────────────────┴─────────┴───────────┴──────┘
     ```

2. Add `profile-report` command:
   ```bash
   configurable-agents profile-report [--run-id <id>] [--mlflow-uri <uri>]
   ```
   - Arguments: `--run-id` (optional, default latest run), `--mlflow-uri` (optional)
   - Queries MLFlow for `node_*_duration_ms` and `node_*_cost_usd` metrics
   - Prints bottleneck analysis table using Rich library
   - Table columns: Node ID, Avg Duration (ms), Total Duration (ms), Calls, % of Total, Cost USD
   - Highlights slowest node with bold/red
   - Highlights bottlenecks (>50%) with yellow
   - Example output:
     ```
     Profile Report: run-id
     ┏━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
     ┃ Node ID  ┃ Avg Duration┃ Total Duration┃ Calls┃ % of Total┃ Cost USD ┃
     ┡━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
     │ node_1   │ 150.0      │ 300.0        │ 2    │ 85.7%     │ $0.05    │
     │ node_2   │ 50.0       │ 50.0         │ 1    │ 14.3%     │ $0.01    │
     ├──────────┼────────────┼──────────────┼──────┼──────────┼──────────┤
     │ TOTAL    │ -          │ 350.0        │ 3    │ 100.0%    │ $0.06    │
     └──────────┴────────────┴──────────────┴──────┴──────────┴──────────┘

     ⚠ Slowest node: node_1 (150.0ms avg)
     ⚠ Bottlenecks (>50% of total time):
       • node_1: 85.7%
     ```

3. Add `observability` command group:
   ```bash
   configurable-agents observability [--mlflow-uri <uri>] <subcommand>
   ```
   - Subcommands: `status`, `cost-report`, `profile-report`
   - `status` subcommand:
     - Shows MLFlow connection status (connected/disconnected)
     - Shows MLFlow URI
     - Shows recent run count (last 24 hours)
     - Shows available experiments
   - `cost-report` subcommand: alias to main cost-report command
   - `profile-report` subcommand: alias to main profile-report command

4. Add `--enable-profiling` flag to `run` command:
   - When set, enables BottleneckAnalyzer for that run
   - Sets environment variable or passes flag to executor
   - Useful for ad-hoc performance investigation

Use Rich library for formatted tables (already used in project).
Reference: Existing CLI command patterns in cli.py.
  </action>
  <verify>
Step 1: `python -m configurable_agents cost-report --help`

Expected: Shows cost-report command with --experiment and --mlflow-uri arguments.

Step 2: `python -m configurable_agents profile-report --help`

Expected: Shows profile-report command with --run-id and --mlflow-uri arguments.

Step 3: `python -m configurable_agents observability --help`

Expected: Shows observability command group with status/cost-report/profile-report subcommands.

Step 4: `python -m configurable_agents observability status --help`

Expected: Shows status subcommand arguments.

Step 5: Verify --enable-profiling flag on run command:
```bash
python -m configurable_agents run --help | grep -i profiling
```
Expected: Shows --enable-profiling flag description.
  </verify>
  <done>
CLI commands added for cost-report/profile-report/observability, Rich tables display cost and timing data, cost-report shows per-provider breakdown with highlighted most expensive, profile-report shows bottleneck analysis with highlighted slowest, observability status shows MLFlow connection and recent runs, --enable-profiling flag added to run command.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add CLI command tests</name>
  <files>tests/observability/test_cli_commands.py</files>
  <action>
Create tests for CLI observability commands:

**Create tests/observability/test_cli_commands.py**:

- `test_cost_report_command_exists`: Verify typer command is registered
- `test_cost_report_requires_experiment`: Verify --experiment is required
- `test_cost_report_with_mock_mlflow`: Mock MLFlow client, verify table output
- `test_cost_report_highlights_most_expensive`: Verify highlighting logic
- `test_cost_report_shows_totals`: Verify totals row is displayed
- `test_profile_report_command_exists`: Verify typer command is registered
- `test_profile_report_defaults_to_latest_run`: Verify default run-id behavior
- `test_profile_report_with_mock_mlflow`: Mock MLFlow client, verify table output
- `test_profile_report_highlights_slowest_node`: Verify highlighting logic
- `test_profile_report_shows_bottlenecks`: Verify bottleneck section displayed
- `test_observability_status_command`: Verify status shows MLFlow connection
- `test_observability_status_shows_recent_runs`: Verify recent run count
- `test_enable_profiling_flag`: Verify --enable-profiling flag is parsed

Use pytest with:
- typer.testing.CliRunner for CLI testing
- unittest.mock for MLFlow API mocking
- rich.console.Console capture for table output verification

Reference: Existing test patterns in tests/core/test_parallel.py.
  </action>
  <verify>
Step 1: `pytest tests/observability/test_cli_commands.py -v`

Expected: All CLI command tests pass.

Step 2: `pytest tests/observability/test_cli_commands.py -k "test_cost_report" -v`

Expected: All cost-report tests pass.

Step 3: `pytest tests/observability/test_cli_commands.py -k "test_profile_report" -v`

Expected: All profile-report tests pass.

Step 4: `pytest tests/observability/test_cli_commands.py -k "test_observability" -v`

Expected: All observability command tests pass.

Step 5: `pytest tests/observability/test_cli_commands.py --cov=src/configurable_agents/cli --cov-report=term-missing`

Expected: Coverage for CLI commands >80%.
  </verify>
  <done>
CLI command tests created with cost-report/profile-report/observability coverage, MLFlow mocking correctly simulates API responses, Rich table output captured and verified, highlighting logic tested (most expensive, slowest, bottlenecks), status command tested with MLFlow connection, --enable-profiling flag test passes.
  </done>
</task>

</tasks>

<verification>
After completing all tasks:

1. **Command Help Verification**:
   - Run: `python -m configurable_agents cost-report --help`
   - Run: `python -m configurable_agents profile-report --help`
   - Run: `python -m configurable_agents observability --help`
   - Run: `python -m configurable_agents observability status --help`
   - Verify all arguments are documented

2. **Cost Report Verification**:
   - Run workflow with multiple providers
   - Run: `python -m configurable_agents cost-report --experiment <name>`
   - Verify table shows Provider/Model, Tokens, Cost USD, Calls
   - Verify totals row displayed
   - Verify most expensive provider highlighted

3. **Profile Report Verification**:
   - Run workflow with --enable-profiling flag
   - Run: `python -m configurable_agents profile-report`
   - Verify table shows Node ID, Avg Duration, Total Duration, Calls, % of Total, Cost USD
   - Verify slowest node highlighted
   - Verify bottlenecks section displayed

4. **Observability Status Verification**:
   - Run: `python -m configurable_agents observability status`
   - Verify MLFlow connection status shown
   - Verify MLFlow URI displayed
   - Verify recent run count shown

5. **Test Coverage Verification**:
   - Run all CLI command tests
   - Verify coverage >80%
</verification>

<success_criteria>
**Plan Success Criteria Met:**
1. cost-report command displays unified cost breakdown by provider
2. cost-report shows Provider/Model, Tokens, Cost USD, Calls columns
3. cost-report highlights most expensive provider
4. profile-report command displays bottleneck analysis
5. profile-report shows Node ID, Avg Duration, Total Duration, Calls, % of Total
6. profile-report highlights slowest node and bottlenecks (>50%)
7. observability status command shows MLFlow connection state
8. --enable-profiling flag on run command enables profiling
9. All CLI tests pass with >80% coverage
</success_criteria>

<output>
After completion, create `.planning/phases/02-agent-infrastructure/02-02C-SUMMARY.md` with:
- Frontmatter (phase, plan, wave, status, completed_at, tech_added, patterns_established, key_files)
- Summary of changes (CLI commands, tests)
- Verification results (command help, cost report, profile report, status)
- Phase 2 completion summary (all 02-01 and 02-02 plans complete)
- Next steps link (Phase 3: Interfaces and Triggers)
</output>
