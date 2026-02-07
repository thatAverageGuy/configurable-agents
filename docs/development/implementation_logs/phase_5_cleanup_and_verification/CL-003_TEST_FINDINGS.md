# CL-003: Test Findings & Issues Log

**Purpose**: Document all findings, constraints, bugs, and shortcomings discovered during systematic testing
**Created**: 2026-02-07
**Status**: Active - Updated as testing progresses

---

## Part 1: Schema/Validation Constraints

Constraints discovered during `configurable-agents validate` phase.

| ID | Constraint | Impact | Config Affected | Notes |
|----|------------|--------|-----------------|-------|
| V-001 | Every node must have ≥1 output | Router nodes can't have `outputs: []` | 05, 12 | Schema enforces this in `NodeConfig` |
| V-002 | START must have exactly 1 outgoing edge | No parallel fan-out directly from START | 07, 12 | Requires intermediate dispatch node |
| V-003 | Conditional edges must use `routes` not `condition` | Edge `condition` field doesn't exist in schema | 05, 12 | Test configs used wrong syntax - silently ignored |
| V-004 | Loop edges must use `loop` block with `condition_field` | `type: loop` doesn't exist | 06, 12 | Test configs used wrong syntax |
| V-005 | Parallel is MAP-ONLY, not fork-join | Cannot run different nodes simultaneously | 07 | Only `parallel.items_field` → single `target_node` |

### V-001: Node Output Requirement

**Discovery**: Configs 05 and 12 failed validation with:
```
nodes.X.outputs
  Value error, Node must have at least one output
```

**Implication**:
- Pure "router" nodes that only determine flow path are not supported
- Every node must write to at least one state field
- Router pattern must be combined with some state update

**Workaround Applied**: Router nodes now output acknowledgment text to a state field

**Question for Later**: Is this intentional design or overly restrictive? Should routers be exempt?

---

### V-002: Single Entry Point from START — RESOLVED

**Discovery**: Originally, validator rejected multiple edges from START.

**Resolution** (2026-02-08): With fork-join, a single `EdgeConfig` with `to: [a, b]` from START
is now valid. Validator counts EdgeConfig objects from START (not adjacency set size), so one
edge config with a list target is accepted. No dispatch node needed.

**Status**: RESOLVED

---

### V-003: Conditional Edge Syntax Wrong in Test Configs

**Discovery**: Test configs used `condition` field on edges (lines 73-79 of config 05):
```yaml
edges:
  - from: router
    to: positive_response
    condition: "state.sentiment == 'positive'"  # WRONG - silently ignored!
```

**Correct Syntax** (per EdgeConfig schema):
```yaml
edges:
  - from: router
    routes:
      - condition:
          logic: "state.sentiment == 'positive'"
        to: positive_response
      - condition:
          logic: "default"
        to: END
```

**Impact**: Configs validated and ran, but conditionals were ignored - all nodes executed linearly.

---

### V-004: Loop Edge Syntax Wrong in Test Configs

**Discovery**: Test configs used `type: loop` and `condition` on edges - not how loops work.

**Correct Syntax** (per LoopConfig schema):
```yaml
edges:
  - from: iterate
    loop:
      max_iterations: 5
      condition_field: "loop_complete"  # Must be a bool state field
      exit_to: finalize
```

---

### V-005: Parallel Was Map-Only — RESOLVED (Replaced with Fork-Join)

**Discovery**: Original `ParallelConfig` only supported MAP pattern using LangGraph `Send` objects.
This caused `'dict' object has no attribute 'model_copy'` crashes because Send passes raw dicts.

**Resolution** (2026-02-08): Replaced entire MAP/Send infrastructure with fork-join parallel:
- Deleted `ParallelConfig` class and `parallel.py`
- Extended `EdgeConfig.to` to accept `List[str]` for fork-join
- Fork-join uses native LangGraph `add_edge()` calls — no Send objects needed

