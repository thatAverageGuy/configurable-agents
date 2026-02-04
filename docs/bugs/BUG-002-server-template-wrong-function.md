# BUG-002: Server Template Calls Wrong Runtime Function

**Status**: ✅ Fixed
**Severity**: Critical (blocks workflow execution)
**Date Reported**: 2026-02-02
**Date Fixed**: 2026-02-02
**Reporter**: User testing deployed container
**Fixed By**: Claude (AI Assistant)
**Related Tasks**: T-023 (FastAPI Server Template)
**Related ADRs**: ADR-012 (Docker Deployment Architecture)

---

## Summary

Deployed FastAPI server returns 500 error when calling `/run` endpoint:
```json
{
  "detail": "Workflow execution failed: Failed to parse config file:
            expected str, bytes or os.PathLike object, not dict"
}
```

**Root Cause**: Server template imported and called `run_workflow()` which expects a file path string, but passed a dict instead.

**Impact**: Complete workflow execution failure - deployed containers cannot execute workflows (0% success rate).

**Fix**: Changed import to `run_workflow_from_config()` and pass `workflow_config` object instead of `config_dict`.

---

## Detailed Description

### What Happened

When calling the deployed workflow API's `/run` endpoint, all requests failed with HTTP 500 Internal Server Error.

**Error Response**:
```json
{
  "detail": "Workflow execution failed: Failed to parse config file: expected str, bytes or os.PathLike object, not dict"
}
```

**Request Example**:
```bash
curl -X 'POST' \
  'http://localhost:8000/run' \
  -H 'Content-Type: application/json' \
  -d '{
    "topic": "AI Bubble",
    "word_count": 200,
    "tone": "professional"
  }'
```

**Result**: HTTP 500 error, no workflow execution

### When It Occurred

- **First observed**: During manual testing of deployed Docker container (T-024)
- **Trigger**: Any POST request to `/run` endpoint
- **Frequency**: 100% reproduction rate (all workflow executions failed)

### Expected Behavior

POST to `/run` should:
1. Validate inputs against workflow schema
2. Execute workflow with provided inputs
3. Return outputs with 200 OK status

### Actual Behavior

POST to `/run`:
1. ❌ Validation passed (inputs correct)
2. ❌ Workflow execution failed with type error
3. ❌ Returned HTTP 500 error
4. ❌ No workflow output

---

## Root Cause Analysis

### The Problem

The `server.py` template (generated from `server.py.template`) had incorrect function calls.

**File**: `src/configurable_agents/deploy/templates/server.py.template`

**Line 18-19** (Import):
```python
# WRONG
from configurable_agents.runtime import run_workflow
```

**Line 156** (Async background execution):
```python
# WRONG
result = await asyncio.to_thread(run_workflow, config_dict, inputs)
```

**Line 242** (Sync execution):
```python
# WRONG
result = await asyncio.wait_for(
    asyncio.to_thread(run_workflow, config_dict, inputs_dict),
    timeout=SYNC_TIMEOUT
)
```

### The Runtime Module Has Two Functions

**From `src/configurable_agents/runtime/executor.py`**:

**Function 1**: `run_workflow(config_path: str, ...)`
```python
def run_workflow(
    config_path: str,  # ← Expects FILE PATH STRING
    inputs: Dict[str, Any],
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Run workflow from config file path.

    Args:
        config_path: Path to workflow YAML/JSON file
    """
```

**Function 2**: `run_workflow_from_config(config: WorkflowConfig, ...)`
```python
def run_workflow_from_config(
    config: WorkflowConfig,  # ← Expects WorkflowConfig OBJECT
    inputs: Dict[str, Any],
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Run workflow from pre-loaded config object.

    Args:
        config: Validated WorkflowConfig instance
    """
```

### What the Server Template Did

**Lines 33-38** (Config loading):
```python
try:
    config_dict = parse_config_file(WORKFLOW_CONFIG_PATH)  # Returns dict
    workflow_config = WorkflowConfig(**config_dict)        # Creates object
except Exception as e:
    print(f"FATAL: Failed to load workflow config: {e}")
    raise
```

**Result**:
- `config_dict`: Python dict (parsed YAML)
- `workflow_config`: WorkflowConfig object (validated)

**Then called** (Line 156, 242):
```python
run_workflow(config_dict, inputs)
         # ^^^^^^^^^^^ WRONG! This is a dict, not a file path string
```

### Why This Failed

`run_workflow()` expects a **file path string** like `"workflow.yaml"`, but received a **dict** like `{"schema_version": "1.0", ...}`.

Inside `run_workflow()`, it tries:
```python
def run_workflow(config_path: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    config_dict = parse_config_file(config_path)  # ← Expects str/Path, got dict
    # Error: expected str, bytes or os.PathLike object, not dict
```

### Why Wasn't This Caught Earlier?

