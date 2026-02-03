"""Factory function for creating storage backend instances.

Provides a single entry point for creating repository instances based on
configuration. Supports SQLite with extensible design for PostgreSQL,
Redis, and other backends.

Example:
    >>> from configurable_agents.storage import create_storage_backend
    >>> runs_repo, states_repo = create_storage_backend()
    >>> # Or with explicit config
    >>> from configurable_agents.config import StorageConfig
    >>> config = StorageConfig(backend="sqlite", path="./workflows.db")
    >>> runs_repo, states_repo = create_storage_backend(config)
"""

from typing import Optional, Tuple

from sqlalchemy import create_engine

from configurable_agents.config.schema import StorageConfig
from configurable_agents.storage.base import (
    AbstractExecutionStateRepository,
    AbstractWorkflowRunRepository,
    AgentRegistryRepository,
    ChatSessionRepository,
    WebhookEventRepository,
)
from configurable_agents.storage.models import Base
from configurable_agents.storage.sqlite import (
    SQLiteExecutionStateRepository,
    SQLiteWorkflowRunRepository,
    SqliteAgentRegistryRepository,
    SQLiteChatSessionRepository,
    SqliteWebhookEventRepository,
)


def create_storage_backend(
    config: Optional[StorageConfig] = None,
) -> Tuple[
    AbstractWorkflowRunRepository,
    AbstractExecutionStateRepository,
    AgentRegistryRepository,
    ChatSessionRepository,
    WebhookEventRepository,
]:
    """Create storage backend repositories from configuration.

    Args:
        config: StorageConfig instance. If None, uses defaults (sqlite, ./workflows.db)

    Returns:
        Tuple of (workflow_run_repository, execution_state_repository,
                  agent_registry_repository, chat_session_repository,
                  webhook_event_repository)

    Raises:
        ValueError: If backend type is not supported

    Example:
        >>> from configurable_agents.storage import create_storage_backend
        >>> runs_repo, states_repo, agents_repo, chat_repo, webhook_repo = create_storage_backend()
        >>> run = WorkflowRunRecord(id="123", workflow_name="test", status="running")
        >>> runs_repo.add(run)
    """
    # Use defaults if no config provided
    if config is None:
        config = StorageConfig()

    backend = config.backend

    # Handle sqlite backend
    if backend == "sqlite" or backend.startswith("sqlite:///"):
        db_path = config.path

        # Create SQLAlchemy engine
        engine = create_engine(f"sqlite:///{db_path}")

        # Ensure tables exist
        Base.metadata.create_all(engine)

        # Create repositories
        runs_repo = SQLiteWorkflowRunRepository(engine)
        states_repo = SQLiteExecutionStateRepository(engine)
        agents_repo = SqliteAgentRegistryRepository(engine)
        chat_repo = SQLiteChatSessionRepository(engine)
        webhook_repo = SqliteWebhookEventRepository(engine)

        return runs_repo, states_repo, agents_repo, chat_repo, webhook_repo

    # Unsupported backend
    raise ValueError(
        f"Unsupported storage backend: {backend}. "
        f"Supported: 'sqlite'. PostgreSQL coming in Phase 2."
    )
