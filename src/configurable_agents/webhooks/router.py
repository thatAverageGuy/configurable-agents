"""FastAPI router for webhook endpoints.

Provides generic webhook endpoint with HMAC validation, idempotency
protection, and async workflow execution. Includes platform-specific
handlers for WhatsApp and Telegram.
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

# Global platform handlers (initialized lazily)
_whatsapp_handler: Optional["WhatsAppWebhookHandler"] = None
_telegram_bot: Optional["Bot"] = None
_telegram_dispatcher: Optional["Dispatcher"] = None


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


def _get_whatsapp_config() -> Dict[str, Optional[str]]:
    """
    Get WhatsApp configuration from environment variables.

    Reads WHATSAPP_PHONE_ID, WHATSAPP_ACCESS_TOKEN, and
    WHATSAPP_VERIFY_TOKEN from environment.

    Returns:
        Dict with phone_id, access_token, verify_token (None if not set)

    Example:
        >>> config = _get_whatsapp_config()
        >>> if config["phone_id"]:
        ...     print("WhatsApp configured")
    """
    return {
        "phone_id": os.getenv("WHATSAPP_PHONE_ID"),
        "access_token": os.getenv("WHATSAPP_ACCESS_TOKEN"),
        "verify_token": os.getenv("WHATSAPP_VERIFY_TOKEN"),
    }


def _get_whatsapp_handler() -> Optional["WhatsAppWebhookHandler"]:
    """
    Get or create WhatsApp webhook handler.

    Lazily initializes the handler on first call if environment
    variables are configured.

    Returns:
        WhatsAppWebhookHandler instance or None if not configured
    """
    global _whatsapp_handler

    if _whatsapp_handler is None:
        config = _get_whatsapp_config()
        if all(config.values()):
            from configurable_agents.webhooks.whatsapp import WhatsAppWebhookHandler

            _whatsapp_handler = WhatsAppWebhookHandler(
                phone_id=config["phone_id"],
                access_token=config["access_token"],
                verify_token=config["verify_token"],
            )
            logger.info("WhatsApp webhook handler initialized")

    return _whatsapp_handler


def _get_telegram_token() -> Optional[str]:
    """
    Get Telegram bot token from environment variable.

    Returns:
        Telegram bot token or None if not configured

    Example:
        >>> token = _get_telegram_token()
        >>> if token:
        ...     bot = create_telegram_bot(token)
    """
    return os.getenv("TELEGRAM_BOT_TOKEN")


def _get_telegram_bot() -> Optional["Bot"]:
    """
    Get or create Telegram Bot instance.

    Lazily initializes the bot on first call if TELEGRAM_BOT_TOKEN
    environment variable is set.

    Returns:
        aiogram Bot instance or None if not configured
    """
    global _telegram_bot

    if _telegram_bot is None:
        token = _get_telegram_token()
        if token:
            try:
                from configurable_agents.webhooks.telegram import create_telegram_bot

                _telegram_bot = create_telegram_bot(token)
                logger.info("Telegram bot initialized")
            except ImportError:
                logger.warning("aiogram not installed, Telegram webhooks unavailable")

    return _telegram_bot


def _get_telegram_dispatcher() -> Optional["Dispatcher"]:
    """
    Get or create Telegram Dispatcher instance.

    Lazily initializes the dispatcher with workflow handlers
    on first call if TELEGRAM_BOT_TOKEN is set.

    Returns:
        aiogram Dispatcher instance or None if not configured
    """
    global _telegram_dispatcher

    if _telegram_dispatcher is None:
        token = _get_telegram_token()
        if token:
            try:
                from configurable_agents.webhooks.telegram import (
                    create_dispatcher,
                    register_workflow_handlers,
                )
                from configurable_agents.runtime.executor import run_workflow_async

                _telegram_dispatcher = create_dispatcher()

                # Register workflow handlers
                async def workflow_runner(workflow_name: str, inputs: dict) -> dict:
                    """Wrapper for workflow execution."""
                    return await run_workflow_async(f"{workflow_name}.yaml", inputs)

                register_workflow_handlers(_telegram_dispatcher, workflow_runner)
                logger.info("Telegram dispatcher initialized with workflow handlers")
            except ImportError:
                logger.warning("aiogram not installed, Telegram webhooks unavailable")

    return _telegram_dispatcher


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


@router.get("/whatsapp")
async def whatsapp_verify_webhook(
    mode: str = None, token: str = None, challenge: str = None
) -> Any:
    """
    Verify WhatsApp webhook with Meta.

    Meta sends a GET request when setting up the webhook to verify
    ownership. This endpoint returns the challenge if verification succeeds.

    Query params:
        hub.mode: Should be "subscribe"
        hub.verify_token: Must match WHATSAPP_VERIFY_TOKEN
        hub.challenge: Random string to return on success

    Args:
        mode: Value from hub.mode query parameter
        token: Value from hub.verify_token query parameter
        challenge: Value from hub.challenge query parameter

    Returns:
        Challenge value as int on success, 403 on failure

    Example:
        # Meta will send:
        GET /webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=123456
    """
    handler = _get_whatsapp_handler()

    if handler is None:
        logger.warning("WhatsApp webhook handler not configured")
        raise HTTPException(status_code=503, detail="WhatsApp webhooks not configured")

    result = handler.verify_webhook(mode, token, challenge)

    if result is None:
        raise HTTPException(status_code=403, detail="Webhook verification failed")

    return result


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request, background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """
    Handle incoming WhatsApp webhook message.

    Receives messages from WhatsApp Business API, parses workflow
    commands, and executes workflows asynchronously.

    Message format:
        /workflow_name <input>

    Args:
        request: FastAPI Request object with Meta webhook payload
        background_tasks: FastAPI BackgroundTasks for async execution

    Returns:
        Acknowledgment response

    Raises:
        HTTPException 503: If WhatsApp not configured

    Example:
        # User sends WhatsApp message: "/article_writer AI Safety"
        # Message is parsed, workflow executed, result sent back
    """
    handler = _get_whatsapp_handler()

    if handler is None:
        logger.warning("WhatsApp webhook handler not configured")
        raise HTTPException(status_code=503, detail="WhatsApp webhooks not configured")

    # Parse webhook payload
    data = await request.json()

    # Extract phone and message
    phone = handler.extract_phone(data)
    message = handler.extract_message(data)

    if phone is None or message is None:
        logger.debug("No phone or message in webhook payload")
        return {"status": "no_message"}

    logger.info(f"Received WhatsApp message from {phone}: {message[:50]}...")

    # Handle message and queue background workflow execution
    ack = await handler.handle_message(phone, message, background_tasks.add_task)

    return {"status": "received", "message": ack}


@router.post("/telegram")
async def telegram_webhook(request: Request) -> Dict[str, str]:
    """
    Handle incoming Telegram webhook update.

    Receives updates from Telegram Bot API and feeds them to the
    aiogram dispatcher for processing.

    Message format:
        /workflow_name <input>

    Args:
        request: FastAPI Request object with Telegram Update JSON

    Returns:
        Success status

    Raises:
        HTTPException 503: If Telegram not configured

    Example:
        # User sends Telegram message: "/article_writer AI Safety"
        # Update is fed to dispatcher, workflow executed, result sent back
    """
    bot = _get_telegram_bot()
    dispatcher = _get_telegram_dispatcher()

    if bot is None or dispatcher is None:
        logger.warning("Telegram webhook handler not configured")
        raise HTTPException(status_code=503, detail="Telegram webhooks not configured")

    try:
        from configurable_agents.webhooks.telegram import handle_telegram_webhook

        result = await handle_telegram_webhook(request, bot, dispatcher)
        logger.debug("Telegram update processed")
        return result
    except ImportError:
        logger.error("aiogram not installed")
        raise HTTPException(status_code=503, detail="aiogram not installed")


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
        Health status with webhook repository info and platform availability
    """
    webhook_repo = get_webhook_repository()

    return {
        "status": "healthy",
        "service": "webhooks",
        "repository": type(webhook_repo).__name__,
        "signature_configured": bool(_get_webhook_secret("generic")),
        "whatsapp_configured": _get_whatsapp_handler() is not None,
        "telegram_configured": _get_telegram_bot() is not None,
    }
