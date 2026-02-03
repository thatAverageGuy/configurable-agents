"""Webhook handlers for external integrations.

Provides generic webhook infrastructure with HMAC signature validation,
idempotency protection, and async workflow execution. Platform-specific
handlers (WhatsApp, Telegram) extend this base infrastructure.

Public API:
    - WebhookHandler: Generic webhook handler with HMAC validation
    - verify_signature: HMAC signature verification utility
    - WebhookError, InvalidSignatureError, ReplayAttackError: Exception classes
    - router: FastAPI router with generic webhook endpoint

Example:
    >>> from configurable_agents.webhooks import WebhookHandler
    >>> handler = WebhookHandler(secret="my-secret")
    >>> await handler.handle_webhook(request, process_func, webhook_repo)
"""

from configurable_agents.webhooks.base import (
    InvalidSignatureError,
    ReplayAttackError,
    WebhookError,
    WebhookHandler,
    verify_signature,
)

__all__ = [
    "WebhookHandler",
    "verify_signature",
    "WebhookError",
    "InvalidSignatureError",
    "ReplayAttackError",
]
