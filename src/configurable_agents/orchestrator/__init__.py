"""Orchestrator components for agent coordination.

This module provides client libraries for orchestrators to discover,
communicate with, and coordinate agents registered in the agent registry.

Public API:
    - AgentRegistryOrchestratorClient: Client for registry communication
    - create_orchestrator_client: Factory function for creating clients

Example:
    >>> from configurable_agents.orchestrator import create_orchestrator_client
    >>> client = create_orchestrator_client("http://localhost:9000")
    >>> agents = client.list_agents()
    >>> active = client.get_active_agents(cutoff_seconds=30)
    >>> gpt_agents = client.query_by_capability({"model": "gpt-*"})
    >>> client.close()
"""

from configurable_agents.orchestrator.client import (
    AgentRegistryOrchestratorClient,
    create_orchestrator_client,
)

__all__ = [
    "AgentRegistryOrchestratorClient",
    "create_orchestrator_client",
]
