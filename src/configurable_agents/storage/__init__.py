"""Storage abstraction layer for configurable agents.

Provides pluggable storage backend with Repository Pattern for workflow
run persistence and execution state tracking.

Public API:
    - AbstractWorkflowRunRepository: Interface for workflow run storage
    - AbstractExecutionStateRepository: Interface for execution state storage
    - WorkflowRunRecord: ORM model for workflow runs
    - ExecutionStateRecord: ORM model for execution states
    - Base: SQLAlchemy DeclarativeBase for all models
    - create_storage_backend: Factory function for creating repositories

Example:
    >>> from configurable_agents.storage import create_storage_backend
    >>> runs_repo, states_repo = create_storage_backend()
    >>> # Use repositories for persistence operations
"""

from configurable_agents.storage.base import (
    AbstractExecutionStateRepository,
    AbstractWorkflowRunRepository,
)
from configurable_agents.storage.factory import create_storage_backend
from configurable_agents.storage.models import (
    Base,
    ExecutionStateRecord,
    WorkflowRunRecord,
)

__all__ = [
    # Abstract interfaces
    "AbstractWorkflowRunRepository",
    "AbstractExecutionStateRepository",
    # ORM models
    "Base",
    "WorkflowRunRecord",
    "ExecutionStateRecord",
    # Factory
    "create_storage_backend",
]
