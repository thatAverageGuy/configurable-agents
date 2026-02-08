# CONTEXT.md

> **Purpose**: Quick context for resuming development. Updated after each task completion.
>
> **For LLMs**: Read this first to understand current state, next action, and project standards.
> Fetch details from linked docs as needed during implementation.

---

**Last Updated**: 2026-02-08

---

## Current State

**Task**: CL-003 (Bug Fixes) | **Phase**: Bug Fixing | **Status**: IN_PROGRESS

### What Was Done This Session

**BF-004: Fixed MLFlow cost summary and GenAI view integration** ✅
- Fixed `search_traces()` location format and return type
- Fixed model name attribution for Gemini spans (fallback chain)
- Fixed token key mismatch (`prompt_tokens` vs `input_tokens`)
- Rewrote `log_workflow_summary()` to use `log_feedback()` for GenAI view visibility
- Added `flush_trace_async_logging()` in executor to prevent race condition

**BF-005: Fixed pre-existing test failures** ✅
- Fixed 22 test failures across 5 test files (all 69 tests now pass)
- dict-vs-Pydantic: `execute_node()` returns partial dict, tests expected Pydantic model
- Deploy artifacts: generator produces 10 artifacts (was 8), fixed count + port + directory assertions

**MLflow mlruns → sqlite migration** ✅
- Changed default `tracking_uri` from `file://./mlruns` to `sqlite:///mlflow.db` (12 code/template files)
- Updated user-facing docs (OBSERVABILITY.md, DEPLOYMENT.md)

### Previous Session Fixes (already committed)

**BF-001**: Fixed storage backend tuple unpacking (8 call sites, 5 files) ✅
**BF-002**: Implemented tool execution agent loop (two-phase in `provider.py`) ✅
**BF-003**: Fixed memory persistence (scope-aware namespaces, truthiness, GlobalConfig) ✅

### What's Still Pending

| ID | Issue | Priority | Status |
|----|-------|----------|--------|
| BF-006 | ChatLiteLLM deprecation migration | LOW | TODO |

### Next Steps
1. [ ] **BF-006: Migrate ChatLiteLLM** — Update to `langchain-litellm` package (R-004)
2. [ ] Final test suite verification after all fixes

### Blockers
- None currently

---

## Pending Work

| Task | Summary | Details |
|------|---------|---------|
| CL-003 | Codebase cleanup, testing, and verification | docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_TEST_FINDINGS.md |
| BF-006 | Migrate ChatLiteLLM | `langchain-litellm` package migration |

## Relevant Quick Links

- **Bug fix impl log (BF-001/002/003)**: docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_bug_fixes_BF001_BF002_BF003.md
- **Bug fix impl log (BF-004)**: docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_bug_fix_BF004.md
- **Bug fix impl log (BF-005)**: docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_bug_fix_BF005.md
- **Test findings**: docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_TEST_FINDINGS.md
- **Test configs**: test_configs/README.md
- Documentation Index: docs/README.md
- Architecture: docs/development/ARCHITECTURE.md
- ADRs: docs/development/adr/

---

*Last Updated: 2026-02-08 | BF-001 through BF-005 fixed. MLflow defaults migrated to sqlite. Remaining: BF-006 (LiteLLM migration)*
