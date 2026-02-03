"""Base webhook handler with HMAC signature validation.

Provides generic webhook infrastructure for external integrations with
security features including signature verification and replay attack
prevention via idempotency key tracking.
"""

import hashlib
import hmac
import logging
from typing import Any, Callable, Dict, Optional

from fastapi import Request

from configurable_agents.storage.base import WebhookEventRepository

logger = logging.getLogger(__name__)


class WebhookError(Exception):
    """Base exception for webhook errors."""

    pass


class InvalidSignatureError(WebhookError):
    """Raised when webhook signature verification fails."""

    pass


class ReplayAttackError(WebhookError):
    """Raised when webhook_id has already been processed (replay attack)."""

    pass


def verify_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256",
) -> bool:
    """
    Verify HMAC signature of webhook payload.

    Uses constant-time comparison (hmac.compare_digest) to prevent
    timing attacks on signature verification.

    Args:
        payload: Raw request body bytes
        signature: Signature from request header (may include algorithm prefix)
        secret: Webhook secret key for HMAC computation
        algorithm: Hash algorithm to use (default: "sha256")

    Returns:
        True if signature valid, False otherwise

    Example:
        >>> payload = b'{"test": "data"}'
        >>> signature = "abc123..."
        >>> verify_signature(payload, signature, "my-secret")
        True
    """
    # Encode secret to bytes
    secret_bytes = secret.encode() if isinstance(secret, str) else secret

    # Remove algorithm prefix if present (e.g., "sha256=", "hmac_sha256")
    if "=" in signature:
        signature = signature.split("=", 1)[1]

    # Compute expected HMAC hash
    hash_func = getattr(hashlib, algorithm, hashlib.sha256)
    expected = hmac.new(secret_bytes, payload, hash_func).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected, signature)


class WebhookHandler:
    """
    Generic webhook handler with signature verification.

    Provides secure webhook processing with HMAC signature validation
    and replay attack prevention via idempotency key tracking.

    Attributes:
        secret: Webhook secret key for signature verification
        signature_header: HTTP header name containing signature (default: "X-Signature")
        algorithm: Hash algorithm for HMAC (default: "sha256")

    Example:
        >>> handler = WebhookHandler(secret="my-secret")
        >>> async def process(data): return {"status": "ok"}
        >>> result = await handler.handle_webhook(request, process, webhook_repo)
    """

    def __init__(
        self,
        secret: str,
        signature_header: str = "X-Signature",
        algorithm: str = "sha256",
    ):
        """
        Initialize webhook handler.

        Args:
            secret: Webhook secret key for signature verification
            signature_header: HTTP header containing signature
            algorithm: Hash algorithm for HMAC computation
        """
        self.secret = secret
        self.signature_header = signature_header
        self.algorithm = algorithm

    def verify_request(self, request: Request) -> bool:
        """
        Verify webhook request signature.

        Reads the request body and verifies the HMAC signature.

        Args:
            request: FastAPI Request object

        Returns:
            True if signature valid, False otherwise

        Note:
            This method consumes the request body. Use handle_webhook()
            for complete processing with payload access.
        """
        # Get signature from header
        signature = request.headers.get(self.signature_header)
        if not signature:
            return False

        # Read request body
        # Note: This is a simplified version. For actual use, you'd need
        # to handle the request body asynchronously.
        return False  # Placeholder - use handle_webhook instead

    async def handle_webhook(
        self,
        request: Request,
        handler_func: Callable[[Dict[str, Any]], Any],
        webhook_repo: Optional[WebhookEventRepository] = None,
        signature_required: bool = False,
    ) -> Dict[str, Any]:
        """
        Handle webhook with signature verification and replay protection.

        Processes webhook payload with the following steps:
        1. Read raw request body
        2. Extract and verify HMAC signature (if present or required)
        3. Check for replay attack using webhook_id (if provided)
        4. Parse JSON payload
        5. Call handler function with validated data
        6. Mark webhook as processed (if webhook_id provided)

        Args:
            request: FastAPI Request object
            handler_func: Async function to process validated payload
            webhook_repo: Optional repository for idempotency tracking
            signature_required: If True, reject requests without valid signature

        Returns:
            Handler response as dictionary

        Raises:
            InvalidSignatureError: Signature verification fails
            ReplayAttackError: webhook_id already processed
            WebhookError: JSON parsing or other processing error

        Example:
            >>> async def process_trigger(data: dict) -> dict:
            ...     return {"status": "processed", "result": data}
            >>> result = await handler.handle_webhook(
            ...     request, process_trigger, webhook_repo
            ... )
        """
        # 1. Read raw payload
        payload = await request.body()

        # 2. Extract and verify signature
        signature = request.headers.get(self.signature_header)
        if signature:
            if not verify_signature(payload, signature, self.secret, self.algorithm):
                logger.warning(f"Invalid signature from {request.client.host if request.client else 'unknown'}")
                raise InvalidSignatureError("HMAC signature verification failed")
            logger.debug("Signature verified successfully")
        elif signature_required:
            logger.warning(f"Missing required signature from {request.client.host if request.client else 'unknown'}")
            raise InvalidSignatureError(f"Missing {self.signature_header} header")

        # 3. Parse JSON payload
        try:
            data: Dict[str, Any] = await request.json()
        except Exception as e:
            logger.error(f"Failed to parse webhook JSON: {e}")
            raise WebhookError(f"Invalid JSON payload: {e}")

        # 4. Check for replay attack using webhook_id
        webhook_id = data.get("webhook_id") or data.get("id")
        if webhook_id and webhook_repo:
            if webhook_repo.is_processed(webhook_id):
                logger.info(f"Replay attack detected: webhook_id={webhook_id}")
                raise ReplayAttackError(f"Webhook event {webhook_id} already processed")

            # Mark as processed before calling handler
            provider = data.get("provider", "unknown")
            webhook_repo.mark_processed(webhook_id, provider)
            logger.debug(f"Marked webhook {webhook_id} as processed")

        # 5. Call handler function
        try:
            result = await handler_func(data)
            return result if isinstance(result, dict) else {"result": result}
        except Exception as e:
            logger.error(f"Handler function failed: {e}")
            raise WebhookError(f"Handler failed: {e}")
