"""SQLAlchemy ORM models for storage layer.

Defines the database schema for workflow runs and execution state tracking.
Uses SQLAlchemy 2.0 DeclarativeBase pattern with Mapped/mapped_column syntax.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models.

    Uses SQLAlchemy 2.0 DeclarativeBase pattern.
    All models inherit from this class to gain ORM capabilities.
    """

    pass


class WorkflowRunRecord(Base):
    """ORM model for workflow execution records.

    Tracks metadata and results of workflow executions including status,
    timestamps, inputs/outputs, errors, token usage, and cost tracking.

    Attributes:
        id: UUID primary key for the run
        workflow_name: Name of the workflow being executed
        status: Current status ("pending", "running", "completed", "failed")
        config_snapshot: JSON-serialized workflow configuration
        inputs: JSON-serialized input data
        outputs: JSON-serialized output data
        error_message: Error message if status is "failed"
        started_at: When the run started
        completed_at: When the run completed (null if running)
        duration_seconds: Execution time in seconds
        total_tokens: Total tokens used across all LLM calls
        total_cost_usd: Total estimated cost in USD
        bottleneck_info: JSON-serialized bottleneck analysis data
    """

    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workflow_name: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32))
    config_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inputs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outputs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bottleneck_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ExecutionStateRecord(Base):
    """ORM model for execution state checkpoints.

    Stores workflow state after each node execution, enabling resume
    functionality and debugging.

    Attributes:
        id: Auto-increment primary key
        run_id: Foreign key to workflow_runs.id
        node_id: Which node produced this state
        state_data: JSON-serialized state dictionary
        created_at: When this checkpoint was created
    """

    __tablename__ = "execution_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_runs.id"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(String(128))
    state_data: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentRecord(Base):
    """ORM model for agent registry records.

    Tracks registered agents in the system including their network location,
    heartbeat status for TTL-based expiration, and metadata.

    Attributes:
        agent_id: Unique identifier for the agent (primary key)
        agent_name: Human-readable name for the agent
        host: Host address where the agent is running
        port: Port number where the agent is listening
        last_heartbeat: Timestamp of the last heartbeat from this agent
        ttl_seconds: Time-to-live in seconds (default: 60)
        agent_metadata: JSON blob with additional agent information
        registered_at: When the agent first registered
    """

    __tablename__ = "agents"

    agent_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(256))
    host: Mapped[str] = mapped_column(String(256))
    port: Mapped[int] = mapped_column(Integer)
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    ttl_seconds: Mapped[int] = mapped_column(Integer, default=60)
    agent_metadata: Mapped[Optional[str]] = mapped_column(String(4000), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs: object) -> None:
        """Initialize AgentRecord with default TTL and heartbeat if not provided."""
        ttl_seconds = kwargs.pop("ttl_seconds", 60)
        kwargs["ttl_seconds"] = ttl_seconds
        if "last_heartbeat" not in kwargs:
            kwargs["last_heartbeat"] = datetime.utcnow()
        if "registered_at" not in kwargs:
            kwargs["registered_at"] = datetime.utcnow()
        super().__init__(**kwargs)

    def is_alive(self) -> bool:
        """Check if this agent is still alive based on TTL.

        An agent is considered alive if the current time is before
        the expiration time (last_heartbeat + ttl_seconds).

        Returns:
            True if agent is alive, False if expired
        """
        ttl = self.ttl_seconds if self.ttl_seconds is not None else 60
        expiration_time = self.last_heartbeat + timedelta(seconds=ttl)
        return datetime.utcnow() < expiration_time