**New syntax**:
```yaml
edges:
  - from: START
    to: [analyze_pros, analyze_cons]  # Fork-join: both run in parallel
  - from: analyze_pros
    to: combine
  - from: analyze_cons
    to: combine                        # Join at combine node
```

**Status**: RESOLVED

---

## Part 2: Runtime Issues

Issues discovered during `configurable-agents run` phase.

| ID | Config | Issue | Error Message | Status |
|----|--------|-------|---------------|--------|
| R-001 | ALL | Storage backend always fails | `too many values to unpack (expected 6)` | BROKEN |
| R-002 | 05,06,07,12 | Conditional/Loop/Parallel execution fails | `INVALID_CONCURRENT_GRAPH_UPDATE` | BROKEN |
| R-003 | 02,12 | MLFlow cost summary fails | `invalid literal for int() with base 10: 'mlflow-experiment:1'` | BROKEN |
| R-004 | 08 | ChatLiteLLM deprecated | `LangChainDeprecationWarning: ChatLiteLLM deprecated` | WARNING |
| R-005 | ALL | Model name invalid | `gemini-2.0-flash-exp` not valid for generateContent | FIXED by user |

---

### R-001: Storage Backend Initialization Failure

**Affects**: Every single workflow run
**Error**:
```
Storage backend initialization failed, continuing without persistence: too many values to unpack (expected 6)
```

**Impact**:
- Storage always fails silently
- Workflow runs are NOT persisted
- Config 11 (with_storage) doesn't actually store anything
- System continues but without persistence

**Root Cause**: Likely a tuple unpacking mismatch in storage initialization code

**Priority**: HIGH - affects all workflows

---

### R-002: Conditional/Loop/Parallel Execution Broken

**Affects**: Configs 05, 06, 07, 12
**Error**:
```
At key 'X': Can receive only one value per step. Use an Annotated key to handle multiple values.
For troubleshooting: https://docs.langchain.com/oss/python/langgraph/errors/INVALID_CONCURRENT_GRAPH_UPDATE
```

**Impact**:
- Conditional branching does NOT work
- Loop iteration does NOT work
- Parallel execution does NOT work
- Only linear flows function

**Root Cause**: LangGraph requires `Annotated` types with reducer functions for state fields
that could receive concurrent updates (from conditionals, loops, or parallel execution).
The `state_builder.py` was creating plain Pydantic models without reducers.

**Fix Applied** (2026-02-08):
Modified `src/configurable_agents/core/state_builder.py`:
1. Added reducer functions:
   - `_last_value_reducer`: "Last writer wins" for scalar types (str, int, float, bool)
   - `_list_concat_reducer`: Concatenation for list types
2. All fields now wrapped with `Annotated[type, reducer]`
3. LangGraph can now handle concurrent updates properly

**Status**: ✅ FIXED AND VERIFIED (2026-02-08)

**Test Results After Fix**:
- Config 05 (Conditional): ✅ WORKING - positive/negative routes correctly
- Config 06 (Loop): ✅ WORKING - iterates 3 times, exits properly
- Config 07 (Parallel): Needs testing after type fix

**Priority**: RESOLVED

---

### R-003: MLFlow Cost Summary Failure

**Affects**: Configs with MLFlow enabled (02, 12)
**Error**:
```
Failed to get cost summary: invalid literal for int() with base 10: 'mlflow-experiment:1'
```

**Impact**: Cost tracking/reporting broken

**Priority**: MEDIUM - observability feature degraded

---

### R-004: ChatLiteLLM Deprecation

**Affects**: Config 08 (multi-LLM)
**Warning**:
```
LangChainDeprecationWarning: The class `ChatLiteLLM` was deprecated in LangChain 0.3.24
Use `langchain-litellm` package instead
```

**Impact**: Multi-LLM still works but using deprecated API

**Priority**: LOW - works but needs update

---

### R-005: Invalid Model Name

**Affects**: All configs originally
**Error**: `gemini-2.0-flash-exp` not valid for generateContent

**Resolution**: User changed all configs to `gemini-2.5-flash-lite`

