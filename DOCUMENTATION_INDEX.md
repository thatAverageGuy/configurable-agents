# Documentation Index and Migration Guide

**Created**: 2026-02-06
**Purpose**: Navigation guide for finding information across restructured documentation
**Scope**: Complete documentation inventory with cross-references

---

## Quick Reference

### What to Use For...

**Task History**: `tasks_old.md` - Complete task history (T-001 to T-058)
**Changelog**: `changelog_old.md` (v0.1) + `CHANGELOG.md` (v1.0+)
**Requirements**: `docs/TASKS.md` (v1.0 requirements format)
**Planning**: `.planning/` directory (phase plans, milestones)
**Architecture**: `docs/ARCHITECTURE.md` + ADRs
**Implementation**: `docs/implementation_logs/v0.1/` (detailed logs)

---

## Document Categories

### 📋 Active Documents (Current Format)

| Document | Purpose | Version Era | Status |
|----------|---------|-------------|--------|
| `docs/TASKS.md` | Requirements tracking (RT-XX, ARCH-XX, etc.) | v1.0+ | Active |
| `CHANGELOG.md` | Current changelog (v1.0+) | v1.0+ | Active |
| `docs/ARCHITECTURE.md` | Architecture overview | v1.0+ | Active |
| `docs/SPEC.md` | Technical specification | v0.1+ | Active |
| `README.md` | Main project README | v1.0+ | Active |
| `.planning/` | Current planning system | v1.0+ | Active |

### 📚 Archived Documents (Historical Reference)

| Document | Purpose | Version Era | Status |
|----------|---------|-------------|--------|
| `tasks_old.md` | ⭐ COMPLETE TASK HISTORY (v0.1 → present) | v0.1-v1.2 | Archived ⭐ PRIMARY SOURCE |
| `changelog_old.md` | v0.1 historical changelog | v0.1 | Archived |
| `docs/implementation_logs/v0.1/` | v0.1 detailed implementation logs | v0.1 | Archived |

---

## Version Timeline

### v0.1 (2026-01-24 to 2026-02-02)
**Tasks**: T-001 to T-024, T-025 (was T-028)
**Docs**:
- `tasks_old.md` sections "Phase 1-4 (v0.1)"
- `changelog_old.md`
- `docs/implementation_logs/v0.1/`

**Characteristics**:
- Individual git commits per task
- 25 tasks completed
- 645 tests passing
- Linear workflows only
- Google Gemini provider
- MLFlow 2.9 → 3.9 migration

---

### v1.0 (2026-02-03 to 2026-02-04)
**Tasks**: T-026 to T-044
**Plans**: Phase 1-4 (01-01 through 04-03)
**Requirements**: 27 requirements (RT-XX, OBS-XX, UI-XX, ARCH-XX, INT-XX)

**Docs**:
- `tasks_old.md` sections "Phase 1-4 (v1.0)"
- `docs/TASKS.md` (requirements format)
- `.planning/phases/01-core-engine/` through `04-advanced-capabilities/`
- `CHANGELOG.md` [1.0.0] section

**Key Features**:
- Multi-LLM support (OpenAI, Anthropic, Google, Ollama)
- Advanced control flow (conditional, loops, parallel)
- Agent registry with heartbeat/TTL
- Gradio Chat UI
- HTMX Dashboard
- Webhook integrations
- Sandbox code execution
- Memory backend
- 15 pre-built tools
- MLFlow optimization

---

### v1.1 (2026-02-04 to 2026-02-05)
**Tasks**: T-045 to T-047
**Plans**: Phase 5 (05-01 through 05-03)
**Requirements**: 11 requirements (Startup, Onboarding, Navigation, Observability, Error Handling)

**Docs**:
- `tasks_old.md` sections "Phase 5 (v1.1)"
- `.planning/phases/05-foundation-reliability/`
- `CHANGELOG.md` (minor entries)

**Key Features**:
- Single-command startup (`configurable-agents ui`)
- Database auto-initialization
- Status dashboard with HTMX polling
- Error formatter with resolution steps

---

