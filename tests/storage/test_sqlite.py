"""Tests for SQLite storage repository implementation.

Tests all CRUD operations for executions and execution state
using temporary database files.

Updated in UI Redesign (2026-02-13):
- WorkflowRunRecord → Execution
- ExecutionStateRecord → ExecutionState
- SQLiteWorkflowRunRepository → SQLiteExecutionRepository
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from configurable_agents.storage.models import (
    Base,
    ExecutionState,
    Execution,
)
from configurable_agents.storage.sqlite import (
    SQLiteExecutionStateRepository,
    SQLiteExecutionRepository,
)


@pytest.fixture
def temp_engine(tmp_path):
    """Create a temporary SQLite database engine.

    Args:
        tmp_path: pytest fixture for temporary directory

    Returns:
        SQLAlchemy Engine instance
    """
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def execution_repo(temp_engine):
    """Create an execution repository with temporary database.

    Args:
        temp_engine: Engine fixture

    Returns:
        SQLiteExecutionRepository instance
    """
    return SQLiteExecutionRepository(temp_engine)


@pytest.fixture
def states_repo(temp_engine):
    """Create an execution state repository with temporary database.

    Args:
        temp_engine: Engine fixture

    Returns:
        SQLiteExecutionStateRepository instance
    """
    return SQLiteExecutionStateRepository(temp_engine)


class TestSQLiteExecutionRepo:
    """Tests for SQLiteExecutionRepository."""

    def test_add_and_get_execution(self, execution_repo) -> None:
        """Test adding an execution and retrieving it.

        Args:
            execution_repo: Repository fixture
        """
        execution = Execution(
            id="test-exec-1",
            workflow_name="test_workflow",
            status="pending",
        )

        execution_repo.add(execution)
        retrieved = execution_repo.get("test-exec-1")

        assert retrieved is not None
        assert retrieved.id == "test-exec-1"
        assert retrieved.workflow_name == "test_workflow"
        assert retrieved.status == "pending"

    def test_get_nonexistent_execution_returns_none(self, execution_repo) -> None:
        """Test that getting a non-existent execution returns None.

        Args:
            execution_repo: Repository fixture
        """
        result = execution_repo.get("nonexistent-id")
        assert result is None

    def test_list_by_workflow_ordered_by_started_at_desc(
        self, execution_repo
    ) -> None:
        """Test listing executions for a workflow ordered by started_at DESC.

        Args:
            execution_repo: Repository fixture
        """
        # Create executions with different timestamps
        exec1 = Execution(
            id="exec-1",
            workflow_name="test_workflow",
            status="completed",
            started_at=datetime(2025, 1, 1, 10, 0, 0),
        )
        exec2 = Execution(
            id="exec-2",
            workflow_name="test_workflow",
            status="running",
            started_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        exec3 = Execution(
            id="exec-3",
            workflow_name="test_workflow",
            status="pending",
            started_at=datetime(2025, 1, 1, 11, 0, 0),
        )

        execution_repo.add(exec1)
        execution_repo.add(exec2)
        execution_repo.add(exec3)

        # List should return executions ordered by started_at DESC (newest first)
        executions = execution_repo.list_by_workflow("test_workflow")

        assert len(executions) == 3
        assert executions[0].id == "exec-2"  # 12:00
        assert executions[1].id == "exec-3"  # 11:00
        assert executions[2].id == "exec-1"  # 10:00

    def test_list_by_workflow_with_limit(self, execution_repo) -> None:
        """Test listing executions with a limit applied.

        Args:
            execution_repo: Repository fixture
        """
        for i in range(5):
            execution = Execution(
                id=f"exec-{i}",
                workflow_name="test_workflow",
                status="pending",
            )
            execution_repo.add(execution)

        executions = execution_repo.list_by_workflow("test_workflow", limit=3)

        assert len(executions) == 3

    def test_list_by_workflow_filters_by_workflow_name(
        self, execution_repo
    ) -> None:
        """Test that listing only returns executions for specified workflow.

        Args:
            execution_repo: Repository fixture
        """
        exec1 = Execution(
            id="exec-1",
            workflow_name="workflow_a",
            status="pending",
        )
        exec2 = Execution(
            id="exec-2",
            workflow_name="workflow_b",
            status="pending",
        )

        execution_repo.add(exec1)
        execution_repo.add(exec2)

        execs_a = execution_repo.list_by_workflow("workflow_a")
        execs_b = execution_repo.list_by_workflow("workflow_b")

        assert len(execs_a) == 1
        assert execs_a[0].id == "exec-1"
        assert len(execs_b) == 1
        assert execs_b[0].id == "exec-2"

    def test_update_status_to_completed_sets_completed_at(
        self, execution_repo, temp_engine
    ) -> None:
        """Test that updating status to completed sets completed_at.

        Args:
            execution_repo: Repository fixture
            temp_engine: Engine fixture for direct query
        """
        execution = Execution(
            id="test-exec",
            workflow_name="test_workflow",
            status="running",
            completed_at=None,
        )
        execution_repo.add(execution)

        execution_repo.update_status("test-exec", "completed")

        # Verify the update
        with Session(temp_engine) as session:
            updated = session.get(Execution, "test-exec")
            assert updated.status == "completed"
            assert updated.completed_at is not None

    def test_update_status_to_failed_sets_completed_at(
        self, execution_repo, temp_engine
    ) -> None:
        """Test that updating status to failed sets completed_at.

        Args:
            execution_repo: Repository fixture
            temp_engine: Engine fixture for direct query
        """
        execution = Execution(
            id="test-exec",
            workflow_name="test_workflow",
            status="running",
            completed_at=None,
        )
        execution_repo.add(execution)

        execution_repo.update_status("test-exec", "failed")

        # Verify the update
        with Session(temp_engine) as session:
            updated = session.get(Execution, "test-exec")
            assert updated.status == "failed"
            assert updated.completed_at is not None

    def test_update_status_nonexistent_execution_raises_value_error(
        self, execution_repo
    ) -> None:
        """Test that updating status for non-existent execution raises ValueError.

        Args:
            execution_repo: Repository fixture
        """
        with pytest.raises(ValueError, match="Execution not found"):
            execution_repo.update_status("nonexistent", "completed")

    def test_delete_execution(self, execution_repo) -> None:
        """Test deleting an execution.

        Args:
            execution_repo: Repository fixture
        """
        execution = Execution(
            id="test-exec",
            workflow_name="test_workflow",
            status="completed",
        )
        execution_repo.add(execution)

        # Verify it exists
        assert execution_repo.get("test-exec") is not None

        # Delete it
        execution_repo.delete("test-exec")

        # Verify it's gone
        assert execution_repo.get("test-exec") is None

    def test_delete_nonexistent_execution_raises_value_error(self, execution_repo) -> None:
        """Test that deleting non-existent execution raises ValueError.

        Args:
            execution_repo: Repository fixture
        """
        with pytest.raises(ValueError, match="Execution not found"):
            execution_repo.delete("nonexistent")

    def test_update_execution_completion_with_all_fields(self, execution_repo, temp_engine) -> None:
        """Test that update_execution_completion sets all completion metrics.

        Args:
            execution_repo: Repository fixture
            temp_engine: Engine fixture for direct query
        """
        execution = Execution(
            id="test-exec",
            workflow_name="test_workflow",
            status="running",
        )
        execution_repo.add(execution)

        # Update with completion metrics
        execution_repo.update_execution_completion(
            execution_id="test-exec",
            status="completed",
            duration_seconds=5.5,
            total_tokens=1000,
            total_cost_usd=0.0015,
            outputs='{"result": "done"}',
        )

        # Verify the update
        with Session(temp_engine) as session:
            updated = session.get(Execution, "test-exec")
            assert updated.status == "completed"
            assert updated.completed_at is not None
            assert updated.duration_seconds == 5.5
            assert updated.total_tokens == 1000
            assert updated.total_cost_usd == 0.0015
            assert updated.outputs == '{"result": "done"}'

    def test_update_execution_completion_with_error_message(self, execution_repo, temp_engine) -> None:
        """Test that update_execution_completion sets error message on failure.

        Args:
            execution_repo: Repository fixture
            temp_engine: Engine fixture for direct query
        """
        execution = Execution(
            id="test-exec",
            workflow_name="test_workflow",
            status="running",
        )
        execution_repo.add(execution)

        # Update with failure status
        execution_repo.update_execution_completion(
            execution_id="test-exec",
            status="failed",
            duration_seconds=2.0,
            total_tokens=0,
            total_cost_usd=0.0,
            error_message="Something went wrong",
        )

        # Verify the update
        with Session(temp_engine) as session:
            updated = session.get(Execution, "test-exec")
            assert updated.status == "failed"
            assert updated.completed_at is not None
            assert updated.duration_seconds == 2.0
            assert updated.error_message == "Something went wrong"

    def test_update_execution_completion_nonexistent_raises_value_error(
        self, execution_repo
    ) -> None:
        """Test that updating completion for non-existent execution raises ValueError.

        Args:
            execution_repo: Repository fixture
        """
        with pytest.raises(ValueError, match="Execution not found"):
            execution_repo.update_execution_completion(
                execution_id="nonexistent",
                status="completed",
                duration_seconds=1.0,
                total_tokens=100,
                total_cost_usd=0.0001,
            )


class TestSQLiteExecutionStateRepo:
    """Tests for SQLiteExecutionStateRepository."""

    def test_save_and_get_latest_state(self, execution_repo, states_repo) -> None:
        """Test saving state and retrieving the latest.

        Args:
            execution_repo: Repository fixture for creating execution
            states_repo: State repository fixture
        """
        # First create an execution
        execution = Execution(
            id="test-exec",
            workflow_name="test_workflow",
            status="running",
        )
        execution_repo.add(execution)

        # Save state
        state_data = {"counter": 1, "message": "hello"}
        states_repo.save_state("test-exec", state_data, "node1")

        # Get latest state
        retrieved = states_repo.get_latest_state("test-exec")

        assert retrieved is not None
        assert retrieved == state_data

    def test_get_latest_state_nonexistent_execution_returns_none(
        self, execution_repo, states_repo
    ) -> None:
        """Test that getting state for non-existent execution returns None.

        Args:
            execution_repo: Repository fixture (not used)
            states_repo: State repository fixture
        """
        result = states_repo.get_latest_state("nonexistent-exec")
        assert result is None

    def test_save_state_for_nonexistent_execution_raises_value_error(
        self, states_repo
    ) -> None:
        """Test that saving state for non-existent execution raises ValueError.

        Args:
            states_repo: State repository fixture
        """
        with pytest.raises(ValueError, match="Execution not found"):
            states_repo.save_state("nonexistent-exec", {}, "node1")

    def test_get_state_history(self, execution_repo, states_repo) -> None:
        """Test retrieving full state history for an execution.

        Args:
            execution_repo: Repository fixture for creating execution
            states_repo: State repository fixture
        """
        # Create execution
        execution = Execution(
            id="test-exec",
            workflow_name="test_workflow",
            status="running",
        )
        execution_repo.add(execution)

        # Save multiple states
        states_repo.save_state("test-exec", {"step": 1}, "node1")
        states_repo.save_state("test-exec", {"step": 2}, "node2")
        states_repo.save_state("test-exec", {"step": 3}, "node3")

        # Get history
        history = states_repo.get_state_history("test-exec")

        assert len(history) == 3
        assert history[0]["node_id"] == "node1"
        assert history[0]["state_data"]["step"] == 1
        assert history[1]["node_id"] == "node2"
        assert history[1]["state_data"]["step"] == 2
        assert history[2]["node_id"] == "node3"
        assert history[2]["state_data"]["step"] == 3

    def test_get_state_history_empty_for_new_execution(self, execution_repo, states_repo) -> None:
        """Test that state history is empty for an execution with no states.

        Args:
            execution_repo: Repository fixture for creating execution
            states_repo: State repository fixture
        """
        execution = Execution(
            id="test-exec",
            workflow_name="test_workflow",
            status="running",
        )
        execution_repo.add(execution)

        history = states_repo.get_state_history("test-exec")

        assert history == []

    def test_get_state_history_round_trips_json(self, execution_repo, states_repo) -> None:
        """Test that state data survives JSON round-trip.

        Args:
            execution_repo: Repository fixture for creating execution
            states_repo: State repository fixture
        """
        execution = Execution(
            id="test-exec",
            workflow_name="test_workflow",
            status="running",
        )
        execution_repo.add(execution)

        # Complex state with nested structures
        original_state = {
            "numbers": [1, 2, 3],
            "nested": {"key": "value", "another": 42},
            "bool": True,
            "null": None,
        }

        states_repo.save_state("test-exec", original_state, "node1")

        history = states_repo.get_state_history("test-exec")

        assert len(history) == 1
        assert history[0]["state_data"] == original_state
