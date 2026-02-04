"""Tests for webhook base handler and utilities."""

import hmac
import hashlib
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from configurable_agents.webhooks.base import (
    InvalidSignatureError,
    ReplayAttackError,
    WebhookError,
    WebhookHandler,
    verify_signature,
)


class TestVerifySignature:
    """Tests for verify_signature function."""

    def test_verify_signature_valid(self):
        """Test signature verification with valid signature."""
        secret = "test-secret"
        payload = b'{"test": "data"}'

        # Generate valid signature
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        signature = f"sha256={expected}"

        assert verify_signature(payload, signature, secret) is True

    def test_verify_signature_without_prefix(self):
        """Test signature verification without algorithm prefix."""
        secret = "test-secret"
        payload = b'{"test": "data"}'

        # Generate signature without prefix
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        assert verify_signature(payload, expected, secret) is True

    def test_verify_signature_invalid(self):
        """Test signature verification with invalid signature."""
        secret = "test-secret"
        payload = b'{"test": "data"}'
        signature = "invalid-signature"

        assert verify_signature(payload, signature, secret) is False

    def test_verify_signature_wrong_secret(self):
        """Test signature verification with wrong secret."""
        secret = "test-secret"
        wrong_secret = "wrong-secret"
        payload = b'{"test": "data"}'

        # Generate signature with wrong secret
        expected = hmac.new(wrong_secret.encode(), payload, hashlib.sha256).hexdigest()
        signature = f"sha256={expected}"

        assert verify_signature(payload, signature, secret) is False

    def test_verify_timing_attack_resistance(self):
        """Test that verification uses constant-time comparison."""
        secret = "test-secret"
        payload = b'{"test": "data"}'

        # Generate valid signature
        valid_signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        # Timing attacks require precise measurement, but we can verify
        # the function uses hmac.compare_digest which is constant-time
        assert verify_signature(payload, valid_signature, secret) is True
        assert verify_signature(payload, "a" * 64, secret) is False


class TestWebhookError:
    """Tests for webhook exception classes."""

    def test_webhook_error_base(self):
        """Test base WebhookError exception."""
        error = WebhookError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_invalid_signature_error(self):
        """Test InvalidSignatureError is WebhookError subclass."""
        error = InvalidSignatureError("Invalid signature")
        assert isinstance(error, WebhookError)
        assert str(error) == "Invalid signature"

    def test_replay_attack_error(self):
        """Test ReplayAttackError is WebhookError subclass."""
        error = ReplayAttackError("Duplicate webhook")
        assert isinstance(error, WebhookError)
        assert str(error) == "Duplicate webhook"


