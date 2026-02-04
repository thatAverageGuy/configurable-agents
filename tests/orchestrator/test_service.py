"""Tests for orchestrator service.

Tests the OrchestratorService which coordinates agent lifecycle,
connection management, and workflow execution.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from configurable_agents.orchestrator.models import AgentConnection, OrchestratorConfig
from configurable_agents.orchestrator.service import (
    OrchestratorService,
    create_orchestrator_service,
)


@pytest.fixture
def mock_registry_client():
    """Create a mock registry client."""
    client = Mock()
    client.list_agents = Mock(return_value=[])
    client.get_agent = Mock(return_value=None)
    return client


class TestOrchestratorService:
    """Tests for OrchestratorService."""

    def test_init_with_config(self, mock_registry_client) -> None:
        """Test service initialization with custom config."""
        config = OrchestratorConfig(
            orchestrator_id="test-orchestrator",
            max_parallel_executions=10,
        )

        service = OrchestratorService(mock_registry_client, config=config)

        assert service.config.orchestrator_id == "test-orchestrator"
        assert service.config.max_parallel_executions == 10

    def test_discover_agents(self, mock_registry_client) -> None:
        """Test discovering agents from registry."""
        mock_agents = [
            {
                "agent_id": "agent-1",
                "agent_name": "Agent 1",
                "host": "localhost",
                "port": 8001,
                "is_alive": True,
            },
            {
                "agent_id": "agent-2",
                "agent_name": "Agent 2",
                "host": "localhost",
                "port": 8002,
                "is_alive": True,
            },
        ]

        mock_registry_client.list_agents.return_value = mock_agents

        service = OrchestratorService(mock_registry_client)
        agents = service.discover_agents()

        assert len(agents) == 2
        assert agents[0]["agent_id"] == "agent-1"
        mock_registry_client.list_agents.assert_called_once()

    def test_discover_agents_filters_dead(self, mock_registry_client) -> None:
        """Test that dead agents can be excluded."""
        all_mock_agents = [
            {"agent_id": "agent-1", "is_alive": True, "host": "localhost", "port": 8001},
            {"agent_id": "agent-2", "is_alive": False, "host": "localhost", "port": 8002},
        ]

        # Set up mock to filter based on include_dead parameter
        def mock_list_agents(include_dead=False):
            if include_dead:
                return all_mock_agents
            else:
                return [a for a in all_mock_agents if a.get("is_alive", True)]

        mock_registry_client.list_agents.side_effect = mock_list_agents

        service = OrchestratorService(mock_registry_client)

        # Include all agents
        all_agents = service.discover_agents(include_dead=True)
        assert len(all_agents) == 2

        # Exclude dead agents - service.discover_agents filters by is_alive
        alive_agents = service.discover_agents(include_dead=False)
        # Only agent-1 should be returned since it's the only one with is_alive=True
        assert len(alive_agents) == 1
        assert alive_agents[0]["agent_id"] == "agent-1"

    def test_register_agent(self, mock_registry_client) -> None:
        """Test registering an agent connection."""
        mock_agent_info = {
            "agent_id": "agent-1",
            "agent_name": "Agent 1",
            "host": "localhost",
            "port": 8001,
            "is_alive": True,
        }

        mock_registry_client.get_agent.return_value = mock_agent_info

        service = OrchestratorService(mock_registry_client)
        connection = service.register_agent("agent-1")

        assert connection.agent_id == "agent-1"
        assert connection.status == "connected"
        assert "agent-1" in service.agent_connections

    def test_register_agent_not_found(self, mock_registry_client) -> None:
        """Test error when registering non-existent agent."""
        mock_registry_client.get_agent.return_value = None

        service = OrchestratorService(mock_registry_client)

        with pytest.raises(ValueError, match="not found in registry"):
            service.register_agent("nonexistent")

    def test_register_agent_custom_params(self, mock_registry_client) -> None:
        """Test registering agent with custom connection parameters."""
        mock_agent_info = {
            "agent_id": "agent-1",
            "agent_name": "Agent 1",
            "host": "remote-host",
            "port": 9000,
        }

        mock_registry_client.get_agent.return_value = mock_agent_info

        service = OrchestratorService(mock_registry_client)
        connection = service.register_agent(
            "agent-1",
            connection_params={"host": "custom-host", "port": 8888},
        )

        # Should use custom params
        assert connection.host == "custom-host"
        assert connection.port == 8888

    def test_deregister_agent(self, mock_registry_client) -> None:
        """Test deregistering an agent."""
        mock_agent_info = {
            "agent_id": "agent-1",
            "agent_name": "Agent 1",
            "host": "localhost",
            "port": 8001,
            "is_alive": True,
        }

        mock_registry_client.get_agent.return_value = mock_agent_info

        service = OrchestratorService(mock_registry_client)
        service.register_agent("agent-1")

        # Deregister
        result = service.deregister_agent("agent-1")

        assert result is True
        assert "agent-1" not in service.agent_connections

    def test_deregister_nonexistent_agent(self, mock_registry_client) -> None:
        """Test deregistering agent that's not connected."""
        service = OrchestratorService(mock_registry_client)

        result = service.deregister_agent("nonexistent")

        assert result is False

    def test_get_agent_connection(self, mock_registry_client) -> None:
        """Test getting agent connection details."""
        mock_agent_info = {
            "agent_id": "agent-1",
            "agent_name": "Agent 1",
            "host": "localhost",
            "port": 8001,
            "is_alive": True,
        }

        mock_registry_client.get_agent.return_value = mock_agent_info

        service = OrchestratorService(mock_registry_client)
        service.register_agent("agent-1")

        connection = service.get_agent_connection("agent-1")

        assert connection is not None
        assert connection.agent_id == "agent-1"

    def test_list_connections(self, mock_registry_client) -> None:
        """Test listing all active connections."""
        mock_agent_info = {
            "agent_id": "agent-1",
            "agent_name": "Agent 1",
            "host": "localhost",
            "port": 8001,
            "is_alive": True,
        }

        mock_registry_client.get_agent.return_value = mock_agent_info

        service = OrchestratorService(mock_registry_client)
        service.register_agent("agent-1")
        service.register_agent("agent-2")

        connections = service.list_connections()

        assert len(connections) == 2

    def test_check_agent_health_healthy(self, mock_registry_client) -> None:
        """Test health check for healthy agent."""
        mock_agent_info = {
            "agent_id": "agent-1",
            "agent_name": "Agent 1",
            "is_alive": True,
            "host": "localhost",
            "port": 8001,
        }

        mock_registry_client.get_agent.return_value = mock_agent_info

        service = OrchestratorService(mock_registry_client)
        service.register_agent("agent-1")

        is_healthy = service.check_agent_health("agent-1")

        assert is_healthy is True

    def test_check_agent_health_not_in_registry(self, mock_registry_client) -> None:
        """Test health check when agent removed from registry."""
        mock_agent_info = {
            "agent_id": "agent-1",
            "agent_name": "Agent 1",
            "is_alive": True,
            "host": "localhost",
            "port": 8001,
        }

        mock_registry_client.get_agent.return_value = mock_agent_info

        service = OrchestratorService(mock_registry_client)
        service.register_agent("agent-1")

        # Agent removed from registry
        mock_registry_client.get_agent.return_value = None

        is_healthy = service.check_agent_health("agent-1")

        assert is_healthy is False

    def test_check_agent_health_heartbeat_expired(self, mock_registry_client) -> None:
        """Test health check when agent heartbeat expired."""
        mock_agent_info = {
            "agent_id": "agent-1",
            "agent_name": "Agent 1",
            "is_alive": False,  # Heartbeat expired
            "host": "localhost",
            "port": 8001,
        }

        mock_registry_client.get_agent.return_value = mock_agent_info

        service = OrchestratorService(mock_registry_client)
        service.register_agent("agent-1")

        is_healthy = service.check_agent_health("agent-1")

        assert is_healthy is False

    def test_get_unhealthy_agents(self, mock_registry_client) -> None:
        """Test getting list of unhealthy agents."""
        mock_agent_info_healthy = {
            "agent_id": "agent-1",
            "agent_name": "Agent 1",
            "is_alive": True,
            "host": "localhost",
            "port": 8001,
        }

        mock_agent_info_unhealthy = {
            "agent_id": "agent-2",
            "agent_name": "Agent 2",
            "is_alive": False,
            "host": "localhost",
            "port": 8002,
        }

        mock_registry_client.get_agent.side_effect = lambda aid: (
            mock_agent_info_healthy if aid == "agent-1" else mock_agent_info_unhealthy
        )

        service = OrchestratorService(mock_registry_client)
        service.register_agent("agent-1")
        service.register_agent("agent-2")

        unhealthy = service.get_unhealthy_agents()

        assert len(unhealthy) == 1
        assert unhealthy[0] == "agent-2"

    def test_execute_on_agent(self, mock_registry_client) -> None:
        """Test executing workflow on specific agent."""
        mock_agent_info = {
            "agent_id": "agent-1",
            "agent_name": "Agent 1",
            "is_alive": True,
            "host": "localhost",
            "port": 8001,
        }

        mock_registry_client.get_agent.return_value = mock_agent_info

        service = OrchestratorService(mock_registry_client)
        service.register_agent("agent-1")

        workflow_config = {"name": "test-workflow"}
        inputs = {"input": "value"}

        result = service.execute_on_agent("agent-1", workflow_config, inputs)

        assert result["agent_id"] == "agent-1"
        assert result["status"] == "completed"

    def test_execute_on_agent_not_connected(self, mock_registry_client) -> None:
        """Test executing workflow on agent that's not connected."""
        service = OrchestratorService(mock_registry_client)

        with pytest.raises(ValueError, match="No connection"):
            service.execute_on_agent("agent-1", {}, {})

    def test_execute_on_agent_unhealthy(self, mock_registry_client) -> None:
        """Test executing workflow on unhealthy agent."""
        mock_agent_info = {
            "agent_id": "agent-1",
            "agent_name": "Agent 1",
            "is_alive": False,
            "host": "localhost",
            "port": 8001,
        }

        mock_registry_client.get_agent.return_value = mock_agent_info

        service = OrchestratorService(mock_registry_client)
        service.register_agent("agent-1")

        with pytest.raises(RuntimeError, match="is unhealthy"):
            service.execute_on_agent("agent-1", {}, {})

    def test_get_status(self, mock_registry_client) -> None:
        """Test getting orchestrator status."""
        mock_agent_info = {
            "agent_id": "agent-1",
            "agent_name": "Agent 1",
            "is_alive": True,
            "host": "localhost",
            "port": 8001,
        }

        mock_registry_client.get_agent.return_value = mock_agent_info
        mock_registry_client.list_agents.return_value = [mock_agent_info]

        config = OrchestratorConfig(orchestrator_id="test-orchestrator")
        service = OrchestratorService(mock_registry_client, config=config)
        service.register_agent("agent-1")

        status = service.get_status()

        assert status["orchestrator_id"] == "test-orchestrator"
        assert status["total_connections"] == 1
        assert status["connected_agents"] == 1
        assert status["unhealthy_agents"] == []
        assert status["discovered_agents"] == 1


class TestCreateOrchestratorService:
    """Tests for create_orchestrator_service factory function."""

    @patch("configurable_agents.orchestrator.client.create_orchestrator_client")
    def test_factory_creates_service(self, mock_create_client) -> None:
        """Test factory function creates service instance."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        service = create_orchestrator_service("http://localhost:9000")

        assert isinstance(service, OrchestratorService)
        mock_create_client.assert_called_once_with("http://localhost:9000")

    @patch("configurable_agents.orchestrator.client.create_orchestrator_client")
    def test_factory_with_config(self, mock_create_client) -> None:
        """Test factory function with custom config."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        config = OrchestratorConfig(orchestrator_id="custom")
        service = create_orchestrator_service("http://localhost:9000", config=config)

        assert isinstance(service, OrchestratorService)
        assert service.config.orchestrator_id == "custom"
