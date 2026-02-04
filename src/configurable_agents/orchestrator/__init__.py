"""Orchestrator components for agent coordination.

This module provides client libraries and services for orchestrators to discover,
communicate with, and coordinate agents registered in the agent registry.

Public API:
    - AgentRegistryOrchestratorClient: Client for registry communication
    - OrchestratorService: Service for agent lifecycle management
    - OrchestratorConfig: Configuration for orchestrator service
    - AgentConnection: Connection tracking model
    - create_orchestrator_client: Factory function for creating clients
    - create_orchestrator_service: Factory function for creating service

Example:
    >>> from configurable_agents.orchestrator import create_orchestrator_service
    >>> service = create_orchestrator_service("http://localhost:9000")
    >>> agents = service.discover_agents()
    >>> service.register_agent("agent-1", {"host": "localhost", "port": 8000})
    >>> results = service.execute_parallel(["agent-1", "agent-2"], workflow, inputs)
    >>> status = service.get_status()
"""

from configurable_agents.orchestrator.client import (
    AgentRegistryOrchestratorClient,
    create_orchestrator_client,
)
from configurable_agents.orchestrator.models import (
    AgentConnection,
    OrchestratorConfig,
)
from configurable_agents.orchestrator.service import (
    OrchestratorService,
    create_orchestrator_service,
)

__all__ = [
    "AgentRegistryOrchestratorClient",
    "OrchestratorService",
    "OrchestratorConfig",
    "AgentConnection",
    "create_orchestrator_client",
    "create_orchestrator_service",
]
