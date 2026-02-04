"""Orchestrator client for agent registry communication.

This module provides the client library that orchestrators use to discover,
query, and manage agents registered in the agent registry.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class AgentRegistryOrchestratorClient:
    """Client for orchestrators to communicate with the agent registry.

    Provides methods for discovering agents, querying by capabilities,
    and managing agent connections.

    Attributes:
        registry_url: Base URL of the registry server (e.g., "http://localhost:9000")
        auth_token: Optional authentication token for secured registries
        timeout: HTTP request timeout in seconds
    """

    def __init__(
        self,
        registry_url: str,
        auth_token: Optional[str] = None,
        timeout: float = 10.0,
    ):
        """Initialize the orchestrator registry client.

        Args:
            registry_url: Base URL of the registry server
            auth_token: Optional authentication token for secured registries
            timeout: HTTP request timeout in seconds (default: 10)
        """
        self.registry_url = registry_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout

        # HTTP client with connection pooling
        self._client = httpx.Client(timeout=timeout)

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for registry requests.

        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ConfigurableAgents-Orchestrator/1.0",
        }

        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        return headers

    def list_agents(
        self, include_dead: bool = False, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """List all agents from the registry.

        Args:
            include_dead: If False, only return active (non-expired) agents
            filters: Optional metadata filters (e.g., {"capability": "llm", "model": "gpt-*"})

        Returns:
            List of agent dictionaries with keys:
            - agent_id: Unique agent identifier
            - agent_name: Human-readable name
            - host: Agent host address
            - port: Agent port number
            - last_heartbeat: Last heartbeat timestamp
            - ttl_seconds: Time-to-live in seconds
            - agent_metadata: JSON metadata blob
            - registered_at: Registration timestamp

        Raises:
            httpx.HTTPError: If registry request fails
        """
        params = {}
        if include_dead:
            params["include_dead"] = "true"

        url = f"{self.registry_url}/agents"
        response = self._client.get(
            url,
            params=params,
            headers=self._get_headers(),
        )
        response.raise_for_status()

        agents = response.json()

        # Apply client-side filtering if requested
        if filters:
            agents = self._filter_by_metadata(agents, filters)

        return agents

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific agent.

        Args:
            agent_id: Unique agent identifier

        Returns:
            Agent dictionary if found, None otherwise

        Raises:
            httpx.HTTPError: If registry request fails
        """
        url = f"{self.registry_url}/agents/{agent_id}"
        try:
            response = self._client.get(
                url,
                headers=self._get_headers(),
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def query_by_capability(self, metadata_filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query agents by metadata/capabilities.

        Allows filtering agents by their metadata JSON blob using
        key-value matching with wildcard support.

        Args:
            metadata_filters: Dictionary of metadata filters
                - String values support "*" wildcard (e.g., {"model": "gpt-*"})
                - Nested keys use dot notation (e.g., {"capabilities.llm": true})
                - Multiple filters are AND-ed together

        Returns:
            List of matching agent dictionaries

        Example:
            >>> client = AgentRegistryOrchestratorClient("http://localhost:9000")
            >>> # Find all LLM agents
            >>> llm_agents = client.query_by_capability({"type": "llm"})
            >>> # Find specific model family
            >>> gpt_agents = client.query_by_capability({"model": "gpt-*"})
            >>> # Multiple filters
            >>> agents = client.query_by_capability({
            ...     "capabilities": ["llm", "vision"],
            ...     "provider": "openai"
            ... })
        """
        all_agents = self.list_agents(include_dead=False)
        return self._filter_by_metadata(all_agents, metadata_filters)

    def get_active_agents(self, cutoff_seconds: int = 60) -> List[Dict[str, Any]]:
        """Get only active (recently heartbeating) agents.

        An agent is considered active if its last heartbeat was within
        the specified cutoff period.

        Args:
            cutoff_seconds: Seconds since last heartbeat (default: 60)

        Returns:
            List of active agent dictionaries

        Example:
            >>> client = AgentRegistryOrchestratorClient("http://localhost:9000")
            >>> # Get agents that heartbeat within last 30 seconds
            >>> active = client.get_active_agents(cutoff_seconds=30)
        """
        all_agents = self.list_agents(include_dead=True)

        # Use UTC now without timezone info for comparison
        cutoff_time = datetime.utcnow() - timedelta(seconds=cutoff_seconds)

        active_agents = []
        for agent in all_agents:
            # Parse last_heartbeat timestamp
            last_heartbeat_str = agent.get("last_heartbeat")
            if not last_heartbeat_str:
                continue

            try:
                # Parse ISO format timestamp
                last_heartbeat = datetime.fromisoformat(last_heartbeat_str.replace("Z", "+00:00"))

                # Convert to UTC naive for comparison
                if last_heartbeat.tzinfo is not None:
                    last_heartbeat = last_heartbeat.replace(tzinfo=None)

                if last_heartbeat >= cutoff_time:
                    active_agents.append(agent)
            except (ValueError, AttributeError):
                logger.warning(f"Invalid timestamp for agent {agent.get('agent_id')}")
                continue

        return active_agents

    def _filter_by_metadata(
        self, agents: List[Dict[str, Any]], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter agents by metadata criteria.

        Args:
            agents: List of agent dictionaries
            filters: Metadata filter criteria

        Returns:
            Filtered list of agents matching all criteria
        """
        filtered = []

        for agent in agents:
            # Parse agent_metadata JSON
            metadata_str = agent.get("agent_metadata")
            if not metadata_str:
                continue

            try:
                import json

                metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str

                # Check if agent matches all filters
                if self._matches_filters(metadata, filters):
                    filtered.append(agent)

            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse metadata for agent {agent.get('agent_id')}")
                continue

        return filtered

    def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if metadata matches all filter criteria.

        Args:
            metadata: Agent metadata dictionary
            filters: Filter criteria

        Returns:
            True if metadata matches all filters, False otherwise
        """
        for key, value in filters.items():
            # Support nested keys with dot notation
            metadata_value = metadata
            for key_part in key.split("."):
                if isinstance(metadata_value, dict):
                    metadata_value = metadata_value.get(key_part)
                else:
                    metadata_value = None
                    break

            # Check if value matches (with wildcard support for strings)
            if not self._value_matches(metadata_value, value):
                return False

        return True

    def _value_matches(self, actual: Any, expected: Any) -> bool:
        """Check if actual value matches expected value (with wildcard support).

        Args:
            actual: The actual value from metadata
            expected: The expected filter value

        Returns:
            True if values match, False otherwise
        """
        # Handle wildcard matching for strings
        if isinstance(expected, str) and isinstance(actual, str):
            if "*" in expected:
                import fnmatch

                return fnmatch.fnmatch(actual, expected)

        # Handle list matching (actual contains expected)
        if isinstance(expected, list) and isinstance(actual, str):
            return actual in expected

        # Handle list matching (actual list contains expected)
        if isinstance(expected, str) and isinstance(actual, list):
            return expected in actual

        # Handle list-to-list matching (any match)
        if isinstance(expected, list) and isinstance(actual, list):
            return any(item in actual for item in expected)

        # Direct comparison
        return actual == expected

    def close(self):
        """Close the HTTP client and release resources.

        Should be called when the client is no longer needed.
        """
        self._client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def create_orchestrator_client(
    registry_url: str,
    auth_token: Optional[str] = None,
    timeout: float = 10.0,
) -> AgentRegistryOrchestratorClient:
    """Factory function to create an orchestrator registry client.

    Args:
        registry_url: Base URL of the registry server
        auth_token: Optional authentication token for secured registries
        timeout: HTTP request timeout in seconds (default: 10)

    Returns:
        Configured AgentRegistryOrchestratorClient instance

    Example:
        >>> from configurable_agents.orchestrator import create_orchestrator_client
        >>> client = create_orchestrator_client("http://localhost:9000")
        >>> agents = client.list_agents()
        >>> client.close()
    """
    return AgentRegistryOrchestratorClient(
        registry_url=registry_url,
        auth_token=auth_token,
        timeout=timeout,
    )
