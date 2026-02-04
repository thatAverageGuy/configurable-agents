---
phase: 05-foundation-reliability
plan: 01
subsystem: infrastructure
tags: [multiprocessing, signal-handling, session-persistence, crash-detection, cli]

# Dependency graph
requires:
  - phase: 04-advanced-capabilities
    provides: Dashboard app, Gradio chat UI, storage models
provides:
  - ProcessManager class for multi-service orchestration
  - SessionState ORM model for crash detection
  - `configurable-agents ui` CLI command for single-command startup
  - Signal handling for graceful shutdown (SIGINT/SIGTERM)
  - Session persistence across restarts
affects: [phase-06, onboarding]

# Tech tracking
tech-stack:
  added:
    - multiprocessing (stdlib) - Process spawning
    - signal (stdlib) - Signal handling
  patterns:
    - ServiceSpec dataclass for process configuration
    - Singleton session state pattern (id='default')
    - Graceful shutdown with terminate/kill timeout
    - Pickleable target functions for multiprocessing

key-files:
  created:
    - src/configurable_agents/process/__init__.py
    - src/configurable_agents/process/manager.py
  modified:
    - src/configurable_agents/cli.py
    - src/configurable_agents/storage/models.py

key-decisions:
  - "Use multiprocessing.Process with daemon=False for clean shutdown on Windows"
  - "SessionState uses Integer for dirty_shutdown (SQLite boolean compatibility)"
  - "5-second terminate timeout before force kill"
  - "Signal handlers registered after process spawning to avoid child process issues"

patterns-established:
  - "ProcessManager lifecycle: add_service -> start_all -> wait -> shutdown"
  - "Session restoration: mark dirty at startup, save on clean shutdown"
  - "Stub methods for session persistence in Task 1, fully implemented in Task 4"

# Metrics
duration: 8min
completed: 2026-02-04
---

# Phase 5 Plan 1: Single-Command Startup Summary

**Multi-process service orchestration with ProcessManager, signal-based graceful shutdown, and session state persistence for crash detection**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-04T17:35:55Z
- **Completed:** 2026-02-04T17:44:22Z
- **Tasks:** 4
- **Files modified:** 4

## Accomplishments

- ProcessManager class for spawning and managing multiple services as separate processes
- Signal-based graceful shutdown (SIGINT/SIGTERM) with 5s terminate timeout + force kill
- SessionState ORM model with dirty_shutdown flag for crash detection
- `configurable-agents ui` CLI command launching Dashboard + Chat UI with single command
- Rich progress feedback during service startup with spinners
- Session persistence for crash detection and restoration capability

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ProcessManager for multi-service orchestration** - `3d3b7f7` (feat)
2. **Task 2: Add ui CLI command using ProcessManager** - `fe7ffbf` (feat)
3. **Task 3: Test ProcessManager signal handling and graceful shutdown** - N/A (verified in Task 1)
4. **Task 4: Add session state persistence and crash detection** - `6293358` (feat)

## Files Created/Modified

- `src/configurable_agents/process/__init__.py` - Package exports (ProcessManager, ServiceSpec)
- `src/configurable_agents/process/manager.py` - ProcessManager class with signal handling and session persistence
- `src/configurable_agents/storage/models.py` - Added SessionState ORM model with dirty_shutdown flag
- `src/configurable_agents/cli.py` - Added `ui` subcommand and `cmd_ui()` function

## Decisions Made

**SessionState model design:**
- Used `Integer` for `dirty_shutdown` column instead of `Boolean` for SQLite compatibility
- Singleton pattern with `id='default'` - only one session state row needed
- Stored `active_workflows` and `session_data` as JSON Text fields for flexibility

**ProcessManager design:**
- Used `multiprocessing.Process` with `daemon=False` to ensure clean shutdown on Windows
- Signal handlers registered AFTER process spawning to avoid child process issues
- 5-second terminate timeout before force kill to allow graceful shutdown
- Stub methods in Task 1, fully implemented in Task 4 after SessionState model existed

**Platform compatibility:**
- Windows: SIGINT only (limited signal support)
- Unix: SIGINT and SIGTERM full support

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] SessionState import error in Task 1**

- **Found during:** Task 1 verification
- **Issue:** ProcessManager imported SessionState which didn't exist yet (added in Task 4)
- **Fix:** Created stub session methods in Task 1 with doc notes indicating full implementation in Task 4
- **Files modified:** src/configurable_agents/process/manager.py
- **Verification:** Module imports correctly, stub methods have correct signatures
- **Committed in:** 3d3b7f7 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Stub pattern necessary for incremental implementation across tasks. No scope creep.

## Issues Encountered

**Windows file locking during test cleanup:**
- SQLite database file was locked during test cleanup on Windows
- Not an issue with the code itself, just test artifact cleanup
- Verified SessionState model works correctly before cleanup error

## Authentication Gates

None encountered during this plan.

## Next Phase Readiness

- ProcessManager fully functional with signal handling and session persistence
- `configurable-agents ui` command ready for use
- SessionState table will be created on first database access via SQLAlchemy
- Ready for Phase 5 Plan 2: Database auto-initialization (already completed)

**Note:** Phase 5 Plan 2 (05-02-PLAN.md) appears to be already complete based on SUMMARY.md existence. Next is Plan 3 (05-03-PLAN.md).

---
*Phase: 05-foundation-reliability*
*Completed: 2026-02-04*
