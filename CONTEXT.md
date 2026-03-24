# CONTEXT.md

> **Purpose**: Quick context for resuming development. Updated after each task completion.
>
> **For LLMs**: Read this first to understand current state, next action, and project standards.
> Fetch details from linked docs as needed during implementation.

---

**Last Updated**: 2026-03-24

---

## Current State

**Task**: BF-011 | **Phase**: Not Started | **Status**: READY TO IMPLEMENT

### What Was Done This Session

**2026-03-24 — BF-010 implemented:**
- Fixed loop `max_iterations` guard (was always 0 due to Pydantic dropping unknown fields)
- Added `extra_fields` param to `build_state_model()`; added `get_loop_counter_fields()` helper
- Updated key prefix `_loop_iteration_` → `__loop_counter_` in control_flow + updated tests
- Tests written but not executed — `litellm` PyPI package quarantined (supply chain compromise), dev environment cannot be set up until dependency is resolved

### Next Steps

1. [x] **BF-010**: Fix loop `max_iterations` — DONE
2. [ ] **BF-011**: Fix list field reducer — add `replace` semantics — HIGH
3. [ ] **T-014**: Runtime memory override (`--memory-scope` CLI flag) — HIGH
4. [ ] **T-015**: Memory extraction opt-in (`extract_facts: false` default) — HIGH
5. [ ] **BF-012**: Fix double CostEstimator call — MEDIUM
6. [ ] **BF-013**: Fix silent route condition failure logging — MEDIUM
7. [ ] **T-016**: Web search hardening (retry, fallback, cache) — MEDIUM
8. [ ] Dashboard scope definition + tasks (separate session)

### Blockers
- None. All planning docs complete. Ready to start BF-010.

---

## Pending Work

| Task | Summary | Details |
|------|---------|---------|
| BF-010 | Fix loop max_iterations — counter never persists | [BF-010 Log](docs/development/implementation_logs/phase_6_v1_1_hardening/BF-010_loop_max_iterations.md) |
| BF-011 | Fix list reducer — loops accumulate stale data | [BF-011 Log](docs/development/implementation_logs/phase_6_v1_1_hardening/BF-011_list_reducer.md) |
| BF-012 | Fix double CostEstimator call per node | [BF-012 Log](docs/development/implementation_logs/phase_6_v1_1_hardening/BF-012_cost_estimator_double_call.md) |
| BF-013 | Fix silent route condition failure | [BF-013 Log](docs/development/implementation_logs/phase_6_v1_1_hardening/BF-013_silent_route_condition_logging.md) |
| T-014 | Runtime memory override per invocation | [T-014 Log](docs/development/implementation_logs/phase_6_v1_1_hardening/T-014_runtime_memory_override.md) |
| T-015 | Memory extraction opt-in | [T-015 Log](docs/development/implementation_logs/phase_6_v1_1_hardening/T-015_memory_extraction_opt_in.md) |
| T-016 | Web search hardening | [T-016 Log](docs/development/implementation_logs/phase_6_v1_1_hardening/T-016_web_search_hardening.md) |
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

*Last Updated: 2026-03-23 | v1.1 planning complete. All docs ready. Start with BF-010.*
