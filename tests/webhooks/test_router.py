"""Tests for webhook router with platform endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from configurable_agents.webhooks.router import router


@pytest.fixture
def test_client():
    """Create test client for webhook router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_whatsapp_handler():
    """Create mock WhatsApp handler."""
    handler = MagicMock()
    handler.verify_webhook = MagicMock(return_value=123456)
    handler.extract_phone = MagicMock(return_value="1234567890")
    handler.extract_message = MagicMock(return_value="/workflow_name input")
    handler.handle_message = AsyncMock(return_value="Executing workflow: workflow_name")
    return handler


@pytest.fixture
def mock_telegram_bot():
    """Create mock Telegram bot."""
    return MagicMock()


@pytest.fixture
def mock_telegram_dispatcher():
    """Create mock Telegram dispatcher."""
    return MagicMock()


class TestWhatsAppEndpoints:
    """Tests for WhatsApp webhook endpoints."""

    def test_whatsapp_verification_success(self, test_client, mock_whatsapp_handler):
        """Test WhatsApp webhook verification with valid token."""
        with patch(
            "configurable_agents.webhooks.router._get_whatsapp_handler",
            return_value=mock_whatsapp_handler,
        ):
            response = test_client.get(
                "/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=test_token&hub.challenge=123456"
            )

            assert response.status_code == 200
            assert response.json() == 123456

    def test_whatsapp_verification_not_configured(self, test_client):
        """Test WhatsApp endpoint returns 503 when not configured."""
        with patch(
            "configurable_agents.webhooks.router._get_whatsapp_handler",
            return_value=None,
        ):
            response = test_client.get(
                "/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=123456"
            )

            assert response.status_code == 503
            assert "not configured" in response.json()["detail"]

    def test_whatsapp_post_message(self, test_client, mock_whatsapp_handler):
        """Test POST to WhatsApp webhook with message."""
        webhook_payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {"from": "1234567890", "text": {"body": "/workflow_name input"}}
                                ]
                            }
                        }
                    ]
                }
            ]
        }

        with patch(
            "configurable_agents.webhooks.router._get_whatsapp_handler",
            return_value=mock_whatsapp_handler,
        ):
            response = test_client.post("/webhooks/whatsapp", json=webhook_payload)

            assert response.status_code == 200
            assert response.json()["status"] == "received"

    def test_whatsapp_post_no_message(self, test_client, mock_whatsapp_handler):
        """Test POST to WhatsApp webhook with no message payload."""
        mock_whatsapp_handler.extract_phone.return_value = None
        mock_whatsapp_handler.extract_message.return_value = None

        webhook_payload = {"entry": [{"changes": [{"value": {"messages": []}}]}]}

        with patch(
            "configurable_agents.webhooks.router._get_whatsapp_handler",
            return_value=mock_whatsapp_handler,
        ):
            response = test_client.post("/webhooks/whatsapp", json=webhook_payload)

            assert response.status_code == 200
            assert response.json()["status"] == "no_message"


class TestTelegramEndpoints:
    """Tests for Telegram webhook endpoints."""

    def test_telegram_webhook_not_configured(self, test_client):
        """Test Telegram endpoint returns 503 when not configured."""
        with patch(
            "configurable_agents.webhooks.router._get_telegram_bot",
            return_value=None,
        ):
            response = test_client.post("/webhooks/telegram", json={"update_id": 123})

            assert response.status_code == 503
            assert "not configured" in response.json()["detail"]

    def test_telegram_webhook_success(self, test_client, mock_telegram_bot, mock_telegram_dispatcher):
        """Test Telegram webhook processes update."""
        update_json = {
            "update_id": 123,
            "message": {
                "message_id": 1,
                "from": {"id": 123456789, "is_bot": False, "first_name": "Test"},
                "chat": {"id": 123456789, "type": "private"},
                "date": 1234567890,
                "text": "/start",
            },
        }

        with patch(
            "configurable_agents.webhooks.router._get_telegram_bot",
            return_value=mock_telegram_bot,
        ), patch(
            "configurable_agents.webhooks.router._get_telegram_dispatcher",
            return_value=mock_telegram_dispatcher,
        ), patch(
            "configurable_agents.webhooks.telegram.handle_telegram_webhook",
            new_callable=AsyncMock,
            return_value={"status": "ok"},
        ):
            response = test_client.post("/webhooks/telegram", json=update_json)

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}


class TestGenericWebhook:
    """Tests for generic webhook endpoint."""

    def test_generic_webhook_still_works(self, test_client):
        """Test that generic webhook endpoint still functions."""
        # Use unique webhook_id to avoid idempotency conflicts
        import uuid
        webhook_id = f"test-id-{uuid.uuid4()}"

        payload = {
            "workflow_name": "test_workflow",
            "inputs": {"topic": "AI"},
            "webhook_id": webhook_id,
        }

        # Mock the run_workflow_async to avoid actual execution
        with patch(
            "configurable_agents.runtime.executor.run_workflow_async",
            new_callable=AsyncMock,
            return_value={"result": "success"},
        ):
            response = test_client.post("/webhooks/generic", json=payload)

            # Should get 200 since we're mocking the workflow execution
            assert response.status_code == 200
            assert response.json()["status"] == "success"

    def test_generic_webhook_missing_workflow_name(self, test_client):
        """Test generic webhook with missing workflow_name."""
        payload = {"inputs": {"topic": "AI"}}

        response = test_client.post("/webhooks/generic", json=payload)

        assert response.status_code == 400
        assert "workflow_name" in response.json()["detail"]

    def test_generic_webhook_missing_inputs(self, test_client):
        """Test generic webhook with missing inputs."""
        payload = {"workflow_name": "test"}

        response = test_client.post("/webhooks/generic", json=payload)

        assert response.status_code == 400
        assert "inputs" in response.json()["detail"]


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_endpoint(self, test_client):
        """Test health check endpoint returns status."""
        response = test_client.get("/webhooks/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "whatsapp_configured" in data
        assert "telegram_configured" in data


class TestPlatformConfiguration:
    """Tests for platform configuration detection."""

    def test_whatsapp_config_helper(self):
        """Test WhatsApp config helper returns correct values."""
        from configurable_agents.webhooks.router import _get_whatsapp_config

        # Should return dict with all values as None when not set
        config = _get_whatsapp_config()
        assert "phone_id" in config
        assert "access_token" in config
        assert "verify_token" in config

    def test_telegram_token_helper(self):
        """Test Telegram token helper."""
        from configurable_agents.webhooks.router import _get_telegram_token

        # Should return None when not set
        token = _get_telegram_token()
        assert token is None
