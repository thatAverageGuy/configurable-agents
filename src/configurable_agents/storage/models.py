"""SQLAlchemy ORM models for storage layer.

Defines the database schema for executions, deployments, and execution state tracking.
Uses SQLAlchemy 2.0 DeclarativeBase pattern with Mapped/mapped_column syntax.

Renamed in UI Redesign (2026-02-13):
- WorkflowRunRecord → Execution (table: workflow_runs → executions)
- AgentRecord → Deployment (table: agents → deployments)
- OrchestratorRecord → REMOVED (absorbed into deployments)
- ExecutionStateRecord.run_id → execution_id
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


class Execution(Base):
    """ORM model for workflow execution records.

    Tracks metadata and results of workflow executions including status,
    timestamps, inputs/outputs, errors, token usage, and cost tracking.

    Renamed from WorkflowRunRecord in UI Redesign.

    Attributes:
        id: UUID primary key for the execution
        workflow_name: Name of the workflow being executed
        status: Current status ("pending", "running", "completed", "failed")
        config_snapshot: JSON-serialized workflow configuration
        inputs: JSON-serialized input data
        outputs: JSON-serialized output data
        error_message: Error message if status is "failed"
        started_at: When the execution started
        completed_at: When the execution completed (null if running)
        duration_seconds: Execution time in seconds
        total_tokens: Total tokens used across all LLM calls
        total_cost_usd: Total estimated cost in USD
        bottleneck_info: JSON-serialized bottleneck analysis data
        deployment_id: FK to deployments table (NULL for runtime executions)
    """

    __tablename__ = "executions"

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
    deployment_id: Mapped[Optional[str]] = mapped_column(
        String(255), ForeignKey("deployments.deployment_id"), nullable=True
    )


class ExecutionState(Base):
    """ORM model for execution state checkpoints.

    Stores workflow state after each node execution, enabling resume
    functionality and debugging.

    Renamed from ExecutionStateRecord in UI Redesign.
    Field run_id renamed to execution_id.

    Attributes:
        id: Auto-increment primary key
        execution_id: Foreign key to executions.id
        node_id: Which node produced this state
        state_data: JSON-serialized state dictionary
        created_at: When this checkpoint was created
    """

    __tablename__ = "execution_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("executions.id"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(String(128))
    state_data: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Deployment(Base):
    """ORM model for deployment registry records.

    Tracks registered deployments (Docker containers running workflows) in the system
    including their network location, heartbeat status for TTL-based expiration,
    and metadata.

    Renamed from AgentRecord in UI Redesign.
    Field names updated: agent_id → deployment_id, agent_name → deployment_name, etc.

    Attributes:
        deployment_id: Unique identifier for the deployment (primary key)
        deployment_name: Human-readable name for the deployment
        workflow_name: Name of the workflow this deployment runs
        host: Host address where the deployment is running
        port: Port number where the deployment is listening
        last_heartbeat: Timestamp of the last heartbeat from this deployment
        ttl_seconds: Time-to-live in seconds (default: 60)
        capabilities: JSON blob with capabilities (tools, features supported)
        deployment_metadata: JSON blob with additional deployment information
        registered_at: When the deployment first registered
    """

    __tablename__ = "deployments"

    deployment_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    deployment_name: Mapped[str] = mapped_column(String(256))
    workflow_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    host: Mapped[str] = mapped_column(String(256))
    port: Mapped[int] = mapped_column(Integer)
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    ttl_seconds: Mapped[int] = mapped_column(Integer, default=60)
    capabilities: Mapped[Optional[str]] = mapped_column(String(4000), nullable=True)
    deployment_metadata: Mapped[Optional[str]] = mapped_column(String(4000), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs: object) -> None:
        """Initialize Deployment with default TTL and heartbeat if not provided."""
        ttl_seconds = kwargs.pop("ttl_seconds", 60)
        kwargs["ttl_seconds"] = ttl_seconds
        if "last_heartbeat" not in kwargs:
            kwargs["last_heartbeat"] = datetime.utcnow()
        if "registered_at" not in kwargs:
            kwargs["registered_at"] = datetime.utcnow()
        super().__init__(**kwargs)

    def is_alive(self) -> bool:
        """Check if this deployment is still alive based on TTL.

        A deployment is considered alive if the current time is before
        the expiration time (last_heartbeat + ttl_seconds).

        Returns:
            True if deployment is alive, False if expired
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


class SessionState(Base):
    """ORM model for session state persistence and crash detection.

    Tracks the current session state across application restarts, enabling
    crash detection and recovery. A single row should exist with id='default'.

    Attributes:
        id: Primary key, always 'default' for singleton pattern
        session_start: When the current session started
        dirty_shutdown: True if previous session crashed (not cleanly shut down)
        active_workflows: JSON list of workflow IDs that were running
        session_data: JSON blob for additional session state (chat history, filters, etc.)
        last_updated: Timestamp of last state update
    """

    __tablename__ = "session_state"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="default")
    session_start: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    dirty_shutdown: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # Boolean as int
    active_workflows: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    session_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON dict
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def is_dirty(self) -> bool:
        """Check if previous shutdown was dirty (crash)."""
        return bool(self.dirty_shutdown)

    def mark_clean(self) -> None:
        """Mark shutdown as clean."""
        self.dirty_shutdown = 0
        self.active_workflows = None
