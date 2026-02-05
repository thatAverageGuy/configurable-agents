# Phase 8 Context: Dashboard UI Testing & Fixes

**Created:** 2026-02-05
**Phase:** 8 of 11 - Dashboard UI Testing & Fixes
**Goal:** All Dashboard pages load and function correctly

## Decisions Made

### 1. MLFlow Integration Strategy

**Integration Approach:**
- CLI flag: `--mlflow` → Start local MLFlow server + embed in Dashboard
- CLI flag: `--mlflow-uri <uri>` → Use external MLFlow at URI
- No flag → Skip MLFlow entirely
- Startup flow: `configurable-agents ui --mlflow` starts both Dashboard and MLFlow together

**Backend Configuration:**
- Use MLFlow 2.x default (SQLite backend)
- No custom backend flags needed
- Production users point to Databricks/managed MLFlow

**Unavailable Behavior:**
- Graceful degradation if MLFlow not installed but flag provided
- Dashboard still starts, shows helpful message
- Rest of UI works normally

**404 Behavior:**
- Friendly HTML 404 page when /mlflow accessed but not mounted
- Clear message: "MLFlow not configured"
- Navigation still works

---

### 2. Jinja2 Template Architecture

**Shared Macros:**
- Create `templates/macros.html` with common reusable macros
- Include: status badges, tables, date formatting, relative time strings
- All templates import from macros.html

**Helper Functions:**
- Use global context processor (best practice)
- Register in `app.py` via `templates.TemplateResponse` context
- Add `_format_duration`, `_format_cost`, `_time_ago`, `_parse_capabilities`, etc.
- No template-level imports needed

**Template Organization:**
- Keep flat structure: `templates/` (no nested folders)
- Shared: `macros.html`, `base.html`
- Partials: `*_table.html` for HTMX refresh
- Pages: `workflows.html`, `agents.html`, etc.

**HTMX Partials:**
- Keep current pattern: `workflows_table.html`, `agents_table.html`
- Main page includes partial via HTMX
- Don't over-engineer yet (can refactor later if needed)

---

### 3. Testing Approach for UI

**Test Strategy:**
- Browser-based E2E with Playwright
- Most realistic, catches actual browser issues
- Tests real user interactions, not just HTTP responses

**Test Data:**
- In-memory SQLite (`:memory:`)
- Fast, isolated, clean slate for each test
- Seed with fixtures: workflows, agents, runs

**Test Scope:**
- Comprehensive coverage
- Every page loads without errors
- Every button/link works
- Every HTMX interaction works
- Empty states render correctly
- Error pages display correctly

**CI Integration:**
- Mark browser tests with `@pytest.mark.slow`
- Exclude from default CI run: `pytest -m "not slow"`
- Run manually before releases: `pytest -m "slow"`

---

### 4. Error Handling Philosophy

**Template Rendering Errors:**
- Friendly error page with template name
- Stack trace only in debug mode
- Rest of dashboard still accessible

**Repository Errors (database unavailable):**
- Empty state with guidance
- "No workflows found" + "Try running a workflow"
- Better UX than error banners

**Async Route Errors:**
- Custom exception handler middleware
- Consistent error handling across all routes
- Log errors, return friendly error page

**MLFlow Errors (Optimization page):**
- Graceful degradation
- Show "MLFlow unavailable" message
- Disable MLFlow-dependent features
- Rest of optimization page still works

---

## Known Bugs to Fix

From `.planning/UI_BUG_REPORT.md`:

1. ✅ **CLI run command** - Fixed (Quick-009)
2. ❌ **Chat UI history** - Multi-turn conversations broken (Phase 9)
3. ❌ **Chat UI download/validate** - Same history issue (Phase 9)
4. ❌ **Dashboard Workflows page** - Missing macros.html (Phase 8)
5. ❌ **Dashboard Agents page** - Jinja2 underscore import (Phase 8)
6. ❌ **Dashboard MLFlow page** - 404 error (Phase 8)
7. ❌ **Dashboard Optimization page** - MLFlow filesystem errors (Phase 8)

---

## Technical Context

**Dashboard Stack:**
- FastAPI + Jinja2Templates
- HTMX for dynamic updates
- MLFlow WSGI middleware (when mounted)
- SQLite backend (workflow runs, agent registry)

**Template Files:**
- `base.html` - Main layout
- `dashboard.html` - Home page
- `workflows.html` - Workflows list page
- `workflows_table.html` - HTMX partial
- `workflow_detail.html` - Single workflow view
- `agents.html` - Agents list page
- `agents_table.html` - HTMX partial (broken: underscore import)
- `experiments.html` - Experiments page
- `optimization.html` - Optimization page (MLFlow errors)
- `orchestrator.html` - Orchestrator view

**Route Files:**
- `routes/workflows.py` - Helper functions (exported in `__all__`)
- `routes/agents.py` - Helper functions (underscore-prefixed, broken)
- `routes/metrics.py` - Metrics endpoints
- `routes/optimization.py` - Optimization endpoints
- `routes/status.py` - Status panel SSE
- `routes/orchestrator.py` - Orchestrator view

---

## Implementation Notes

**Plan 08-01: Fix Workflows Page Template Errors**
- Create `templates/macros.html` with common macros
- Add status badge macro, duration formatting, cost formatting
- Update `workflows_table.html` to use macros

**Plan 08-02: Fix Agents Page Jinja2 Import Errors**
- Rename `_time_ago`, `_format_capabilities` to `time_ago`, `format_capabilities`
- Add global context processor in `app.py`
- Remove template-level imports from `agents_table.html`

**Plan 08-03: Fix MLFlow Page 404**
- Add friendly 404 page for `/mlflow` when not mounted
- Check if MLFlow is mounted before returning 404
- Show helpful message with next steps

**Plan 08-04: Fix Optimization Page Filesystem Errors**
- Add error handling for MLFlow backend failures
- Show graceful degradation message
- Disable MLFlow-dependent features when unavailable

**Plan 08-05: Test All Dashboard Pages**
- Create Playwright-based E2E tests
- Test every page load, button, HTMX interaction
- Use in-memory SQLite with fixtures
- Mark as `@pytest.mark.slow`

**Plan 08-06: Add Dashboard Integration Tests**
- Add smoke tests for all routes
- Add template rendering tests
- Add error handling tests
- Ensure comprehensive coverage

---

## Next Steps

1. ✅ Discussion complete
2. ⏭️ Run `/gsd:plan-phase 8` to create detailed execution plans
3. ⏭️ Execute plans with `/gsd:execute-phase 8`

---

*Context captured: 2026-02-05*
*All decisions approved by user*
