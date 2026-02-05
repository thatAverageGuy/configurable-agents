# Orchestrator Manual Test Plan

## Test Environment
- **Dashboard URL:** http://localhost:8001
- **Orchestrator Page:** http://localhost:8001/orchestrator
- **Status:** Dashboard running (PID 42004)

---

## Test 1: Page Loads Correctly
**URL:** http://localhost:8001/orchestrator

**Expected:**
- [ ] Page title: "Orchestrator - Configurable Agents Dashboard"
- [ ] Navigation: "Orchestrator" tab is active
- [ ] Header: "Orchestrator" and "Manage distributed agents and execute workflows on them"
- [ ] Registration form visible with 4 fields:
  - Agent ID (required)
  - Agent Name (required)
  - Agent URL (required)
  - Description (optional)
- [ ] "Register Agent" button (green)
- [ ] "Clear" button (gray)
- [ ] Agent list section shows: "No agents registered yet. Use the form above to register your first agent."

---

## Test 2: Registration Form Validation

### Test 2a: Empty Form
**Steps:**
1. Leave all fields empty
2. Click "Register Agent"

**Expected:**
- [ ] Browser validation prevents submission (required fields)
- [ ] No error message from server (form doesn't submit)

### Test 2b: Invalid URL
**Steps:**
1. Enter: Agent ID = "test"
2. Enter: Agent Name = "Test"
3. Enter: Agent URL = "not-a-url" (missing scheme)
4. Click "Register Agent"

**Expected:**
- [ ] Browser validates URL format (HTML5 validation)
- [ ] Form doesn't submit

### Test 2c: Unreachable Agent
**Steps:**
1. Enter: Agent ID = "fake-agent"
2. Enter: Agent Name = "Fake Agent"
3. Enter: Agent URL = "http://localhost:9999" (not running)
4. Click "Register Agent"

**Expected:**
- [ ] Form submits
- [ ] Error message appears: "Cannot connect to agent at http://localhost:9999: All connection attempts failed"
- [ ] Error styled with red background
- [ ] Agent NOT added to database

### Test 2d: Clear Button
**Steps:**
1. Fill in some fields
2. Click "Clear"

**Expected:**
- [ ] Form resets to empty fields
- [ ] No error messages

---

## Test 3: Agent List Display (After Registration)

**NOTE:** Requires a real agent running. Skip for now.

**To test later:**
1. Start an agent (see "Test Agent Setup" below)
2. Register it successfully
3. Verify agent appears in list
4. Check status shows ✓ Healthy
5. Verify details: Agent Name, ID, URL, Last Seen
6. Verify [Execute] and [Remove] buttons present

---

## Test 4: Auto-Refresh (HTMX Polling)

**Steps:**
1. Go to orchestrator page
2. Wait 10 seconds
3. Observe the agent list section

**Expected (no agents):**
- [ ] Message stays: "No agents registered yet..."
- [ ] No page reload
- [ ] HTMX polling happens in background

**Expected (with agents):**
- [ ] "Last Seen" timestamp updates every 10s
- [ ] Status changes if agent goes down
- [ ] No page flicker (smooth update)

---

## Test 5: Database Verification

**Steps:**
1. After attempting registration (even failed), check database
2. Run in terminal:
```bash
cd "C:\Users\ghost\OneDrive\Desktop\Test\configurable-agents"
python -c "from sqlalchemy import create_engine; engine = create_engine('sqlite:///configurable_agents.db'); result = engine.execute('SELECT * FROM agents'); print(list(result))"
```

**Expected:**
- [ ] Empty list = [] (no agents registered yet)
- [ ] Agents table exists with correct schema

---

## Test 6: Navigation Links

**Steps:**
1. Click "Configurable Agents" logo (top left)
2. Navigate back to "Orchestrator"

**Expected:**
- [ ] All navigation works
- [ ] "Orchestrator" link in nav bar highlighted/active

---

## Test 7: Workflows Page Agent Filter

**URL:** http://localhost:8001/workflows

**Expected:**
- [ ] "Agent ID" column present (may show "-" for local workflows)
- [ ] Agent filter dropdown visible with options:
  - "All"
  - "Orchestrator Agents"
- [ ] Column count: 9 columns (ID, Workflow, Agent ID, Status, Started, Duration, Tokens, Cost, Actions)

---

## Test Agent Setup (For Full Testing)

To test with a real agent, create this file `test_agent.py`:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from uvicorn import run

app = FastAPI()

class WorkflowInput(BaseModel):
    topic: str

@app.get("/health")
async def health():
    return {"status": "alive", "timestamp": "2025-01-01T00:00:00"}

@app.get("/schema")
async def schema():
    return {
        "workflow": "test-workflow",
        "inputs": {
            "topic": {
                "type": "str",
                "description": "Topic to research",
                "required": True
            }
        },
        "outputs": ["result"]
    }

@app.post("/run")
async def run(inputs: WorkflowInput):
    return {
        "status": "success",
        "outputs": {"result": f"Test result for: {inputs.topic}"},
        "cost_usd": 0.0001,
        "total_tokens": 50
    }

if __name__ == "__main__":
    run(app, host="127.0.0.1", port=8002)
```

**To run test agent:**
```bash
pip install fastapi uvicorn
python test_agent.py
```

**Then register in orchestrator:**
- Agent ID: `test-agent`
- Agent Name: `Test Agent`
- Agent URL: `http://localhost:8002`

---

## Test 8: Execute Workflow (With Real Agent)

**Prerequisite:** Test agent running

**Steps:**
1. Click [Execute] button on agent
2. Modal appears: "Execute on Test Agent"
3. Modal shows: "Workflow: test-workflow"
4. Modal shows input field: "topic *"
5. Enter topic: "AI research"
6. Click "Execute"

**Expected:**
- [ ] Modal closes
- [ ] Redirects to `/runs/{run_id}`
- [ ] Page shows execution details
- [ ] Workflow name = "test-agent"
- [ ] Status = "completed"
- [ ] Outputs visible

---

## Known Limitations (Expected Behavior)

1. **No agents yet:** Cannot test full workflow without real agent
2. **Agent detection logic:** Agent ID column uses simple heuristics (contains "-" or ends with "-agent")
3. **Execute modal:** Shows error if agent unreachable or schema endpoint fails

---

## Test Results Summary

| Test | Status | Notes |
|------|--------|-------|
| 1. Page Loads | ⏳ TBD | Open http://localhost:8001/orchestrator in browser |
| 2a. Empty Form | ⏳ TBD | Browser validation |
| 2b. Invalid URL | ⏳ TBD | Browser validation |
| 2c. Unreachable Agent | ✅ PASS | API returns correct error |
| 2d. Clear Button | ⏳ TBD | Test in browser |
| 3. Agent List | ⏳ TBD | Requires real agent |
| 4. Auto-Refresh | ⏳ TBD | Wait 10s to verify |
| 5. Database | ✅ PASS | Schema verified, empty table |
| 6. Navigation | ⏳ TBD | Test in browser |
| 7. Workflows Filter | ⏳ TBD | Check http://localhost:8001/workflows |
| 8. Execute Workflow | ⏳ TBD | Requires real agent |

---

## Next Steps

1. **Open in browser:** http://localhost:8001/orchestrator
2. **Run through tests 1-2d** (don't need real agent)
3. **Let me know results** of any tests that fail
4. **If all pass:** Create test agent for full E2E testing (Test 8)
