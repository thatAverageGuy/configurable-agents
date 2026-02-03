"""Tests for WhatsApp webhook handler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from configurable_agents.webhooks.whatsapp import WhatsAppWebhookHandler


@pytest.fixture
def whatsapp_handler():
    """Create a test handler instance."""
    return WhatsAppWebhookHandler(
        phone_id="123456789",
        access_token="test_access_token",
        verify_token="test_verify_token",
    )


@pytest.fixture
def valid_webhook_payload():
    """Create a valid WhatsApp webhook payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "+1234567890",
                                "phone_number_id": "123456789",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Test User"},
                                    "wa_id": "1234567890",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "1234567890",
                                    "id": "wamid.xxx",
                                    "timestamp": "1234567890",
                                    "text": {"body": "/article_writer AI Safety"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


class TestVerifyWebhook:
    """Tests for verify_webhook method."""

    def test_verify_webhook_valid(self, whatsapp_handler):
        """Test webhook verification with valid token."""
        result = whatsapp_handler.verify_webhook("subscribe", "test_verify_token", "123456")
        assert result == 123456

    def test_verify_webhook_wrong_mode(self, whatsapp_handler):
        """Test webhook verification fails with wrong mode."""
        result = whatsapp_handler.verify_webhook("invalid", "test_verify_token", "123456")
        assert result is None

    def test_verify_webhook_wrong_token(self, whatsapp_handler):
        """Test webhook verification fails with wrong token."""
        result = whatsapp_handler.verify_webhook("subscribe", "wrong_token", "123456")
        assert result is None

    def test_verify_webhook_non_numeric_challenge(self, whatsapp_handler):
        """Test webhook verification with non-numeric challenge."""
        result = whatsapp_handler.verify_webhook("subscribe", "test_verify_token", "abc123")
        assert result == "abc123"


class TestExtractPhone:
    """Tests for extract_phone method."""

    def test_extract_phone_valid(self, whatsapp_handler, valid_webhook_payload):
        """Test phone extraction from valid payload."""
        phone = whatsapp_handler.extract_phone(valid_webhook_payload)
        assert phone == "1234567890"

    def test_extract_phone_no_messages(self, whatsapp_handler):
        """Test phone extraction with no messages."""
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [],
                            }
                        }
                    ]
                }
            ]
        }
        phone = whatsapp_handler.extract_phone(payload)
        assert phone is None

    def test_extract_phone_no_from_field(self, whatsapp_handler):
        """Test phone extraction when from field missing."""
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [{}],
                            }
                        }
                    ]
                }
            ]
        }
        phone = whatsapp_handler.extract_phone(payload)
        assert phone is None

    def test_extract_phone_malformed_payload(self, whatsapp_handler):
        """Test phone extraction with malformed payload."""
        phone = whatsapp_handler.extract_phone({})
        assert phone is None


class TestExtractMessage:
    """Tests for extract_message method."""

    def test_extract_message_valid(self, whatsapp_handler, valid_webhook_payload):
        """Test message extraction from valid payload."""
        message = whatsapp_handler.extract_message(valid_webhook_payload)
        assert message == "/article_writer AI Safety"

    def test_extract_message_no_messages(self, whatsapp_handler):
        """Test message extraction with no messages."""
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [],
                            }
                        }
                    ]
                }
            ]
        }
        message = whatsapp_handler.extract_message(payload)
        assert message is None

    def test_extract_message_no_text_body(self, whatsapp_handler):
        """Test message extraction when text body missing."""
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [{}],
                            }
                        }
                    ]
                }
            ]
        }
        message = whatsapp_handler.extract_message(payload)
        assert message is None


class TestParseWorkflowCommand:
    """Tests for parse_workflow_command static method."""

    def test_parse_valid_command(self):
        """Test parsing valid workflow command."""
        result = WhatsAppWebhookHandler.parse_workflow_command("/article_writer AI Safety")
        assert result == ("article_writer", "AI Safety")

    def test_parse_command_with_multiword_input(self):
        """Test parsing command with multi-word input."""
        result = WhatsAppWebhookHandler.parse_workflow_command(
            "/workflow_name This is a multi word input"
        )
        assert result == ("workflow_name", "This is a multi word input")

    def test_parse_command_no_slash(self):
        """Test parsing command without leading slash."""
        result = WhatsAppWebhookHandler.parse_workflow_command("workflow_name input")
        assert result is None

    def test_parse_command_no_input(self):
        """Test parsing command without input."""
        result = WhatsAppWebhookHandler.parse_workflow_command("/workflow_name")
        assert result is None

    def test_parse_command_empty(self):
        """Test parsing empty command."""
        result = WhatsAppWebhookHandler.parse_workflow_command("")
        assert result is None

    def test_parse_command_with_extra_spaces(self):
        """Test parsing command with extra whitespace."""
        result = WhatsAppWebhookHandler.parse_workflow_command(
            "  /workflow_name   input data  "
        )
        assert result == ("workflow_name", "input data")


