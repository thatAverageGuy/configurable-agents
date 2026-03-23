# ADR-027: Runtime Overrides Layer

**Status**: ACCEPTED
**Date**: 2026-03-23
**Task**: T-014

---

## Context

The v1.0 system treats the YAML config as the sole source of truth for all execution parameters — including memory scope, LLM temperature, and model selection. This means changing any parameter requires editing the config file, which defeats the goal of having a single reusable config that can be invoked differently across contexts.

The specific trigger for this ADR: memory is configured per-node in YAML (`memory.enabled`, `memory.default_scope`). For workflows that need to behave consistently across runs (GTM copy generation, research templates), memory should be disabled or scoped to `workflow` (not `agent`) — but the same YAML config should work for both "full memory" and "no memory" invocations without file changes.

The broader pattern will recur: LLM temperature override, model switching for cost optimization, and disabling specific features for testing all share the same need.

---

## Decision

Introduce a **`runtime_overrides` dict** as an optional, third parameter to `run_workflow()`, alongside `config_path` and `inputs`. The overrides are applied after config parsing and validation, before execution. They shadow specific config values for the duration of that run only.

The overrides are surfaced at each interface:

**CLI**:
```bash
configurable-agents run workflow.yaml \
  --input topic="AI Safety" \
  --memory-scope none
```

**Webhook POST body**:
```json
{
  "workflow_name": "research_agent",
  "inputs": { "topic": "AI Safety" },
  "runtime": { "memory": { "scope": "none" } }
}
```

**Programmatic**:
```python
run_workflow("workflow.yaml", inputs, runtime_overrides={"memory": {"scope": "none"}})
```

### Override Scope (v1.1)

Initial supported overrides (intentionally minimal):
```python
{
  "memory": {
    "scope": "none | workflow | agent",  # overrides all nodes' memory.default_scope
    "enabled": True | False               # overrides all nodes' memory.enabled
  }
}
```

### Override Application

Overrides are applied in `executor.py`, after `parse_and_validate_config()` and before `build_state_model()`. They are merged into the parsed config object — not stored or logged as part of the config snapshot (the config snapshot in the execution record reflects the original YAML, not the overrides). Overrides ARE logged as a separate field in the execution record for auditability.

---

## Alternatives Considered

**A: Special input variables (`_memory_enabled=false`)**
Pass override intent as workflow inputs. Rejected: pollutes the state model concern, inputs are workflow data not execution control, type-unsafe.

**B: Multiple config files with inheritance**
Define a base config and environment-specific override files. Rejected: more files, same problem — you still need to edit something per invocation.

**C: Named profiles in YAML**
```yaml
runtime_profiles:
  production: { memory: { scope: none } }
  testing: { memory: { scope: workflow } }
```
Invoked via `--profile production`. Not rejected — this is a good future addition built on top of the runtime overrides layer. Deferred to a later task.

**D: Environment variables**
`MEMORY_SCOPE=none configurable-agents run workflow.yaml`. Rejected for primary interface: env vars don't compose well, don't show in logs naturally, and are invisible to the webhook interface.

---

## Consequences

**Positive**:
- One config file, many invocation patterns
- Webhook triggers can control memory scope per-request without config changes
- Paves the way for future overrides (model, temperature, tool config)

**Negative**:
- Overrides are not visible in the YAML — a reviewer looking at the file alone doesn't know what overrides were applied to a given run. Mitigated by logging overrides in the execution record.
- Could be misused to silently change behavior in production. Mitigated by execution record logging.

**Future**:
- Named profiles (ADR candidate when implemented)
- Per-node overrides: `{"nodes": {"draft": {"memory": {"enabled": false}}}}` — deferred, all-or-nothing is sufficient for v1.1
