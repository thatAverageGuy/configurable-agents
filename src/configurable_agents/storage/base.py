"""Abstract repository interfaces for storage backend.

Defines the pluggable storage abstraction layer following the Repository Pattern.
Implementations can be SQLite, PostgreSQL, Redis, or any other backend that
implements these interfaces.

See https://www.cosmicpython.com/book/chapter_02_repository.html for pattern
reference.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

# Forward declarations for ORM models (avoiding circular import)
# WorkflowRunRecord and ExecutionStateRecord are defined in models.py


class AbstractWorkflowRunRepository(ABC):
    """Abstract repository for workflow run persistence.

    Provides CRUD operations for workflow execution records. Implementations
    must handle persistence, retrieval, and querying of workflow runs.

    Methods:
        add: Persist a new workflow run
        get: Retrieve a single run by ID
        list_by_workflow: List runs for a specific workflow
        update_status: Change the status of a run
        delete: Remove a run from storage
    """

    @abstractmethod
    def add(self, run: Any) -> None:
        """Persist a new workflow run.

        Args:
            run: WorkflowRunRecord instance to persist

        Raises:
            IntegrityError: If run ID already exists
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, run_id: str) -> Optional[Any]:
        """Get a workflow run by ID.

        Args:
            run_id: Unique identifier for the workflow run

        Returns:
            WorkflowRunRecord if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def list_by_workflow(
        self, workflow_name: str, limit: int = 100
    ) -> List[Any]:
        """List runs for a specific workflow.

        Args:
            workflow_name: Name of the workflow to filter by
            limit: Maximum number of runs to return (default: 100)

        Returns:
            List of WorkflowRunRecord instances, ordered by started_at DESC
        """
        raise NotImplementedError

    @abstractmethod
    def update_status(self, run_id: str, status: str) -> None:
        """Update the status of a workflow run.

        Also sets completed_at timestamp when status is "completed" or "failed".

        Args:
            run_id: Unique identifier for the workflow run
            status: New status value ("pending", "running", "completed", "failed")

        Raises:
            ValueError: If run_id not found
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, run_id: str) -> None:
        """Delete a workflow run.

        Args:
            run_id: Unique identifier for the workflow run

        Raises:
            ValueError: If run_id not found
        """
        raise NotImplementedError


class AbstractExecutionStateRepository(ABC):
    """Abstract repository for execution state persistence.

    Provides storage and retrieval of workflow execution state checkpoints.
    State is saved after each node execution, enabling resume functionality
    and debugging.

    Methods:
        save_state: Save a state checkpoint after node execution
        get_latest_state: Get the most recent state for a run
        get_state_history: Get all state checkpoints for a run
    """

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def get_latest_state(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest state checkpoint for a run.

        Args:
            run_id: Unique identifier for the workflow run

        Returns:
            State dictionary if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError
