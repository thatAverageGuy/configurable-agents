# Phase 5: Foundation & Reliability - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

## Phase Boundary

Users can start the platform with one command (`configurable-agents ui`) and it just works — databases auto-initialize, all services launch successfully, progress is clearly communicated, and errors are handled gracefully with helpful messages.

This phase covers startup experience, auto-initialization from any entry point (UI/CLI/Python API), status dashboard, and error handling. Navigation and onboarding are Phase 6.

---

## Implementation Decisions

### Startup progress feedback
- Simple step-by-step output with spinners (e.g., "Starting dashboard...", "Initializing database...")
- Show steps + final summary (e.g., "All 5 services started successfully")
- Helpful inline errors for common failures (port conflicts, missing dependencies) with fix suggestions
- Add `--verbose` flag for power users debugging issues (shows detailed startup logs)

### Auto-initialization behavior
- Block and show progress when databases don't exist (show "Initializing database..." with spinner)
- Check every startup, skip if tables exist (very fast check via SQLAlchemy)
- Generic initialization message only ("Initializing database..."), not per-table details
- Helpful errors with fix suggestions if initialization fails (permissions, disk full, etc.)

### Status dashboard scope
- Show 4 key metrics: Active workflows, Agent health, Recent errors, System resources
- Simple counts presentation (e.g., "3 workflows running", "5 agents"), no visual indicators needed
- Periodic refresh (not real-time SSE, not manual)
- Status dashboard on main page (not separate section)

### Error message format
- No error codes needed (just descriptive messages)
- Every error includes: Error description, Resolution steps, Collapsible technical details
- Technical details (stack traces, file paths) collapsed by default, accessible via "Show details" button

### Claude's Discretion
- Exact refresh interval for periodic status updates
- Spinner/loading indicator styling
- Specific wording of summary messages
- Which errors qualify as "common" for inline suggestions

---

## Specific Ideas

- Startup should feel like Docker Compose or Streamlit — clean, informative, not overwhelming
- Error messages should be actionable — "what do I do now?" is clear from the message
- Status dashboard is for quick health checks, not deep monitoring (that's MLFlow's job)

---

## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 05-foundation-reliability*
*Context gathered: 2026-02-04*
