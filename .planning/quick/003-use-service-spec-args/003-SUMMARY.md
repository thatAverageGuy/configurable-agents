---
phase: quick
plan: 003
subsystem: windows-multiprocessing
tags: [pickle, functools.partial, multiprocessing, ServiceSpec]

# Dependency graph
requires:
  - phase: quick-002
    provides: functools.partial fix (superseded by this approach)
provides:
  - Pickle-safe service configuration using ServiceSpec args
affects: [all-service-management]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level config wrapper functions for multiprocessing pickle safety"

key-files:
  created: []
  modified:
    - src/configurable_agents/cli.py

key-decisions:
  - "Use ServiceSpec args field instead of functools.partial for Windows multiprocessing"

patterns-established:
  - "Pattern: Config dict unpacking via wrapper function avoids partial/weakref pickle issues"

# Metrics
duration: 3min
completed: 2026-02-05
---

# Quick Task 003: Use ServiceSpec Args Summary

**Replaced functools.partial with ServiceSpec args to fix Windows multiprocessing pickle errors**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-05T00:45:00Z
- **Completed:** 2026-02-05T00:48:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Removed `functools.partial` import (contains unpickleable weakrefs)
- Added `_run_dashboard_with_config` wrapper function for dashboard service
- Added `_run_chat_with_config` wrapper function for chat service
- Replaced partial() calls with simple module-level targets and args dict
- Updated docstrings to reference wrapper functions

## Task Commits

1. **Task 1: Replace functools.partial with ServiceSpec.args** - `30d8d84` (fix)

## Files Created/Modified

- `src/configurable_agents/cli.py` - Replaced partial-based service targeting with config dict args

## Decisions Made

- **Use ServiceSpec args field instead of functools.partial**: ServiceSpec already has args/kwargs fields designed for passing parameters to targets. Using config dicts with wrapper functions is more pickleable than functools.partial objects which contain weakrefs.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Windows multiprocessing now fully pickle-safe for cmd_ui command
- Dashboard and Chat UI services launch correctly via ProcessManager

---
*Phase: quick-003*
*Completed: 2026-02-05*
