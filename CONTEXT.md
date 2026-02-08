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

**BF-001: Fixed storage backend tuple unpacking** ✅
- `create_storage_backend()` returns 8 values but callers unpacked 3-6
- Fixed 8 call sites across 5 files (executor.py, cli.py ×2, 3 test files)
- Verified: 47 previously-failing tests now pass, configs 09 and 12 run end-to-end

**BF-002: Implemented tool execution agent loop** ✅
- Added `_execute_tool_loop()` in `provider.py` — two-phase approach replaces broken one-shot tool binding
- Config 12 `web_search` now returns real results instead of echoing the query

**BF-003: Fixed memory persistence across runs** ✅
- **Root cause 1**: Namespace ignored scope — `AgentMemory` was created with per-run UUID and node_id regardless of scope, making agent-scoped memory unique per run
- **Root cause 2**: `AgentMemory.__len__` returns 0 on empty memory, so `if agent_memory:` was False on first run (no writes ever happened)
- **Root cause 3**: `GlobalConfig` lacked `memory` field — `config.memory:` in YAML was silently ignored
- Fixed: scope-aware namespace construction, `is not None` checks, GlobalConfig field, config 09 field names
- Added: auto-extraction of facts from responses, `max_entries` limit on prompt injection
- Verified: Run 1 stores `name=Alice`, Run 2 recalls "Your name is Alice"

### What Works Now
- Basic linear workflows (01, 02, 03)
- Multi-LLM support via LiteLLM (08)
- Code sandbox execution via RestrictedPython (10)
- MLFlow observability (02) — tracking works, cost summary broken (R-003)
- Conditional branching (05) — FIXED prior session
- Loop iteration (06) — FIXED prior session
- Fork-join parallel execution (07) — FIXED prior session
- Full-featured workflow (12) — FIXED prior session
- **Memory persistence (09)** — FIXED this session

### What's Still Broken

| ID | Issue | Priority | Root Cause |
|----|-------|----------|------------|
| R-003 | MLFlow cost summary — `invalid literal for int()` parsing `'mlflow-experiment:1'` | MEDIUM | Experiment ID parsing bug in cost reporter |
| R-004 | ChatLiteLLM deprecated — LangChain 0.3.24 deprecation warning | LOW | Need to migrate to `langchain-litellm` package |

### Pre-existing Test Failures (NOT caused by our changes)

| Area | Count | Root Cause |
|------|-------|------------|
| `test_node_executor.py` + `test_node_executor_metrics.py` | 3-7 failures | Tests access `.research`/`.summary` on dict (execute_node returns dict, tests expect Pydantic) |
| `test_generator.py` + `test_generator_integration.py` | 5 failures | Deploy generator creates 10 artifacts, tests expect 8 |
| `test_integration.py` (sandbox) | 10 failures | Same dict-vs-Pydantic issue as node_executor |

### Next Steps (Recommended Priority Order)
1. [x] **BF-001: Fix storage backend** — ✅ Fixed tuple unpacking (8 call sites, 5 files)
2. [x] **BF-002: Fix tool execution** — ✅ Two-phase agent loop in `provider.py`
3. [x] **BF-003: Fix memory persistence** — ✅ Scope-aware namespaces, truthiness fix, GlobalConfig field, auto-extraction
4. [ ] **BF-004: Fix MLFlow cost summary** — Fix experiment ID parsing (R-003).
5. [ ] **BF-005: Fix pre-existing test failures** — Update tests to expect dict returns from `execute_node`, fix deploy artifact count.
6. [ ] **BF-006: Migrate ChatLiteLLM** — Update to `langchain-litellm` package (R-004).

### Blockers
- None currently

---

## Pending Work

| Task | Summary | Details |
|------|---------|---------|
| CL-003 | Codebase cleanup, testing, and verification | docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_TEST_FINDINGS.md |
| BF-004 | Fix MLFlow cost summary parsing | Experiment ID parsing bug in cost reporter |
| BF-005 | Fix pre-existing test failures | dict-vs-Pydantic, deploy artifact count |
| BF-006 | Migrate ChatLiteLLM | `langchain-litellm` package migration |

## Relevant Quick Links

- **Bug fix impl log**: docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_bug_fixes_BF001_BF002_BF003.md
- **Test findings**: docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_TEST_FINDINGS.md
- **Fork-join impl log**: docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_fork_join_parallel.md
- **Test configs**: test_configs/README.md
- Documentation Index: docs/README.md
- Architecture: docs/development/ARCHITECTURE.md
- ADRs: docs/development/adr/

---

*Last Updated: 2026-02-08 | BF-001, BF-002, BF-003 all fixed. Remaining: BF-004 (MLFlow), BF-005 (tests), BF-006 (LiteLLM migration)*
