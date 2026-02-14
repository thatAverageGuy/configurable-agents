"""Factory function for creating storage backend instances.

Provides a single entry point for creating repository instances based on
configuration. Supports SQLite with extensible design for PostgreSQL,
Redis, and other backends.

Example:
    >>> from configurable_agents.storage import create_storage_backend
    >>> exec_repo, states_repo, memory_repo = create_storage_backend()
    >>> # Or with explicit config
    >>> from configurable_agents.config import StorageConfig
    >>> config = StorageConfig(backend="sqlite", path="./configurable_agents.db")
    >>> exec_repo, states_repo, memory_repo = create_storage_backend(config)

Updated in UI Redesign (2026-02-13):
- Renamed classes: Execution, Deployment, ExecutionState
- Removed OrchestratorRepository from return tuple
- Updated expected table names
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import create_engine, inspect

from configurable_agents.config.schema import StorageConfig

logger = logging.getLogger(__name__)
from configurable_agents.storage.base import (
    AbstractExecutionStateRepository,
    AbstractExecutionRepository,
    DeploymentRepository,
    ChatSessionRepository,
    WebhookEventRepository,
    MemoryRepository,
    WorkflowRegistrationRepository,
)
from configurable_agents.storage.models import Base
from configurable_agents.storage.sqlite import (
    SQLiteExecutionStateRepository,
    SQLiteExecutionRepository,
    SqliteDeploymentRepository,
    SQLiteChatSessionRepository,
    SqliteWebhookEventRepository,
    SQLiteMemoryRepository,
    SqliteWorkflowRegistrationRepository,
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

    # Expected tables from models.py (updated names)
    expected_tables = [
        "executions",  # Execution (was workflow_runs)
        "execution_states",  # ExecutionState
        "deployments",  # Deployment (was agents)
        "chat_sessions",  # ChatSession
        "chat_messages",  # ChatMessage
        "webhook_events",  # WebhookEventRecord
        "memory_records",  # MemoryRecord
        "workflow_registrations",  # WorkflowRegistrationRecord
        "session_state",  # SessionState
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
    auto_init: bool = True,
) -> Tuple[
    AbstractExecutionRepository,
    AbstractExecutionStateRepository,
    DeploymentRepository,
    ChatSessionRepository,
    WebhookEventRepository,
    MemoryRepository,
    WorkflowRegistrationRepository,
]:
    """Create storage backend repositories from configuration.

    Args:
        config: StorageConfig instance. If None, uses defaults (sqlite, ./configurable_agents.db)
        auto_init: Automatically initialize database if tables missing (default: True)

    Returns:
        Tuple of (execution_repository, execution_state_repository,
                  deployment_repository, chat_session_repository,
                  webhook_event_repository, memory_repository,
                  workflow_registration_repository)

    Raises:
        ValueError: If backend type is not supported

    Example:
        >>> from configurable_agents.storage import create_storage_backend
        >>> exec_repo, states_repo, deploy_repo, chat_repo, webhook_repo, memory_repo, workflow_reg_repo = create_storage_backend()
        >>> execution = Execution(id="123", workflow_name="test", status="running")
        >>> exec_repo.add(execution)
    """
    # Use defaults if no config provided
    if config is None:
        config = StorageConfig()

    backend = config.backend
    db_path = config.path
    db_url = f"sqlite:///{db_path}"

    # Handle sqlite backend
    if backend == "sqlite" or backend.startswith("sqlite:///"):
        # Ensure tables exist if auto_init is True
        if auto_init:
            ensure_initialized(db_url, show_progress=False)

        # Create SQLAlchemy engine
        engine = create_engine(db_url)

        # Create repositories
        exec_repo = SQLiteExecutionRepository(engine)
        states_repo = SQLiteExecutionStateRepository(engine)
        deploy_repo = SqliteDeploymentRepository(engine)
        chat_repo = SQLiteChatSessionRepository(engine)
        webhook_repo = SqliteWebhookEventRepository(engine)
        memory_repo = SQLiteMemoryRepository(engine)
        workflow_reg_repo = SqliteWorkflowRegistrationRepository(engine)

        return exec_repo, states_repo, deploy_repo, chat_repo, webhook_repo, memory_repo, workflow_reg_repo

    # Unsupported backend
    raise ValueError(
        f"Unsupported storage backend: {backend}. "
        f"Supported: 'sqlite'. PostgreSQL coming in Phase 2."
    )
