"""FastAPI router for webhook endpoints.

Provides generic webhook endpoint with HMAC validation, idempotency
protection, and async workflow execution.
"""

import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from configurable_agents.storage import create_storage_backend, WebhookEventRepository
from configurable_agents.webhooks.base import InvalidSignatureError, ReplayAttackError, WebhookHandler

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Global webhook repository (initialized on startup)
_webhook_repo: Optional[WebhookEventRepository] = None


def get_webhook_repository() -> WebhookEventRepository:
    """Get or create webhook event repository.

    Returns:
        WebhookEventRepository instance
    """
    global _webhook_repo
    if _webhook_repo is None:
        # Get repository from storage backend
        _, _, _, _, _webhook_repo = create_storage_backend()
    return _webhook_repo


def _get_webhook_secret(provider: str = "default") -> str:
    """
    Get webhook secret from environment variable.

    Checks for provider-specific secret (WEBHOOK_SECRET_{PROVIDER}) first,
    then falls back to default secret (WEBHOOK_SECRET_DEFAULT).

    Args:
        provider: Provider name (e.g., "whatsapp", "telegram", "generic")

    Returns:
        Webhook secret string

    Raises:
        HTTPException: If no secret configured for the provider
    """
    # Try provider-specific secret first
    env_var = f"WEBHOOK_SECRET_{provider.upper()}"
    secret = os.getenv(env_var)

    if not secret:
        # Fall back to default secret
        secret = os.getenv("WEBHOOK_SECRET_DEFAULT", "")

    if not secret and provider != "default":
        # If no secret configured, return empty string (signature verification skipped)
        logger.warning(f"No webhook secret configured for provider '{provider}'")

    return secret


async def _process_generic_webhook(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process generic webhook payload and trigger workflow.

    Expected payload format:
    {
        "workflow_name": str,  # Name of workflow to execute
        "inputs": dict,         # Workflow inputs
        "webhook_id": str       # Optional idempotency key
    }

    Args:
        data: Validated webhook payload

    Returns:
        Workflow execution result

    Raises:
        HTTPException: If workflow_name or inputs missing
    """
    from configurable_agents.runtime.executor import run_workflow_async

    # Extract workflow trigger parameters
    workflow_name = data.get("workflow_name")
    inputs = data.get("inputs")

    if not workflow_name:
        raise HTTPException(status_code=400, detail="Missing 'workflow_name' in payload")

    if inputs is None:
        raise HTTPException(status_code=400, detail="Missing 'inputs' in payload")

    logger.info(f"Triggering workflow '{workflow_name}' from generic webhook")

    try:
        # Run workflow asynchronously
        result = await run_workflow_async(workflow_name, inputs)

        return {
            "status": "success",
            "workflow_name": workflow_name,
            "result": result,
        }
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {e}")


@router.post("/generic")
async def generic_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Generic webhook endpoint for triggering workflows.

    Accepts POST requests with JSON payload containing workflow_name and inputs.
    Optionally validates HMAC signature via X-Signature header.

    Payload format:
    {
        "workflow_name": "article_writer",
        "inputs": {"topic": "AI Safety"},
        "webhook_id": "unique-id-123"  // Optional, for idempotency
    }

    Signature validation (if X-Signature header present):
    - Computes HMAC-SHA256 of request body using WEBHOOK_SECRET_DEFAULT
    - Compares with X-Signature header value
    - Rejects request if signature doesn't match

    Idempotency (if webhook_id provided):
    - Tracks processed webhook IDs to prevent duplicate execution
    - Returns 409 Conflict if webhook_id already processed

    Args:
        request: FastAPI Request object
        background_tasks: FastAPI BackgroundTasks for async execution

    Returns:
        Response with status and workflow execution result

    Raises:
        HTTPException 400: Invalid payload
        HTTPException 403: Invalid signature
        HTTPException 409: Duplicate webhook_id (replay attack)
        HTTPException 500: Workflow execution failed
    """
    # Get webhook repository for idempotency tracking
    webhook_repo = get_webhook_repository()

    # Get secret for signature verification
    secret = _get_webhook_secret("generic")
    signature_required = os.getenv("WEBHOOK_SIGNATURE_REQUIRED", "false").lower() == "true"

    # Create handler with optional signature validation
    handler = WebhookHandler(
        secret=secret or "dummy-secret",  # Dummy secret if validation not required
        signature_header="X-Signature",
    )

    # If no secret configured and signature not required, skip validation
    if not secret and not signature_required:
        # Just process the webhook without signature validation
        try:
            data = await request.json()
            webhook_id = data.get("webhook_id") or data.get("id")
            if webhook_id and webhook_repo:
                if webhook_repo.is_processed(webhook_id):
                    raise HTTPException(status_code=409, detail=f"Webhook {webhook_id} already processed")
                webhook_repo.mark_processed(webhook_id, "generic")

            result = await _process_generic_webhook(data)
            return result
        except ReplayAttackError:
            raise HTTPException(status_code=409, detail="Duplicate webhook_id")
        except Exception as e:
            if "Missing" in str(e) or "Invalid" in str(e):
                raise HTTPException(status_code=400, detail=str(e))
            raise HTTPException(status_code=500, detail=str(e))

    # With signature validation
    try:
        return await handler.handle_webhook(
            request,
            _process_generic_webhook,
            webhook_repo=webhook_repo,
            signature_required=signature_required,
        )
    except InvalidSignatureError as e:
        logger.warning(f"Invalid signature: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except ReplayAttackError as e:
        logger.info(f"Replay attack prevented: {e}")
        raise HTTPException(status_code=409, detail=str(e))
    except WebhookError as e:
        logger.error(f"Webhook processing error: {e}")
        if "Missing" in str(e) or "Invalid" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def webhook_health() -> Dict[str, Any]:
    """
    Health check endpoint for webhook system.

    Returns:
        Health status with webhook repository info
    """
    webhook_repo = get_webhook_repository()

    return {
        "status": "healthy",
        "service": "webhooks",
        "repository": type(webhook_repo).__name__,
        "signature_configured": bool(_get_webhook_secret("generic")),
    }
