"""Storage abstraction layer for configurable agents.

Provides pluggable storage backend with Repository Pattern for execution
persistence, execution state tracking, deployment registry, chat sessions,
agent memory, and workflow registration.

Updated in UI Redesign (2026-02-13):
- WorkflowRunRecord → Execution (table: executions)
- AgentRecord → Deployment (table: deployments)
- OrchestratorRecord → REMOVED
- AbstractWorkflowRunRepository → AbstractExecutionRepository
- AgentRegistryRepository → DeploymentRepository
- OrchestratorRepository → REMOVED

Public API:
    - AbstractExecutionRepository: Interface for execution storage
    - AbstractExecutionStateRepository: Interface for execution state storage
    - DeploymentRepository: Interface for deployment registry storage
    - ChatSessionRepository: Interface for chat session storage
    - WebhookEventRepository: Interface for webhook event tracking
    - MemoryRepository: Interface for agent memory storage
    - WorkflowRegistrationRepository: Interface for webhook workflow registration
    - Execution: ORM model for executions
    - ExecutionState: ORM model for execution states
    - Deployment: ORM model for deployments
    - ChatSession: ORM model for chat sessions
    - ChatMessage: ORM model for chat messages
    - WebhookEventRecord: ORM model for webhook events
    - MemoryRecord: ORM model for agent memory
    - WorkflowRegistrationRecord: ORM model for workflow registrations
    - SessionState: ORM model for session state
    - Base: SQLAlchemy DeclarativeBase for all models
    - create_storage_backend: Factory function for creating repositories

Example:
    >>> from configurable_agents.storage import create_storage_backend
    >>> exec_repo, states_repo, deploy_repo, chat_repo, webhook_repo, memory_repo, workflow_reg_repo = create_storage_backend()
    >>> # Use repositories for persistence operations
"""

from configurable_agents.storage.base import (
    AbstractExecutionStateRepository,
    AbstractExecutionRepository,
    DeploymentRepository,
    ChatSessionRepository,
    WebhookEventRepository,
    MemoryRepository,
    WorkflowRegistrationRepository,
)
from configurable_agents.storage.factory import create_storage_backend, ensure_initialized
from configurable_agents.storage.models import (
    Deployment,
    Base,
    ExecutionState,
    Execution,
    ChatSession,
    ChatMessage,
    WebhookEventRecord,
    MemoryRecord,
    WorkflowRegistrationRecord,
    SessionState,
)

__all__ = [
    # Abstract interfaces
    "AbstractExecutionRepository",
    "AbstractExecutionStateRepository",
    "DeploymentRepository",
    "ChatSessionRepository",
    "WebhookEventRepository",
    "MemoryRepository",
    "WorkflowRegistrationRepository",
    # ORM models
    "Base",
    "Execution",
    "ExecutionState",
    "Deployment",
    "ChatSession",
    "ChatMessage",
    "WebhookEventRecord",
    "MemoryRecord",
    "WorkflowRegistrationRecord",
    "SessionState",
    # Factory
    "create_storage_backend",
    "ensure_initialized",
]
