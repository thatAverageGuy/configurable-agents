"""Abstract repository interfaces for storage backend.

Defines the pluggable storage abstraction layer following the Repository Pattern.
Implementations can be SQLite, PostgreSQL, Redis, or any other backend that
implements these interfaces.

Renamed in UI Redesign (2026-02-13):
- AbstractWorkflowRunRepository → AbstractExecutionRepository
- AgentRegistryRepository → DeploymentRepository
- OrchestratorRepository → REMOVED (absorbed into deployments)

See https://www.cosmicpython.com/book/chapter_02_repository.html for pattern
reference.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

# Forward declarations for ORM models (avoiding circular import)
# Execution, ExecutionState, Deployment, ChatSession, and ChatMessage
# are defined in models.py


class DeploymentRepository(ABC):
    """Abstract repository for deployment registry persistence.

    Provides CRUD operations for deployment registration records with support
    for TTL-based expiration tracking via heartbeat updates.

    Renamed from AgentRegistryRepository in UI Redesign.

    Methods:
        add: Register a new deployment
        get: Retrieve a single deployment by ID
        list_all: List all deployments (optionally including expired ones)
        update_heartbeat: Refresh a deployment's last_heartbeat timestamp
        delete: Remove a deployment from the registry
        delete_expired: Remove all expired deployments from the registry
    """

    @abstractmethod
    def add(self, deployment: Any) -> None:
        """Register a new deployment.

        Args:
            deployment: Deployment instance to persist

        Raises:
            IntegrityError: If deployment_id already exists
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, deployment_id: str) -> Optional[Any]:
        """Get a deployment by ID.

        Args:
            deployment_id: Unique identifier for the deployment

        Returns:
            Deployment if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def list_all(self, include_dead: bool = False) -> List[Any]:
        """List all registered deployments.

        Args:
            include_dead: If False, only return deployments where is_alive() is True.
                         If True, return all deployments regardless of TTL status.

        Returns:
            List of Deployment instances
        """
        raise NotImplementedError

    @abstractmethod
    def update_heartbeat(self, deployment_id: str) -> None:
        """Update a deployment's heartbeat timestamp.

        Sets last_heartbeat to the current time, effectively refreshing
        the deployment's TTL.

        Args:
            deployment_id: Unique identifier for the deployment

        Raises:
            ValueError: If deployment_id not found
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, deployment_id: str) -> None:
        """Delete a deployment from the registry.

        Args:
            deployment_id: Unique identifier for the deployment

        Raises:
            ValueError: If deployment_id not found
        """
        raise NotImplementedError

    @abstractmethod
    def delete_expired(self) -> int:
        """Delete all expired deployments from the registry.

        A deployment is considered expired if the current time is after
        its expiration time (last_heartbeat + ttl_seconds).

        Returns:
            Number of deployments deleted
        """
        raise NotImplementedError

    @abstractmethod
    def query_by_metadata(self, metadata_filter: Dict[str, Any]) -> List[Any]:
        """Query deployments by metadata/capabilities.

        Allows filtering deployments by their metadata JSON blob using
        key-value matching.

        Args:
            metadata_filter: Dictionary of metadata filters
                - String values support "*" wildcard (e.g., {"model": "gpt-*"})
                - Nested keys use dot notation (e.g., {"capabilities.llm": true})

        Returns:
            List of Deployment instances matching the criteria

        Example:
            >>> # Find all LLM deployments
            >>> llm_deployments = repo.query_by_metadata({"type": "llm"})
        """
        raise NotImplementedError

    @abstractmethod
    def get_active_deployments(self, cutoff_seconds: int = 60) -> List[Any]:
        """Get only active (recently heartbeating) deployments.

        A deployment is considered active if its last heartbeat was within
        the specified cutoff period.

        Args:
            cutoff_seconds: Seconds since last heartbeat (default: 60)

        Returns:
            List of active Deployment instances

        Example:
            >>> # Get deployments that heartbeat within last 30 seconds
            >>> active = repo.get_active_deployments(cutoff_seconds=30)
        """
        raise NotImplementedError