1. **No integration tests**: T-023 implementation didn't include end-to-end API tests
2. **Template complexity**: Generated code not easily testable before deployment
3. **Similar function names**: `run_workflow` vs `run_workflow_from_config` easy to confuse
4. **Type hints not enforced**: Python allows passing wrong types at runtime

---

## Impact Assessment

### Severity: Critical

**User Impact**:
- ✅ **Docker build**: Works (containers build successfully)
- ✅ **Health checks**: Pass (container shows healthy)
- ✅ **API docs**: Accessible at `/docs`
- ❌ **Workflow execution**: Completely blocked (0% success rate)
- ❌ **Sync execution**: Fails
- ❌ **Async execution**: Fails

**Business Impact**:
- **Deployed containers useless**: Cannot execute workflows
- **T-024 blocked**: Docker deployment feature non-functional
- **User frustration**: Deploy succeeds, but usage fails (confusing)

**Scope**:
- Affects: All deployed containers from templates
- Affected users: 100% of users calling `/run` endpoint
- Affected versions: All deployments using current template

### Why Critical?

1. **Total feature failure**: Deployed containers cannot execute workflows
2. **Confusing UX**: Deploy succeeds, health checks pass, docs work, but execution fails
3. **Silent template bug**: Error not visible until runtime
4. **No workaround**: Users cannot fix without regenerating container

---

## Solution Implemented

### Strategy

**Change the server template to use the correct runtime function.**

**Fix**:
1. Import `run_workflow_from_config` instead of `run_workflow`
2. Pass `workflow_config` (object) instead of `config_dict` (dict)
3. No other changes needed (function signatures compatible)

### Changes Made

#### File: `src/configurable_agents/deploy/templates/server.py.template`

**Change 1: Import** (Line 18-19)
```python
# Before
from configurable_agents.runtime import run_workflow

# After
from configurable_agents.runtime import run_workflow_from_config
```

**Change 2: Async Execution** (Line 156)
```python
# Before
result = await asyncio.to_thread(run_workflow, config_dict, inputs)

# After
result = await asyncio.to_thread(run_workflow_from_config, workflow_config, inputs)
```

**Change 3: Sync Execution** (Line 242)
```python
# Before
result = await asyncio.wait_for(
    asyncio.to_thread(run_workflow, config_dict, inputs_dict),
    timeout=SYNC_TIMEOUT
)

# After
result = await asyncio.wait_for(
    asyncio.to_thread(run_workflow_from_config, workflow_config, inputs_dict),
    timeout=SYNC_TIMEOUT
)
```

### Why This Works

**Correct function signature**:
```python
run_workflow_from_config(
    config: WorkflowConfig,  # ← workflow_config is WorkflowConfig object ✓
    inputs: Dict[str, Any],  # ← inputs_dict is dict ✓
    verbose: bool = False
) -> Dict[str, Any]
```

**Function behavior**:
- Takes pre-validated `WorkflowConfig` object
- Skips file loading and parsing (already done at startup)
- Directly executes workflow
- Returns outputs as dict

---

## Verification

### Manual Test

**Before Fix**:
```bash
curl -X POST http://localhost:8000/run \
  -H 'Content-Type: application/json' \
  -d '{"topic": "AI", "word_count": 200}'

# Result: HTTP 500 - "expected str, bytes or os.PathLike object, not dict"
```

**After Fix** (requires redeployment):
```bash
# Regenerate artifacts with fixed template
configurable-agents deploy test_config.yaml --name article-writer-fixed

# Test again
curl -X POST http://localhost:8000/run \
  -H 'Content-Type: application/json' \
  -d '{"topic": "AI", "word_count": 200}'

# Expected: HTTP 200 - {"status": "success", "outputs": {...}}
```

### Code Review

```bash
# Verify changes
grep "run_workflow" src/configurable_agents/deploy/templates/server.py.template

# Output:
# 19:from configurable_agents.runtime import run_workflow_from_config
# 156:        result = await asyncio.to_thread(run_workflow_from_config, workflow_config, inputs)
# 242:            asyncio.to_thread(run_workflow_from_config, workflow_config, inputs_dict),
```

✅ All occurrences updated correctly

---

## Files Changed

| File | Change Type | Lines Changed | Purpose |
|------|-------------|---------------|---------|
| `src/configurable_agents/deploy/templates/server.py.template` | Modified | 3 lines | Fix function calls |

**Total**: 1 file, 3 lines changed

---

## Lessons Learned

### What Went Wrong

1. **Confusing API**: Two similar functions (`run_workflow` vs `run_workflow_from_config`)
   - **Lesson**: Consider consolidating or renaming for clarity

2. **No template tests**: Generated code not tested before deployment
   - **Lesson**: Test generated artifacts, not just generator code

3. **Type hints ignored**: Python allows wrong types at runtime
   - **Lesson**: Consider using `mypy` for static type checking

4. **Integration gap**: Generator works, build works, runtime fails
   - **Lesson**: End-to-end tests must include actual API calls

### What Went Right

