"""SQLite implementation of storage repository interfaces.

Provides concrete implementations of AbstractExecutionRepository,
AbstractExecutionStateRepository, DeploymentRepository, and
ChatSessionRepository using SQLAlchemy 2.0 with SQLite backend.

All database operations use context manager pattern for automatic
transaction handling and connection cleanup.

Renamed in UI Redesign (2026-02-13):
- SQLiteWorkflowRunRepository → SQLiteExecutionRepository
- SqliteAgentRegistryRepository → SqliteDeploymentRepository
- SqliteOrchestratorRepository → REMOVED
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import Engine, Select, create_engine, select, text
from sqlalchemy.orm import Session

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
from configurable_agents.storage.models import (
    ExecutionState,
    Execution,
    Deployment,
    ChatSession,
    ChatMessage,
    WebhookEventRecord,
    MemoryRecord,
    WorkflowRegistrationRecord,
)


class SQLiteExecutionRepository(AbstractExecutionRepository):
    """SQLite implementation of execution repository.

    Provides CRUD operations for Execution using SQLite backend.
    Uses context managers for automatic transaction handling.

    Renamed from SQLiteWorkflowRunRepository in UI Redesign.

    Attributes:
        engine: SQLAlchemy Engine instance for database connections
    """

    def __init__(self, engine: Engine) -> None:
        """Initialize repository with database engine.

        Args:
            engine: SQLAlchemy Engine instance (created by factory)
        """
        self.engine = engine

    def add(self, execution: Execution) -> None:
        """Persist a new execution.

        Args:
            execution: Execution instance to persist

        Raises:
            IntegrityError: If execution ID already exists
        """
        with Session(self.engine) as session:
            session.add(execution)
            session.commit()

    def get(self, execution_id: str) -> Optional[Execution]:
        """Get an execution by ID.

        Args:
            execution_id: Unique identifier for the execution

        Returns:
            Execution if found, None otherwise
        """
        with Session(self.engine) as session:
            return session.get(Execution, execution_id)

    def list_by_workflow(
        self, workflow_name: str, limit: int = 100
    ) -> List[Execution]:
        """List executions for a specific workflow.

        Args:
            workflow_name: Name of the workflow to filter by
            limit: Maximum number of executions to return (default: 100)

        Returns:
            List of Execution instances, ordered by started_at DESC
        """
        with Session(self.engine) as session:
            stmt: Select[Execution] = (
                select(Execution)
                .where(Execution.workflow_name == workflow_name)
                .order_by(Execution.started_at.desc())
                .limit(limit)
            )
            return list(session.scalars(stmt).all())

    def update_status(self, execution_id: str, status: str) -> None:
        """Update the status of an execution.

        Also sets completed_at timestamp when status is "completed" or "failed".

        Args:
            execution_id: Unique identifier for the execution
            status: New status value ("pending", "running", "completed", "failed")

        Raises:
            ValueError: If execution_id not found
        """
        with Session(self.engine) as session:
            execution = session.get(Execution, execution_id)
            if execution is None:
                raise ValueError(f"Execution not found: {execution_id}")

            execution.status = status

            # Set completed_at for terminal states
            if status in ("completed", "failed"):
                execution.completed_at = datetime.utcnow()

            session.commit()

    def delete(self, execution_id: str) -> None:
        """Delete an execution.

        Args:
            execution_id: Unique identifier for the execution

        Raises:
            ValueError: If execution_id not found
        """
        with Session(self.engine) as session:
            execution = session.get(Execution, execution_id)
            if execution is None:
                raise ValueError(f"Execution not found: {execution_id}")

            session.delete(execution)
            session.commit()

    def update_execution_completion(
        self,
        execution_id: str,
        status: str,
        duration_seconds: float,
        total_tokens: int,
        total_cost_usd: float,
        outputs: Optional[str] = None,
        error_message: Optional[str] = None,
        bottleneck_info: Optional[str] = None,
    ) -> None:
        """Update an execution with completion metrics.

        Args:
            execution_id: Unique identifier for the execution
            status: New status value ("completed" or "failed")
            duration_seconds: Execution time in seconds
            total_tokens: Total tokens used across all LLM calls
            total_cost_usd: Total estimated cost in USD
            outputs: JSON-serialized output data (optional)
            error_message: Error message if status is "failed" (optional)
            bottleneck_info: JSON-serialized bottleneck analysis (optional)

        Raises:
            ValueError: If execution_id not found
        """
        with Session(self.engine) as session:
            execution = session.get(Execution, execution_id)
            if execution is None:
                raise ValueError(f"Execution not found: {execution_id}")

            execution.status = status
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = duration_seconds
            execution.total_tokens = total_tokens
            execution.total_cost_usd = total_cost_usd

            if outputs is not None:
                execution.outputs = outputs
            if error_message is not None:
                execution.error_message = error_message
            if bottleneck_info is not None:
                execution.bottleneck_info = bottleneck_info

            session.commit()


class SQLiteExecutionStateRepository(AbstractExecutionStateRepository):
    """SQLite implementation of execution state repository.

    Provides storage and retrieval of workflow execution state checkpoints.
    State is saved after each node execution for resume functionality.

    Attributes:
        engine: SQLAlchemy Engine instance for database connections
    """

    def __init__(self, engine: Engine) -> None:
        """Initialize repository with database engine.

        Args:
            engine: SQLAlchemy Engine instance (created by factory)
        """
        self.engine = engine

    def save_state(
        self, execution_id: str, state_data: Dict[str, Any], node_id: str
    ) -> None:
        """Save execution state checkpoint after a node.

        Args:
            execution_id: Unique identifier for the execution
            state_data: Current workflow state as a dictionary
            node_id: ID of the node that produced this state

        Raises:
            ValueError: If execution_id not found in executions
        """
        with Session(self.engine) as session:
            # Verify execution exists
            execution = session.get(Execution, execution_id)
            if execution is None:
                raise ValueError(f"Execution not found: {execution_id}")

            # Create state record
            record = ExecutionState(
                execution_id=execution_id,
                node_id=node_id,
                state_data=json.dumps(state_data),
            )
            session.add(record)
            session.commit()

    def get_latest_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest state checkpoint for an execution.

        Args:
            execution_id: Unique identifier for the execution

        Returns:
            State dictionary if found, None otherwise
        """
        with Session(self.engine) as session:
            stmt: Select[ExecutionState] = (
                select(ExecutionState)
                .where(ExecutionState.execution_id == execution_id)
                .order_by(ExecutionState.created_at.desc())
                .limit(1)
            )
            record = session.scalar(stmt)

            if record is None:
                return None

            return json.loads(record.state_data)

    def get_state_history(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get all state checkpoints for an execution.

        Args:
            execution_id: Unique identifier for the execution

        Returns:
            List of state checkpoints, each containing:
            - node_id: Which node produced this state
            - state_data: The state dictionary (parsed from JSON)
            - created_at: Timestamp when checkpoint was saved
            Ordered by created_at ASC (oldest first)
        """
        with Session(self.engine) as session:
            stmt: Select[ExecutionState] = (
                select(ExecutionState)
                .where(ExecutionState.execution_id == execution_id)
                .order_by(ExecutionState.created_at.asc())
            )
            records = list(session.scalars(stmt).all())

            return [
                {
                    "node_id": r.node_id,
                    "state_data": json.loads(r.state_data),
                    "created_at": r.created_at,
                }
                for r in records
            ]


class SqliteDeploymentRepository(DeploymentRepository):
    """SQLite implementation of deployment repository.

    Provides CRUD operations for Deployment using SQLite backend.
    Uses context managers for automatic transaction handling.

    Renamed from SqliteAgentRegistryRepository in UI Redesign.

    Attributes:
        engine: SQLAlchemy Engine instance for database connections
    """

    def __init__(self, engine: Engine) -> None:
        """Initialize repository with database engine.

        Args:
            engine: SQLAlchemy Engine instance (created by factory)
        """
        self.engine = engine

    def add(self, deployment: Deployment) -> None:
        """Register a new deployment.

        Args:
            deployment: Deployment instance to persist

        Raises:
            IntegrityError: If deployment_id already exists
        """
        with Session(self.engine) as session:
            session.add(deployment)
            session.commit()

    def get(self, deployment_id: str) -> Optional[Deployment]:
        """Get a deployment by ID.

        Args:
            deployment_id: Unique identifier for the deployment

        Returns:
            Deployment if found, None otherwise
        """
        with Session(self.engine) as session:
            return session.get(Deployment, deployment_id)

    def list_all(self, include_dead: bool = False) -> List[Deployment]:
        """List all registered deployments.

        Args:
            include_dead: If False, only return deployments where is_alive() is True.
                         If True, return all deployments regardless of TTL status.

        Returns:
            List of Deployment instances
        """
        with Session(self.engine) as session:
            stmt: Select[Deployment] = select(Deployment).order_by(
                Deployment.registered_at.desc()
            )
            deployments = list(session.scalars(stmt).all())

            if not include_dead:
                deployments = [d for d in deployments if d.is_alive()]

            return deployments

    def update_heartbeat(self, deployment_id: str) -> None:
        """Update a deployment's heartbeat timestamp.

        Sets last_heartbeat to the current time, effectively refreshing
        the deployment's TTL.

        Args:
            deployment_id: Unique identifier for the deployment

        Raises:
            ValueError: If deployment_id not found
        """
        with Session(self.engine) as session:
            deployment = session.get(Deployment, deployment_id)
            if deployment is None:
                raise ValueError(f"Deployment not found: {deployment_id}")

            deployment.last_heartbeat = datetime.utcnow()
            session.commit()

    def delete(self, deployment_id: str) -> None:
        """Delete a deployment from the registry.

        Args:
            deployment_id: Unique identifier for the deployment

        Raises:
            ValueError: If deployment_id not found
        """
        with Session(self.engine) as session:
            deployment = session.get(Deployment, deployment_id)
            if deployment is None:
                raise ValueError(f"Deployment not found: {deployment_id}")

            session.delete(deployment)
            session.commit()

    def delete_expired(self) -> int:
        """Delete all expired deployments from the registry.

        A deployment is considered expired if the current time is after
        its expiration time (last_heartbeat + ttl_seconds).

        Returns:
            Number of deployments deleted
        """
        with Session(self.engine) as session:
            # Query all deployments
            stmt: Select[Deployment] = select(Deployment)
            deployments = list(session.scalars(stmt).all())

            # Filter and delete expired deployments
            expired_deployments = [
                d for d in deployments if not d.is_alive()
            ]

            count = 0
            for deployment in expired_deployments:
                session.delete(deployment)
                count += 1

            session.commit()
            return count

    def query_by_metadata(self, metadata_filter: Dict[str, Any]) -> List[Deployment]:
        """Query deployments by metadata/capabilities.

        Allows filtering deployments by their metadata JSON blob using
        key-value matching with wildcard support.

        Args:
            metadata_filter: Dictionary of metadata filters
                - String values support "*" wildcard (e.g., {"model": "gpt-*"})
                - Nested keys use dot notation (e.g., {"capabilities.llm": true})

        Returns:
            List of Deployment instances matching the criteria
        """
        # Get all deployments first
        deployments = self.list_all(include_dead=False)

        # Filter by metadata
        filtered = []
        for deployment in deployments:
            metadata_str = deployment.deployment_metadata
            if not metadata_str:
                continue

            try:
                metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str

                # Check if deployment matches all filters
                if self._matches_filters(metadata, metadata_filter):
                    filtered.append(deployment)

            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse metadata for deployment {deployment.deployment_id}")
                continue

        return filtered

    def get_active_deployments(self, cutoff_seconds: int = 60) -> List[Deployment]:
        """Get only active (recently heartbeating) deployments.

        A deployment is considered active if its last heartbeat was within
        the specified cutoff period.

        Args:
            cutoff_seconds: Seconds since last heartbeat (default: 60)

        Returns:
            List of active Deployment instances
        """
        # Get all deployments (including dead ones for filtering)
        all_deployments = self.list_all(include_dead=True)
        cutoff_time = datetime.utcnow() - timedelta(seconds=cutoff_seconds)

        active_deployments = []
        for deployment in all_deployments:
            # Skip deployments with no heartbeat
            if deployment.last_heartbeat is None:
                continue
            # Check if heartbeat is recent enough
            if deployment.last_heartbeat >= cutoff_time:
                active_deployments.append(deployment)

        return active_deployments

    def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if metadata matches all filter criteria.

        Args:
            metadata: Deployment metadata dictionary
            filters: Filter criteria

        Returns:
            True if metadata matches all filters, False otherwise
        """
        for key, value in filters.items():
            # Support nested keys with dot notation
            metadata_value = metadata
            for key_part in key.split("."):
                if isinstance(metadata_value, dict):
                    metadata_value = metadata_value.get(key_part)
                else:
                    metadata_value = None
                    break

            # Check if value matches (with wildcard support for strings)
            if not self._value_matches(metadata_value, value):
                return False

        return True

    def _value_matches(self, actual: Any, expected: Any) -> bool:
        """Check if actual value matches expected value (with wildcard support).

        Args:
            actual: The actual value from metadata
            expected: The expected filter value

        Returns:
            True if values match, False otherwise
        """
        import fnmatch

        # Handle wildcard matching for strings
        if isinstance(expected, str) and isinstance(actual, str):
            if "*" in expected:
                return fnmatch.fnmatch(actual, expected)

        # Handle list matching (actual contains expected)
        if isinstance(expected, list) and isinstance(actual, str):
            return actual in expected

        # Handle list matching (actual list contains expected)
        if isinstance(expected, str) and isinstance(actual, list):
            return expected in actual

        # Handle list-to-list matching (any match)
        if isinstance(expected, list) and isinstance(actual, list):
            return any(item in actual for item in expected)

        # Direct comparison
        return actual == expected


class SQLiteChatSessionRepository(ChatSessionRepository):
    """SQLite implementation of chat session repository.

    Provides CRUD operations for ChatSession and ChatMessage using
    SQLite backend. Uses context managers for automatic transaction
    handling.

    Attributes:
        engine: SQLAlchemy Engine instance for database connections
    """

    def __init__(self, engine: Engine) -> None:
        """Initialize repository with database engine.

        Args:
            engine: SQLAlchemy Engine instance (created by factory)
        """
        self.engine = engine

        # Enable WAL mode for concurrent access
        self._enable_wal_mode()

    def _enable_wal_mode(self) -> None:
        """Enable WAL mode for better concurrent access.

        WAL (Write-Ahead Logging) allows concurrent reads and writes,
        which is important for multi-user chat sessions.
        """
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.commit()

    def create_session(self, user_identifier: str) -> str:
        """Create a new chat session.

        Args:
            user_identifier: Browser fingerprint or IP for session tracking

        Returns:
            session_id: UUID of the created session
        """
        session_id = str(uuid.uuid4())

        with Session(self.engine) as session:
            chat_session = ChatSession(
                session_id=session_id,
                user_identifier=user_identifier,
                status="in_progress",
            )
            session.add(chat_session)
            session.commit()

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID.

        Args:
            session_id: UUID of the session

        Returns:
            Dictionary with session data if found, None otherwise
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session is None:
                return None
            return chat_session.to_dict()

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a message to a session.

        Args:
            session_id: UUID of the session
            role: Message role ("user" or "assistant")
            content: Message content
            metadata: Optional JSON metadata (model, tokens, etc.)

        Raises:
            ValueError: If session_id not found
        """
        with Session(self.engine) as session:
            # Verify session exists
            chat_session = session.get(ChatSession, session_id)
            if chat_session is None:
                raise ValueError(f"Chat session not found: {session_id}")

            # Create message
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                message_metadata=json.dumps(metadata) if metadata else None,
            )
            session.add(message)

            # Update session's updated_at timestamp
            chat_session.updated_at = datetime.utcnow()

            session.commit()

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a session.

        Args:
            session_id: UUID of the session

        Returns:
            List of message dictionaries ordered by created_at ASC
        """
        with Session(self.engine) as session:
            stmt: Select[ChatMessage] = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.asc())
            )
            messages = list(session.scalars(stmt).all())

            return [m.to_dict() for m in messages]

    def update_config(self, session_id: str, config_yaml: str) -> None:
        """Save generated config to session.

        Args:
            session_id: UUID of the session
            config_yaml: Generated YAML configuration

        Raises:
            ValueError: If session_id not found
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session is None:
                raise ValueError(f"Chat session not found: {session_id}")

            chat_session.generated_config = config_yaml
            chat_session.status = "completed"
            chat_session.updated_at = datetime.utcnow()

            session.commit()

    def list_recent_sessions(
        self, user_identifier: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List recent sessions for a user.

        Args:
            user_identifier: User's identifier
            limit: Maximum number of sessions to return

        Returns:
            List of session dictionaries ordered by updated_at DESC
        """
        with Session(self.engine) as session:
            stmt: Select[ChatSession] = (
                select(ChatSession)
                .where(ChatSession.user_identifier == user_identifier)
                .order_by(ChatSession.updated_at.desc())
                .limit(limit)
            )
            sessions = list(session.scalars(stmt).all())

            return [s.to_dict() for s in sessions]