class TestSendMessage:
    """Tests for send_message method."""

    @pytest.mark.asyncio
    async def test_send_message_success(self, whatsapp_handler):
        """Test successful message sending."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            await whatsapp_handler.send_message("1234567890", "Test message")

            mock_instance.post.assert_called_once()
            call_args = mock_instance.post.call_args
            assert "messages" in call_args[0][0]
            assert call_args[1]["json"]["to"] == "1234567890"
            assert call_args[1]["json"]["text"]["body"] == "Test message"

    @pytest.mark.asyncio
    async def test_send_message_http_error(self, whatsapp_handler):
        """Test message sending with HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=MagicMock()
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            with pytest.raises(httpx.HTTPStatusError):
                await whatsapp_handler.send_message("1234567890", "Test message")


class TestHandleMessage:
    """Tests for handle_message method."""

    @pytest.mark.asyncio
    async def test_handle_message_valid_command(self, whatsapp_handler):
        """Test handling valid workflow command."""
        background_tasks = []

        # Mock that simulates FastAPI BackgroundTasks.add_task (synchronous)
        def mock_add_task(func):
            background_tasks.append(func)

        with patch(
            "configurable_agents.webhooks.whatsapp.run_workflow_async",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = {"result": "success"}

            with patch.object(whatsapp_handler, "send_message", new_callable=AsyncMock):
                ack = await whatsapp_handler.handle_message(
                    "1234567890", "/article_writer AI Safety", mock_add_task
                )

                assert "Executing workflow" in ack
                assert len(background_tasks) == 1

                # Execute the background task
                await background_tasks[0]()
                mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_invalid_format(self, whatsapp_handler):
        """Test handling invalid command format."""
        background_tasks = []

        def mock_add_task(func):
            background_tasks.append(func)

        ack = await whatsapp_handler.handle_message(
            "1234567890", "invalid format", mock_add_task
        )

        assert "Usage:" in ack
        assert len(background_tasks) == 0

    @pytest.mark.asyncio
    async def test_handle_message_no_slash(self, whatsapp_handler):
        """Test handling message without leading slash."""
        background_tasks = []

        def mock_add_task(func):
            background_tasks.append(func)

        ack = await whatsapp_handler.handle_message(
            "1234567890", "workflow_name input", mock_add_task
        )

        assert "Usage:" in ack
        assert len(background_tasks) == 0

    @pytest.mark.asyncio
    async def test_handle_message_workflow_error(self, whatsapp_handler):
        """Test handling workflow execution error."""
        background_tasks = []

        def mock_add_task(func):
            background_tasks.append(func)

        with patch(
            "configurable_agents.webhooks.whatsapp.run_workflow_async",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.side_effect = Exception("Workflow failed")

            with patch.object(whatsapp_handler, "send_message", new_callable=AsyncMock) as mock_send:
                ack = await whatsapp_handler.handle_message(
                    "1234567890", "/article_writer AI Safety", mock_add_task
                )

                # Execute the background task
                await background_tasks[0]()

                # Should send error message
                mock_send.assert_called()
                error_msg = mock_send.call_args[0][1]
                assert "Error:" in error_msg

    @pytest.mark.asyncio
    async def test_handle_message_long_result_truncation(self, whatsapp_handler):
        """Test that long results are truncated for WhatsApp."""
        background_tasks = []

        def mock_add_task(func):
            background_tasks.append(func)

        # Create a result longer than WhatsApp's 4096 char limit
        long_result = "x" * 5000

        with patch(
            "configurable_agents.webhooks.whatsapp.run_workflow_async",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = long_result

            with patch.object(whatsapp_handler, "send_message", new_callable=AsyncMock) as mock_send:
                ack = await whatsapp_handler.handle_message(
                    "1234567890", "/article_writer AI Safety", mock_add_task
                )

                # Execute the background task
                await background_tasks[0]()

                # Check that sent message is truncated
                sent_message = mock_send.call_args[0][1]
                assert len(sent_message) <= 4096
                assert "..." in sent_message
