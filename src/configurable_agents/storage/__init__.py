"""Storage abstraction layer for configurable agents.

Provides pluggable storage backend with Repository Pattern for workflow
run persistence, execution state tracking, agent registry, chat sessions,
and agent memory.

Public API:
    - AbstractWorkflowRunRepository: Interface for workflow run storage
    - AbstractExecutionStateRepository: Interface for execution state storage
    - AgentRegistryRepository: Interface for agent registry storage
    - ChatSessionRepository: Interface for chat session storage
    - MemoryRepository: Interface for agent memory storage
    - WorkflowRunRecord: ORM model for workflow runs
    - ExecutionStateRecord: ORM model for execution states
    - AgentRecord: ORM model for agent registry
    - ChatSession: ORM model for chat sessions
    - ChatMessage: ORM model for chat messages
    - MemoryRecord: ORM model for agent memory
    - Base: SQLAlchemy DeclarativeBase for all models
    - create_storage_backend: Factory function for creating repositories

Example:
    >>> from configurable_agents.storage import create_storage_backend
    >>> runs_repo, states_repo, agents_repo, chat_repo, webhook_repo, memory_repo = create_storage_backend()
    >>> # Use repositories for persistence operations
"""

from configurable_agents.storage.base import (
    AbstractExecutionStateRepository,
    AbstractWorkflowRunRepository,
    AgentRegistryRepository,
    ChatSessionRepository,
    WebhookEventRepository,
    MemoryRepository,
)
from configurable_agents.storage.factory import create_storage_backend
from configurable_agents.storage.models import (
    AgentRecord,
    Base,
    ExecutionStateRecord,
    WorkflowRunRecord,
    ChatSession,
    ChatMessage,
    WebhookEventRecord,
    MemoryRecord,
)

__all__ = [
    # Abstract interfaces
    "AbstractWorkflowRunRepository",
    "AbstractExecutionStateRepository",
    "AgentRegistryRepository",
    "ChatSessionRepository",
    "WebhookEventRepository",
    "MemoryRepository",
    # ORM models
    "Base",
    "WorkflowRunRecord",
    "ExecutionStateRecord",
    "AgentRecord",
    "ChatSession",
    "ChatMessage",
    "WebhookEventRecord",
    "MemoryRecord",
    # Factory
    "create_storage_backend",
]