class SqliteWebhookEventRepository(WebhookEventRepository):
    """SQLite implementation of webhook event repository.

    Provides idempotency tracking for webhook events to prevent replay attacks.
    Uses context managers for automatic transaction handling.

    Attributes:
        engine: SQLAlchemy Engine instance for database connections
    """

    def __init__(self, engine: Engine) -> None:
        """Initialize repository with database engine.

        Args:
            engine: SQLAlchemy Engine instance (created by factory)
        """
        self.engine = engine

    def is_processed(self, webhook_id: str) -> bool:
        """Check if webhook event was already processed.

        Args:
            webhook_id: Unique identifier for the webhook event

        Returns:
            True if already processed, False otherwise
        """
        with Session(self.engine) as session:
            stmt: Select[WebhookEventRecord] = (
                select(WebhookEventRecord)
                .where(WebhookEventRecord.webhook_id == webhook_id)
                .limit(1)
            )
            record = session.scalar(stmt)
            return record is not None

    def mark_processed(self, webhook_id: str, provider: str) -> None:
        """Record webhook as processed.

        Uses INSERT OR IGNORE for idempotency - calling this multiple times
        with the same webhook_id is safe.

        Args:
            webhook_id: Unique identifier for the webhook event
            provider: Name of the webhook provider (e.g., "whatsapp", "telegram")
        """
        with Session(self.engine) as session:
            # Use raw SQL with INSERT OR IGNORE for idempotency
            # SQLAlchemy's merge() doesn't work well with unique constraint violations
            session.execute(
                text(
                    "INSERT OR IGNORE INTO webhook_events (webhook_id, provider, processed_at) "
                    "VALUES (:webhook_id, :provider, :processed_at)"
                ),
                {"webhook_id": webhook_id, "provider": provider, "processed_at": datetime.utcnow()},
            )
            session.commit()

    def cleanup_old_events(self, days: int = 7) -> int:
        """Delete webhook event records older than N days.

        Args:
            days: Number of days to retain records (default: 7)

        Returns:
            Number of records deleted
        """
        with Session(self.engine) as session:
            # Calculate cutoff time
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)

            # Delete old records
            stmt: Select[WebhookEventRecord] = (
                select(WebhookEventRecord)
                .where(WebhookEventRecord.processed_at < cutoff)
            )
            records = list(session.scalars(stmt).all())

            count = 0
            for record in records:
                session.delete(record)
                count += 1

            session.commit()
            return count