### v1.2 (2026-02-05 to Present)
**Tasks**: T-048 to T-058 (in-progress)
**Plans**: Phase 7-8 (07-01 through 08-06), Phase 9-11 planned
**Requirements**: 27 requirements (CLI, Dashboard, Chat UI, Execution, Integration)

**Docs**:
- `tasks_old.md` sections "Phase 7-8 (v1.2)"
- `.planning/phases/07-cli-testing-and-fixes/`
- `.planning/phases/08-dashboard-ui-testing-and-fixes/`

**Key Features**:
- CLI integration testing
- Dashboard UI testing
- Bug fixes (HTMX, MLFlow, optimization page)
- E2E testing
- Template macros and global helpers

---

## Numbering Cross-Reference

### Task Numbers (T-XXX)
- **v0.1**: T-001 to T-025 (includes T-028 renumbered)
- **v1.0**: T-026 to T-044
- **v1.1**: T-045 to T-047
- **v1.2**: T-048 to T-058 (in-progress)

**See**: `task_numbering_map.md` for complete bidirectional mapping

### Phase-Plan Numbers
- **Phase 1**: 01-01, 01-02, 01-03, 01-04 → T-026 to T-029
- **Phase 2**: 02-01A, 02-01B, 02-01C, 02-02A, 02-02B, 02-02C → T-030 to T-035
- **Phase 3**: 03-01, 03-02, 03-03, 03-03B, 03-04, 03-05 → T-036 to T-041
- **Phase 4**: 04-01, 04-02, 04-03 → T-042 to T-044
- **Phase 5**: 05-01, 05-02, 05-03 → T-045 to T-047
- **Phase 7**: 07-01, 07-02, 07-03, 07-04, 07-05 → T-048 to T-052
- **Phase 8**: 08-01, 08-02, 08-03, 08-04, 08-05, 08-06 → T-053 to T-058

### Requirement IDs
- **RT-XX**: Runtime requirements (RT-01 through RT-08)
- **OBS-XX**: Observability requirements (OBS-01 through OBS-04)
- **UI-XX**: UI requirements (UI-01 through UI-06)
- **ARCH-XX**: Architecture requirements (ARCH-01 through ARCH-06)
- **INT-XX**: Integration requirements (INT-01 through INT-03)

**See**: `docs/TASKS.md` for requirement details

### ADR Numbers
- ADR-001 through ADR-025 (25 architecture decision records)
- See `docs/adr/` directory

---

## File Migration Paths

### Task Documentation

**Original Location**: `docs/TASKS.md` (v0.1 format, detailed task logs)
**Current Location**: `docs/TASKS.md` (v1.0 requirements format)
**Historical Archive**: `tasks_old.md` (complete history, v0.1 through v1.2)

**Usage**:
- For **task-by-task details**: Use `tasks_old.md`
- For **requirement tracking**: Use `docs/TASKS.md`
- For **implementation details**: Use `docs/implementation_logs/v0.1/`

### Changelog

**Original Location**: `CHANGELOG.md` (contained v0.1 section)
**Current Location**: `CHANGELOG.md` (v1.0+ only)
**Historical Archive**: `changelog_old.md` (v0.1 complete history)

**Usage**:
- For **v0.1 changes**: Use `changelog_old.md`
- For **v1.0+ changes**: Use `CHANGELOG.md`

---

## How to Find Information

### "I want to know what Task T-XXX did..."
1. Look up T-XXX in `tasks_old.md`
2. Find the task section with detailed description, files, tests, decisions
3. Check implementation log: `docs/implementation_logs/v0.1/phase_X/T-XXX_*.md` (if v0.1)

### "I want to know when feature RT-XX was implemented..."
1. Look up RT-XX in `task_numbering_map.md` to find T-number
2. Look up T-number in `tasks_old.md` for implementation details
3. Check `docs/TASKS.md` for requirement status

### "I want to understand the architecture..."
1. Read `docs/ARCHITECTURE.md` (current overview)
2. Read relevant ADRs in `docs/adr/` (immutable decisions)
3. Check `docs/implementation_logs/v0.1/` for historical decisions

### "I want to see what changed in version X..."
1. For v0.1: Read `changelog_old.md`
2. For v1.0+: Read `CHANGELOG.md` [1.0.0] section
3. For detailed breakdown: Read relevant sections in `tasks_old.md`

