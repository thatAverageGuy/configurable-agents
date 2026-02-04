# Phase 2 Plan 01B: Agent Registry Client and Deployment Generator Integration Summary

**Phase:** 02-agent-infrastructure
**Plan:** 01B
**Status:** complete
**Completed at:** 2026-02-03
**Wave:** 2
**Duration:** 7 minutes

## One-Liner

Agent registry client with TTL-based heartbeat loop and deployment generator integration for self-registering agent containers.

## Summary

Implemented the client-side component for agent self-registration and integrated it with the deployment artifact generator. Agents can now register themselves with the registry server on startup, send periodic heartbeats to maintain their registration, and deregister on shutdown.

The deployment generator now conditionally includes registry client code based on the `enable_registry` parameter, allowing agents to be deployed with or without registry integration.

### Key Changes

#### Agent Registry Client (`src/configurable_agents/registry/client.py`)
- **AgentRegistryClient** class with registration, heartbeat, and deregistration methods
- `register(metadata)` - POST to `/agents/register` with agent info
- `start_heartbeat_loop()` - starts background asyncio task for periodic heartbeats
- `_heartbeat()` - infinite loop with retry-on-error (5s sleep on HTTP errors)
- `deregister()` - cancels heartbeat task and DELETEs agent from registry
- `_get_host_port()` - auto-detects host/port from env vars (AGENT_HOST, AGENT_PORT) or defaults
- Async context manager support for clean shutdown
- Exported from `configurable_agents.registry` module

#### Deployment Generator Updates (`src/configurable_agents/deploy/generator.py`)
- Added `enable_registry`, `registry_url`, `agent_id` parameters to `generate()`
- Added registry-related template variables to `_build_template_variables()`:
  - `registry_import` - import line for AgentRegistryClient
  - `registry_client_init` - client initialization code
  - `registry_startup_handler` - FastAPI startup event handler
  - `registry_shutdown_handler` - FastAPI shutdown event handler
  - `health_check_endpoints` - /health/live and /health/ready endpoints
- Template variables are populated or empty based on `enable_registry` flag
- Validation: raises ValueError if enable_registry=True but registry_url missing

#### Template Updates
- **server.py.template**: Added `${registry_import}`, `${registry_client_init}`, `${registry_startup_handler}`, `${registry_shutdown_handler}`, `${health_check_endpoints}` placeholders
- **requirements.txt.template**: Added `httpx>=0.26.0` for async HTTP in registry client

## Verification Results

### Client Verification
```bash
# Import test
from configurable_agents.registry import AgentRegistryClient

# Client creation test
client = AgentRegistryClient('http://localhost:8000', 'test-agent')
# Client created with TTL: 60
# Client heartbeat interval: 20
```

### Generator Verification (enable_registry=True)
```bash
artifacts = generate_deployment_artifacts(
    'examples/simple_workflow.yaml',
    '/tmp/deploy',
    enable_registry=True,
    registry_url='http://localhost:9000',
    agent_id='test-agent'
)
```
Results:
- AgentRegistryClient import: True
- heartbeat_loop: True
- health endpoints: True
- registry_startup_handler: True
- registry_shutdown_handler: True

### Generator Verification (enable_registry=False)
Results:
- AgentRegistryClient import: False
- heartbeat_loop: False
- health endpoints: False
- registry_startup_handler: False
- registry_shutdown_handler: False

## Deviations from Plan

None - plan executed exactly as written.

## Authentication Gates

None encountered during this plan.

## Key Files

### Created
- `src/configurable_agents/registry/client.py` (253 lines) - AgentRegistryClient implementation

### Modified
- `src/configurable_agents/registry/__init__.py` - Added AgentRegistryClient export
- `src/configurable_agents/deploy/generator.py` - Added registry parameters and template variables
- `src/configurable_agents/deploy/templates/server.py.template` - Added registry code placeholders
- `src/configurable_agents/deploy/templates/requirements.txt.template` - Added httpx dependency

## Tech Stack Added

- **httpx>=0.26.0** - Async HTTP client for registry communication

## Patterns Established

1. **TTL Heartbeat Pattern** - Agents refresh TTL via periodic POST to /heartbeat endpoint
2. **Retry-on-Error Pattern** - Background heartbeat loop catches HTTP errors and retries instead of crashing
3. **Conditional Code Generation** - Template variables populated or empty based on feature flags
4. **Auto-detection Pattern** - Host/port detected from environment variables with sensible defaults

## Decisions Made

1. **Heartbeat interval default (20s)** - Set to ~1/3 of TTL (60s) for reliable refresh without excessive network traffic
2. **Retry delay (5s)** - Balances responsiveness to transient failures with load on registry server
3. **Environment variables for host/port** - AGENT_HOST and AGENT_PORT for containerized deployments where hostname is dynamic
4. **Best-effort deregistration** - Errors during deregistration are logged but don't raise exceptions (agent is shutting down anyway)

## Dependencies

### Requires
- 02-01A - Agent registry server with /agents/register, /agents/{id}/heartbeat, /agents/{id} endpoints

### Provides
- Agent self-registration capability for deployed containers
- Health check endpoints (/health, /health/live, /health/ready)

### Affects
- 02-01C - CLI will use these registry parameters for deploy command
- Future phases requiring agent discovery and orchestration

## Next Steps

**02-01C: CLI + Tests** - Add registry parameters to CLI deploy command and write tests for the complete registration flow.

## Success Criteria Met

- [x] AgentRegistryClient registers agent via POST /agents/register
- [x] Heartbeat loop runs in background with asyncio.create_task()
- [x] Heartbeat loop retries on HTTP errors (5 second sleep)
- [x] Agent deregisters cleanly on shutdown
- [x] Generated server.py includes registry code when enable_registry=True
- [x] Generated server.py excludes registry code when enable_registry=False
- [x] Health endpoints (/health, /health/live, /health/ready) are generated

## Commits

- **a955d55** feat(02-01B): add agent registry client with heartbeat loop
- **fa1235f** feat(02-01B): integrate registry client with deployment generator