class AbstractExecutionRepository(ABC):
    """Abstract repository for workflow execution persistence.

    Provides CRUD operations for workflow execution records. Implementations
    must handle persistence, retrieval, and querying of executions.

    Renamed from AbstractWorkflowRunRepository in UI Redesign.

    Methods:
        add: Persist a new execution
        get: Retrieve a single execution by ID
        list_by_workflow: List executions for a specific workflow
        update_status: Change the status of an execution
        delete: Remove an execution from storage
    """

    @abstractmethod
    def add(self, execution: Any) -> None:
        """Persist a new execution.

        Args:
            execution: Execution instance to persist

        Raises:
            IntegrityError: If execution ID already exists
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, execution_id: str) -> Optional[Any]:
        """Get an execution by ID.

        Args:
            execution_id: Unique identifier for the execution

        Returns:
            Execution if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def list_by_workflow(
        self, workflow_name: str, limit: int = 100
    ) -> List[Any]:
        """List executions for a specific workflow.

        Args:
            workflow_name: Name of the workflow to filter by
            limit: Maximum number of executions to return (default: 100)

        Returns:
            List of Execution instances, ordered by started_at DESC
        """
        raise NotImplementedError

    @abstractmethod
    def update_status(self, execution_id: str, status: str) -> None:
        """Update the status of an execution.

        Also sets completed_at timestamp when status is "completed" or "failed".

        Args:
            execution_id: Unique identifier for the execution
            status: New status value ("pending", "running", "completed", "failed")

        Raises:
            ValueError: If execution_id not found
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, execution_id: str) -> None:
        """Delete an execution.

        Args:
            execution_id: Unique identifier for the execution

        Raises:
            ValueError: If execution_id not found
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError


class AbstractExecutionStateRepository(ABC):
    """Abstract repository for execution state persistence.

    Provides storage and retrieval of workflow execution state checkpoints.
    State is saved after each node execution, enabling resume functionality
    and debugging.

    Methods:
        save_state: Save a state checkpoint after node execution
        get_latest_state: Get the most recent state for an execution
        get_state_history: Get all state checkpoints for an execution
    """

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def get_latest_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest state checkpoint for an execution.

        Args:
            execution_id: Unique identifier for the execution

        Returns:
            State dictionary if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError


class ChatSessionRepository(ABC):
    """Abstract repository for chat session persistence.

    Provides CRUD operations for chat sessions and messages used by
    the Gradio config generation UI. Supports conversation history
    persistence across browser sessions.

    Methods:
        create_session: Create a new chat session
        get_session: Retrieve a session by ID
        add_message: Add a message to a session
        get_messages: Get all messages for a session
        update_config: Save generated config to session
        list_recent_sessions: List recent sessions for a user
    """

    @abstractmethod
    def create_session(self, user_identifier: str) -> str:
        """Create a new chat session.

        Args:
            user_identifier: Browser fingerprint or IP for session tracking

        Returns:
            session_id: UUID of the created session
        """
        raise NotImplementedError

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID.

        Args:
            session_id: UUID of the session

        Returns:
            Dictionary with session data if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a session.

        Args:
            session_id: UUID of the session

        Returns:
            List of message dictionaries ordered by created_at ASC
        """
        raise NotImplementedError

    @abstractmethod
    def update_config(self, session_id: str, config_yaml: str) -> None:
        """Save generated config to session.

        Args:
            session_id: UUID of the session
            config_yaml: Generated YAML configuration

        Raises:
            ValueError: If session_id not found
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError


