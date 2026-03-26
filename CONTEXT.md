# CONTEXT.md

> **Purpose**: Quick context for resuming development. Updated after each task completion.
>
> **For LLMs**: Read this first to understand current state, next action, and project standards.
> Fetch details from linked docs as needed during implementation.

---

**Last Updated**: 2026-03-26

---

## Current State

**Task**: T-016 | **Phase**: Not Started | **Status**: READY TO START

### What Was Done This Session (2026-03-26)

**T-015 — Memory extraction opt-in**: DONE
- `extract_facts: bool = False` + `extraction_model: Optional[str]` added to `MemoryConfig`
- `_build_extraction_llm()` helper + extraction guard in `node_executor.py`
- 13 tests in `tests/core/test_memory_extraction_opt_in.py` — all pass

**BF-010 Pydantic 2.12 fix**: DONE
- `__loop_counter_{node_id}` → `lc_{node_id}` (Pydantic 2.12 rejects `__` prefixed fields)
- Fixed in `control_flow.py` + all 3 affected test files

**T-014 scope guard bug**: FIXED
- `_apply_runtime_overrides` no longer creates `MemoryConfig` on nodes with `memory=None` for `scope=workflow/agent`

**BF-012 mock path**: FIXED
- `test_node_executor_metrics.py` patch path corrected to `configurable_agents.core.node_executor.CostEstimator`

**MLflow API drift tests**: FIXED
- `test_cost_reporter.py`: rewrote 11 methods — `make_mock_run` → `make_mock_trace`, old runs API → traces API mocks
- `test_multi_provider_tracker.py`: fixed `test_generate_cost_report_success` — `client.get_experiment_by_name` + `mlflow.search_traces`

**Dependency pinning**: DONE
- All deps pinned to exact `==` versions from `uv.lock`; `litellm==1.80.0` (pre-compromise)

**Full test suite**: 1078 passed, 6 skipped

### Next Steps

1. [x] **BF-010**: Fix loop `max_iterations` — DONE
2. [x] **BF-011**: Fix list field reducer — DONE
3. [x] **BF-012**: Fix double CostEstimator call — DONE
4. [x] **BF-013**: Fix silent route condition logging — DONE
5. [x] **T-014**: Runtime memory override — DONE
6. [x] **T-015**: Memory extraction opt-in — DONE
7. [ ] **T-016**: Web search hardening (retry, fallback, cache) — MEDIUM
8. [ ] Dashboard scope definition (separate session)

### Blockers
- None

---

## Pending Work

| Task | Summary | Details |
|------|---------|---------|
| T-016 | Web search hardening (retry, fallback, cache) | [T-016 Log](docs/development/implementation_logs/phase_6_v1_1_hardening/T-016_web_search_hardening.md) |
| Dashboard | Scope TBD | Separate session |

## Session History
→ docs/development/session_context/ (archived sessions)

## Relevant Quick Links
- **Roadmap**: docs/development/ROADMAP.md
- **Phase 2 Vision**: docs/development/VISION_AUTONOMOUS.md
- **v1.1 Tasks**: docs/development/TASKS.md (top section)
- **Implementation logs**: docs/development/implementation_logs/phase_6_v1_1_hardening/
- **ADR-027** (runtime overrides): docs/development/adr/ADR-027-runtime-overrides-layer.md
- **ADR-028** (loop counter): docs/development/adr/ADR-028-loop-counter-state-injection.md
- **ADR-029** (list reducer): docs/development/adr/ADR-029-list-field-reducer-config.md
- Documentation index: docs/README.md
- Architecture: docs/development/ARCHITECTURE.md

---

*Last Updated: 2026-03-26 | BF-010 through T-015 complete. All v1.1 fixes landed. Next: T-016 web search hardening.*