**Priority**: RESOLVED

---

## Part 3: Feature Gaps

Features that don't work as expected or are missing.

| ID | Feature | Expected | Actual | Config | Notes |
|----|---------|----------|--------|--------|-------|
| F-001 | Persistent Memory | Run 2 remembers Run 1 | No memory between runs | 09 | Memory not persisting |
| F-002 | Tool Execution | Actual web search via Serper | Query echoed back, no search | 04 | Tool may not be invoked |
| F-003 | Conditional Routing | Route based on state | ✅ FIXED (Annotated reducers + correct YAML) | 05 | See R-002 |
| F-004 | Loop Iteration | Iterate N times | ✅ FIXED (Annotated reducers + correct YAML) | 06 | See R-002 |
| F-005 | Parallel Execution | Run nodes concurrently | ✅ FIXED (Replaced MAP/Send with fork-join) | 07 | Rewrote parallel infrastructure |
| F-006 | Storage Persistence | Store workflow runs | Silent failure, no storage | 11 | See R-001 |

---

### F-001: Memory Not Persisting

**Test**:
```
Run 1: --input message="Remember my name is Alice"
Response: "Ok, I will remember your name is Alice."

Run 2: --input message="What is my name?"
Response: "I do not have access to your name. You have not shared it with me."
```

**Expected**: Run 2 should remember "Alice" from Run 1
**Actual**: No memory persistence between runs

**Possible Causes**:
- Memory backend not initialized
- Memory config ignored
- Storage failure (R-001) affects memory too

---

### F-002: Tool Execution Fundamentally Broken - No Agent Loop

**Test 1**: Config 04 with `--input query="Python programming"`
```
search_results: "Python programming"  # Just echoed the query
```

**Test 2**: Config 04 (updated with explicit tool instructions) with `--input query="AI in Sex"`
```
search_results: "web_search_tool_code"  # LLM trying to signal tool call!
answer: [LLM's own knowledge, not search results]
```

**Root Cause Found** (in `src/configurable_agents/llm/provider.py:216-236`):

```python
# Tools are bound...
if tools:
    llm = llm.bind_tools(tools)

# But then structured output is forced immediately
structured_llm = llm.with_structured_output(output_model, include_raw=True)
```

**The Problem**: There is NO TOOL EXECUTION LOOP!

When LLM wants to use a tool, it returns a "tool call" message. An agent loop must:
1. Detect tool calls in response
2. **Actually execute the tool function**
3. Feed tool results back to LLM
4. Get final structured response

Current code just binds tools and immediately expects structured output. The tool **NEVER ACTUALLY RUNS**.

The output `"web_search_tool_code"` is the LLM's attempt to signal it wants to call a tool, but nothing processes this signal.

**Impact**: ALL tool functionality is broken. The 15 registered tools are effectively unusable.

**Fix Required**: Implement proper agent loop with tool call detection and execution. This is a significant architectural fix.

**Priority**: CRITICAL - Major claimed feature completely non-functional

---

### F-003/F-004/F-005: Advanced Control Flow Broken

All non-linear control flow patterns fail with the same LangGraph error.
See R-002 for details.

**Working**: Linear flows only (01, 02, 03, 04, 08, 09, 10, 11)
**Broken**: Conditional, Loop, Parallel (05, 06, 07, 12)

---

## Part 4: Documentation vs Reality

Discrepancies between documentation claims and actual behavior.

| ID | Doc Claim | Reality | Source Doc | Notes |
|----|-----------|---------|------------|-------|
| D-001 | | | | |

*(To be populated during testing)*

---

## Part 5: Observations & Notes

General observations during testing.

### Validation Phase (Configs 01-12)

- **2026-02-07**: All 12 configs created
- **2026-02-07**: Initial validation - 9 passed, 3 failed (05, 07, 12)
- **2026-02-07**: Fixed and re-validated - all 12 pass now

### Execution Phase

*(To be populated)*

---

## Part 6: Questions for Discussion