class WebhookEventRepository(ABC):
    """Abstract repository for webhook event idempotency tracking.

    Provides idempotency key storage to prevent replay attacks in webhook
    processing. Each webhook event has a unique webhook_id that is checked
    before processing.

    Methods:
        is_processed: Check if webhook event was already processed
        mark_processed: Record webhook as processed
        cleanup_old_events: Delete records older than N days
    """

    @abstractmethod
    def is_processed(self, webhook_id: str) -> bool:
        """Check if webhook event was already processed.

        Args:
            webhook_id: Unique identifier for the webhook event

        Returns:
            True if already processed, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def mark_processed(self, webhook_id: str, provider: str) -> None:
        """Record webhook as processed.

        Uses INSERT OR IGNORE for idempotency - calling this multiple times
        with the same webhook_id is safe.

        Args:
            webhook_id: Unique identifier for the webhook event
            provider: Name of the webhook provider (e.g., "whatsapp", "telegram")
        """
        raise NotImplementedError

    @abstractmethod
    def cleanup_old_events(self, days: int = 7) -> int:
        """Delete webhook event records older than N days.

        Args:
            days: Number of days to retain records (default: 7)

        Returns:
            Number of records deleted
        """
        raise NotImplementedError


class MemoryRepository(ABC):
    """Abstract repository for agent memory persistence.

    Provides key-value storage for agent memory with namespaced keys to prevent
    conflicts between agents, workflows, and nodes. Memory persists across
    workflow executions, enabling agents to maintain context over time.

    Methods:
        get: Retrieve a value by namespace key
        set: Store a value with namespace key (upsert semantics)
        delete: Remove a value by namespace key
        list: List all keys for an agent with optional prefix filtering
        clear: Clear all memory for an agent
        clear_by_workflow: Clear all memory for a specific workflow
    """

    @abstractmethod
    def get(self, namespace_key: str) -> Optional[str]:
        """Get a value by namespace key.

        Args:
            namespace_key: Combined namespace key (agent:workflow:node:key)

        Returns:
            JSON-serialized value if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def set(
        self,
        namespace_key: str,
        value: str,
        agent_id: str,
        workflow_id: Optional[str],
        node_id: Optional[str],
        key: str,
    ) -> None:
        """Store a value with namespace key.

        Uses upsert semantics - creates new record or updates existing.

        Args:
            namespace_key: Combined namespace key (agent:workflow:node:key)
            value: JSON-serialized value to store
            agent_id: Agent identifier
            workflow_id: Workflow identifier (optional)
            node_id: Node identifier (optional)
            key: User-facing key name
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, namespace_key: str) -> bool:
        """Delete a value by namespace key.

        Args:
            namespace_key: Combined namespace key (agent:workflow:node:key)

        Returns:
            True if record was deleted, False if not found
        """
        raise NotImplementedError

    @abstractmethod
    def list(self, agent_id: str, prefix: str = "") -> List[tuple[str, str]]:
        """List all keys for an agent with optional prefix filtering.

        Args:
            agent_id: Agent identifier to filter by
            prefix: Optional key prefix to filter results (e.g., "user:")

        Returns:
            List of (key, value) tuples matching the criteria
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self, agent_id: str) -> int:
        """Clear all memory for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Number of records deleted
        """
        raise NotImplementedError

    @abstractmethod
    def clear_by_workflow(self, agent_id: str, workflow_id: str) -> int:
        """Clear all memory for a specific workflow.

        Args:
            agent_id: Agent identifier
            workflow_id: Workflow identifier

        Returns:
            Number of records deleted
        """
        raise NotImplementedError


class WorkflowRegistrationRepository(ABC):
    """Abstract repository for webhook workflow registration.

    Manages workflow configurations registered for webhook triggering across
    different platforms (generic, WhatsApp, Telegram).

    Methods:
        register: Register a workflow for webhook triggering
        get: Get registration by workflow name
        list_all: List all registrations
        delete: Unregister a workflow
        get_by_method: Get workflows by platform/method
    """

    @abstractmethod
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
            allowed_methods: Optional list of allowed methods (generic, whatsapp, telegram)
            default_inputs: Optional dict of default input values
            rate_limit: Optional rate limit (requests per minute)

        Raises:
            ValueError: If workflow already registered
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Get workflow registration by name.

        Args:
            workflow_name: Unique workflow identifier

        Returns:
            Dictionary with registration data if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> List[Dict[str, Any]]:
        """List all workflow registrations.

        Returns:
            List of registration dictionaries
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, workflow_name: str) -> bool:
        """Unregister a workflow.

        Args:
            workflow_name: Unique workflow identifier

        Returns:
            True if registration was deleted, False if not found
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_method(self, method: str) -> List[Dict[str, Any]]:
        """Get workflows by platform/method.

        Args:
            method: Platform/method name (generic, whatsapp, telegram)

        Returns:
            List of registration dictionaries that allow this method
        """
        raise NotImplementedError
