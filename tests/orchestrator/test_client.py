"""Tests for orchestrator registry client.

Tests the AgentRegistryOrchestratorClient which provides the interface
for orchestrators to discover and query agents from the registry.
"""

import json
from unittest.mock import Mock, patch

import httpx
import pytest

from configurable_agents.orchestrator.client import (
    AgentRegistryOrchestratorClient,
    create_orchestrator_client,
)


class TestAgentRegistryOrchestratorClient:
    """Tests for AgentRegistryOrchestratorClient."""

    def test_init_with_required_params(self) -> None:
        """Test client initialization with required parameters."""
        client = AgentRegistryOrchestratorClient("http://localhost:9000")

        assert client.registry_url == "http://localhost:9000"
        assert client.auth_token is None
        assert client.timeout == 10.0
        assert client._client is not None

    def test_init_with_auth_token(self) -> None:
        """Test client initialization with authentication token."""
        client = AgentRegistryOrchestratorClient(
            registry_url="http://localhost:9000",
            auth_token="test-token",
        )

        assert client.auth_token == "test-token"

    def test_init_strips_trailing_slash(self) -> None:
        """Test that trailing slash is stripped from registry URL."""
        client = AgentRegistryOrchestratorClient("http://localhost:9000/")

        assert client.registry_url == "http://localhost:9000"

    def test_get_headers_without_auth(self) -> None:
        """Test HTTP headers without authentication."""
        client = AgentRegistryOrchestratorClient("http://localhost:9000")
        headers = client._get_headers()

        assert headers["Content-Type"] == "application/json"
        assert headers["User-Agent"] == "ConfigurableAgents-Orchestrator/1.0"
        assert "Authorization" not in headers

    def test_get_headers_with_auth(self) -> None:
        """Test HTTP headers with authentication."""
        client = AgentRegistryOrchestratorClient(
            registry_url="http://localhost:9000",
            auth_token="test-token",
        )
        headers = client._get_headers()

        assert headers["Authorization"] == "Bearer test-token"

    @patch("configurable_agents.orchestrator.client.httpx.Client")
    def test_list_agents(self, mock_client_class: Mock) -> None:
        """Test listing all agents from registry."""
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "agent_id": "agent-1",
                "agent_name": "Test Agent",
                "host": "localhost",
                "port": 8000,
                "last_heartbeat": "2026-02-04T10:00:00Z",
                "ttl_seconds": 60,
                "agent_metadata": '{"type": "llm"}',
                "registered_at": "2026-02-04T09:00:00Z",
            }
        ]
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = AgentRegistryOrchestratorClient("http://localhost:9000")
        agents = client.list_agents()

        assert len(agents) == 1
        assert agents[0]["agent_id"] == "agent-1"
        assert agents[0]["agent_name"] == "Test Agent"

    @patch("configurable_agents.orchestrator.client.httpx.Client")
    def test_list_agents_with_filters(self, mock_client_class: Mock) -> None:
        """Test listing agents with metadata filters."""
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "agent_id": "agent-1",
                "agent_metadata": '{"type": "llm", "model": "gpt-4"}',
            },
            {
                "agent_id": "agent-2",
                "agent_metadata": '{"type": "tool"}',
            },
        ]
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = AgentRegistryOrchestratorClient("http://localhost:9000")
        agents = client.list_agents(filters={"type": "llm"})

        assert len(agents) == 1
        assert agents[0]["agent_id"] == "agent-1"

    @patch("configurable_agents.orchestrator.client.httpx.Client")
    def test_get_agent_found(self, mock_client_class: Mock) -> None:
        """Test getting a specific agent that exists."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "agent_id": "agent-1",
            "agent_name": "Test Agent",
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = AgentRegistryOrchestratorClient("http://localhost:9000")
        agent = client.get_agent("agent-1")

        assert agent is not None
        assert agent["agent_id"] == "agent-1"

    @patch("configurable_agents.orchestrator.client.httpx.Client")
    def test_get_agent_not_found(self, mock_client_class: Mock) -> None:
        """Test getting a specific agent that doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("Not Found", request=Mock(), response=mock_response)
        )

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = AgentRegistryOrchestratorClient("http://localhost:9000")
        agent = client.get_agent("nonexistent")

        assert agent is None

    def test_query_by_capability_filters_by_metadata(self) -> None:
        """Test querying agents by capability filters metadata correctly."""
        client = AgentRegistryOrchestratorClient("http://localhost:9000")

        # Mock list_agents
        agents = [
            {
                "agent_id": "agent-1",
                "agent_metadata": '{"type": "llm", "model": "gpt-4"}',
            },
            {
                "agent_id": "agent-2",
                "agent_metadata": '{"type": "tool", "model": "browser"}',
            },
            {
                "agent_id": "agent-3",
                "agent_metadata": '{"type": "llm", "model": "claude"}',
            },
        ]

        with patch.object(client, "list_agents", return_value=agents):
            results = client.query_by_capability({"type": "llm"})

            assert len(results) == 2
            assert results[0]["agent_id"] == "agent-1"
            assert results[1]["agent_id"] == "agent-3"

    def test_query_by_capability_with_wildcard(self) -> None:
        """Test querying agents with wildcard filters."""
        client = AgentRegistryOrchestratorClient("http://localhost:9000")

        agents = [
            {
                "agent_id": "agent-1",
                "agent_metadata": '{"model": "gpt-4"}',
            },
            {
                "agent_id": "agent-2",
                "agent_metadata": '{"model": "gpt-3.5"}',
            },
            {
                "agent_id": "agent-3",
                "agent_metadata": '{"model": "claude"}',
            },
        ]

        with patch.object(client, "list_agents", return_value=agents):
            results = client.query_by_capability({"model": "gpt-*"})

            assert len(results) == 2
            assert results[0]["agent_id"] == "agent-1"
            assert results[1]["agent_id"] == "agent-2"

    def test_query_by_capability_with_nested_keys(self) -> None:
        """Test querying agents with nested key filters."""
        client = AgentRegistryOrchestratorClient("http://localhost:9000")

        agents = [
            {
                "agent_id": "agent-1",
                "agent_metadata": '{"capabilities": {"llm": true, "vision": false}}',
            },
            {
                "agent_id": "agent-2",
                "agent_metadata": '{"capabilities": {"llm": false, "tool": true}}',
            },
        ]

        with patch.object(client, "list_agents", return_value=agents):
            results = client.query_by_capability({"capabilities.llm": True})

            assert len(results) == 1
            assert results[0]["agent_id"] == "agent-1"

    def test_get_active_agents_filters_by_heartbeat(self) -> None:
        """Test getting active agents filters by recent heartbeat."""
        client = AgentRegistryOrchestratorClient("http://localhost:9000")

        from datetime import datetime, timedelta

        now = datetime.utcnow()
        recent = now - timedelta(seconds=30)
        old = now - timedelta(seconds=120)

        agents = [
            {
                "agent_id": "agent-1",
                "last_heartbeat": recent.isoformat() + "Z",
            },
            {
                "agent_id": "agent-2",
                "last_heartbeat": old.isoformat() + "Z",
            },
        ]

        with patch.object(client, "list_agents", return_value=agents):
            results = client.get_active_agents(cutoff_seconds=60)

            assert len(results) == 1
            assert results[0]["agent_id"] == "agent-1"

    def test_value_matches_with_wildcard(self) -> None:
        """Test value matching with wildcard support."""
        client = AgentRegistryOrchestratorClient("http://localhost:9000")

        # Wildcard match
        assert client._value_matches("gpt-4", "gpt-*")
        assert client._value_matches("gpt-3.5-turbo", "gpt-*")

        # Non-matching
        assert not client._value_matches("claude", "gpt-*")
        assert not client._value_matches("gpt", "gpt-*")

    def test_value_matches_with_lists(self) -> None:
        """Test value matching with list values."""
        client = AgentRegistryOrchestratorClient("http://localhost:9000")

        # String in list
        assert client._value_matches("llm", ["llm", "tool", "vision"])

        # List contains string
        assert client._value_matches(["llm", "tool"], "llm")

        # List-to-list any match
        assert client._value_matches(["llm", "vision"], ["tool", "llm"])

    def test_matches_filters_with_all_criteria(self) -> None:
        """Test that all filter criteria must match."""
        client = AgentRegistryOrchestratorClient("http://localhost:9000")

        metadata = {
            "type": "llm",
            "model": "gpt-4",
            "capabilities": {"llm": True, "vision": False},
        }

        # All match
        assert client._matches_filters(
            metadata, {"type": "llm", "model": "gpt-4"}
        )

        # Partial match (should pass)
        assert client._matches_filters(metadata, {"type": "llm"})

        # No match (should fail)
        assert not client._matches_filters(metadata, {"type": "tool"})

    def test_close(self) -> None:
        """Test closing the client releases resources."""
        client = AgentRegistryOrchestratorClient("http://localhost:9000")
        mock_close = Mock()

        client._client.close = mock_close
        client.close()

        mock_close.assert_called_once()

    def test_context_manager(self) -> None:
        """Test using client as context manager."""
        with AgentRegistryOrchestratorClient("http://localhost:9000") as client:
            assert client is not None
            assert client.registry_url == "http://localhost:9000"
            # Client should be closed on exit


class TestCreateOrchestratorClient:
    """Tests for create_orchestrator_client factory function."""

    def test_factory_creates_client(self) -> None:
        """Test factory function creates client instance."""
        client = create_orchestrator_client("http://localhost:9000")

        assert isinstance(client, AgentRegistryOrchestratorClient)
        assert client.registry_url == "http://localhost:9000"

    def test_factory_with_all_params(self) -> None:
        """Test factory function with all parameters."""
        client = create_orchestrator_client(
            registry_url="http://localhost:9000",
            auth_token="test-token",
            timeout=30.0,
        )

        assert isinstance(client, AgentRegistryOrchestratorClient)
        assert client.auth_token == "test-token"
        assert client.timeout == 30.0
