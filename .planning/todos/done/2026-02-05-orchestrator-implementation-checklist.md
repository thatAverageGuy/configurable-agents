---
created: 2026-02-05T22:50
completed: 2026-02-06T18:40
title: Orchestrator Implementation Checklist - P0
area: orchestrator
priority: P0
status: DONE
---

# ✅ ALL TASKS COMPLETED

**Completed:** 2026-02-06
**Total Duration:** ~2 hours
**Test Results:** 14/14 integration tests passing
**Git Commits:** 8 atomic commits

See `ORCHESTRATOR_COMPLETE.md` for full test summary and implementation details.

---

## Implementation Tasks (All Completed)

### ✅ Task 1: Fix Orchestrator Routes Backend
**File:** `src/configurable_agents/ui/dashboard/routes/orchestrator.py`

**Current Issues:**
- Routes create new orchestrator service on each request (line 22-45)
- Should use embedded orchestrator from app.state instead
- Missing endpoints: register agent, execute workflow, get schema

**Changes Required:**
1. Modify `get_orchestrator_service()` to use `request.app.state.orchestrator`
2. Add `POST /orchestrator/register` - Register agent with health check
3. Add `GET /orchestrator/{agent_id}/schema` - Get workflow schema from agent
4. Add `POST /orchestrator/{agent_id}/execute` - Execute workflow on agent
5. Add `DELETE /orchestrator/{agent_id}` - Deregister agent
6. Add `GET /orchestrator/health-check` - Health check all agents (for HTMX polling)

**Integration Test:**
- Start dashboard, call each endpoint, verify responses
- Test with real agent URL (if available) or mock HTTP responses

---

### ✅ Task 2: Initialize Orchestrator in Dashboard
**File:** `src/configurable_agents/ui/dashboard/app.py`

**Changes Required:**
1. Import `create_orchestrator_service` from `configurable_agents.orchestrator`
2. In `Dashboard.__init__()`: Create orchestrator service instance
3. Store in `self.orchestrator_service`
4. Add to app.state: `self.app.state.orchestrator = orchestrator_service`
5. On startup: Load agents from database, check health of all

**Critical:** Ensure agent registry database URL uses same DB as dashboard
- Dashboard uses: `sqlite:///workflows.db`
- Orchestrator should use: `sqlite:///workflows.db` (NOT separate DB)

**Integration Test:**
- Start dashboard: `configurable-agents ui`
- Verify `app.state.orchestrator` exists
- Check database has `agents` table created if not exists

---

### ✅ Task 3: Update Orchestrator Page Template
**File:** `src/configurable_agents/ui/dashboard/templates/orchestrator.html`

**Current Issues:**
- References non-existent `configurable-agents orchestrator` command
- "Discover Agents" button (should be removed - no auto-discovery)
- JavaScript tries to use non-existent API responses
- No registration form
- No execute workflow modal

