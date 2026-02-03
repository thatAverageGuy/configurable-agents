"""SQLAlchemy ORM models for storage layer.

Defines the database schema for workflow runs and execution state tracking.
Uses SQLAlchemy 2.0 DeclarativeBase pattern with Mapped/mapped_column syntax.
"""

from datetime import datetime
from typing import Optional

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
