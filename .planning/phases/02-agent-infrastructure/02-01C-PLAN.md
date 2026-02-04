---
phase: 02-agent-infrastructure
plan: 01C
type: execute
wave: 3
depends_on: ["02-01B"]
files_modified:
  - src/configurable_agents/cli.py
  - tests/registry/test_client.py
  - tests/registry/test_server.py
  - tests/registry/test_ttl_expiry.py
autonomous: true

must_haves:
  truths:
    - "CLI command 'configurable-agents agent-registry start' runs uvicorn with AgentRegistryServer"
    - "CLI command 'configurable-agents agent-registry list' displays registered agents in table format"
    - "CLI command 'configurable-agents agent-registry cleanup' reports count of expired agents deleted"
    - "Registry client tests cover registration, heartbeat loop, and deregistration"
    - "Registry server tests cover all endpoints (register, heartbeat, list, get, delete)"
    - "TTL expiry tests verify AgentRecord.is_alive() and delete_expired() behavior"
  artifacts:
    - path: "src/configurable_agents/cli.py"
      provides: "CLI commands for agent registry management"
      contains: "agent-registry command group with start/list/cleanup subcommands"
    - path: "tests/registry/test_client.py"
      provides: "AgentRegistryClient unit tests"
      min_lines: 50
    - path: "tests/registry/test_server.py"
      provides: "AgentRegistryServer endpoint tests"
      min_lines: 100
    - path: "tests/registry/test_ttl_expiry.py"
      provides: "TTL expiry logic tests"
      min_lines: 50
  key_links:
    - from: "src/configurable_agents/cli.py"
      to: "src/configurable_agents/registry/server.py"
      via: "AgentRegistryServer import for CLI start command"
      pattern: "from configurable_agents.registry import AgentRegistryServer"
---

<objective>
Add CLI commands for registry management and comprehensive test suite.

**Purpose:** Provide user-friendly CLI commands for running and managing the agent registry server. Also create comprehensive tests for registry client, server, and TTL expiry logic to ensure reliability. This completes the agent registry feature with both management tools and test coverage.

**Output:**
- CLI command group: agent-registry with start, list, cleanup subcommands
- Registry client tests (registration, heartbeat loop, deregistration, error handling)
- Registry server tests (all endpoints, idempotent registration, background cleanup)
- TTL expiry tests (is_alive(), delete_expired(), edge cases)
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
@.planning/phases/02-agent-infrastructure/02-01A-SUMMARY.md
@.planning/phases/02-agent-infrastructure/02-01B-SUMMARY.md

# Existing infrastructure
@src/configurable_agents/registry/server.py
@src/configurable_agents/registry/client.py
@src/configurable_agents/cli.py
@tests/core/test_parallel.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create CLI command for standalone registry server</name>
  <files>src/configurable_agents/cli.py</files>
  <action>
Add CLI command to run standalone agent registry server:

**Update cli.py**:

Add new command group `agent-registry` with subcommands:
- `configurable-agents agent-registry start` - Start registry server
- `configurable-agents agent-registry list` - List registered agents
- `configurable-agents agent-registry cleanup` - Manually trigger cleanup

Implementation details:
1. Use Typer for CLI argument parsing (existing pattern)
2. `start` subcommand:
   - Arguments: `--host 0.0.0.0`, `--port 9000`, `--db-url sqlite:///agent_registry.db`
   - Creates AgentRegistryRepository from db_url
   - Creates AgentRegistryServer with repo
   - Runs uvicorn with server's app
3. `list` subcommand:
   - Arguments: `--db-url`, `--include-dead`
   - Queries repo and prints table of agents using Rich library
   - Table columns: Agent ID, Name, Host:Port, Last Heartbeat, Status (Alive/Dead)
4. `cleanup` subcommand:
   - Arguments: `--db-url`
   - Calls repo.delete_expired() and prints count

Reference: Existing CLI patterns in cli.py (run/validate/deploy commands).
  </action>
  <verify>
Step 1: `python -m configurable_agents agent-registry --help`

Expected: Shows agent-registry command group with available subcommands.

Step 2: `python -m configurable_agents agent-registry start --help`

Expected: Shows start command arguments (host, port, db-url).

Step 3: `python -m configurable_agents agent-registry list --help`

Expected: Shows list command arguments (db-url, include-dead).
  </verify>
  <done>
CLI command group added for agent-registry with start/list/cleanup subcommands, start command runs uvicorn with FastAPI app, list command displays agent table using Rich, cleanup command manually triggers expired agent deletion.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add registry integration tests</name>
  <files>tests/registry/test_client.py, tests/registry/test_server.py, tests/registry/test_ttl_expiry.py</files>
  <action>
Create tests for agent registry functionality:

1. **Create tests/registry/__init__.py**