class ChatSession(Base):
    """ORM model for chat session storage.

    Tracks a user's conversation history across multiple messages
    for config generation. Sessions persist to enable context-aware
    config generation and cross-device recovery.

    Attributes:
        session_id: UUID primary key for the session
        user_identifier: Browser fingerprint or IP for session continuity
        created_at: When the session was created
        updated_at: Last message timestamp (auto-updated)
        generated_config: Final YAML config (null until generated)
        status: Session status ("in_progress", "completed", "abandoned")
    """

    __tablename__ = "chat_sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_identifier: Mapped[str] = mapped_column(String(256), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    generated_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="in_progress")

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary representation.

        Returns:
            Dictionary with session data
        """
        return {
            "session_id": self.session_id,
            "user_identifier": self.user_identifier,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "generated_config": self.generated_config,
            "status": self.status,
        }


class ChatMessage(Base):
    """ORM model for individual chat messages.

    Stores user and assistant messages in order within a session.
    Each message is part of a ChatSession.

    Attributes:
        id: Auto-increment primary key
        session_id: Foreign key to chat_sessions.session_id
        role: Message role ("user" or "assistant")
        content: Message content text
        created_at: When the message was created
        metadata: JSON blob for LLM metadata (model, tokens, cost, etc.)
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.session_id")
    )
    role: Mapped[str] = mapped_column(String(32))  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    message_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON (renamed from 'metadata' to avoid SQLAlchemy reserved word)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary representation.

        Returns:
            Dictionary with message data including parsed metadata
        """
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": json.loads(self.message_metadata) if self.message_metadata else None,
        }


class WebhookEventRecord(Base):
    """ORM model for webhook event idempotency tracking.

    Tracks processed webhook events to prevent replay attacks. Each webhook
    should have a unique idempotency key (webhook_id) that is stored before
    processing. If the same webhook_id is received again, it's a replay attack.

    Attributes:
        id: Auto-increment primary key
        webhook_id: Unique identifier for the webhook event (from external provider)
        provider: Name of the webhook provider (e.g., "whatsapp", "telegram", "generic")
        processed_at: When the webhook was processed
    """

    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    webhook_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class MemoryRecord(Base):
    """ORM model for persistent agent memory storage.

    Stores key-value pairs for agent memory with namespaced keys to prevent
    conflicts between agents, workflows, and nodes. Memory persists across
    workflow executions, enabling agents to maintain context over time.

    Attributes:
        id: Auto-increment primary key
        agent_id: Agent identifier (indexed for filtering)
        workflow_id: Workflow identifier (optional, indexed for filtering)
        node_id: Node identifier (optional, indexed for filtering)
        key: User-facing key name (indexed)
        namespace_key: Combined namespace key "agent:workflow:node:key" (unique, indexed)
        value: JSON-serialized value
        created_at: When the memory entry was created
        updated_at: When the memory entry was last updated
    """

    __tablename__ = "memory_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    node_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    namespace_key: Mapped[str] = mapped_column(String(1000), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class WorkflowRegistrationRecord(Base):
    """ORM model for webhook workflow registration.

    Tracks workflow configurations registered for webhook triggering across
    different platforms (generic, WhatsApp, Telegram).

    Attributes:
        workflow_name: Unique workflow identifier (primary key)
        webhook_secret: Optional secret for HMAC signature validation
        description: Optional human-readable description
        allowed_methods: JSON list of allowed webhook methods (generic, whatsapp, telegram)
        default_inputs: JSON dict of default input values
        rate_limit: Optional rate limit (requests per minute)
        enabled: Whether registration is active
        created_at: When the workflow was registered
    """

    __tablename__ = "workflow_registrations"

    workflow_name: Mapped[str] = mapped_column(String(255), primary_key=True, nullable=False)
    webhook_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    allowed_methods: Mapped[str] = mapped_column(String(1000), nullable=False, default="[]")  # JSON list
    default_inputs: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON dict
    rate_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Integer, nullable=False, default=1)  # Boolean as int
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert registration to dictionary representation.

        Returns:
            Dictionary with registration data including parsed JSON fields
        """
        return {
            "workflow_name": self.workflow_name,
            "webhook_secret": self.webhook_secret,
            "description": self.description,
            "allowed_methods": json.loads(self.allowed_methods) if self.allowed_methods else [],
            "default_inputs": json.loads(self.default_inputs) if self.default_inputs else {},
            "rate_limit": self.rate_limit,
            "enabled": bool(self.enabled),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class OrchestratorRecord(Base):
    """ORM model for orchestrator registration records.

    Tracks orchestrators that have registered with the agent registry.
    Orchestrators can discover and coordinate agents bidirectionally.

    Attributes:
        orchestrator_id: Unique identifier for the orchestrator (primary key)
        orchestrator_name: Human-readable name for the orchestrator
        orchestrator_type: Type of orchestrator (e.g., "central", "distributed")
        api_endpoint: URL where the orchestrator exposes its API
        last_heartbeat: Timestamp of the last heartbeat from this orchestrator
        ttl_seconds: Time-to-live in seconds (default: 300 - 5 minutes)
        registered_at: When the orchestrator first registered
    """

    __tablename__ = "orchestrators"

    orchestrator_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    orchestrator_name: Mapped[str] = mapped_column(String(256))
    orchestrator_type: Mapped[str] = mapped_column(String(64))  # e.g., "central", "distributed"
    api_endpoint: Mapped[str] = mapped_column(String(500))  # URL for orchestrator API
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    ttl_seconds: Mapped[int] = mapped_column(Integer, default=300)  # 5 minutes default
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs: object) -> None:
        """Initialize OrchestratorRecord with defaults."""
        ttl_seconds = kwargs.pop("ttl_seconds", 300)
        kwargs["ttl_seconds"] = ttl_seconds
        if "last_heartbeat" not in kwargs:
            kwargs["last_heartbeat"] = datetime.utcnow()
        if "registered_at" not in kwargs:
            kwargs["registered_at"] = datetime.utcnow()
        super().__init__(**kwargs)

    def is_alive(self) -> bool:
        """Check if this orchestrator is still alive based on TTL.

        An orchestrator is considered alive if the current time is before
        the expiration time (last_heartbeat + ttl_seconds).

        Returns:
            True if orchestrator is alive, False if expired
        """
        ttl = self.ttl_seconds if self.ttl_seconds is not None else 300
        expiration_time = self.last_heartbeat + timedelta(seconds=ttl)
        return datetime.utcnow() < expiration_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert orchestrator to dictionary representation.

        Returns:
            Dictionary with orchestrator data
        """
        return {
            "orchestrator_id": self.orchestrator_id,
            "orchestrator_name": self.orchestrator_name,
            "orchestrator_type": self.orchestrator_type,
            "api_endpoint": self.api_endpoint,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "ttl_seconds": self.ttl_seconds,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "is_alive": self.is_alive(),
        }