### "I want to know what Phase X did..."
1. Find Phase X in `tasks_old.md` (v1.0+ phases are documented)
2. Read the Phase summary at the beginning of the section
3. See individual tasks (T-numbers) for that phase

### "I want to understand the current planning..."
1. Read `.planning/ROADMAP.md` (current roadmap)
2. Read `.planning/STATE.md` (current state)
3. Check phase plans in `.planning/phases/`

---

## Directory Structure

```
configurable-agents/
├── tasks_old.md                  ⭐ COMPLETE TASK HISTORY (PRIMARY SOURCE)
├── changelog_old.md              ⭐ v0.1 CHANGELOG
├── CHANGELOG.md                  (v1.0+ changelog)
├── task_numbering_map.md         (T-XXX ↔ Phase-Plan mapping)
├── commit_mapping.md             (git commit history)
├── DISCREPANCIES.md              (verification findings)
│
├── docs/
│   ├── TASKS.md                  (v1.0 requirements format)
│   ├── ARCHITECTURE.md          (architecture overview)
│   ├── SPEC.md                  (technical specification)
│   ├── PROJECT_VISION.md        (project vision)
│   ├── adr/                     (25 ADRs)
│   └── implementation_logs/
│       └── v0.1/                 (26 detailed implementation logs)
│
└── .planning/
    ├── ROADMAP.md                (current roadmap)
    ├── STATE.md                  (current state)
    ├── MILESTONES.md             (milestone overview)
    └── phases/                  (phase plans and summaries)
        ├── 01-core-engine/      (4 plans)
        ├── 02-agent-infrastructure/ (6 plans)
        ├── 03-interfaces-and-triggers/ (6 plans)
        ├── 04-advanced-capabilities/ (3 plans)
        ├── 05-foundation-reliability/ (3 plans)
        ├── 07-cli-testing-and-fixes/ (5 plans)
        └── 08-dashboard-ui-testing-and-fixes/ (6 plans)
```

---

## Legacy vs Current Formats

### Task Documentation

**Legacy Format** (v0.1, in tasks_old.md):
```markdown
### T-XXX: Task Title
**Status**: DONE
**Priority**: P0
**Dependencies**: T-YY
**Completed**: YYYY-MM-DD
**Actual Effort**: X days

**Description**: ...
**Acceptance Criteria**: ...
**Files Created**: ...
**Files Modified**: ...
**Tests**: ...
**Key Decisions**: ...
```

**Current Format** (v1.0, in docs/TASKS.md):
```markdown
## v1.0 Requirements Status
**RT-XX**: Description
**Status**: Complete
```

**Planning Format** (v1.0+, in .planning/phases/*/):
- PLAN.md (planning)
- SUMMARY.md (completion summary)
- RESEARCH.md (research)
- VERIFICATION.md (verification)

---

## Restoration Summary

### Files Created During Restoration
1. ✅ `md_inventory.json` - File inventory
2. ✅ `commit_mapping.md` - Git commit history mapping
3. ✅ `task_numbering_map.md` - T-XXX ↔ Phase-Plan bidirectional mapping
4. ✅ `changelog_old.md` - v0.1 historical changelog
5. ✅ `DISCREPANCIES.md` - Verification findings

### Files Enhanced During Restoration
1. ✅ `tasks_old.md` - Enhanced with v1.0+ tasks (T-001 through T-058)
2. ✅ Renumbered T-028 → T-025 (skipped cancelled tasks)

### Files NOT Modified (as requested)
- ❌ `docs/TASKS.md` - Left unchanged (requirements format)
- ❌ `CHANGELOG.md` - Left unchanged (v1.0+ format)

---

## Next Steps

After reviewing this document:

1. **For historical research**: Use `tasks_old.md` as primary source
2. **For requirement tracking**: Use `docs/TASKS.md`
3. **For planning**: Use `.planning/` directory
4. **For verification**: See `DISCREPANCIES.md`

---

**Document Status**: ✅ COMPLETE
**Last Updated**: 2026-02-06
**Maintainer**: Project Documentation

*This index serves as the navigation guide for all documentation across the restructuring from v0.1 through v1.2*
