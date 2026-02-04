"""Telegram Bot API webhook handler using aiogram 3.x.

Provides webhook handler for Telegram Bot API with:
- Bot and Dispatcher factory functions
- Workflow handler registration with message decorators
- /start command handler with usage instructions
- Workflow trigger messages with typing indicator
- Message chunking for >4096 char results (Telegram limit)
- Webhook handler function for FastAPI integration

Environment variables required:
    TELEGRAM_BOT_TOKEN: Bot token from @BotFather on Telegram

Example:
    >>> from aiogram import Bot, Dispatcher
    >>> bot = create_telegram_bot("YOUR_BOT_TOKEN")
    >>> dp = create_dispatcher()
    >>> register_workflow_handlers(dp, run_workflow_func)
    >>> # In FastAPI route:
    >>> await handle_telegram_webhook(request, bot, dp)
"""

import logging
from typing import Awaitable, Callable, Optional

try:
    from aiogram import Bot, Dispatcher, types
    from aiogram.filters import Command
    from aiogram.types import Update
    from fastapi import Request

    AIOGRAM_AVAILABLE = True
except ImportError:
    AIOGRAM_AVAILABLE = False
    Bot = None
    Dispatcher = None
    types = None
    Command = None
    Update = None
    Request = None

from configurable_agents.runtime.executor import run_workflow_async

logger = logging.getLogger(__name__)

# Telegram message length limit
MAX_TELEGRAM_MESSAGE_LENGTH = 4096


def create_telegram_bot(token: str):
    """
    Create aiogram 3.x Bot instance.

    Factory function for creating a configured Telegram Bot instance.

    Args:
        token: Telegram bot token from @BotFather

    Returns:
        Configured aiogram Bot instance

    Raises:
        ImportError: If aiogram is not installed

    Example:
        >>> bot = create_telegram_bot("123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
        >>> await bot.get_me()
    """
    if not AIOGRAM_AVAILABLE:
        raise ImportError(
            "aiogram is not installed. Install with: pip install aiogram>=3.0.0"
        )

    return Bot(token=token)


def create_dispatcher() -> Dispatcher:
    """
    Create aiogram 3.x Dispatcher instance.

    Factory function for creating an empty dispatcher for handler
    registration. The dispatcher manages message routing and handlers.

    Returns:
        Configured aiogram Dispatcher instance

    Raises:
        ImportError: If aiogram is not installed

    Example:
        >>> dp = create_dispatcher()
        >>> @dp.message()
        ... async def handler(message): ...
    """
    if not AIOGRAM_AVAILABLE:
        raise ImportError(
            "aiogram is not installed. Install with: pip install aiogram>=3.0.0"
        )

    return Dispatcher()


def register_workflow_handlers(
    dispatcher: Dispatcher, run_workflow_func: Callable[[str, dict], Awaitable[dict]]
):
    """
    Register workflow message handlers with the dispatcher.

    Registers two handlers:
    1. /start command - Sends welcome message with usage instructions
    2. All messages - Handles workflow trigger messages

    Args:
        dispatcher: aiogram Dispatcher instance
        run_workflow_func: Async function to run workflows (signature: async func(name, inputs) -> result)

    Example:
        >>> dp = create_dispatcher()
        >>> async def my_runner(name, inputs):
        ...     return await run_workflow_async(f"{name}.yaml", inputs)
        >>> register_workflow_handlers(dp, my_runner)
    """
    if not AIOGRAM_AVAILABLE:
        raise ImportError(
            "aiogram is not installed. Install with: pip install aiogram>=3.0.0"
        )

    @dispatcher.message(Command("start"))
    async def cmd_start(message: types.Message):
        """Handle /start command - send welcome message with usage instructions."""
        welcome_text = (
            "Welcome! I can run workflows for you.\n\n"
            "Usage:\n"
            "  /workflow_name <input>\n\n"
            "Example:\n"
            "  /article_writer AI Safety\n\n"
            "Send a message starting with '/' to trigger a workflow."
        )
        await message.answer(welcome_text)
        logger.info(f"Sent start message to chat {message.chat.id}")

    @dispatcher.message()
    async def handle_workflow_message(message: types.Message):
        """Handle workflow trigger messages."""
        text = message.text

        if not text or not text.startswith("/"):
            await message.answer(
                "Usage: /workflow_name <input>\n"
                "Example: /article_writer AI Safety"
            )
            return

        # Parse workflow command
        parts = text[1:].split(maxsplit=1)
        if len(parts) < 2:
            await message.answer(
                "Usage: /workflow_name <input>\n"
                "Example: /article_writer AI Safety"
            )
            return

        workflow_name = parts[0].strip()
        workflow_input = parts[1].strip()

        logger.info(f"Chat {message.chat.id} triggering workflow: {workflow_name}")

        # Send "typing" indicator
        try:
            await message.bot.send_chat_action(message.chat.id, "typing")
        except Exception as e:
            logger.warning(f"Failed to send typing action: {e}")

        # Execute workflow
        try:
            result = await run_workflow_func(workflow_name, {"input": workflow_input})

            # Format result as text
            if isinstance(result, dict):
                result_text = str(result)
            else:
                result_text = str(result)

            # Send result (split if too long for Telegram)
            await send_telegram_message(message.bot, message.chat.id, result_text)
            logger.info(f"Workflow {workflow_name} completed for chat {message.chat.id}")

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            await message.answer(f"Error: {str(e)}")

    logger.info("Workflow handlers registered with dispatcher")


async def send_telegram_message(bot: Bot, chat_id: int, text: str) -> None:
    """
    Send text message to Telegram chat, splitting if too long.

    Telegram has a 4096 character limit per message. This function
    automatically splits long messages into chunks.

    Args:
        bot: aiogram Bot instance
        chat_id: Telegram chat ID
        text: Message text to send

    Raises:
        Exception: If message sending fails

    Example:
        >>> await send_telegram_message(bot, 123456789, "Long message...")
    """
    if not AIOGRAM_AVAILABLE:
        raise ImportError(
            "aiogram is not installed. Install with: pip install aiogram>=3.0.0"
        )

    # Split message into chunks if too long
    for i in range(0, len(text), MAX_TELEGRAM_MESSAGE_LENGTH):
        chunk = text[i : i + MAX_TELEGRAM_MESSAGE_LENGTH]
        await bot.send_message(chat_id, chunk)

    logger.debug(f"Sent {len(text)} chars to chat {chat_id} in {(len(text) // MAX_TELEGRAM_MESSAGE_LENGTH) + 1} message(s)")


async def handle_telegram_webhook(request: Request, bot: Bot, dispatcher: Dispatcher) -> dict:
    """
    Handle incoming Telegram webhook update.

    Parses the Update from the request body and feeds it to the
    dispatcher for processing.

    Args:
        request: FastAPI Request object
        bot: aiogram Bot instance
        dispatcher: aiogram Dispatcher instance

    Returns:
        {"status": "ok"} on success

    Raises:
        ImportError: If aiogram is not installed
        Exception: If update processing fails

    Example:
        >>> @app.post("/webhooks/telegram")
        ... async def telegram_endpoint(request: Request):
        ...     return await handle_telegram_webhook(request, bot, dispatcher)
    """
    if not AIOGRAM_AVAILABLE:
        raise ImportError(
            "aiogram is not installed. Install with: pip install aiogram>=3.0.0"
        )

    # Parse update from request body
    body = await request.body()
    update = Update.model_validate_json(body)

    logger.debug(f"Received Telegram update: {update.update_id}")

    # Feed update to dispatcher
    await dispatcher.feed_webhook_update(bot, update)

    return {"status": "ok"}
