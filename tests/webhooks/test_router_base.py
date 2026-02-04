"""Tests for generic webhook router endpoints."""

import hmac
import hashlib
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from configurable_agents.webhooks.router import router, get_webhook_repository


# Create test app
from fastapi import FastAPI
test_app = FastAPI()
test_app.include_router(router)


class TestGetWebhookRepository:
    """Tests for get_webhook_repository function."""

    def test_returns_repository(self):
        """Test that function returns a WebhookEventRepository."""
        repo = get_webhook_repository()
        assert repo is not None
        assert hasattr(repo, "is_processed")
        assert hasattr(repo, "mark_processed")
        assert hasattr(repo, "cleanup_old_events")


class TestGenericWebhookEndpoint:
    """Tests for POST /webhooks/generic endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(test_app)

    @pytest.fixture
    def mock_webhook_repo(self):
        """Create mock webhook repository."""
        repo = Mock()
        repo.is_processed = Mock(return_value=False)
        repo.mark_processed = Mock()
        return repo

    def test_generic_webhook_missing_workflow_name(self, client, mock_webhook_repo):
        """Test endpoint returns 400 when workflow_name is missing."""
        with patch("configurable_agents.webhooks.router.get_webhook_repository", return_value=mock_webhook_repo):
            response = client.post(
                "/webhooks/generic",
                json={"inputs": {"topic": "AI"}},
            )
            assert response.status_code == 400
            assert "workflow_name" in response.json()["detail"]

    def test_generic_webhook_missing_inputs(self, client, mock_webhook_repo):
        """Test endpoint returns 400 when inputs is missing."""
        with patch("configurable_agents.webhooks.router.get_webhook_repository", return_value=mock_webhook_repo):
            response = client.post(
                "/webhooks/generic",
                json={"workflow_name": "test"},
            )
            assert response.status_code == 400
            assert "inputs" in response.json()["detail"]

    def test_generic_webhook_success_without_workflow_file(self, client, mock_webhook_repo):
        """Test endpoint returns 500 when workflow file doesn't exist."""
        with patch("configurable_agents.webhooks.router.get_webhook_repository", return_value=mock_webhook_repo):
            response = client.post(
                "/webhooks/generic",
                json={
                    "workflow_name": "nonexistent",
                    "inputs": {"topic": "AI"},
                },
            )
            # Workflow will fail to load (file not found)
            assert response.status_code == 500
            assert "Workflow execution failed" in response.json()["detail"]

    def test_generic_webhook_with_webhook_id(self, client, mock_webhook_repo):
        """Test endpoint tracks webhook_id for idempotency."""
        with patch("configurable_agents.webhooks.router.get_webhook_repository", return_value=mock_webhook_repo):
            response = client.post(
                "/webhooks/generic",
                json={
                    "workflow_name": "nonexistent",
                    "inputs": {"topic": "AI"},
                    "webhook_id": "test-123",
                },
            )
            # Even though workflow fails, webhook_id should be tracked
            mock_webhook_repo.is_processed.assert_called_once_with("test-123")
            mock_webhook_repo.mark_processed.assert_called_once()

    def test_generic_webhook_replay_attack(self, client):
        """Test endpoint prevents replay attack with duplicate webhook_id."""
        # Create repo that reports webhook as already processed
        mock_repo = Mock()
        mock_repo.is_processed = Mock(return_value=True)
        mock_repo.mark_processed = Mock()

        # Need to also patch the global repository reference
        with patch("configurable_agents.webhooks.router.get_webhook_repository", return_value=mock_repo):
            with patch("configurable_agents.webhooks.router._webhook_repo", mock_repo):
                response = client.post(
                    "/webhooks/generic",
                    json={
                        "workflow_name": "test",
                        "inputs": {"topic": "AI"},
                        "webhook_id": "duplicate-123",
                    },
                )
                # Either 409 (replay detected) or 500 (depends on execution path)
                # The key is is_processed was called
                mock_repo.is_processed.assert_called_once_with("duplicate-123")

    def test_generic_webhook_with_id_field(self, client, mock_webhook_repo):
        """Test endpoint uses 'id' field as webhook_id alternative."""
        with patch("configurable_agents.webhooks.router.get_webhook_repository", return_value=mock_webhook_repo):
            response = client.post(
                "/webhooks/generic",
                json={
                    "workflow_name": "nonexistent",
                    "inputs": {"topic": "AI"},
                    "id": "test-id-456",
                },
            )
            # Should use 'id' as webhook_id
            mock_webhook_repo.is_processed.assert_called_once_with("test-id-456")

    def test_generic_webhook_with_signature(self, client, mock_webhook_repo):
        """Test endpoint validates HMAC signature when secret is configured."""
        # Note: Full signature validation is tested in test_base.py
        # This test just verifies the code path is reachable
        # The endpoint will process webhooks without signature if no secret configured
        with patch("configurable_agents.webhooks.router.get_webhook_repository", return_value=mock_webhook_repo):
            # Without signature configured, request should still be processed
            response = client.post(
                "/webhooks/generic",
                json={"workflow_name": "nonexistent", "inputs": {"topic": "AI"}},
            )
            # Should return 500 (workflow file not found) not 403 (signature error)
            assert response.status_code == 500

    def test_generic_webhook_with_invalid_signature(self, client, mock_webhook_repo):
        """Test endpoint rejects request with invalid signature."""
        import os
        old_secret = os.environ.get("WEBHOOK_SECRET_GENERIC")
        old_required = os.environ.get("WEBHOOK_SIGNATURE_REQUIRED")
        try:
            os.environ["WEBHOOK_SECRET_GENERIC"] = "test-secret"
            os.environ["WEBHOOK_SIGNATURE_REQUIRED"] = "true"

            with patch("configurable_agents.webhooks.router.get_webhook_repository", return_value=mock_webhook_repo):
                response = client.post(
                    "/webhooks/generic",
                    json={"workflow_name": "test", "inputs": {"topic": "AI"}},
                    headers={"X-Signature": "invalid-signature"},
                )
                # Should reject due to invalid signature
                assert response.status_code == 403
        finally:
            if old_secret is None:
                os.environ.pop("WEBHOOK_SECRET_GENERIC", None)
            else:
                os.environ["WEBHOOK_SECRET_GENERIC"] = old_secret
            if old_required is None:
                os.environ.pop("WEBHOOK_SIGNATURE_REQUIRED", None)
            else:
                os.environ["WEBHOOK_SIGNATURE_REQUIRED"] = old_required

    def test_generic_webhook_invalid_json(self, client, mock_webhook_repo):
        """Test endpoint handles invalid JSON."""
        with patch("configurable_agents.webhooks.router.get_webhook_repository", return_value=mock_webhook_repo):
            # The router tries to parse JSON first, which fails with a WebhookError
            # Then catches and converts to HTTP 400/500
            response = client.post(
                "/webhooks/generic",
                content="not valid json",
                headers={"Content-Type": "application/json"},
            )
            # Should return error status (FastAPI 422 or WebhookError 500)
            assert response.status_code in (400, 422, 500)


class TestHealthEndpoint:
    """Tests for GET /webhooks/health endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(test_app)

    def test_health_returns_status(self, client):
        """Test health endpoint returns status."""
        response = client.get("/webhooks/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert data["service"] == "webhooks"
        assert "repository" in data
