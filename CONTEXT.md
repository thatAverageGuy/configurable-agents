# CONTEXT.md

> **Purpose**: Quick context for resuming development. Updated after each task completion.
>
> **For LLMs**: Read this first to understand current state, next action, and project standards.
> Fetch details from linked docs as needed during implementation.

---

**Last Updated**: 2026-02-09

---

## Current State

**Task**: CL-003 (Cleanup, Testing, Verification) | **Phase**: CLI Deep Verification | **Status**: IN_PROGRESS

### What Was Done This Session

**CLI Command Discovery & Verification** ✅
- Discovered all 20 CLI commands across 6 categories from `cli.py` (~2975 lines)
- Created `docs/user/cli_guide.md` — comprehensive reference with all flags, defaults, examples
- Manually tested all commands — basic functionality verified for all 20

**BF-007: Fixed webhooks command** ✅
- Wrong router import in `cli.py:1998` — imported module instead of `APIRouter` instance
- Fix: `from configurable_agents.webhooks.router import router as webhook_router`

**BF-008: Fixed Docker deploy (two sub-issues)** ✅
- BF-008a: Invalid `pyproject.toml` scripts (`docs:build` etc.) broke Docker build — rewrote `_copy_pyproject_toml()` to filter invalid entries
- BF-008b: Container port mismatch — hardcoded internal port to 8000, fixed compose port mappings
- Full Docker deploy verified: build → run → health → /docs → /schema → /run all work

**Test fixes**: Updated port assertions in `test_generator_integration.py` and `test_server_template.py`

### All Bug Fixes Complete (BF-001 through BF-008)

### Next Steps — Deep Flag-by-Flag CLI Verification Plan

#### `run` command — 3 flags to verify:
1. [ ] `--input key=value` — Does the value actually reach the agent prompt? Run with `--input topic="AI Safety"` and confirm the LLM output references AI Safety
2. [ ] `--verbose` — Does it actually switch to DEBUG logging? Compare output with/without
3. [ ] `--enable-profiling` — Does it actually create MLFlow profiling metrics? Run with flag, then check `profile-report`

#### `deploy` command — key flags:
4. [ ] `--api-port` / `--mlflow-port` — Do custom ports actually get used in the container?
5. [ ] `--no-mlflow` — Does the container actually skip MLFlow?
6. [ ] `--timeout` — Does the sync timeout value propagate to server.py?
7. [ ] `--name` — Does the container get the custom name?

#### Observability — data flow:
8. [ ] Run a workflow with profiling → do `cost-report`, `profile-report`, `observability status` show the actual data?
9. [ ] Do `--experiment`, `--period`, `--breakdown` filters actually filter?

### Known Issues (Not Blocking)
- UI tests: `test_dashboard.py` has `_time_ago` import error (pre-existing, UI skipped for now)
- Docker sandbox tests: some failures in `test_docker_executor.py` (pre-existing)
- Minor: CLI prints `/execute` endpoint but actual endpoint is `/run`

### Blockers
- None

---

## Pending Work

| Task | Summary | Details |
|------|---------|---------|
| CL-003 | Deep CLI flag verification | This file → Next Steps section |

## Relevant Quick Links

- **CLI Guide**: docs/user/cli_guide.md
- **All BF impl logs**: docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_bug_fix_BF*.md
- **Test findings**: docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_TEST_FINDINGS.md
- **Test configs**: test_configs/README.md
- Documentation Index: docs/README.md
- Architecture: docs/development/ARCHITECTURE.md

---

*Last Updated: 2026-02-09 | BF-001 through BF-008 all fixed. CLI guide created. Next: deep flag-by-flag verification.*