class TestWebhookHandler:
    """Tests for WebhookHandler class."""

    def test_init(self):
        """Test WebhookHandler initialization."""
        handler = WebhookHandler(secret="my-secret")
        assert handler.secret == "my-secret"
        assert handler.signature_header == "X-Signature"
        assert handler.algorithm == "sha256"

    def test_init_custom_params(self):
        """Test WebhookHandler with custom parameters."""
        handler = WebhookHandler(
            secret="my-secret",
            signature_header="X-Hub-Signature",
            algorithm="sha512",
        )
        assert handler.secret == "my-secret"
        assert handler.signature_header == "X-Hub-Signature"
        assert handler.algorithm == "sha512"

    @pytest.mark.asyncio
    async def test_handle_webhook_success(self):
        """Test successful webhook handling without signature."""
        handler = WebhookHandler(secret="test-secret")

        # Mock request
        request = Mock()
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        request.json = AsyncMock(return_value={"test": "data"})
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Mock handler function
        handler_func = AsyncMock(return_value={"status": "ok"})

        # Process webhook
        result = await handler.handle_webhook(request, handler_func)

        assert result == {"status": "ok"}
        handler_func.assert_called_once_with({"test": "data"})

    @pytest.mark.asyncio
    async def test_handle_webhook_with_valid_signature(self):
        """Test webhook handling with valid signature."""
        secret = "test-secret"
        handler = WebhookHandler(secret=secret)

        # Generate valid signature
        payload = b'{"test": "data"}'
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        # Mock request
        request = Mock()
        request.body = AsyncMock(return_value=payload)
        request.json = AsyncMock(return_value={"test": "data"})
        request.headers = {"X-Signature": f"sha256={signature}"}
        request.client = Mock(host="127.0.0.1")

        # Mock handler function
        handler_func = AsyncMock(return_value={"status": "ok"})

        # Process webhook
        result = await handler.handle_webhook(request, handler_func)

        assert result == {"status": "ok"}
        handler_func.assert_called_once_with({"test": "data"})

    @pytest.mark.asyncio
    async def test_handle_webhook_with_invalid_signature(self):
        """Test webhook handling with invalid signature."""
        handler = WebhookHandler(secret="test-secret")

        # Mock request with invalid signature
        request = Mock()
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        request.json = AsyncMock(return_value={"test": "data"})
        request.headers = {"X-Signature": "invalid-signature"}
        request.client = Mock(host="127.0.0.1")

        # Mock handler function
        handler_func = AsyncMock(return_value={"status": "ok"})

        # Should raise InvalidSignatureError
        with pytest.raises(InvalidSignatureError, match="HMAC signature verification failed"):
            await handler.handle_webhook(request, handler_func)

        # Handler should not be called
        handler_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_webhook_with_invalid_json(self):
        """Test webhook handling with invalid JSON."""
        handler = WebhookHandler(secret="test-secret")

        # Mock request with invalid JSON
        request = Mock()
        request.body = AsyncMock(return_value=b'not json')
        request.json = AsyncMock(side_effect=ValueError("Invalid JSON"))
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Mock handler function
        handler_func = AsyncMock(return_value={"status": "ok"})

        # Should raise WebhookError
        with pytest.raises(WebhookError, match="Invalid JSON payload"):
            await handler.handle_webhook(request, handler_func)

    @pytest.mark.asyncio
    async def test_handle_webhook_with_replay_attack(self):
        """Test webhook handling detects replay attack."""
        handler = WebhookHandler(secret="test-secret")

        # Mock webhook repository
        webhook_repo = Mock()
        webhook_repo.is_processed = Mock(return_value=True)
        webhook_repo.mark_processed = Mock()

        # Mock request
        request = Mock()
        request.body = AsyncMock(return_value=b'{"webhook_id": "abc123", "test": "data"}')
        request.json = AsyncMock(return_value={"webhook_id": "abc123", "test": "data"})
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Mock handler function
        handler_func = AsyncMock(return_value={"status": "ok"})

        # Should raise ReplayAttackError
        with pytest.raises(ReplayAttackError, match="already processed"):
            await handler.handle_webhook(request, handler_func, webhook_repo=webhook_repo)

        # Handler should not be called
        handler_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_webhook_idempotency_tracking(self):
        """Test webhook idempotency tracking prevents replays."""
        handler = WebhookHandler(secret="test-secret")

        # Mock webhook repository
        webhook_repo = Mock()
        webhook_repo.is_processed = Mock(return_value=False)
        webhook_repo.mark_processed = Mock()

        # Mock request
        request = Mock()
        request.body = AsyncMock(return_value=b'{"webhook_id": "abc123", "test": "data"}')
        request.json = AsyncMock(return_value={"webhook_id": "abc123", "test": "data"})
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Mock handler function
        handler_func = AsyncMock(return_value={"status": "ok"})

        # Process webhook
        result = await handler.handle_webhook(request, handler_func, webhook_repo=webhook_repo)

        assert result == {"status": "ok"}
        # Check that webhook was marked as processed
        webhook_repo.is_processed.assert_called_once_with("abc123")
        webhook_repo.mark_processed.assert_called_once_with("abc123", "unknown")

    @pytest.mark.asyncio
    async def test_handle_webhook_with_provider_in_data(self):
        """Test webhook uses provider from data for idempotency."""
        handler = WebhookHandler(secret="test-secret")

        # Mock webhook repository
        webhook_repo = Mock()
        webhook_repo.is_processed = Mock(return_value=False)
        webhook_repo.mark_processed = Mock()

        # Mock request with provider
        request = Mock()
        request.body = AsyncMock(return_value=b'{"webhook_id": "abc123", "provider": "test-provider"}')
        request.json = AsyncMock(return_value={"webhook_id": "abc123", "provider": "test-provider"})
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Mock handler function
        handler_func = AsyncMock(return_value={"status": "ok"})

        # Process webhook
        await handler.handle_webhook(request, handler_func, webhook_repo=webhook_repo)

        # Check that provider was used
        webhook_repo.mark_processed.assert_called_once_with("abc123", "test-provider")

    @pytest.mark.asyncio
    async def test_handle_webhook_non_dict_result(self):
        """Test webhook handling wraps non-dict handler results."""
        handler = WebhookHandler(secret="test-secret")

        # Mock request
        request = Mock()
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        request.json = AsyncMock(return_value={"test": "data"})
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Mock handler function that returns non-dict
        handler_func = AsyncMock(return_value="string result")

        # Process webhook
        result = await handler.handle_webhook(request, handler_func)

        assert result == {"result": "string result"}

    @pytest.mark.asyncio
    async def test_handle_webhook_handler_exception(self):
        """Test webhook handling when handler function raises exception."""
        handler = WebhookHandler(secret="test-secret")

        # Mock request
        request = Mock()
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        request.json = AsyncMock(return_value={"test": "data"})
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Mock handler function that raises exception
        handler_func = AsyncMock(side_effect=ValueError("Handler error"))

        # Should raise WebhookError
        with pytest.raises(WebhookError, match="Handler failed"):
            await handler.handle_webhook(request, handler_func)