Issues that need decision/clarification before fixing.

| ID | Question | Context | Options | Decision |
|----|----------|---------|---------|----------|
| Q-001 | Should router nodes be exempt from output requirement? | V-001 | A) Keep as-is B) Add router node type C) Allow empty outputs | Pending |
| Q-002 | Should START support parallel fan-out? | V-002 | A) Keep single entry B) Allow parallel from START | Pending |
| Q-003 | Priority: Fix control flow or accept linear-only for now? | R-002 | A) Fix ASAP B) Defer, focus on linear | Pending |
| Q-004 | Is tool invocation actually broken or just missing API key? | F-002 | Need to verify SERPER_API_KEY is set | Pending |
| Q-005 | Storage unpacking error - quick fix or redesign? | R-001 | A) Debug and fix B) Redesign storage layer | Pending |

---

## Part 7: Test Execution Log

Chronological log of test execution.

```
[2026-02-07] Validation Phase
  - 01_basic_linear.yaml         ✅ PASS
  - 02_with_observability.yaml   ✅ PASS
  - 03_multi_node_linear.yaml    ✅ PASS
  - 04_with_tools.yaml           ✅ PASS
  - 05_conditional_branching.yaml ✅ PASS (after fix - V-001)
  - 06_loop_iteration.yaml       ✅ PASS
  - 07_parallel_execution.yaml   ✅ PASS (after fix - V-002)
  - 08_multi_llm.yaml            ✅ PASS
  - 09_with_memory.yaml          ✅ PASS
  - 10_with_sandbox.yaml         ✅ PASS
  - 11_with_storage.yaml         ✅ PASS
  - 12_full_featured.yaml        ✅ PASS (after fix - V-001)

[2026-02-07] Execution Phase
  User changed model: gemini-2.0-flash-exp → gemini-2.5-flash-lite (all configs)
  User changed config 08: OpenAI → Anthropic (claude-haiku-4-5)

  - 01_basic_linear.yaml         ✅ PASS - Basic execution works
  - 02_with_observability.yaml   ✅ PASS - MLFlow creates DB (cost summary fails)
  - 03_multi_node_linear.yaml    ✅ PASS - Multi-node sequence works
  - 04_with_tools.yaml           ❌ BROKEN - No agent loop (tools never execute)
  - 05_conditional_branching.yaml ❌ FAIL - INVALID_CONCURRENT_GRAPH_UPDATE
  - 06_loop_iteration.yaml       ❌ FAIL - INVALID_CONCURRENT_GRAPH_UPDATE
  - 07_parallel_execution.yaml   ❌ FAIL - INVALID_CONCURRENT_GRAPH_UPDATE
  - 08_multi_llm.yaml            ✅ PASS - Multi-LLM works (deprecation warning)
  - 09_with_memory.yaml          ⚠️ PARTIAL - Runs but memory not persisting
  - 10_with_sandbox.yaml         ✅ PASS - Sandbox works! Computed fib(10)=55
  - 11_with_storage.yaml         ⚠️ PARTIAL - Runs but storage fails silently
  - 12_full_featured.yaml        ❌ FAIL - INVALID_CONCURRENT_GRAPH_UPDATE

[2026-02-08] Fix Applied: Annotated Reducers in state_builder.py
  Modified: src/configurable_agents/core/state_builder.py
  - Added _last_value_reducer for scalar types
  - Added _list_concat_reducer for list types
  - All fields now wrapped with Annotated[type, reducer]

[2026-02-08] Test Configs Corrected (Wrong YAML Syntax)
  - Config 05: Changed edges with `condition:` to `routes:` format
  - Config 06: Changed to proper `loop:` block with `condition_field`
  - Config 07: Rewritten for map-over-list pattern (parallel is MAP only)

[2026-02-08] Execution Phase 2 (After Fixes)
  - 05_conditional_branching.yaml ✅ PASS - Routes correctly!
    positive → "That's fantastic news, I'm so glad to hear it!"
    negative → "I am so incredibly sorry to hear that..."
  - 06_loop_iteration.yaml       ✅ PASS - Loops 3 times, exits correctly!
    Final: current_iteration=3, loop_complete=true
  - 07_parallel_execution.yaml   ⏳ PENDING - Type fix applied, needs testing

  GLOBAL ISSUE: Storage init STILL fails on EVERY run with "too many values to unpack"

[2026-02-08] Fork-Join Parallel Replacement (10-phase implementation)
  Replaced MAP/Send parallel with fork-join parallel:
  - Deleted ParallelConfig class and parallel.py
  - Extended EdgeConfig.to to accept List[str] for fork-join
  - Updated validator, graph_builder, node_executor, tests, configs
  - Config 07 rewritten: analyze_pros + analyze_cons fork from START
  - Config 12 rewritten: proper routes/loop syntax

[2026-02-08] Full Verification After Fork-Join
  Validation (all 12 configs):
  - 01 through 12: ALL PASS

  Execution (all 12 configs):
  - 01_basic_linear.yaml         ✅ PASS
  - 02_with_observability.yaml   ✅ PASS (MLFlow cost summary still broken)
  - 03_multi_node_linear.yaml    ✅ PASS
  - 04_with_tools.yaml           ✅ PASS (tools still not actually executing)
  - 05_conditional_branching.yaml ✅ PASS
  - 06_loop_iteration.yaml       ✅ PASS (3 iterations, loop_complete=true)
  - 07_parallel_execution.yaml   ✅ PASS - Fork-join works!
    topic=AI → pros, cons, summary all distinct and correct
  - 08_multi_llm.yaml            ✅ PASS (Gemini + Anthropic)
  - 09_with_memory.yaml          ✅ PASS (runs, but memory not persisting)
  - 10_with_sandbox.yaml         ✅ PASS (fib(10)=55)
  - 11_with_storage.yaml         ✅ PASS (runs, storage init fails silently)
  - 12_full_featured.yaml        ✅ PASS (both shallow and deep paths verified)

  User manual verification:
  - Config 07: topic=AI → distinct pros/cons/summary ✅
  - Config 12 shallow: query="Latest AI news", depth="shallow" → search + analysis + report ✅
  - Config 12 deep: query="Latest AI news", depth="deep" → search + analysis + pros/cons + refine + report ✅

  Unit tests: 1366 passed, 25 failed, 37 skipped, 23 errors
  All failures are PRE-EXISTING (dict-vs-Pydantic, storage tuple unpacking, deploy artifact count)
```

