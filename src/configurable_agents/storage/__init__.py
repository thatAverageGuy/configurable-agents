"""Storage abstraction layer for configurable agents.

Provides pluggable storage backend with Repository Pattern for workflow
run persistence, execution state tracking, agent registry, chat sessions,
agent memory, workflow registration, and orchestrator management.

Public API:
    - AbstractWorkflowRunRepository: Interface for workflow run storage
    - AbstractExecutionStateRepository: Interface for execution state storage
    - AgentRegistryRepository: Interface for agent registry storage
    - ChatSessionRepository: Interface for chat session storage
    - WebhookEventRepository: Interface for webhook event tracking
    - MemoryRepository: Interface for agent memory storage
    - WorkflowRegistrationRepository: Interface for webhook workflow registration
    - OrchestratorRepository: Interface for orchestrator registry storage
    - WorkflowRunRecord: ORM model for workflow runs
    - ExecutionStateRecord: ORM model for execution states
    - AgentRecord: ORM model for agent registry
    - ChatSession: ORM model for chat sessions
    - ChatMessage: ORM model for chat messages
    - WebhookEventRecord: ORM model for webhook events
    - MemoryRecord: ORM model for agent memory
    - WorkflowRegistrationRecord: ORM model for workflow registrations
    - OrchestratorRecord: ORM model for orchestrators
    - Base: SQLAlchemy DeclarativeBase for all models
    - create_storage_backend: Factory function for creating repositories

Example:
    >>> from configurable_agents.storage import create_storage_backend
    >>> runs_repo, states_repo, agents_repo, chat_repo, webhook_repo, memory_repo, workflow_reg_repo, orchestrator_repo = create_storage_backend()
    >>> # Use repositories for persistence operations
"""

from configurable_agents.storage.base import (
    AbstractExecutionStateRepository,
    AbstractWorkflowRunRepository,
    AgentRegistryRepository,
    ChatSessionRepository,
    WebhookEventRepository,
    MemoryRepository,
    WorkflowRegistrationRepository,
    OrchestratorRepository,
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
    WorkflowRegistrationRecord,
    OrchestratorRecord,
)

__all__ = [
    # Abstract interfaces
    "AbstractWorkflowRunRepository",
    "AbstractExecutionStateRepository",
    "AgentRegistryRepository",
    "ChatSessionRepository",
    "WebhookEventRepository",
    "MemoryRepository",
    "WorkflowRegistrationRepository",
    "OrchestratorRepository",
    # ORM models
    "Base",
    "WorkflowRunRecord",
    "ExecutionStateRecord",
    "AgentRecord",
    "ChatSession",
    "ChatMessage",
    "WebhookEventRecord",
    "MemoryRecord",
    "WorkflowRegistrationRecord",
    "OrchestratorRecord",
    # Factory
    "create_storage_backend",
]
