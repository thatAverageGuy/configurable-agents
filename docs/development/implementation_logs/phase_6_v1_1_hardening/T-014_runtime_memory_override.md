# T-014: Runtime Memory Override — Per-Invocation Control

**Status**: TODO
**Priority**: HIGH
**Created**: 2026-03-23
**ADR**: [ADR-027](../../adr/ADR-027-runtime-overrides-layer.md)

---

## Problem

Memory scope is configured per-node in YAML (`memory.enabled`, `memory.default_scope`). Changing it requires editing the config file, which breaks the goal of having a single reusable workflow config invokable in different modes:
- Production GTM run: memory disabled (consistent behavior, no cross-run state bleed)
- Development/testing: memory scoped to `workflow` (fresh each run)
- Full agent mode: memory scoped to `agent` (cross-run persistence)

The same workflow YAML should support all three without file changes.

---

## Success Criteria

- `configurable-agents run workflow.yaml --memory-scope none` disables all memory for the run
- `configurable-agents run workflow.yaml --memory-scope workflow` scopes memory to this run only
- Webhook POST body with `"runtime": {"memory": {"scope": "none"}}` disables memory for that invocation
- `run_workflow(path, inputs, runtime_overrides={"memory": {"scope": "none"}})` works programmatically
- Original YAML is not modified
- Runtime override is logged in the execution record for auditability
- All memory-disabled runs behave identically to having `memory.enabled: false` in YAML

---

## Implementation Approach

### Step 1: Define `RuntimeOverrides` model

**File**: `src/configurable_agents/config/schema.py` (or new `src/configurable_agents/config/runtime.py`)

```python
class MemoryRuntimeOverride(BaseModel):
    scope: Optional[Literal["none", "workflow", "agent"]] = None
    enabled: Optional[bool] = None

class RuntimeOverrides(BaseModel):
    memory: Optional[MemoryRuntimeOverride] = None
    # Future: llm, tools, etc.
```

### Step 2: Update `run_workflow()` signature

**File**: `src/configurable_agents/runtime/executor.py`

```python
def run_workflow(
    config_path: str,
    inputs: Dict[str, Any],
    verbose: bool = False,
    runtime_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
```

### Step 3: Apply overrides after config parse, before execution

**File**: `src/configurable_agents/runtime/executor.py`

After `parse_and_validate_config(config_path)` and before `build_state_model()`:

```python
if runtime_overrides:
    validated_overrides = RuntimeOverrides(**runtime_overrides)
    config = _apply_runtime_overrides(config, validated_overrides)
    logger.info(f"Runtime overrides applied: {runtime_overrides}")
```

`_apply_runtime_overrides(config, overrides)`:
```python
def _apply_runtime_overrides(config: WorkflowConfig, overrides: RuntimeOverrides) -> WorkflowConfig:
    if overrides.memory is None:
        return config

    # Apply memory overrides to all nodes that have memory config
    for node in config.nodes:
        if node.memory is not None or overrides.memory.enabled is not None:
            # Ensure node has a memory config to modify
            if node.memory is None:
                node.memory = MemoryConfig()

            if overrides.memory.enabled is not None:
                node.memory.enabled = overrides.memory.enabled

            if overrides.memory.scope == "none":
                node.memory.enabled = False

            elif overrides.memory.scope is not None:
                node.memory.default_scope = overrides.memory.scope

    return config
```

### Step 4: Store overrides in execution record

**File**: `src/configurable_agents/runtime/executor.py`

When creating the `Execution` record, add `runtime_overrides` as a JSON field:
```python
run_record = Execution(
    ...
    runtime_overrides=json.dumps(runtime_overrides or {}, default=str),
)
```

Requires migration or nullable column in storage. Check `Execution` model in `storage/`.

### Step 5: Add CLI flag

**File**: `src/configurable_agents/cli.py`

In the `run` subcommand parser:
```python
run_parser.add_argument(
    "--memory-scope",
    choices=["none", "workflow", "agent"],
    default=None,
    help="Override memory scope for this run. 'none' disables memory entirely."
)
```

Build `runtime_overrides` from CLI args:
```python
runtime_overrides = {}
if args.memory_scope:
    runtime_overrides["memory"] = {"scope": args.memory_scope}

result = run_workflow(config_path, inputs, verbose=args.verbose, runtime_overrides=runtime_overrides)
```

### Step 6: Update webhook handler

**File**: `src/configurable_agents/webhooks/router.py`

In `_process_generic_webhook()`, extract `runtime` from the payload:
```python
runtime_overrides = data.get("runtime", {})
result = await run_workflow_async(workflow_name, inputs, runtime_overrides=runtime_overrides)
```

Also update `run_workflow_async()` signature to accept `runtime_overrides`.

---

## Files to Change

| File | Change |
|------|--------|
| `src/configurable_agents/config/schema.py` | Add `RuntimeOverrides`, `MemoryRuntimeOverride` models |
| `src/configurable_agents/runtime/executor.py` | Add `runtime_overrides` param, apply overrides, log in execution record |
| `src/configurable_agents/cli.py` | Add `--memory-scope` flag to `run` command |
| `src/configurable_agents/webhooks/router.py` | Extract `runtime` from webhook payload, pass through |
| Storage `Execution` model | Add nullable `runtime_overrides` JSON column |

---

## Testing Strategy

**Unit tests**:
- `_apply_runtime_overrides()`: verify memory.enabled set to False for `scope=none`
- `_apply_runtime_overrides()`: verify scope set to `workflow` correctly
- `_apply_runtime_overrides()`: verify config with no memory config is unaffected by non-memory overrides

**Integration tests**:
- Run workflow with `--memory-scope none` → verify no memory read/writes occur, verify override in execution record
- Run same workflow without flag → verify memory works as configured in YAML (no regression)
- Webhook: POST with `runtime: {memory: {scope: workflow}}` → verify scoping applied

**Manual verification**:
- Run a memory-enabled workflow twice with `--memory-scope none`, verify outputs are identical (no cross-run state bleed)
- Run same workflow without flag, run again — verify memory facts from first run appear in second

---

## Notes

- `scope: none` is the recommended default for GTM workflows where run-to-run consistency is required
- The overrides layer is designed for extensibility — future overrides (llm.temperature, llm.model) follow the same pattern
- Named profiles (e.g., `--profile production`) are a future addition built on this layer
