# CONTEXT.md

> **Purpose**: Quick context for resuming development. Updated after each task completion.
>
> **For LLMs**: Read this first to understand current state, next action, and project standards.
> Fetch details from linked docs as needed during implementation.

---

**Last Updated**: 2026-02-08

---

## Current State

**Task**: CL-003 | **Phase**: Bug Fixing | **Status**: IN_PROGRESS

### What Was Done This Session

**Fork-Join Parallel Replacement** (10-phase plan, fully implemented):

Replaced broken MAP/Send parallel infrastructure with LangGraph-native fork-join.
The old `ParallelConfig` used `Send` objects that passed raw dicts as state, causing
`'dict' object has no attribute 'model_copy'` crashes. Fork-join uses multiple
`add_edge()` calls — no Send objects needed.

**Key changes**:
- Deleted `ParallelConfig` class and `parallel.py` (149 lines)
- Extended `EdgeConfig.to` to accept `Union[str, List[str]]` for fork-join
- Updated validator, graph_builder, node_executor, all tests, and test configs
- Added dict validation in `node_executor.py` (validates updates against state model)
- Config 07 rewritten: two branch nodes (`analyze_pros`, `analyze_cons`) fork from START
- Config 12 rewritten: proper `routes:` and `loop:` syntax, sequential deep path

**Verification**: All 12 test configs validate AND execute successfully. 1366/1451 unit tests pass (25 failures + 23 errors are all pre-existing, unrelated to fork-join changes).

### What Works Now
- Basic linear workflows (01, 02, 03)
- Multi-LLM support via LiteLLM (08)
- Code sandbox execution via RestrictedPython (10)
- MLFlow observability (02) — tracking works, cost summary broken (R-003)
- Conditional branching (05) — FIXED prior session
- Loop iteration (06) — FIXED prior session
- **Fork-join parallel execution (07)** — FIXED this session
- **Full-featured workflow (12)** — FIXED this session (both shallow and deep paths work)

### What's Still Broken

| ID | Issue | Priority | Root Cause |
|----|-------|----------|------------|
| R-001 | Storage persistence — `too many values to unpack (expected 6)` on every run | HIGH | `create_storage_backend` returns 6 values but callers expect 5 |
| F-002 | Tool invocation — No agent loop in `provider.py`. `bind_tools()` called but tool calls never executed | CRITICAL | Need tool call detection → execute → feed results → get final response loop |
| F-001 | Memory persistence — Not persisting between runs | MEDIUM | Likely depends on R-001 (storage init failure) |
| R-003 | MLFlow cost summary — `invalid literal for int()` parsing `'mlflow-experiment:1'` | MEDIUM | Experiment ID parsing bug in cost reporter |
| R-004 | ChatLiteLLM deprecated — LangChain 0.3.24 deprecation warning | LOW | Need to migrate to `langchain-litellm` package |

### Pre-existing Test Failures (NOT caused by our changes)

| Area | Count | Root Cause |
|------|-------|------------|
| `test_node_executor.py` + `test_node_executor_metrics.py` | 7 failures | Tests access `.research`/`.summary` on dict (execute_node returns dict, tests expect Pydantic) |
| `test_executor_storage.py` + `test_server.py` + `test_ttl_expiry.py` | 3 fails + 23 errors | `create_storage_backend` returns 6 values, tests unpack 5 |
| `test_generator.py` + `test_generator_integration.py` | 5 failures | Deploy generator creates 10 artifacts, tests expect 8 |
| `test_integration.py` (sandbox) | 10 failures | Same dict-vs-Pydantic issue as node_executor |

