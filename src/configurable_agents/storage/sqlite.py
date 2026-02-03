"""SQLite implementation of storage repository interfaces.

Provides concrete implementations of AbstractWorkflowRunRepository and
AbstractExecutionStateRepository using SQLAlchemy 2.0 with SQLite backend.

All database operations use context manager pattern for automatic
transaction handling and connection cleanup.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Engine, Select, create_engine, select
from sqlalchemy.orm import Session

from configurable_agents.storage.base import (
    AbstractExecutionStateRepository,
    AbstractWorkflowRunRepository,
)
from configurable_agents.storage.models import (
    ExecutionStateRecord,
    WorkflowRunRecord,
)


class SQLiteWorkflowRunRepository(AbstractWorkflowRunRepository):
    """SQLite implementation of workflow run repository.

    Provides CRUD operations for WorkflowRunRecord using SQLite backend.
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

    def add(self, run: WorkflowRunRecord) -> None:
        """Persist a new workflow run.

        Args:
            run: WorkflowRunRecord instance to persist

        Raises:
            IntegrityError: If run ID already exists
        """
        with Session(self.engine) as session:
            session.add(run)
            session.commit()

    def get(self, run_id: str) -> Optional[WorkflowRunRecord]:
        """Get a workflow run by ID.

        Args:
            run_id: Unique identifier for the workflow run

        Returns:
            WorkflowRunRecord if found, None otherwise
        """
        with Session(self.engine) as session:
            return session.get(WorkflowRunRecord, run_id)

    def list_by_workflow(
        self, workflow_name: str, limit: int = 100
    ) -> List[WorkflowRunRecord]:
        """List runs for a specific workflow.

        Args:
            workflow_name: Name of the workflow to filter by
            limit: Maximum number of runs to return (default: 100)

        Returns:
            List of WorkflowRunRecord instances, ordered by started_at DESC
        """
        with Session(self.engine) as session:
            stmt: Select[WorkflowRunRecord] = (
                select(WorkflowRunRecord)
                .where(WorkflowRunRecord.workflow_name == workflow_name)
                .order_by(WorkflowRunRecord.started_at.desc())
                .limit(limit)
            )
            return list(session.scalars(stmt).all())

    def update_status(self, run_id: str, status: str) -> None:
        """Update the status of a workflow run.

        Also sets completed_at timestamp when status is "completed" or "failed".

        Args:
            run_id: Unique identifier for the workflow run
            status: New status value ("pending", "running", "completed", "failed")

        Raises:
            ValueError: If run_id not found
        """
        with Session(self.engine) as session:
            run = session.get(WorkflowRunRecord, run_id)
            if run is None:
                raise ValueError(f"Workflow run not found: {run_id}")

            run.status = status

            # Set completed_at for terminal states
            if status in ("completed", "failed"):
                run.completed_at = datetime.utcnow()

            session.commit()

    def delete(self, run_id: str) -> None:
        """Delete a workflow run.

        Args:
            run_id: Unique identifier for the workflow run

        Raises:
            ValueError: If run_id not found
        """
        with Session(self.engine) as session:
            run = session.get(WorkflowRunRecord, run_id)
            if run is None:
                raise ValueError(f"Workflow run not found: {run_id}")

            session.delete(run)
            session.commit()

    def update_run_completion(
        self,
        run_id: str,
        status: str,
        duration_seconds: float,
        total_tokens: int,
        total_cost_usd: float,
        outputs: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update a workflow run with completion metrics.

        Args:
            run_id: Unique identifier for the workflow run
            status: New status value ("completed" or "failed")
            duration_seconds: Execution time in seconds
            total_tokens: Total tokens used across all LLM calls
            total_cost_usd: Total estimated cost in USD
            outputs: JSON-serialized output data (optional)
            error_message: Error message if status is "failed" (optional)

        Raises:
            ValueError: If run_id not found
        """
        with Session(self.engine) as session:
            run = session.get(WorkflowRunRecord, run_id)
            if run is None:
                raise ValueError(f"Workflow run not found: {run_id}")

            run.status = status
            run.completed_at = datetime.utcnow()
            run.duration_seconds = duration_seconds
            run.total_tokens = total_tokens
            run.total_cost_usd = total_cost_usd

            if outputs is not None:
                run.outputs = outputs
            if error_message is not None:
                run.error_message = error_message

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
        self, run_id: str, state_data: Dict[str, Any], node_id: str
    ) -> None:
        """Save execution state checkpoint after a node.

        Args:
            run_id: Unique identifier for the workflow run
            state_data: Current workflow state as a dictionary
            node_id: ID of the node that produced this state

        Raises:
            ValueError: If run_id not found in workflow_runs
        """
        with Session(self.engine) as session:
            # Verify run exists
            run = session.get(WorkflowRunRecord, run_id)
            if run is None:
                raise ValueError(f"Workflow run not found: {run_id}")

            # Create state record
            record = ExecutionStateRecord(
                run_id=run_id,
                node_id=node_id,
                state_data=json.dumps(state_data),
            )
            session.add(record)
            session.commit()

    def get_latest_state(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest state checkpoint for a run.

        Args:
            run_id: Unique identifier for the workflow run

        Returns:
            State dictionary if found, None otherwise
        """
        with Session(self.engine) as session:
            stmt: Select[ExecutionStateRecord] = (
                select(ExecutionStateRecord)
                .where(ExecutionStateRecord.run_id == run_id)
                .order_by(ExecutionStateRecord.created_at.desc())
                .limit(1)
            )
            record = session.scalar(stmt)

            if record is None:
                return None

            return json.loads(record.state_data)

    def get_state_history(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all state checkpoints for a run.

        Args:
            run_id: Unique identifier for the workflow run

        Returns:
            List of state checkpoints, each containing:
            - node_id: Which node produced this state
            - state_data: The state dictionary (parsed from JSON)
            - created_at: Timestamp when checkpoint was saved
            Ordered by created_at ASC (oldest first)
        """
        with Session(self.engine) as session:
            stmt: Select[ExecutionStateRecord] = (
                select(ExecutionStateRecord)
                .where(ExecutionStateRecord.run_id == run_id)
                .order_by(ExecutionStateRecord.created_at.asc())
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