**New Structure:**
1. **Page Header:** Title, description
2. **Registration Form:**
   - Agent ID (text input, required)
   - Agent Name (text input, required)
   - Agent URL (text input, required, format: http://localhost:8001)
   - Description (textarea, optional)
   - Register button (hx-post to `/orchestrator/register`)
   - Error message div (htmx swap for errors)
3. **Agent List:**
   - Table/Grid of registered agents
   - Columns: Status, Name, ID, URL, Last Seen, Actions
   - Actions: [Execute] [Remove]
   - Auto-refresh every 10s: `hx-get="/orchestrator/health-check" hx-trigger="every 10s" hx-swap="outerHTML"`
4. **Execute Modal:**
   - Hidden by default (`style="display: none;"`)
   - Shows on [Execute] button click
   - Fetches schema from agent first
   - Renders form fields dynamically
   - Submit button: `hx-post="/orchestrator/{agent_id}/execute"`
   - Redirects to `/runs/{run_id}` on success

**Integration Test:**
- Load orchestrator page in browser
- Fill registration form, submit, verify agent appears in list
- Check HTMX auto-refresh works (wait 10s, verify status updates)
- Click Execute, verify modal opens
- Test with unreachable agent URL, verify error shows

---

### ✅ Task 4: Add Agent ID to Execution History
**File:** `src/configurable_agents/ui/dashboard/templates/runs.html`

**Changes Required:**
1. Add "Agent ID" column to runs table
2. Add filter dropdown for agent_id (if agent_id is not null/empty)
3. Update table header row
4. Update table data row to show agent_id or "-" for local runs

**Integration Test:**
- Execute workflow on agent via orchestrator
- Navigate to runs page
- Verify Agent ID column shows the agent ID
- Verify filter dropdown includes agent ID
- Filter by agent ID, verify only that agent's runs show

---

### ✅ Task 5: Add Schema Endpoint to Backend
**File:** `src/configurable_agents/ui/dashboard/routes/orchestrator.py`

**New Route:**
```python
@router.get("/{agent_id}/schema")
async def get_agent_schema(agent_id: str, orchestrator: OrchestratorService = Depends(get_orchestrator_service)):
    # Get agent from database
    # Build agent URL: http://{host}:{port}
    # Call GET {agent_url}/schema
    # Return schema JSON
```

**Schema Response Format:**
```json
{
  "workflow": "workflow_name",
  "inputs": {
    "topic": {"type": "str", "description": "...", "required": true},
    "tone": {"type": "str", "description": "...", "required": false}
  },
  "outputs": ["result", "summary"]
}
```

**Integration Test:**
- Start a real agent (if available) or mock HTTP server
- Call `/orchestrator/{agent_id}/schema`
- Verify returns correct schema format

---

### ✅ Task 6: Add Execute Endpoint to Backend
**File:** `src/configurable_agents/ui/dashboard/routes/orchestrator.py`

**New Route:**
```python
@router.post("/{agent_id}/execute")
async def execute_on_agent(agent_id: str, inputs: Dict[str, Any], orchestrator: OrchestratorService = Depends(get_orchestrator_service), repo: WorkflowRunRepository = Depends(get_workflow_repo)):
    # Get agent from database
    # Build agent URL: http://{host}:{port}
    # Call POST {agent_url}/run with inputs
    # Create WorkflowRunRecord with:
    #   - workflow_name = agent_id
    #   - inputs = request inputs
    #   - outputs = response outputs
    #   - status = "completed" or "failed"
    #   - started_at, completed_at, duration_seconds
    # Return redirect to /runs/{run_id}
```

**Integration Test:**
- Mock agent server that returns execution result
- Call `/orchestrator/{agent_id}/execute` with test inputs
- Verify WorkflowRunRecord created in database
- Verify redirect URL returned
- Navigate to redirect URL, verify execution details show

---

### ✅ Task 7: Add Register Endpoint to Backend
**File:** `src/configurable_agents/ui/dashboard/routes/orchestrator.py`

**New Route:**
```python
@router.post("/register")
async def register_agent(request: AgentRegistrationRequest, orchestrator: OrchestratorService = Depends(get_orchestrator_service)):
    # Validate inputs (agent_id, agent_name, agent_url)
    # Parse URL to extract host and port
    # Health check: GET {agent_url}/health
    # If unhealthy: return error with message
    # If healthy: Register in agent database
    #   - Create AgentRecord
    #   - Set last_heartbeat = now
    #   - Set ttl_seconds = 60 (or from metadata)
    # Return success with agent info
```

**Request Format:**
```json
{
  "agent_id": "research-agent",
  "agent_name": "Research Agent",
  "agent_url": "http://localhost:8001",
  "metadata": {"description": "..."}
}
```

**Integration Test:**
- Call `/orchestrator/register` with valid agent URL
- Verify agent appears in database
- Call with invalid URL, verify error returned
- Verify health check was called (check agent logs if available)

---

### ✅ Task 8: Add Health Check Endpoint to Backend
**File:** `src/configurable_agents/ui/dashboard/routes/orchestrator.py`

**New Route:**
```python
@router.get("/health-check")
async def health_check_all(orchestrator: OrchestratorService = Depends(get_orchestrator_service)):
    # Get all agents from database
    # For each agent: GET {agent_url}/health
    # Update status in response (not in database - keep original heartbeat)
    # Return HTML partial for agent list (for HTMX swap)
```

**Response Format:** HTML partial (for HTMX swap of agent list div)

**Integration Test:**
- Register 2 agents (one healthy, one unhealthy/offline)
- Call `/orchestrator/health-check`
- Verify response shows correct statuses
- Verify HTMX swap works in browser

---

### ✅ Task 9: Add Deregister Endpoint to Backend
**File:** `src/configurable_agents/ui/dashboard/routes/orchestrator.py`

**Update Route:** `DELETE /orchestrator/{agent_id}` (already exists, fix implementation)

**Integration Test:**
- Register an agent
- Call `DELETE /orchestrator/{agent_id}`
- Verify agent removed from database
- Verify agent list updates (no longer shows)

---

### ✅ Task 10: Full Integration Test (End-to-End)
**Scenario:** Complete orchestrator workflow

**Steps:**
1. Start dashboard: `configurable-agents ui`
2. Navigate to `http://localhost:8000/orchestrator`
3. Register a test agent:
   - Fill form with mock agent URL (or use httpbin.org for testing)
   - Submit, verify success message
   - Verify agent appears in list with ✓ Healthy status
4. Wait 10s, verify status refreshes (HTMX polling)
5. Click [Execute] on agent:
   - Verify modal opens
   - Verify schema loads (if agent has /schema endpoint)
   - Fill inputs, submit
   - Verify redirect to `/runs/{run_id}`
   - Verify execution details show agent ID
6. Navigate to `/runs`, verify agent appears in filter dropdown
7. Filter by agent ID, verify execution shows
8. Return to orchestrator, click [Remove]
   - Verify agent removed from list
   - Verify agent removed from database

**Success Criteria:**
- No 500 errors
- No "command not found" errors
- No broken imports
- All HTMX swaps work correctly
- Database records created correctly
- Health checks work
- Execution history shows agent executions

---

## Files to Modify Summary:

1. `src/configurable_agents/ui/dashboard/app.py` - Initialize orchestrator
2. `src/configurable_agents/ui/dashboard/routes/orchestrator.py` - Add/fix routes
3. `src/configurable_agents/ui/dashboard/templates/orchestrator.html` - Complete rewrite
4. `src/configurable_agents/ui/dashboard/templates/runs.html` - Add agent_id column

## Testing Strategy:

- **Unit Tests:** Not required (user said integration testing)
- **Integration Tests:** Test each endpoint manually or with httpx
- **E2E Tests:** Test full workflow in browser (Task 10)

## Rollback Plan:

If something breaks:
1. Git revert each file individually
2. Identify which commit broke things
3. Fix and retry
4. Keep commits atomic (one logical change per commit)