### Next Steps (Recommended Priority Order)
1. [ ] **BF-001: Fix storage backend** — Fix tuple unpacking in `create_storage_backend` (R-001). This likely unblocks memory persistence (F-001) and storage tests.
2. [ ] **BF-002: Fix tool execution** — Implement agent loop in `provider.py` (F-002). Tools are bound but never actually executed. Need: detect tool calls → execute tool → feed results back → get structured response.
3. [ ] **BF-003: Fix memory persistence** — Verify after storage fix (F-001). May resolve automatically.
4. [ ] **BF-004: Fix MLFlow cost summary** — Fix experiment ID parsing (R-003).
5. [ ] **BF-005: Fix pre-existing test failures** — Update tests to expect dict returns from `execute_node`, fix storage tuple unpacking in tests, fix deploy artifact count.
6. [ ] **BF-006: Migrate ChatLiteLLM** — Update to `langchain-litellm` package (R-004).

### Blockers
- None currently

---

## Files Modified This Session (Fork-Join Parallel)

| File | Action | Change |
|------|--------|--------|
| `src/configurable_agents/config/schema.py` | Modified | Deleted `ParallelConfig`, extended `EdgeConfig.to` to `Union[str, List[str]]` |
| `src/configurable_agents/config/__init__.py` | Modified | Removed `ParallelConfig` export |
| `src/configurable_agents/config/validator.py` | Modified | Removed parallel validation, handle list `to`, fixed START edge count |
| `src/configurable_agents/core/graph_builder.py` | Modified | Handle list `to` with multiple `add_edge()`, removed Send logic |
| `src/configurable_agents/core/parallel.py` | **DELETED** | Entire 149-line Send-based parallel module removed |
| `src/configurable_agents/core/__init__.py` | Modified | Removed parallel exports |
| `src/configurable_agents/core/node_executor.py` | Modified | Added dict validation (validates updates against state model) |
| `test_configs/07_parallel_execution.yaml` | Rewritten | Fork-join: `to: [analyze_pros, analyze_cons]` |
| `test_configs/12_full_featured.yaml` | Rewritten | Proper routes/loop syntax, sequential deep path |
| `test_configs/README.md` | Updated | Config 07 description, test results |
| `tests/core/test_parallel.py` | **DELETED** | All referenced removed classes |
| `tests/core/test_graph_builder.py` | Modified | Fork-join edge test replaces parallel edge test |
| `tests/config/test_schema.py` | Modified | `TestEdgeConfigForkJoin` replaces `TestParallelConfig` |
| `tests/config/test_validator.py` | Modified | Fork-join validator tests replace parallel tests |

## Pending Work

| Task | Summary | Details |
|------|---------|---------|
| CL-003 | Codebase cleanup, testing, and verification | docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_TEST_FINDINGS.md |
| BF-001 | Fix storage backend tuple unpacking | Investigate `create_storage_backend` return value mismatch |
| BF-002 | Implement tool execution agent loop | src/configurable_agents/llm/provider.py |
| BF-003 | Fix memory persistence | Likely depends on BF-001 |

## How to Proceed (For Next Session)

**Storage fix (BF-001)** is the highest-leverage fix:
- Search for `create_storage_backend` in `src/configurable_agents/storage/factory.py`
- It returns 6 values but callers in `runtime/executor.py` unpack only 5 or 6
- Fix the unpacking to match the actual return value
- This will unblock: storage persistence, memory persistence, and 26 failing tests

**Tool execution (BF-002)** is the most impactful feature fix:
- Location: `src/configurable_agents/llm/provider.py:216-236`
- Currently: `llm.bind_tools(tools)` then immediately `llm.with_structured_output()`
- Need: agent loop that detects tool calls, executes tools, feeds results back
- Reference: LangChain's `AgentExecutor` or manual tool call loop pattern

## Relevant Quick Links

- **Test findings**: docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_TEST_FINDINGS.md
- **Fork-join impl log**: docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_fork_join_parallel.md
- **Test configs**: test_configs/README.md
- Documentation Index: docs/README.md
- Architecture: docs/development/ARCHITECTURE.md
- ADRs: docs/development/adr/

---

*Last Updated: 2026-02-08 | CL-003 Fork-join parallel fix complete, remaining bugs documented*
