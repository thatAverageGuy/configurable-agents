---
created: 2026-02-05T22:45
title: Complete Orchestrator-Initiated Agent Registration (P0)
area: orchestrator
priority: P0
files:
  - docs/adr/ADR-020-agent-registry.md:358-366
  - src/configurable_agents/orchestrator/service.py:1-392
  - src/configurable_agents/orchestrator/client.py:1-200+
  - src/configurable_agents/registry/server.py:1-200+
  - src/configurable_agents/ui/dashboard/routes/orchestrator.py:1-218
  - src/configurable_agents/cli.py:2640-2720
---

## Problem

Per ADR-020, **ARCH-02** (Bidirectional Registration) is marked as **PARTIAL**:

✅ **Agent-Initiated Registration** (COMPLETE):
- Agents register themselves on startup via `AgentRegistryClient`
- Agents send heartbeats every 20s
- Registry expires stale agents after 60s TTL
- Storage backend implemented (SQLAlchemy + SQLite/PostgreSQL)

❌ **Orchestrator-Initiated Registration** (DEFERRED):
- Dashboard/orchestrator cannot discover agents proactively
- No mechanism for port scanning, mDNS, or configuration-based discovery
- No CLI command to start orchestrator service (template incorrectly references `configurable-agents orchestrator`)
- Orchestrator service exists in code (`orchestrator/service.py`) but has no entry point

**Why this is P0:**
1. Template documentation is misleading (tells users to run non-existent command)
2. Dashboard orchestrator page imports from non-existent modules
3. Feature was promised in ARCH-02 but deferred, leaving incomplete functionality
4. Blocks distributed multi-agent deployments (orchestrator cannot discover agents without manual registration)

## Solution

Implement orchestrator-initiated agent registration as specified in ADR-020 Deferred Features section:

### 1. Add Orchestrator CLI Command (LEVEL 2)
Create `configurable-agents orchestrator` CLI command:
```bash
configurable-agents orchestrator start [--port 9000] [--registry-url http://localhost:8000]
configurable-agents orchestrator discover [--registry-url] [--filters]
configurable-agents orchestrator status
```

Reference: CLI pattern in `cli.py:2640-2720` (agent-registry commands)

### 2. Implement Agent Discovery Mechanism (LEVEL 3)

**Option A: Configuration-Based Discovery** (Simplest)
- Read agent configurations from config file or directory
- Connect to pre-configured agent endpoints (host:port)
- Low hanging fruit, explicit control

**Option B: Port Scanning** (Moderate)
- Scan common port ranges for agent services
- Probe HTTP endpoints for agent metadata
- Requires error handling for timeouts, non-agent services

**Option C: mDNS/Bonjour** (Most robust)
- Zero-config local network discovery
- Agents announce themselves via mDNS
- Requires additional library (python-zeroconf)

**Recommendation:** Start with Option A (config-based), add Option B later if needed.

### 3. Fix Dashboard Orchestrator Routes (LEVEL 1)

File: `src/configurable_agents/ui/dashboard/routes/orchestrator.py:13-46`

Routes import from non-existent modules:
```python
from configurable_agents.orchestrator.models import AgentConnection  # ❌ File exists
from configurable_agents.orchestrator.service import OrchestratorService  # ❌ File exists
```

These files DO exist, but the routes try to call `create_orchestrator_service()` which may not be exported properly.

**Fix:**
1. Verify `orchestrator/__init__.py` exports `create_orchestrator_service`
2. Add error handling for when orchestrator service is not running
3. Return graceful degradation (helpful message) instead of 500 error

### 4. Update Orchestrator Page Template (LEVEL 1)

File: `src/configurable_agents/ui/dashboard/templates/orchestrator.html`

**Current state:** Already fixed in commit 5e8fb3b
- Now correctly references `configurable-agents agent-registry start`
- Clarifies deferred status of orchestrator-initiated discovery

**After implementation:** Update to describe orchestrator-initiated discovery

### 5. Integration Testing (LEVEL 2)

Add tests for:
- Orchestrator CLI commands
- Agent discovery via configuration
- Dashboard → Registry → Agent flow
- Bidirectional registration (agent + orchestrator)

### Implementation Order

1. **Quick fix:** Verify orchestrator module exports, fix dashboard routes (LEVEL 1)
2. **Add CLI:** Implement `configurable-agents orchestrator start` command (LEVEL 2)
3. **Discovery:** Implement configuration-based agent discovery (LEVEL 2-3)
4. **Integration:** Wire dashboard to orchestrator service (LEVEL 2)
5. **Tests:** Add integration tests for full flow (LEVEL 2)

### Success Criteria

Per ADR-020 ARCH-02 requirements:
- ✅ Agent-initiated registration (already complete)
- [ ] **Orchestrator can discover agents without manual configuration**
- [ ] **Dashboard can query registry and display discovered agents**
- [ ] **Orchestrator CLI command works** (`configurable-agents orchestrator start`)
- [ ] **No broken imports or 500 errors in dashboard routes**
- [ ] **Tests cover bidirectional registration flow**
- [ ] **Documentation updated** (remove "deferred" from ADR-020, update TASKS.md)

### References

- ADR-020: `docs/adr/ADR-020-agent-registry.md:358-366` (Deferred Features section)
- Orchestrator service: `src/configurable_agents/orchestrator/service.py:1-392`
- Orchestrator client: `src/configurable_agents/orchestrator/client.py:1-200+`
- Registry server: `src/configurable_agents/registry/server.py:1-200+`
- Dashboard routes: `src/configurable_agents/ui/dashboard/routes/orchestrator.py:1-218`
- CLI pattern: `src/configurable_agents/cli.py:2640-2720` (agent-registry commands)
- TASKS.md status: `docs/TASKS.md:44` (ARCH-02 marked as PARTIAL)
