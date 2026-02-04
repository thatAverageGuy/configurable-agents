"""Data models for orchestrator service.

Defines configuration and connection tracking models for the
orchestrator service that coordinates agent lifecycle.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator service.

    Attributes:
        orchestrator_id: Unique identifier for this orchestrator
        max_parallel_executions: Maximum concurrent agent executions
        execution_timeout: Timeout for workflow execution (seconds)
        heartbeat_interval: Seconds between health checks
        connection_retry_attempts: Number of retry attempts for connections
        connection_retry_delay: Delay between retry attempts (seconds)
    """

    orchestrator_id: str = "orchestrator-1"
    max_parallel_executions: int = 5
    execution_timeout: float = 300.0  # 5 minutes
    heartbeat_interval: int = 30  # 30 seconds
    connection_retry_attempts: int = 3
    connection_retry_delay: float = 1.0  # 1 second


@dataclass
class AgentConnection:
    """Tracks a connection to an agent.

    Represents an active connection from the orchestrator to an agent,
    including connection details and health status.

    Attributes:
        agent_id: Unique identifier for the agent
        agent_name: Human-readable name for the agent
        host: Host address where the agent is running
        port: Port number where the agent is listening
        connected_at: Timestamp when connection was established
        disconnected_at: Timestamp when connection was closed (optional)
        status: Connection status (connected, disconnected, error)
        last_health_check: Timestamp of last health check
        metadata: Optional agent metadata from registry
        error_message: Error message if status is 'error'
    """

    agent_id: str
    agent_name: str
    host: str
    port: int
    connected_at: datetime = field(default_factory=datetime.utcnow)
    disconnected_at: Optional[datetime] = None
    status: str = "connected"  # connected, disconnected, error
    last_health_check: Optional[datetime] = None
    metadata: Optional[str] = None
    error_message: Optional[str] = None

    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self.status == "connected"

    def is_healthy(self) -> bool:
        """Check if connection is healthy (connected and no errors)."""
        return self.status == "connected" and self.error_message is None

    def to_dict(self) -> Dict[str, Any]:
        """Convert connection to dictionary representation.

        Returns:
            Dictionary with connection data
        """
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "host": self.host,
            "port": self.port,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "disconnected_at": self.disconnected_at.isoformat() if self.disconnected_at else None,
            "status": self.status,
            "last_health_check": (
                self.last_health_check.isoformat() if self.last_health_check else None
            ),
            "metadata": self.metadata,
            "error_message": self.error_message,
            "is_connected": self.is_connected(),
            "is_healthy": self.is_healthy(),
        }
