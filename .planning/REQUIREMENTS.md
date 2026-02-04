# Requirements: Configurable Agents v1.1 Core UX Polish

**Defined:** 2026-02-04
**Core Value:** Local-first, config-driven agent orchestration with full observability and zero cloud lock-in

## v1.1 Requirements

Requirements for Core UX Polish milestone. Each maps to roadmap phases.

### Startup & Initialization

- [ ] **STARTUP-01**: User can start entire UI with single command (`configurable-agents ui`)
- [ ] **STARTUP-02**: Platform auto-initializes databases and tables on first run (from ANY entry point)
- [ ] **STARTUP-03**: CLI commands work on first run without initialization errors
- [ ] **STARTUP-04**: Python API works on first run without initialization errors
- [ ] **STARTUP-05**: Startup shows progress feedback (spinners or X/Y progress for known steps)
- [ ] **STARTUP-06**: Platform gracefully shuts down with auto-save and session restoration on crash

### Onboarding

- [ ] **ONBOARD-01**: Empty states guide users to clear next actions ("Create workflow" or "Browse templates")

### Navigation

- [ ] **NAV-01**: User can open command palette via Cmd/Ctrl+K for fuzzy search over workflows, agents, templates
- [ ] **NAV-02**: User can filter navigation lists by typing (quick search in sidebars)

### Observability

- [ ] **OBS-01**: Dashboard shows status at a glance (active workflows, agent health, recent errors)

### Error Handling

- [ ] **ERR-01**: Error messages include error code, description, and resolution steps

## v1.2+ Requirements

Deferred to future release. Tracked but not in current roadmap.

### Workspace & Editor

- **WORK-01**: Unified config-to-runtime workspace (editor + execution + monitoring on one page)
- **WORK-02**: Template gallery with one-click apply
- **WORK-03**: Live config validation (inline errors as user types)
- **WORK-04**: Quick-run from any view (run button from dashboard, editor, templates)
- **WORK-05**: Integrated cost estimates (show projected token/cost before running)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Interactive tutorials | High value but complex; requires content creation effort |
| AI-assisted navigation | Nice-to-have feature; depends on search infrastructure |
| Workflow comparison/diff | Useful but not essential for MVP polish |
| Visual workflow builder | Violates config-first philosophy; code-based editing preferred |
| React/Vue-based UI | JavaScript frameworks violate Python-only constraint |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| STARTUP-01 | Phase 5 | Pending |
| STARTUP-02 | Phase 5 | Pending |
| STARTUP-03 | Phase 5 | Pending |
| STARTUP-04 | Phase 5 | Pending |
| STARTUP-05 | Phase 5 | Pending |
| STARTUP-06 | Phase 5 | Pending |
| ONBOARD-01 | Phase 6 | Pending |
| NAV-01 | Phase 6 | Pending |
| NAV-02 | Phase 6 | Pending |
| OBS-01 | Phase 5 | Pending |
| ERR-01 | Phase 5 | Pending |

**Coverage:**
- v1.1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-04*
*Last updated: 2026-02-04 after roadmap creation*