class SQLiteMemoryRepository(MemoryRepository):
    """SQLite implementation of memory repository.

    Provides key-value storage for agent memory with namespaced keys.
    Uses INSERT OR REPLACE for upsert semantics when storing values.

    Attributes:
        engine: SQLAlchemy Engine instance for database connections
    """

    def __init__(self, engine: Engine) -> None:
        """Initialize repository with database engine.

        Args:
            engine: SQLAlchemy Engine instance (created by factory)
        """
        self.engine = engine

    def get(self, namespace_key: str) -> Optional[str]:
        """Get a value by namespace key.

        Args:
            namespace_key: Combined namespace key (agent:workflow:node:key)

        Returns:
            JSON-serialized value if found, None otherwise
        """
        with Session(self.engine) as session:
            stmt: Select[MemoryRecord] = (
                select(MemoryRecord)
                .where(MemoryRecord.namespace_key == namespace_key)
                .limit(1)
            )
            record = session.scalar(stmt)
            return record.value if record else None

    def set(
        self,
        namespace_key: str,
        value: str,
        agent_id: str,
        workflow_id: Optional[str],
        node_id: Optional[str],
        key: str,
    ) -> None:
        """Store a value with namespace key (upsert).

        Uses raw SQL with INSERT OR REPLACE for upsert semantics.

        Args:
            namespace_key: Combined namespace key (agent:workflow:node:key)
            value: JSON-serialized value to store
            agent_id: Agent identifier
            workflow_id: Workflow identifier (optional)
            node_id: Node identifier (optional)
            key: User-facing key name
        """
        with Session(self.engine) as session:
            # Use INSERT OR REPLACE for upsert semantics
            session.execute(
                text(
                    "INSERT OR REPLACE INTO memory_records "
                    "(namespace_key, value, agent_id, workflow_id, node_id, key, created_at, updated_at) "
                    "VALUES (:namespace_key, :value, :agent_id, :workflow_id, :node_id, :key, "
                    "COALESCE((SELECT created_at FROM memory_records WHERE namespace_key = :namespace_key), datetime('now')), "
                    "datetime('now'))"
                ),
                {
                    "namespace_key": namespace_key,
                    "value": value,
                    "agent_id": agent_id,
                    "workflow_id": workflow_id,
                    "node_id": node_id,
                    "key": key,
                },
            )
            session.commit()

    def delete(self, namespace_key: str) -> bool:
        """Delete a value by namespace key.

        Args:
            namespace_key: Combined namespace key (agent:workflow:node:key)

        Returns:
            True if record was deleted, False if not found
        """
        with Session(self.engine) as session:
            stmt: Select[MemoryRecord] = (
                select(MemoryRecord)
                .where(MemoryRecord.namespace_key == namespace_key)
                .limit(1)
            )
            record = session.scalar(stmt)

            if record is None:
                return False

            session.delete(record)
            session.commit()
            return True

    def list(self, agent_id: str, prefix: str = "") -> List[tuple[str, str]]:
        """List all keys for an agent with optional prefix filtering.

        Args:
            agent_id: Agent identifier to filter by
            prefix: Optional key prefix to filter results (e.g., "user:")

        Returns:
            List of (key, value) tuples matching the criteria
        """
        with Session(self.engine) as session:
            stmt: Select[MemoryRecord] = (
                select(MemoryRecord)
                .where(MemoryRecord.agent_id == agent_id)
                .order_by(MemoryRecord.key.asc())
            )

            records = list(session.scalars(stmt).all())

            # Filter by prefix if provided (case-sensitive)
            if prefix:
                records = [r for r in records if r.key.startswith(prefix)]

            return [(r.key, r.value) for r in records]

    def clear(self, agent_id: str) -> int:
        """Clear all memory for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Number of records deleted
        """
        with Session(self.engine) as session:
            stmt: Select[MemoryRecord] = (
                select(MemoryRecord)
                .where(MemoryRecord.agent_id == agent_id)
            )
            records = list(session.scalars(stmt).all())

            count = 0
            for record in records:
                session.delete(record)
                count += 1

            session.commit()
            return count

    def clear_by_workflow(self, agent_id: str, workflow_id: str) -> int:
        """Clear all memory for a specific workflow.

        Args:
            agent_id: Agent identifier
            workflow_id: Workflow identifier

        Returns:
            Number of records deleted
        """
        with Session(self.engine) as session:
            stmt: Select[MemoryRecord] = (
                select(MemoryRecord)
                .where(
                    MemoryRecord.agent_id == agent_id,
                    MemoryRecord.workflow_id == workflow_id,
                )
            )
            records = list(session.scalars(stmt).all())

            count = 0
            for record in records:
                session.delete(record)
                count += 1

            session.commit()
            return count


