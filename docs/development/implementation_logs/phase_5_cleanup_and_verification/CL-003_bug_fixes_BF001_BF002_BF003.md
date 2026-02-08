# CL-003: Bug Fix Session — BF-001, BF-002, BF-003

**Date**: 2026-02-08
**Session**: Bug fix batch (storage, tools, memory)
**Status**: Complete — all 3 fixes verified

---

## Overview

Fixed the three highest-priority bugs discovered during CL-003 systematic testing.
All fixes are batched into a single commit for atomic deployment.

---

## BF-001: Storage Backend Tuple Unpacking

**Problem**: `create_storage_backend()` returns 8 values but callers unpacked 3-6,
causing `too many values to unpack (expected 6)` on every workflow run.

**Root Cause**: Factory was extended to return 8 repos (runs, states, agents, chat,
webhook, memory, workflow_reg, orchestrator) but callers were never updated.

**Files Changed**:
| File | Line(s) | Change |
|------|---------|--------|
| `src/configurable_agents/runtime/executor.py` | 212 | 6 → 8 values |
| `src/configurable_agents/cli.py` | 1287, 1355 | 3 → 8 values |
| `tests/registry/test_ttl_expiry.py` | 21 | 5 → 8 values |
| `tests/registry/test_server.py` | 30 | 5 → 8 values |
| `tests/runtime/test_executor_storage.py` | 126, 176, 229 | 5 → 8 values |

**Verification**: 47 previously-failing tests pass. Configs 09, 11, 12 run with storage.

---

## BF-002: Tool Execution Agent Loop

**Problem**: `call_llm_structured()` in `provider.py` called `bind_tools()` then
immediately `with_structured_output()`. LangChain skips tool calls when structured
output is forced — tools were bound but NEVER executed.

**Root Cause**: No agent loop existed. The code expected tools to execute automatically
via `bind_tools()` but LangChain requires explicit tool call detection, execution,
and result feeding.

**Solution**: Two-phase approach:
1. **Phase 1 — Tool loop** (`_execute_tool_loop()`):
   - Bind tools to LLM (no structured output)
   - Invoke with HumanMessage
   - Detect `tool_calls` in response
   - Execute tools via `tool.invoke(tool_args)`
   - Feed ToolMessage results back
   - Repeat until no more tool calls (max 10 iterations)
   - Build enriched prompt with tool results

2. **Phase 2 — Structured output**:
   - Use clean LLM (no tools bound)
   - Apply `with_structured_output()`
   - Pass enriched prompt (original + tool results)
   - Extract structured response

**Files Changed**:
| File | Change |
|------|--------|
| `src/configurable_agents/llm/provider.py` | Added `_execute_tool_loop()`, modified `call_llm_structured()` |
| `tests/llm/test_provider.py` | Updated `test_call_with_tools` mock for two-phase flow |

**Verification**: Config 12 `web_search` returns real Serper results. 23/23 provider tests pass.

---

## BF-003: Memory Persistence

**Problem**: Config 09 memory doesn't persist between runs. Run 1 stores information,
Run 2 can't recall it. Database shows 0 memory records after execution.

**Root Causes Found (3 separate bugs)**:

### Bug 1: Namespace ignores scope
`AgentMemory` was created with `workflow_id=run_uuid` and `node_id=process_with_memory`
regardless of the configured scope. For "agent" scope (cross-run persistence), namespace
should be `agent:*:*:key` but was `agent:{uuid}:{node}:key` — unique per run.

**Fix**: Scope-aware parameter passing in `node_executor.py`:
```python
mem_workflow_id = workflow_id if scope in ("workflow", "node") else None
mem_node_id = node_id if scope == "node" else None
```

### Bug 2: `AgentMemory.__len__` truthiness trap
`AgentMemory` defines `__len__()` returning 0 for empty memory. Python's truthiness
check `if agent_memory:` calls `bool()` → `__len__()` → 0 → `False`. This silently
skipped ALL memory read/write code on the first run (when memory is empty).

**Fix**: Changed `if agent_memory:` to `if agent_memory is not None:` (2 locations).

### Bug 3: `GlobalConfig` missing `memory` field
Config 09 has `config.memory:` in YAML but `GlobalConfig` had no `memory` field.
Pydantic's `model_config` has `extra = "ignore"`, so the field was silently dropped.

**Fix**: Added `memory: Optional[MemoryConfig] = Field(None)` to `GlobalConfig`.

### Additional improvements
- Auto-extraction of facts from LLM responses via lightweight extraction call
- `max_entries` limit (default 50) on memory entries injected into prompts
- Fixed config 09 field names (`default_scope` instead of `scope`, removed `backend`)
- Added MEM-03 future enhancement task for memory revisit/optimization

**Files Changed**:
| File | Change |
|------|--------|
| `src/configurable_agents/config/schema.py` | Added `memory` to `GlobalConfig`, `max_entries` to `MemoryConfig` |
| `src/configurable_agents/core/node_executor.py` | Scope-aware namespaces, `is not None` checks, fact extraction, memory injection |
| `test_configs/09_with_memory.yaml` | Fixed field names |

**Verification**:
```
Run 1: message="Remember my name is Alice"
→ Response: "Okay, Alice. I will remember that."
→ DB: 1 record — namespace=test_09_memory:*:*:name, value="Alice"

Run 2: message="What is my name?"
→ Response: "Your name is Alice."
```

---

## Test Results After All Fixes

Core test modules (node_executor, provider, graph_builder, schema, validator, executor_storage):
- **187 passed, 3 pre-existing failures**
- Pre-existing: dict-vs-Pydantic in test_node_executor (BF-005)

All 12 test configs now pass validation AND execution.

---

## Files Modified (Complete List)

| File | Fix | Change |
|------|-----|--------|
| `src/configurable_agents/runtime/executor.py` | BF-001 | Tuple unpacking 6→8 |
| `src/configurable_agents/cli.py` | BF-001 | Tuple unpacking 3→8 (2 sites) |
| `tests/registry/test_ttl_expiry.py` | BF-001 | Tuple unpacking 5→8 |
| `tests/registry/test_server.py` | BF-001 | Tuple unpacking 5→8 |
| `tests/runtime/test_executor_storage.py` | BF-001 | Tuple unpacking 5→8 (3 sites) |
| `src/configurable_agents/llm/provider.py` | BF-002 | Added tool loop, two-phase structured output |
| `tests/llm/test_provider.py` | BF-002 | Updated mock for two-phase flow |
| `src/configurable_agents/config/schema.py` | BF-003 | GlobalConfig.memory field, MemoryConfig.max_entries |
| `src/configurable_agents/core/node_executor.py` | BF-003 | Memory scope, truthiness, extraction, injection |
| `test_configs/09_with_memory.yaml` | BF-003 | Fixed config field names |
| `CLAUDE.md` | Docs | Added pre-commit doc rule, commit format examples |
| `CHANGELOG.md` | Docs | BF-001, BF-002, BF-003 entries |
| `CONTEXT.md` | Docs | Session state, next steps |
| `docs/development/TASKS.md` | Docs | BF-001/002/003 status, MEM-03 future task |
| `test_configs/README.md` | Docs | Updated test results for all 12 configs |