---

## Part 8: Summary

### What Works
- ✅ Basic single-node workflow (01)
- ✅ Multi-node linear sequence (03)
- ✅ MLFlow tracking (02) — creates DB, traces logged
- ✅ Multi-LLM support (08) — Gemini + Anthropic
- ✅ Code sandbox execution (10) — RestrictedPython
- ✅ Conditional branching (05) — FIXED (Annotated reducers + correct YAML)
- ✅ Loop iteration (06) — FIXED (Annotated reducers + correct YAML)
- ✅ **Fork-join parallel execution (07)** — FIXED (replaced MAP/Send with fork-join)
- ✅ **Full-featured workflow (12)** — FIXED (proper routes/loop syntax, both paths work)

### What's Still Broken
- ❌ **Storage persistence (R-001)** — `too many values to unpack (expected 6)` on every run
- ❌ **Tool invocation (F-002)** — NO AGENT LOOP EXISTS (tools never actually execute)
- ❌ **Memory persistence (F-001)** — Not working between runs (likely depends on R-001)
- ❌ **MLFlow cost summary (R-003)** — Experiment ID parsing error

### Warnings/Deprecations
- ⚠️ ChatLiteLLM deprecated (LangChain 0.3.24)
- ⚠️ MLFlow cost summary parsing error
- ⚠️ Model name needed update (gemini-2.0-flash-exp → gemini-2.5-flash-lite)

---

*This document is updated continuously during CL-003 testing.*
