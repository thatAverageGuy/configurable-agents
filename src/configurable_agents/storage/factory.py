"""Factory function for creating storage backend instances.

Provides a single entry point for creating repository instances based on
configuration. Supports SQLite with extensible design for PostgreSQL,
Redis, and other backends.

Example:
    >>> from configurable_agents.storage import create_storage_backend
    >>> runs_repo, states_repo, memory_repo = create_storage_backend()
    >>> # Or with explicit config
    >>> from configurable_agents.config import StorageConfig
    >>> config = StorageConfig(backend="sqlite", path="./workflows.db")
    >>> runs_repo, states_repo, memory_repo = create_storage_backend(config)
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import create_engine, inspect

from configurable_agents.config.schema import StorageConfig

logger = logging.getLogger(__name__)
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
from configurable_agents.storage.models import Base
from configurable_agents.storage.sqlite import (
    SQLiteExecutionStateRepository,
    SQLiteWorkflowRunRepository,
    SqliteAgentRegistryRepository,
    SQLiteChatSessionRepository,
    SqliteWebhookEventRepository,
    SQLiteMemoryRepository,
    SqliteWorkflowRegistrationRepository,
    SqliteOrchestratorRepository,
)


def _check_tables_exist(engine) -> bool:
    """Check if expected database tables exist.

    Args:
        engine: SQLAlchemy engine instance

    Returns:
        True if all expected tables exist, False otherwise
    """
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # Expected tables from models.py
    expected_tables = [
        "workflow_runs",  # WorkflowRunRecord
        "execution_states",  # ExecutionStateRecord
        "agents",  # AgentRecord
        "chat_sessions",  # ChatSessionRecord
        "chat_messages",  # ChatMessage
        "webhook_events",  # WebhookEventRecord
        "memory_records",  # MemoryRecord
        "workflow_registrations",  # WorkflowRegistrationRecord
        "orchestrators",  # OrchestratorRecord
    ]

    return all(table in existing_tables for table in expected_tables)


def ensure_initialized(
    db_url: str,
    verbose: bool = False,
    show_progress: bool = True,
) -> bool:
    """Ensure database tables exist, creating them if needed.

    This function is safe to call on every startup - it checks if tables
    exist and only initializes if the database is new.

    Args:
        db_url: SQLAlchemy database URL (e.g., "sqlite:///configurable_agents.db")
        verbose: Enable verbose logging
        show_progress: Show Rich progress spinner during initialization

    Returns:
        True if database is ready, False if running in degraded mode

    Raises:
        PermissionError: If database directory is not writable
        OSError: If disk is full or other IO error occurs
    """
    # Extract path from SQLite URL and ensure directory exists
    if db_url.startswith("sqlite:///"):
        db_path = Path(db_url.replace("sqlite:///", ""))
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise PermissionError(
                f"Cannot create database directory: {db_path.parent}\n"
                f"Permission denied: {e}\n"
                f"To fix: Check directory permissions or set AGENTS_DB_PATH to a writable location"
            ) from e
        except OSError as e:
            if "No space left on device" in str(e):
                raise OSError(
                    f"Disk full, cannot create database: {db_path}\n"
                    f"To fix: Free up disk space and try again"
                ) from e
            raise

    # Create engine
    engine = create_engine(db_url)

    # Check if tables already exist
    if _check_tables_exist(engine):
        if verbose:
            logger.debug(f"Database already initialized: {db_url}")
        return True

    # Need to initialize - show progress if requested
    try:
        if show_progress:
            try:
                from rich.console import Console
                from rich.status import Status

                console = Console()
                with Status(
                    "[bold blue]Initializing database...",
                    console=console,
                    spinner="dots",
                ):
                    Base.metadata.create_all(engine)
                console.print("[green]+[/green] Database initialized successfully")
            except ImportError:
                # Rich not available, initialize without spinner
                logger.info("Initializing database...")
                Base.metadata.create_all(engine)
                logger.info("Database initialized successfully")
        else:
            # No progress display requested
            logger.info("Initializing database...")
            Base.metadata.create_all(engine)
            logger.info("Database initialized successfully")
    except PermissionError as e:
        raise PermissionError(
            f"Cannot write to database: {db_url}\n"
            f"To fix:\n"
            f"  1. Check directory permissions\n"
            f"  2. Ensure database directory is writable\n"
            f"  3. Try running with elevated privileges if needed"
        ) from e
    except OSError as e:
        if "No space left on device" in str(e) or "disk full" in str(e).lower():
            raise OSError(
                f"Disk full, cannot write to database\n"
                f"To fix: Free up disk space and try again"
            ) from e
        raise

    # Verify tables were created
    if not _check_tables_exist(engine):
        logger.warning("Database initialization may have failed - some tables missing")
        return False

    return True


def create_storage_backend(
    config: Optional[StorageConfig] = None,
) -> Tuple[
    AbstractWorkflowRunRepository,
    AbstractExecutionStateRepository,
    AgentRegistryRepository,
    ChatSessionRepository,
    WebhookEventRepository,
    MemoryRepository,
    WorkflowRegistrationRepository,
    OrchestratorRepository,
]:
    """Create storage backend repositories from configuration.

    Args:
        config: StorageConfig instance. If None, uses defaults (sqlite, ./workflows.db)

    Returns:
        Tuple of (workflow_run_repository, execution_state_repository,
                  agent_registry_repository, chat_session_repository,
                  webhook_event_repository, memory_repository,
                  workflow_registration_repository, orchestrator_repository)

    Raises:
        ValueError: If backend type is not supported

    Example:
        >>> from configurable_agents.storage import create_storage_backend
        >>> runs_repo, states_repo, agents_repo, chat_repo, webhook_repo, memory_repo, workflow_reg_repo, orchestrator_repo = create_storage_backend()
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
        memory_repo = SQLiteMemoryRepository(engine)
        workflow_reg_repo = SqliteWorkflowRegistrationRepository(engine)
        orchestrator_repo = SqliteOrchestratorRepository(engine)

        return runs_repo, states_repo, agents_repo, chat_repo, webhook_repo, memory_repo, workflow_reg_repo, orchestrator_repo

    # Unsupported backend
    raise ValueError(
        f"Unsupported storage backend: {backend}. "
        f"Supported: 'sqlite'. PostgreSQL coming in Phase 2."
    )
