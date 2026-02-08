# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

For detailed task-by-task implementation notes, see [implementation logs](docs/development/implementation_logs/).

---

## [Unreleased]

### WARNING: PROJECT STATE IS BROKEN

After introducing an autonomous agent system post-v1.0, the codebase and documentation
became inconsistent and out of sync. Cleanup tasks are in progress to restore
the project to a verifiable state.

### Fixed

**BF-001: Fix storage backend tuple unpacking** (2026-02-08)
- Fixed `create_storage_backend()` callers that unpacked wrong number of values (function returns 8, callers expected 3-6)
- Fixed 8 call sites across 5 files: `runtime/executor.py`, `cli.py` (×2), `tests/registry/test_ttl_expiry.py`, `tests/registry/test_server.py`, `tests/runtime/test_executor_storage.py` (×3)
- Resolves `too many values to unpack (expected 6)` crash on every workflow run with storage enabled
- Verified with test configs 09 and 12 (end-to-end execution) and 47 previously-failing unit tests now pass

**BF-002: Implement tool execution agent loop** (2026-02-08)
- Added `_execute_tool_loop()` in `provider.py` — manual agent loop: invoke LLM → detect tool calls → execute tools → feed results back → repeat
- Changed `call_llm_structured()` to two-phase approach: Phase 1 runs tool loop (enriches prompt with tool results), Phase 2 extracts structured output
- Previously tools were bound via `bind_tools()` but `with_structured_output()` was applied immediately, causing the LLM to skip tool calls entirely
- Updated `test_call_with_tools` mock setup to match new two-phase flow
- Verified: config 12 `web_search` tool now returns real search results instead of echoing the query
- Confirmed BF-003 (memory persistence) is a separate issue — storage initializes but memory load/save not wired into prompts

**BF-003: Fix memory persistence across runs** (2026-02-08)
- Fixed scope-aware namespace construction: agent scope now uses wildcard `*:*` for workflow/node instead of per-run UUIDs, enabling cross-run memory persistence
- Fixed `AgentMemory` truthiness bug: `if agent_memory:` evaluated to False due to `__len__` returning 0 on empty memory, skipping all memory read/write code — changed to `if agent_memory is not None:`
- Added `memory` field to `GlobalConfig` schema so `config.memory:` in YAML is actually parsed
- Added auto-extraction of facts from LLM responses via lightweight extraction call
- Added `max_entries` limit on memory injection into prompts to prevent context bloat
- Fixed config 09 field names to match schema (`default_scope` instead of `scope`)
- Verified end-to-end: Run 1 stores "name=Alice", Run 2 recalls "Your name is Alice"

### Added

**CL-002: Documentation Index and Dead Link Cleanup** (In Progress - 2026-02-06)
- Created `docs/README.md` as comprehensive documentation index
- Updated all references to non-existent `.planning/` directory
- Updated doc paths to correct locations (docs/development/adr/, etc.)
- Updated CHANGELOG.md to remove dead references
- Updated README.md with documentation index link
- Updated CLAUDE.md with documentation structure information
- Updated docs/development/TASKS.md to remove dead references

**CL-001: Documentation Reorganization** ✅ (2026-02-06)
- Created `docs/user/` for user-facing documentation
- Moved internal docs to `docs/development/` (PROJECT_VISION, ARCHITECTURE, SPEC)
- Created `docs/development/session_context/` for archived contexts
- Updated CLAUDE.md with permanent project instructions
- Rewrote CONTEXT.md with streamlined structure
- Updated README.md with new doc paths
- Created implementation log for CL-001

### Changed
- Documentation reorganized into `docs/user/` and `docs/development/`
- All doc paths updated to reflect new structure

### Removed
- `.planning/` directory references (directory no longer exists)
- Various documentation files from autonomous agent cleanup

---

## [1.0.0] - 2026-02-04

### 🎉 Major Release: Production-Ready Multi-Agent Orchestration Platform

**v1.0 Foundation** - 4 phases, 19 plans, 27 requirements, 1,000+ tests (98%+ pass rate)

Transformed from a simple linear workflow runner (v0.1) into a full-featured local-first agent orchestration platform with multi-LLM support, advanced control flow, complete observability, and zero cloud lock-in.

---

**NOTE**: Full v1.0 details exist but project state is currently broken due to post-v1.0
autonomous agent issues. Cleanup is in progress to restore verifiable state.

---

## Version Planning

### [1.1.0] - TBD (Planning Deferred)

**Focus**: Cleanup and verification of current state before planning new features.

---

## Notes

### About This Changelog

This changelog follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format:
- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes

### Versioning

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for added functionality (backwards-compatible)
- **PATCH** version for backwards-compatible bug fixes

Current version: **1.0.0** (production release, but state verification needed)

---

*For the latest project state, see [CONTEXT.md](CONTEXT.md)*
*For development progress, see [docs/development/TASKS.md](docs/development/TASKS.md)*
*For documentation index, see [docs/README.md](docs/README.md)*