class SqliteWorkflowRegistrationRepository(WorkflowRegistrationRepository):
    """SQLite implementation of workflow registration repository.

    Manages workflow configurations registered for webhook triggering.
    Uses context managers for automatic transaction handling.

    Attributes:
        engine: SQLAlchemy Engine instance for database connections
    """

    def __init__(self, engine: Engine) -> None:
        """Initialize repository with database engine.

        Args:
            engine: SQLAlchemy Engine instance (created by factory)
        """
        self.engine = engine

    def register(
        self,
        workflow_name: str,
        webhook_secret: Optional[str] = None,
        description: Optional[str] = None,
        allowed_methods: Optional[List[str]] = None,
        default_inputs: Optional[Dict[str, Any]] = None,
        rate_limit: Optional[int] = None,
    ) -> None:
        """Register a workflow for webhook triggering.

        Args:
            workflow_name: Unique workflow identifier
            webhook_secret: Optional secret for HMAC validation
            description: Optional human-readable description
            allowed_methods: Optional list of allowed methods
            default_inputs: Optional dict of default input values
            rate_limit: Optional rate limit (requests per minute)

        Raises:
            ValueError: If workflow already registered
        """
        with Session(self.engine) as session:
            # Check if already registered
            existing = session.get(WorkflowRegistrationRecord, workflow_name)
            if existing is not None:
                raise ValueError(f"Workflow '{workflow_name}' is already registered")

            # Create new registration
            record = WorkflowRegistrationRecord(
                workflow_name=workflow_name,
                webhook_secret=webhook_secret,
                description=description,
                allowed_methods=json.dumps(allowed_methods or []),
                default_inputs=json.dumps(default_inputs or {}),
                rate_limit=rate_limit,
                enabled=True,
            )
            session.add(record)
            session.commit()

    def get(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Get workflow registration by name.

        Args:
            workflow_name: Unique workflow identifier

        Returns:
            Dictionary with registration data if found, None otherwise
        """
        with Session(self.engine) as session:
            record = session.get(WorkflowRegistrationRecord, workflow_name)
            if record is None:
                return None
            return record.to_dict()

    def list_all(self) -> List[Dict[str, Any]]:
        """List all workflow registrations.

        Returns:
            List of registration dictionaries
        """
        with Session(self.engine) as session:
            stmt = select(WorkflowRegistrationRecord).where(
                WorkflowRegistrationRecord.enabled == True
            )
            records = list(session.scalars(stmt).all())
            return [r.to_dict() for r in records]

    def delete(self, workflow_name: str) -> bool:
        """Unregister a workflow.

        Args:
            workflow_name: Unique workflow identifier

        Returns:
            True if registration was deleted, False if not found
        """
        with Session(self.engine) as session:
            record = session.get(WorkflowRegistrationRecord, workflow_name)
            if record is None:
                return False
            session.delete(record)
            session.commit()
            return True

    def get_by_method(self, method: str) -> List[Dict[str, Any]]:
        """Get workflows by platform/method.

        Args:
            method: Platform/method name (generic, whatsapp, telegram)

        Returns:
            List of registration dictionaries that allow this method
        """
        with Session(self.engine) as session:
            stmt = select(WorkflowRegistrationRecord).where(
                WorkflowRegistrationRecord.enabled == True
            )
            records = list(session.scalars(stmt).all())

            # Filter by allowed methods
            result = []
            for record in records:
                allowed_methods = json.loads(record.allowed_methods)
                if method in allowed_methods:
                    result.append(record.to_dict())

            return result
