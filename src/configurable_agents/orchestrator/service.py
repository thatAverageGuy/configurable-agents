"""Orchestrator service for agent lifecycle management.

This module provides the core orchestrator service that discovers,
connects to, and coordinates agents registered in the agent registry.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from configurable_agents.orchestrator.client import AgentRegistryOrchestratorClient
from configurable_agents.orchestrator.models import (
    AgentConnection,
    OrchestratorConfig,
)
logger = logging.getLogger(__name__)


class OrchestratorService:
    """Service for orchestrating agent lifecycle and workflow execution.

    Manages the discovery, connection, and coordination of agents.
    Handles connection pooling, health checking, and workflow execution
    on specific agents.

    Attributes:
        registry_client: Client for communicating with the agent registry
        config: Orchestrator configuration
        agent_connections: Active connections to agents
        storage: Optional storage backend for persistence
    """

    def __init__(
        self,
        registry_client: AgentRegistryOrchestratorClient,
        config: Optional[OrchestratorConfig] = None,
        storage: Optional[Any] = None,
    ):
        """Initialize the orchestrator service.

        Args:
            registry_client: Client for registry communication
            config: Orchestrator configuration (optional, uses defaults)
            storage: Optional storage backend for persistence
        """
        self.registry_client = registry_client
        self.config = config or OrchestratorConfig()
        self.storage = storage

        # Track active agent connections
        self.agent_connections: Dict[str, AgentConnection] = {}

    def discover_agents(self, include_dead: bool = False) -> List[Dict[str, Any]]:
        """Discover agents from the registry.

        Queries the registry for all available agents, optionally filtering
        out dead/expired agents.

        Args:
            include_dead: If False, only return alive agents

        Returns:
            List of agent dictionaries from registry

        Example:
            >>> service = OrchestratorService(client)
            >>> agents = service.discover_agents()
            >>> print(f"Found {len(agents)} agents")
        """
        try:
            agents = self.registry_client.list_agents(include_dead=include_dead)
            logger.info(f"Discovered {len(agents)} agents from registry")
            return agents
        except Exception as e:
            logger.error(f"Failed to discover agents: {e}")
            return []

    def register_agent(
        self,
        agent_id: str,
        connection_params: Optional[Dict[str, Any]] = None,
    ) -> AgentConnection:
        """Register and initiate connection to an agent.

        Creates a connection entry for tracking the agent. Connection
        parameters include host, port, and authentication details.

        Args:
            agent_id: Unique identifier for the agent
            connection_params: Optional connection parameters (host, port, auth)

        Returns:
            AgentConnection instance

        Raises:
            ValueError: If agent_id not found in registry
        """
        # Check if agent exists in registry
        agent_info = self.registry_client.get_agent(agent_id)
        if agent_info is None:
            raise ValueError(f"Agent {agent_id} not found in registry")

        # Extract connection params from agent info if not provided
        if connection_params is None:
            connection_params = {
                "host": agent_info["host"],
                "port": agent_info["port"],
            }

        # Create connection record
        connection = AgentConnection(
            agent_id=agent_id,
            agent_name=agent_info["agent_name"],
            host=connection_params.get("host", agent_info["host"]),
            port=connection_params.get("port", agent_info["port"]),
            connected_at=datetime.utcnow(),
            status="connected",
            metadata=agent_info.get("agent_metadata"),
        )

        # Track connection
        self.agent_connections[agent_id] = connection

        logger.info(f"Registered connection to agent {agent_id}")
        return connection

    def deregister_agent(self, agent_id: str) -> bool:
        """Remove agent connection and clean up resources.

        Args:
            agent_id: Unique identifier for the agent

        Returns:
            True if connection was removed, False if not found
        """
        if agent_id in self.agent_connections:
            connection = self.agent_connections[agent_id]
            connection.status = "disconnected"
            connection.disconnected_at = datetime.utcnow()

            del self.agent_connections[agent_id]

            logger.info(f"Deregistered agent {agent_id}")
            return True

        return False

    def get_agent_connection(self, agent_id: str) -> Optional[AgentConnection]:
        """Get connection details for a specific agent.

        Args:
            agent_id: Unique identifier for the agent

        Returns:
            AgentConnection if connected, None otherwise
        """
        return self.agent_connections.get(agent_id)

    def list_connections(self) -> List[AgentConnection]:
        """List all active agent connections.

        Returns:
            List of AgentConnection instances
        """
        return list(self.agent_connections.values())

    def check_agent_health(self, agent_id: str) -> bool:
        """Check if an agent connection is healthy.

        Verifies that the agent is still alive by checking registry
        heartbeat status.

        Args:
            agent_id: Unique identifier for the agent

        Returns:
            True if agent is healthy, False otherwise
        """
        connection = self.agent_connections.get(agent_id)
        if connection is None:
            return False

        # Check if agent is still alive in registry
        try:
            agent_info = self.registry_client.get_agent(agent_id)
            if agent_info is None:
                logger.warning(f"Agent {agent_id} no longer in registry")
                return False

            # Check is_alive field from registry
            if not agent_info.get("is_alive", False):
                logger.warning(f"Agent {agent_id} heartbeat expired")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to check agent {agent_id} health: {e}")
            return False

    def get_unhealthy_agents(self) -> List[str]:
        """Get list of unhealthy agent connections.

        Checks all connected agents and returns those that are
        no longer healthy (heartbeat expired or removed from registry).

        Returns:
            List of agent_ids that are unhealthy
        """
        unhealthy = []

        for agent_id in self.agent_connections:
            if not self.check_agent_health(agent_id):
                unhealthy.append(agent_id)

        return unhealthy

    def execute_on_agent(
        self,
        agent_id: str,
        workflow_config: Dict[str, Any],
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a workflow on a specific agent.

        Sends workflow execution request to the specified agent.
        This is a placeholder for the actual execution logic.

        Args:
            agent_id: Unique identifier for the agent
            workflow_config: Workflow configuration
            inputs: Input values for the workflow

        Returns:
            Execution results

        Raises:
            ValueError: If agent not connected
            RuntimeError: If execution fails

        Note:
            This is a placeholder implementation. In production, this would
            make HTTP/gRPC calls to the agent's execution endpoint.
        """
        connection = self.agent_connections.get(agent_id)
        if connection is None:
            raise ValueError(f"No connection to agent {agent_id}")

        # Check agent health before execution
        if not self.check_agent_health(agent_id):
            raise RuntimeError(f"Agent {agent_id} is unhealthy")

        # Placeholder: In production, this would call the agent's execution endpoint
        logger.info(f"Executing workflow on agent {agent_id}")

        result = {
            "agent_id": agent_id,
            "status": "completed",
            "message": "Workflow execution placeholder",
            "timestamp": datetime.utcnow().isoformat(),
        }

        return result

    def execute_parallel(
        self,
        agent_ids: List[str],
        workflow_config: Dict[str, Any],
        inputs: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Execute workflow on multiple agents in parallel.

        Executes the same workflow on multiple agents concurrently.
        Returns results from all successful executions.

        Args:
            agent_ids: List of agent identifiers to execute on
            workflow_config: Workflow configuration
            inputs: Input values for the workflow

        Returns:
            List of execution results, one per agent

        Example:
            >>> results = service.execute_parallel(
            ...     ["agent-1", "agent-2", "agent-3"],
            ...     workflow_config,
            ...     inputs
            ... )
            >>> for result in results:
            ...     print(f"Agent {result['agent_id']}: {result['status']}")
        """
        import concurrent.futures

        results = []

        def execute_on_single(agent_id: str) -> Dict[str, Any]:
            """Execute workflow on a single agent."""
            try:
                return self.execute_on_agent(agent_id, workflow_config, inputs)
            except Exception as e:
                logger.error(f"Execution on agent {agent_id} failed: {e}")
                return {
                    "agent_id": agent_id,
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }

        # Execute in parallel with thread pool
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.max_parallel_executions
        ) as executor:
            futures = {
                executor.submit(execute_on_single, agent_id): agent_id
                for agent_id in agent_ids
            }

            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=self.config.execution_timeout)
                    results.append(result)
                except concurrent.futures.TimeoutError:
                    agent_id = futures[future]
                    logger.warning(f"Execution on agent {agent_id} timed out")
                    results.append({
                        "agent_id": agent_id,
                        "status": "timeout",
                        "error": "Execution timeout",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                except Exception as e:
                    agent_id = futures[future]
                    logger.error(f"Execution on agent {agent_id} failed: {e}")
                    results.append({
                        "agent_id": agent_id,
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    })

        return results

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status and connection info.

        Returns:
            Status dictionary with connection counts and health info

        Example:
            >>> status = service.get_status()
            >>> print(f"Connected: {status['connected_agents']}")
            >>> print(f"Unhealthy: {status['unhealthy_agents']}")
        """
        unhealthy_agents = self.get_unhealthy_agents()

        return {
            "orchestrator_id": self.config.orchestrator_id,
            "total_connections": len(self.agent_connections),
            "connected_agents": len(self.agent_connections) - len(unhealthy_agents),
            "unhealthy_agents": unhealthy_agents,
            "discovered_agents": len(self.discover_agents()),
            "timestamp": datetime.utcnow().isoformat(),
        }


def create_orchestrator_service(
    registry_url: str,
    config: Optional[OrchestratorConfig] = None,
) -> OrchestratorService:
    """Factory function to create an orchestrator service.

    Args:
        registry_url: URL of the agent registry server
        config: Optional orchestrator configuration

    Returns:
        Configured OrchestratorService instance

    Example:
        >>> from configurable_agents.orchestrator import create_orchestrator_service
        >>> service = create_orchestrator_service("http://localhost:9000")
        >>> agents = service.discover_agents()
        >>> status = service.get_status()
    """
    from configurable_agents.orchestrator.client import create_orchestrator_client

    client = create_orchestrator_client(registry_url)
    return OrchestratorService(client, config)
