---
phase: 02-agent-infrastructure
plan: 01B
type: execute
wave: 2
depends_on: ["02-01A"]
files_modified:
  - src/configurable_agents/registry/client.py
  - src/configurable_agents/deploy/generator.py
  - src/configurable_agents/deploy/templates/Dockerfile.template
  - src/configurable_agents/deploy/templates/server.py.template
  - src/configurable_agents/deploy/templates/requirements.txt.template
autonomous: true

must_haves:
  truths:
    - "AgentRegistryClient successfully registers agent with registry server"
    - "Heartbeat loop runs in background without blocking FastAPI event loop"
    - "Heartbeat loop retries on HTTP errors instead of crashing"
    - "Agent deregisters cleanly on shutdown (DELETE /agents/{agent_id})"
    - "Generated deployment artifacts include registry client code when enable_registry=True"
    - "Generated Dockerfile includes httpx dependency for async HTTP"
  artifacts:
    - path: "src/configurable_agents/registry/client.py"
      provides: "Agent registration client for heartbeat loop"
      exports: ["AgentRegistryClient"]
      min_lines: 100
    - path: "src/configurable_agents/deploy/generator.py"
      provides: "Deployment generator with registry parameters"
      contains: "enable_registry, registry_url, agent_id parameters"
  key_links:
    - from: "src/configurable_agents/deploy/templates/server.py.template"
      to: "src/configurable_agents/registry/client.py"
      via: "AgentRegistryClient import and usage"
      pattern: "from configurable_agents.registry import AgentRegistryClient"
    - from: "src/configurable_agents/registry/client.py"
      to: "src/configurable_agents/registry/server.py"
      via: "HTTP calls to registry endpoints"
      pattern: "httpx.AsyncClient"
---

<objective>
Implement agent registry client and integrate with deployment generator.

**Purpose:** Create the client-side component that agents use to register themselves and send heartbeats to the registry server. Also update the deployment generator to conditionally include registry client code in generated agent containers. This enables agents to self-register on startup.

**Output:**
- AgentRegistryClient with registration, heartbeat loop, and deregistration
- Host/port auto-detection from environment variables
- Deployment generator updates for registry integration
- Template updates for conditional registry code generation
- Health check endpoints (/health, /health/live, /health/ready)
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

# Existing infrastructure
@src/configurable_agents/registry/server.py
@src/configurable_agents/deploy/generator.py
@src/configurable_agents/deploy/templates/Dockerfile.template
@src/configurable_agents/deploy/templates/server.py.template
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create agent registry client (heartbeat loop)</name>
  <files>src/configurable_agents/registry/client.py</files>
  <action>
Create agent registry client for self-registration and heartbeat:

**Create src/configurable_agents/registry/client.py**:

- `AgentRegistryClient` class with:
  - `__init__(self, registry_url: str, agent_id: str, ttl_seconds: int = 60, heartbeat_interval: int = 20)`
    - Store registry_url, agent_id, TTL, heartbeat_interval
    - Create `httpx.AsyncClient()` for HTTP requests
  - `async def register(self, metadata: dict) -> None`:
    - POST to `{registry_url}/agents/register` with payload
    - Payload: agent_id, agent_name (from metadata or agent_id), host (auto-detect or from metadata), port, ttl_seconds, metadata
  - `async def start_heartbeat_loop(self) -> None`:
    - Create background task via `asyncio.create_task(self._heartbeat())`
    - Store task in `self._heartbeat_task`
  - `async def _heartbeat(self) -> None`:
    - Infinite loop: POST to `/agents/{agent_id}/heartbeat`, sleep for `heartbeat_interval`
    - Catch asyncio.CancelledError to exit cleanly
    - On HTTP errors: sleep 5 seconds and retry (don't crash)
  - `async def deregister(self) -> None`:
    - Cancel heartbeat task if running
    - DELETE to `/agents/{agent_id}`

- **Auto-detection helper**: `_get_host_port()` method that:
  - Tries env vars: `AGENT_HOST`, `AGENT_PORT`
  - Falls back to socket.gethostname() and port 8000

Reference: RESEARCH.md Pattern 2 (Agent self-registration with TTL heartbeat code example).
  </action>
  <verify>
Run: `python -c "from configurable_agents.registry import AgentRegistryClient; print('Client imported:', AgentRegistryClient)"`

Run: `python -c "import asyncio; from configurable_agents.registry import AgentRegistryClient; client = AgentRegistryClient('http://localhost:8000', 'test-agent'); print('Client created with TTL:', client.ttl_seconds)"`
  </verify>
  <done>
AgentRegistryClient created with register/start_heartbeat_loop/deregister methods, background heartbeat loop implements retry-on-error, host/port auto-detection from env vars.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update deployment generator for registry integration</name>
  <files>src/configurable_agents/deploy/generator.py, src/configurable_agents/deploy/templates/Dockerfile.template, src/configurable_agents/deploy/templates/server.py.template, src/configurable_agents/deploy/templates/requirements.txt.template</files>
  <action>
Update deployment templates to include agent registry integration:

1. **Update generator.py**:
   - Add `enable_registry: bool = False` parameter to `generate()` method
   - Add `registry_url: str | None = None` parameter
   - Add `agent_id: str | None = None` parameter (default: workflow_name)
   - Pass registry variables to `_build_template_variables()`

2. **Update _build_template_variables() in generator.py**:
   - Add registry-related template variables:
     - `registry_enabled`: boolean
     - `registry_url`: registry endpoint or empty string
     - `agent_id`: agent identifier
     - `heartbeat_interval`: default 20 (TTL/3)
     - `registry_import`: import line for AgentRegistryClient or empty string
     - `registry_client_init`: client initialization code or empty string
     - `registry_startup_handler`: startup event code or empty string
     - `registry_shutdown_handler`: shutdown event code or empty string
     - `health_check_endpoints`: health endpoint code or empty string

3. **Update Dockerfile.template**:
   - Add httpx to requirements section (registry client needs async HTTP)
   - Ensure HEALTHCHECK remains (already present)

4. **Update server.py.template**:
   - Add conditional import (top of file): `${registry_import}`
   - Add agent registry initialization (after workflow config load): `${registry_client_init}`
   - Add startup event to register agent and start heartbeat: `${registry_startup_handler}`
   - Add shutdown event to deregister: `${registry_shutdown_handler}`
   - Add /health/live and /health/ready endpoints: `${health_check_endpoints}`

5. **Update requirements.txt.template**:
   - Add `httpx>=0.26.0` for async HTTP in registry client

6. **Template variable substitution logic**:
   - If `enable_registry=True`: generate code that imports AgentRegistryClient, initializes it, starts heartbeat on startup, stops on shutdown
   - If `enable_registry=False`: generate empty/no-op code blocks

Reference: Existing generator.py patterns, RESEARCH.md Pattern 2 (heartbeat background task), Pattern 3 (health endpoints).
  </action>
  <verify>
Step 1: `python -c "from configurable_agents.deploy import DeploymentArtifactGenerator; from configurable_agents.config import WorkflowConfig; print('Generator imports OK')"`

Step 2: Create a test config file at `/tmp/test_config.yaml`:
```yaml
workflow:
  name: test-agent
  nodes:
    - id: test
      model: openai/gpt-4o-mini
```

Step 3: Run template generation test:
```bash
python -c "
from configurable_agents.deploy import DeploymentArtifactGenerator
from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    generator = DeploymentArtifactGenerator()
    generator.generate(
        config_path='/tmp/test_config.yaml',
        output_dir=tmpdir,
        enable_registry=True,
        registry_url='http://localhost:9000',
        agent_id='test-agent'
    )
    server_py = Path(tmpdir) / 'server.py'
    content = server_py.read_text()
    print('=== Generated server.py contains registry code ===')
    print('AgentRegistryClient import:', 'AgentRegistryClient' in content)
    print('heartbeat_loop:', 'start_heartbeat_loop' in content)
    print('health endpoints:', '/health/live' in content)
"
```

Expected output: All checks should return True.
  </verify>
  <done>
Deployment generator updated with registry parameters, Dockerfile template includes httpx dependency, server.py template conditionally generates registry client code, health/live/ready endpoints added, template substitution handles enable_registry flag. Verification test confirms generated code contains registry integration.
  </done>
</task>

</tasks>

<verification>
After completing all tasks:

1. **Client Verification**:
   - Import test: `from configurable_agents.registry import AgentRegistryClient`
   - Create client instance and verify attributes (registry_url, agent_id, ttl_seconds, heartbeat_interval)
   - Verify `_get_host_port()` method exists for auto-detection

2. **Generator Verification**:
   - Verify generator accepts enable_registry, registry_url, agent_id parameters
   - Run generator with enable_registry=True and verify generated server.py contains:
     - AgentRegistryClient import
     - Client initialization
     - Startup handler with register() and start_heartbeat_loop()
     - Shutdown handler with deregister()
     - /health/live and /health/ready endpoints
   - Run generator with enable_registry=False and verify no registry code is generated

3. **Template Verification**:
   - Verify Dockerfile.template includes httpx
   - Verify requirements.txt.template includes httpx>=0.26.0
   - Verify server.py.template has all template variable placeholders
</verification>

<success_criteria>
**Plan Success Criteria Met:**
1. AgentRegistryClient registers agent via POST /agents/register
2. Heartbeat loop runs in background with asyncio.create_task()
3. Heartbeat loop retries on HTTP errors (5 second sleep)
4. Agent deregisters cleanly on shutdown
5. Generated server.py includes registry code when enable_registry=True
6. Generated server.py excludes registry code when enable_registry=False
7. Health endpoints (/health, /health/live, /health/ready) are generated
</success_criteria>

<output>
After completion, create `.planning/phases/02-agent-infrastructure/02-01B-SUMMARY.md` with:
- Frontmatter (phase, plan, wave, status, completed_at, tech_added, patterns_established, key_files)
- Summary of changes (registry client, generator integration)
- Verification results (client functionality, template generation test)
- Next steps link (02-01C: CLI + Tests)
</output>
