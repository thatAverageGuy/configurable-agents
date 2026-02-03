"""Storage abstraction layer for configurable agents.

Provides pluggable storage backend with Repository Pattern for workflow
run persistence, execution state tracking, and agent registry.

Public API:
    - AbstractWorkflowRunRepository: Interface for workflow run storage
    - AbstractExecutionStateRepository: Interface for execution state storage
    - AgentRegistryRepository: Interface for agent registry storage
    - WorkflowRunRecord: ORM model for workflow runs
    - ExecutionStateRecord: ORM model for execution states
    - AgentRecord: ORM model for agent registry
    - Base: SQLAlchemy DeclarativeBase for all models
    - create_storage_backend: Factory function for creating repositories

Example:
    >>> from configurable_agents.storage import create_storage_backend
    >>> runs_repo, states_repo, agents_repo = create_storage_backend()
    >>> # Use repositories for persistence operations
"""

from configurable_agents.storage.base import (
    AbstractExecutionStateRepository,
    AbstractWorkflowRunRepository,
    AgentRegistryRepository,
)
from configurable_agents.storage.factory import create_storage_backend
from configurable_agents.storage.models import (
    AgentRecord,
    Base,
    ExecutionStateRecord,
    WorkflowRunRecord,
)

__all__ = [
    # Abstract interfaces
    "AbstractWorkflowRunRepository",
    "AbstractExecutionStateRepository",
    "AgentRegistryRepository",
    # ORM models
    "Base",
    "WorkflowRunRecord",
    "ExecutionStateRecord",
    "AgentRecord",
    # Factory
    "create_storage_backend",
]