2. **Create tests/registry/test_client.py**:
   - `test_client_initialization`: Verify AgentRegistryClient stores parameters correctly
   - `test_register`: Mock HTTP response, verify POST to /agents/register with correct payload
   - `test_heartbeat_loop_starts`: Verify start_heartbeat_loop() creates background task
   - `test_heartbeat_loop_cancellation`: Verify loop exits on CancelledError
   - `test_heartbeat_retry_on_error`: Verify HTTP errors trigger 5-second sleep and retry
   - `test_deregister`: Verify DELETE to /agents/{agent_id} and task cancellation

3. **Create tests/registry/test_server.py**:
   - `test_register_creates_agent`: POST /agents/register creates new AgentRecord
   - `test_register_idempotent`: POST with existing agent_id updates instead of duplicating
   - `test_heartbeat_updates_timestamp`: POST /agents/{id}/heartbeat updates last_heartbeat
   - `test_list_agents_filters_dead`: GET /agents?include_dead=false filters expired agents
   - `test_list_agents_includes_dead`: GET /agents?include_dead=true returns all agents
   - `test_get_agent`: GET /agents/{id} returns specific agent or 404
   - `test_delete_agent`: DELETE /agents/{id} removes agent from registry
   - `test_health_endpoint`: GET /health returns 200 with status
   - `test_background_cleanup`: Verify cleanup task runs and removes expired agents

4. **Create tests/registry/test_ttl_expiry.py**:
   - `test_is_alive_with_valid_heartbeat`: AgentRecord.is_alive() returns True when heartbeat is recent
   - `test_is_alive_with_expired_heartbeat`: Returns False when heartbeat + TTL < now
   - `test_delete_expired_removes_only_expired`: Verify expired agents deleted, valid agents remain
   - `test_ttl_zero`: Edge case - TTL=0 means always expired
   - `test_negative_ttl`: Edge case - negative TTL handled gracefully

Use pytest with httpx.TestClient (async) for server tests, unittest.mock for client HTTP tests.

Reference: Existing test patterns in tests/core/test_parallel.py.
  </action>
  <verify>
Step 1: `pytest tests/registry/ -v`

Expected: All tests pass, no errors.

Step 2: `pytest tests/registry/test_client.py -k "test_register" -v`

Expected: Registration tests pass.

Step 3: `pytest tests/registry/test_server.py -k "test_heartbeat" -v`

Expected: Heartbeat tests pass.

Step 4: `pytest tests/registry/test_ttl_expiry.py -v`

Expected: TTL expiry tests pass.

Step 5: `pytest tests/registry/ --cov=src/configurable_agents/registry --cov-report=term-missing`

Expected: Coverage >80% for registry module.
  </verify>
  <done>
Registry test suite created with client/server/model tests, all tests pass, coverage >80% for registry module, HTTP mocking correctly simulates API responses, async tests properly handle TestClient.
  </done>
</task>

</tasks>

<verification>
After completing all tasks:

1. **CLI Verification**:
   - Run: `python -m configurable_agents agent-registry --help`
   - Verify help shows start, list, cleanup subcommands
   - Run: `python -m configurable_agents agent-registry start --help`
   - Verify all arguments are documented

2. **Start Command Verification**:
   - Run: `python -m configurable_agents agent-registry start --port 9999 --db-url /tmp/test_registry.db`
   - Verify uvicorn starts without errors
   - Press Ctrl+C to stop

3. **List Command Verification**:
   - Start a registry server: `python -m configurable_agents agent-registry start --port 9999`
   - In another terminal, register an agent via curl or test client
   - Run: `python -m configurable_agents agent-registry list --db-url /tmp/test_registry.db`
   - Verify agent appears in table

4. **Test Verification**:
   - Run: `pytest tests/registry/ -v`
   - Verify all tests pass
   - Run coverage report: `pytest tests/registry/ --cov=src/configurable_agents/registry`
   - Verify coverage >80%
</verification>

<success_criteria>
**Plan Success Criteria Met:**
1. CLI agent-registry command group exists with start/list/cleanup subcommands
2. start command runs uvicorn with AgentRegistryServer app
3. list command displays agent table with Agent ID, Name, Host:Port, Last Heartbeat, Status
4. cleanup command reports count of expired agents deleted
5. Registry client tests cover registration, heartbeat loop, error retry, and deregistration
6. Registry server tests cover all endpoints with idempotent registration verification
7. TTL expiry tests verify is_alive() and delete_expired() with edge cases
8. Overall test coverage >80% for registry module
</success_criteria>

<output>
After completion, create `.planning/phases/02-agent-infrastructure/02-01C-SUMMARY.md` with:
- Frontmatter (phase, plan, wave, status, completed_at, tech_added, patterns_established, key_files)
- Summary of changes (CLI commands, test suite)
- Verification results (CLI help, start command, list command, test suite)
- Agent Registry (01A-01C) completion summary
- Next steps link (02-02A: Multi-Provider Cost Tracking)
</output>
