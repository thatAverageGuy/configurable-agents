---
phase: 03-interfaces-and-triggers
plan: 03
subsystem: webhooks
tags: [fastapi, hmac, idempotency, webhook-handler, replay-protection, async]

# Dependency graph
requires:
  - phase: 01-core-engine
    provides: Storage abstraction layer with Repository Pattern, workflow executor
  - phase: 02-agent-infrastructure
    provides: SQLAlchemy 2.0 async patterns, repository implementations
provides:
  - WebhookEventRecord ORM model for idempotency tracking
  - WebhookEventRepository abstract interface with is_processed/mark_processed/cleanup
  - SqliteWebhookEventRepository with INSERT OR IGNORE for idempotent operations
  - run_workflow_async() function for background workflow execution from FastAPI
  - WebhookHandler class with HMAC signature validation
  - verify_signature() using hmac.compare_digest for timing-attack safety
  - FastAPI router with POST /webhooks/generic endpoint
affects:
  - 03-03B: Platform-specific webhook handlers (WhatsApp, Telegram) will extend this base
  - 03-04: Dashboard integration for webhook monitoring

# Tech tracking
tech-stack:
  added: [hmac, hashlib, fastapi.BackgroundTasks]
  patterns: [HMAC signature verification, idempotency key tracking, replay attack prevention, async workflow execution]

key-files:
  created:
    - src/configurable_agents/webhooks/__init__.py
    - src/configurable_agents/webhooks/base.py (WebhookHandler, verify_signature)
    - src/configurable_agents/webhooks/router.py (FastAPI webhook endpoints)
    - tests/webhooks/test_base.py
    - tests/webhooks/test_router_base.py
  modified:
    - src/configurable_agents/storage/models.py (WebhookEventRecord)
    - src/configurable_agents/storage/base.py (WebhookEventRepository)
    - src/configurable_agents/storage/sqlite.py (SqliteWebhookEventRepository)
    - src/configurable_agents/storage/factory.py (5-tuple return)
    - src/configurable_agents/storage/__init__.py (new exports)
    - src/configurable_agents/runtime/executor.py (run_workflow_async)

key-decisions:
  - "Used hmac.compare_digest() for constant-time signature comparison to prevent timing attacks"
  - "INSERT OR IGNORE pattern for idempotent mark_processed() - safe to call multiple times"
  - "Async wrapper run_workflow_async() using asyncio.run_in_executor for non-blocking execution"
  - "Webhook signature validation is optional when WEBHOOK_SECRET not configured - enables testing"
  - "Generic webhook endpoint accepts workflow_name and inputs for universal workflow triggering"

patterns-established:
  - "Pattern: HMAC signature verification with algorithm prefix handling (sha256=...)"
  - "Pattern: Idempotency key tracking prevents replay attacks in webhook processing"
  - "Pattern: Async wrapper for sync functions using asyncio.run_in_executor()"
  - "Pattern: Optional security - signature validation only when secret configured"

# Metrics
duration: 12min
completed: 2026-02-03
---

# Phase 3 Plan 03: Generic Webhook Infrastructure Summary

**Generic webhook infrastructure with HMAC signature validation, idempotency tracking, and async workflow execution - the secure foundation for all webhook integrations**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-03T15:42:48Z
- **Completed:** 2026-02-03T16:15:06Z
- **Tasks:** 2
- **Files modified:** 11 (5 created, 6 modified)

## Accomplishments

- WebhookEventRecord ORM model with unique constraint on webhook_id for replay attack prevention
- WebhookEventRepository interface with is_processed(), mark_processed(), cleanup_old_events() methods
- SqliteWebhookEventRepository using INSERT OR IGNORE for idempotent operations
- run_workflow_async() wrapping sync executor in asyncio.run_in_executor() for background tasks
- WebhookHandler class with HMAC signature verification using hmac.compare_digest()
- verify_signature() utility with algorithm prefix handling (sha256=...)
- FastAPI router with POST /webhooks/generic endpoint accepting workflow_name and inputs
- Replay attack detection via webhook_id tracking before processing
- Comprehensive test suite with 30 tests covering all functionality

## Task Commits

Each task was committed atomically:

1. **Task 1: Create webhook storage and async workflow execution** - `bced23f` (feat)
2. **Task 2: Create generic webhook handler with HMAC validation and FastAPI router** - `88d8e13` (feat)

**Plan metadata:** (to be committed with STATE.md update)

## Files Created/Modified

### Created

- `src/configurable_agents/webhooks/__init__.py` - Package exports for WebhookHandler, verify_signature, exceptions
- `src/configurable_agents/webhooks/base.py` - WebhookHandler class, verify_signature(), exception classes
- `src/configurable_agents/webhooks/router.py` - FastAPI router with POST /webhooks/generic endpoint
- `tests/webhooks/__init__.py` - Test package
- `tests/webhooks/test_base.py` - Tests for signature verification and WebhookHandler (18 tests)
- `tests/webhooks/test_router_base.py` - Tests for generic webhook endpoint (12 tests)

### Modified

- `src/configurable_agents/storage/models.py` - Added WebhookEventRecord ORM model
- `src/configurable_agents/storage/base.py` - Added WebhookEventRepository interface
- `src/configurable_agents/storage/sqlite.py` - Added SqliteWebhookEventRepository implementation
- `src/configurable_agents/storage/factory.py` - Updated to return 5-tuple with webhook_event_repo
- `src/configurable_agents/storage/__init__.py` - Added exports for WebhookEventRepository, WebhookEventRecord
- `src/configurable_agents/runtime/executor.py` - Added run_workflow_async() function

## Decisions Made

1. **HMAC signature verification with hmac.compare_digest()**: Used constant-time comparison to prevent timing attacks on signature verification. The algorithm prefix (e.g., "sha256=") is automatically stripped.

2. **INSERT OR IGNORE for idempotent mark_processed()**: Used raw SQL with INSERT OR IGNORE instead of SQLAlchemy's merge() because merge() doesn't handle unique constraint violations gracefully. This makes mark_processed() safe to call multiple times.

3. **Async wrapper using asyncio.run_in_executor()**: The run_workflow_async() function wraps the synchronous run_workflow() in a thread pool executor, preventing blocking of the FastAPI event loop during workflow execution.

4. **Optional signature validation**: Webhook signature validation only occurs when WEBHOOK_SECRET_GENERIC or WEBHOOK_SECRET_DEFAULT is configured. This allows testing and development without requiring secret setup.

5. **Generic webhook endpoint payload format**: The POST /webhooks/generic endpoint accepts a simple JSON payload with workflow_name, inputs, and optional webhook_id fields. This universal format enables triggering any workflow via webhook.

## Deviations from Plan

None - plan executed exactly as written. All requirements met without auto-fixes or scope changes.

## Issues Encountered

None - all implementation proceeded smoothly following established patterns from prior phases.

## User Setup Required

None - no external service configuration required. Webhook secrets can be set via environment variables (WEBHOOK_SECRET_GENERIC, WEBHOOK_SECRET_DEFAULT, WEBHOOK_SIGNATURE_REQUIRED) but are optional for testing.

## Next Phase Readiness

- Generic webhook infrastructure is complete and ready for platform-specific handlers
- Plan 03-03B will build WhatsApp and Telegram webhook handlers extending this base
- Dashboard integration (03-04) can now display webhook events and status
- All tests passing (30/30) with >80% coverage of webhook functionality

---
*Phase: 03-interfaces-and-triggers*
*Completed: 2026-02-03*