1. **Clear error message**: "expected str, bytes or os.PathLike" immediately identified issue
2. **Quick fix**: Simple import/function name change
3. **Isolated bug**: Only affects template, not runtime or CLI

### Process Improvements

**Recommended Actions**:

1. **Add Template Validation** (High Priority):
   ```python
   # tests/test_server_template.py
   def test_server_template_uses_correct_function():
       """Verify server.py uses run_workflow_from_config"""
       template_path = Path("src/configurable_agents/deploy/templates/server.py.template")
       content = template_path.read_text()

       assert "run_workflow_from_config" in content
       assert "run_workflow," not in content  # Catch wrong function
   ```

2. **Add Integration Test** (High Priority):
   ```python
   # tests/test_deploy_integration.py
   def test_deployed_container_executes_workflow():
       """Test that deployed container can execute workflows"""
       # Deploy container
       # Call /run endpoint
       # Assert HTTP 200 with outputs
   ```

3. **Add Type Checking** (Medium Priority):
   - Run `mypy` on generated server.py during tests
   - Catch type mismatches before runtime

4. **Clarify Runtime API** (Low Priority):
   - Rename `run_workflow` to `run_workflow_from_file`?
   - Add deprecation warning for unclear naming

---

## Alternative Solutions Considered

### Option 1: Change to Use run_workflow() Correctly

**Approach**: Keep using `run_workflow()` but pass file path string

```python
# At startup
WORKFLOW_CONFIG_PATH = "workflow.yaml"

# In endpoint
result = await asyncio.to_thread(run_workflow, WORKFLOW_CONFIG_PATH, inputs_dict)
```

**Pros**:
- Uses original function (matches current import)

**Cons**:
- Re-parses config file on every request (inefficient)
- Re-validates on every request (slower)
- Duplicates work done at startup

**Decision**: ❌ Rejected - Inefficient, defeats purpose of startup loading

### Option 2: Pass config_path String

**Approach**: Store path as string, not config object

```python
# At startup
WORKFLOW_CONFIG_PATH = "workflow.yaml"
# Don't load config here

# In endpoint
result = await asyncio.to_thread(run_workflow, WORKFLOW_CONFIG_PATH, inputs_dict)
```

**Pros**:
- Simpler startup (no config loading)

**Cons**:
- No fail-fast (config errors only at first request)
- Slower (parse on every request)
- No input validation model at startup

**Decision**: ❌ Rejected - Violates fail-fast principle

### Option 3: Use run_workflow_from_config() (Chosen Solution)

**Approach**: Load config at startup, pass object to runtime

```python
# At startup
config_dict = parse_config_file(WORKFLOW_CONFIG_PATH)
workflow_config = WorkflowConfig(**config_dict)  # Fail-fast

# In endpoint
result = await asyncio.to_thread(run_workflow_from_config, workflow_config, inputs_dict)
```

**Pros**:
- ✅ Fail-fast (config errors at startup)
- ✅ Efficient (parse once, use many times)
- ✅ Fast (no repeated parsing)
- ✅ Pre-validated (WorkflowConfig object)

**Cons**:
- None

**Decision**: ✅ **Accepted** - Best approach for server context

---

## Future Considerations

### Runtime API Refactoring

Consider unifying the two functions:

```python
def run_workflow(
    config: str | WorkflowConfig,  # Accept both types
    inputs: Dict[str, Any],
    verbose: bool = False
) -> Dict[str, Any]:
    """Run workflow from file path or config object"""
    if isinstance(config, str):
        config_dict = parse_config_file(config)
        config = WorkflowConfig(**config_dict)

    # Execute with WorkflowConfig object
    return _execute_workflow(config, inputs, verbose)
```

**Pros**:
- Single function, clearer API
- Type-based dispatch (Pythonic)

**Cons**:
- Breaks existing code (requires migration)
- Less explicit (function name doesn't indicate file vs object)

**Recommendation**: Consider for v0.2+ after v0.1 release stabilizes

---

## References

- **T-023**: FastAPI Server Template (created the buggy template)
- **ADR-012**: Docker Deployment Architecture
- **BUG-001**: Docker Build PyPI Dependency (first deployment bug)
- **Runtime Executor**: `src/configurable_agents/runtime/executor.py`

---

## Related Issues

This bug is related to BUG-001:
- Both bugs in deployment system (T-022, T-023, T-024)
- Both critical severity (total feature failure)
- Both caught during manual testing (before release)
- Both fixed same day

**Pattern**: Deployment feature not tested end-to-end before user testing.

**Action**: Add comprehensive deployment integration tests (see Process Improvements).

---

## Sign-Off

**Bug Fixed By**: Claude AI Assistant
**Verified By**: Pending (user must redeploy)
**Approved By**: Pending
**Change Level**: 2 (LOCAL - template only)
**Release Notes**: Include in v0.1 as "Fixed: Deployed workflows now execute correctly"

---

**End of Bug Report**
