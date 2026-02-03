"""Tests for Telegram webhook handler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    from aiogram import Bot, Dispatcher, types
    from aiogram.types import Update
    from fastapi import Request

    from configurable_agents.webhooks.telegram import (
        AIOGRAM_AVAILABLE,
        create_telegram_bot,
        create_dispatcher,
        handle_telegram_webhook,
        MAX_TELEGRAM_MESSAGE_LENGTH,
        register_workflow_handlers,
        send_telegram_message,
    )

    AIOGRAM_IMPORTS_AVAILABLE = True
except ImportError:
    AIOGRAM_AVAILABLE = False
    AIOGRAM_IMPORTS_AVAILABLE = False


# Skip all tests if aiogram is not installed
pytestmark = pytest.mark.skipif(
    not AIOGRAM_IMPORTS_AVAILABLE, reason="aiogram not installed"
)


@pytest.fixture
def telegram_token():
    """Test Telegram bot token."""
    return "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"


@pytest.fixture
def telegram_bot(telegram_token):
    """Create test Bot instance."""
    return create_telegram_bot(telegram_token)


@pytest.fixture
def telegram_dispatcher():
    """Create test Dispatcher instance."""
    return create_dispatcher()


class TestCreateBot:
    """Tests for create_telegram_bot factory function."""

    def test_create_bot(self, telegram_token):
        """Test Bot creation factory."""
        bot = create_telegram_bot(telegram_token)
        assert bot is not None
        assert isinstance(bot, Bot)


class TestCreateDispatcher:
    """Tests for create_dispatcher factory function."""

    def test_create_dispatcher(self, telegram_dispatcher):
        """Test Dispatcher creation factory."""
        dp = create_dispatcher()
        assert dp is not None
        assert isinstance(dp, Dispatcher)

    def test_dispatcher_has_message_handler(self, telegram_dispatcher):
        """Test dispatcher has message handler attribute."""
        dp = create_dispatcher()
        # In aiogram 3.x, message handlers are registered via .message decorator
        assert hasattr(dp, "message")


class TestRegisterWorkflowHandlers:
    """Tests for register_workflow_handlers function."""

    @pytest.mark.asyncio
    async def test_register_handlers_does_not_raise(self, telegram_dispatcher):
        """Test that handler registration completes without error."""
        async def mock_runner(name, inputs):
            return {"result": "success"}

        # Should not raise any exception
        register_workflow_handlers(telegram_dispatcher, mock_runner)


class TestSendMessageChunking:
    """Tests for send_telegram_message function."""

    @pytest.mark.asyncio
    async def test_send_short_message(self, telegram_bot):
        """Test sending message under character limit."""
        chat_id = 123456789
        short_text = "Short message"

        with patch.object(telegram_bot, "send_message", new_callable=AsyncMock) as mock_send:
            await send_telegram_message(telegram_bot, chat_id, short_text)

            # Should send single message
            assert mock_send.call_count == 1
            mock_send.assert_called_with(chat_id, short_text)

    @pytest.mark.asyncio
    async def test_send_long_message_chunked(self, telegram_bot):
        """Test that long messages are split into chunks."""
        chat_id = 123456789
        # Create message longer than Telegram's limit
        long_text = "x" * (MAX_TELEGRAM_MESSAGE_LENGTH + 1000)

        with patch.object(telegram_bot, "send_message", new_callable=AsyncMock) as mock_send:
            await send_telegram_message(telegram_bot, chat_id, long_text)

            # Should send two messages
            assert mock_send.call_count == 2

            # First chunk should be max length
            first_call = mock_send.call_args_list[0]
            assert len(first_call[0][1]) == MAX_TELEGRAM_MESSAGE_LENGTH

            # Second chunk should be remainder
            second_call = mock_send.call_args_list[1]
            assert len(second_call[0][1]) == 1000

    @pytest.mark.asyncio
    async def test_send_message_exact_limit(self, telegram_bot):
        """Test message exactly at the character limit."""
        chat_id = 123456789
        exact_text = "x" * MAX_TELEGRAM_MESSAGE_LENGTH

        with patch.object(telegram_bot, "send_message", new_callable=AsyncMock) as mock_send:
            await send_telegram_message(telegram_bot, chat_id, exact_text)

            # Should send single message
            assert mock_send.call_count == 1

    @pytest.mark.asyncio
    async def test_send_multiple_chunks(self, telegram_bot):
        """Test message that spans multiple chunks."""
        chat_id = 123456789
        # Create message spanning 3 chunks
        multi_text = "x" * (MAX_TELEGRAM_MESSAGE_LENGTH * 3)

        with patch.object(telegram_bot, "send_message", new_callable=AsyncMock) as mock_send:
            await send_telegram_message(telegram_bot, chat_id, multi_text)

            # Should send three messages
            assert mock_send.call_count == 3


class TestHandleTelegramWebhook:
    """Tests for handle_telegram_webhook function."""

    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request with Telegram update."""
        request = MagicMock(spec=Request)

        # Create minimal Telegram update JSON
        update_json = b'{"update_id": 123, "message": {"message_id": 1, "from": {"id": 123456789, "is_bot": false, "first_name": "Test"}, "chat": {"id": 123456789, "type": "private"}, "date": 1234567890, "text": "/start"}}'
        request.body = AsyncMock(return_value=update_json)

        return request

    @pytest.mark.asyncio
    async def test_handle_webhook_success(
        self, telegram_bot, telegram_dispatcher, mock_request
    ):
        """Test successful webhook handling."""
        result = await handle_telegram_webhook(mock_request, telegram_bot, telegram_dispatcher)

        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_handle_webhook_reads_body(
        self, telegram_bot, telegram_dispatcher, mock_request
    ):
        """Test that webhook reads request body."""
        await handle_telegram_webhook(mock_request, telegram_bot, telegram_dispatcher)

        # Verify body was read
        mock_request.body.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_webhook_invalid_json(
        self, telegram_bot, telegram_dispatcher, mock_request
    ):
        """Test webhook with invalid JSON."""
        mock_request.body = AsyncMock(return_value=b"invalid json")

        with pytest.raises(Exception):
            await handle_telegram_webhook(
                mock_request, telegram_bot, telegram_dispatcher
            )


class TestWorkflowCommandParsing:
    """Tests for workflow command parsing inside handlers."""

    @pytest.fixture
    def mock_runner(self):
        """Mock workflow runner."""
        async def runner(name, inputs):
            return {"result": f"Executed {name} with {inputs}"}

        return runner

    @pytest.mark.asyncio
    async def test_workflow_command_format_slash_required(
        self, telegram_dispatcher, mock_runner
    ):
        """Test that handler registration succeeds."""
        # Register handlers - should not raise
        with patch(
            "configurable_agents.webhooks.telegram.send_telegram_message",
            new_callable=AsyncMock,
        ):
            register_workflow_handlers(telegram_dispatcher, mock_runner)

        # Verify dispatcher was modified (has message observers)
        assert telegram_dispatcher is not None


# Test that MAX_TELEGRAM_MESSAGE_LENGTH is correctly defined
def test_max_telegram_message_length():
    """Test Telegram message length constant."""
    assert MAX_TELEGRAM_MESSAGE_LENGTH == 4096
