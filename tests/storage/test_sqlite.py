"""Tests for SQLite storage repository implementation.

Tests all CRUD operations for workflow runs and execution state
using temporary database files.
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from configurable_agents.storage.models import (
    Base,
    ExecutionStateRecord,
    WorkflowRunRecord,
)
from configurable_agents.storage.sqlite import (
    SQLiteExecutionStateRepository,
    SQLiteWorkflowRunRepository,
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
def runs_repo(temp_engine):
    """Create a workflow run repository with temporary database.

    Args:
        temp_engine: Engine fixture

    Returns:
        SQLiteWorkflowRunRepository instance
    """
    return SQLiteWorkflowRunRepository(temp_engine)


@pytest.fixture
def states_repo(temp_engine):
    """Create an execution state repository with temporary database.

    Args:
        temp_engine: Engine fixture

    Returns:
        SQLiteExecutionStateRepository instance
    """
    return SQLiteExecutionStateRepository(temp_engine)


class TestSQLiteWorkflowRunRepo:
    """Tests for SQLiteWorkflowRunRepository."""

    def test_add_and_get_workflow_run(self, runs_repo) -> None:
        """Test adding a workflow run and retrieving it.

        Args:
            runs_repo: Repository fixture
        """
        run = WorkflowRunRecord(
            id="test-run-1",
            workflow_name="test_workflow",
            status="pending",
        )

        runs_repo.add(run)
        retrieved = runs_repo.get("test-run-1")

        assert retrieved is not None
        assert retrieved.id == "test-run-1"
        assert retrieved.workflow_name == "test_workflow"
        assert retrieved.status == "pending"

    def test_get_nonexistent_run_returns_none(self, runs_repo) -> None:
        """Test that getting a non-existent run returns None.

        Args:
            runs_repo: Repository fixture
        """
        result = runs_repo.get("nonexistent-id")
        assert result is None

    def test_list_by_workflow_ordered_by_started_at_desc(
        self, runs_repo
    ) -> None:
        """Test listing runs for a workflow ordered by started_at DESC.

        Args:
            runs_repo: Repository fixture
        """
        # Create runs with different timestamps
        run1 = WorkflowRunRecord(
            id="run-1",
            workflow_name="test_workflow",
            status="completed",
            started_at=datetime(2025, 1, 1, 10, 0, 0),
        )
        run2 = WorkflowRunRecord(
            id="run-2",
            workflow_name="test_workflow",
            status="running",
            started_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        run3 = WorkflowRunRecord(
            id="run-3",
            workflow_name="test_workflow",
            status="pending",
            started_at=datetime(2025, 1, 1, 11, 0, 0),
        )

        runs_repo.add(run1)
        runs_repo.add(run2)
        runs_repo.add(run3)

        # List should return runs ordered by started_at DESC (newest first)
        runs = runs_repo.list_by_workflow("test_workflow")

        assert len(runs) == 3
        assert runs[0].id == "run-2"  # 12:00
        assert runs[1].id == "run-3"  # 11:00
        assert runs[2].id == "run-1"  # 10:00

    def test_list_by_workflow_with_limit(self, runs_repo) -> None:
        """Test listing runs with a limit applied.

        Args:
            runs_repo: Repository fixture
        """
        for i in range(5):
            run = WorkflowRunRecord(
                id=f"run-{i}",
                workflow_name="test_workflow",
                status="pending",
            )
            runs_repo.add(run)

        runs = runs_repo.list_by_workflow("test_workflow", limit=3)

        assert len(runs) == 3

    def test_list_by_workflow_filters_by_workflow_name(
        self, runs_repo
    ) -> None:
        """Test that listing only returns runs for specified workflow.

        Args:
            runs_repo: Repository fixture
        """
        run1 = WorkflowRunRecord(
            id="run-1",
            workflow_name="workflow_a",
            status="pending",
        )
        run2 = WorkflowRunRecord(
            id="run-2",
            workflow_name="workflow_b",
            status="pending",
        )

        runs_repo.add(run1)
        runs_repo.add(run2)

        runs_a = runs_repo.list_by_workflow("workflow_a")
        runs_b = runs_repo.list_by_workflow("workflow_b")

        assert len(runs_a) == 1
        assert runs_a[0].id == "run-1"
        assert len(runs_b) == 1
        assert runs_b[0].id == "run-2"

    def test_update_status_to_completed_sets_completed_at(
        self, runs_repo, temp_engine
    ) -> None:
        """Test that updating status to completed sets completed_at.

        Args:
            runs_repo: Repository fixture
            temp_engine: Engine fixture for direct query
        """
        run = WorkflowRunRecord(
            id="test-run",
            workflow_name="test_workflow",
            status="running",
            completed_at=None,
        )
        runs_repo.add(run)

        runs_repo.update_status("test-run", "completed")

        # Verify the update
        with Session(temp_engine) as session:
            updated = session.get(WorkflowRunRecord, "test-run")
            assert updated.status == "completed"
            assert updated.completed_at is not None

    def test_update_status_to_failed_sets_completed_at(
        self, runs_repo, temp_engine
    ) -> None:
        """Test that updating status to failed sets completed_at.

        Args:
            runs_repo: Repository fixture
            temp_engine: Engine fixture for direct query
        """
        run = WorkflowRunRecord(
            id="test-run",
            workflow_name="test_workflow",
            status="running",
            completed_at=None,
        )
        runs_repo.add(run)

        runs_repo.update_status("test-run", "failed")

        # Verify the update
        with Session(temp_engine) as session:
            updated = session.get(WorkflowRunRecord, "test-run")
            assert updated.status == "failed"
            assert updated.completed_at is not None

    def test_update_status_nonexistent_run_raises_value_error(
        self, runs_repo
    ) -> None:
        """Test that updating status for non-existent run raises ValueError.

        Args:
            runs_repo: Repository fixture
        """
        with pytest.raises(ValueError, match="Workflow run not found"):
            runs_repo.update_status("nonexistent", "completed")

    def test_delete_workflow_run(self, runs_repo) -> None:
        """Test deleting a workflow run.

        Args:
            runs_repo: Repository fixture
        """
        run = WorkflowRunRecord(
            id="test-run",
            workflow_name="test_workflow",
            status="completed",
        )
        runs_repo.add(run)

        # Verify it exists
        assert runs_repo.get("test-run") is not None

        # Delete it
        runs_repo.delete("test-run")

        # Verify it's gone
        assert runs_repo.get("test-run") is None

    def test_delete_nonexistent_run_raises_value_error(self, runs_repo) -> None:
        """Test that deleting non-existent run raises ValueError.

        Args:
            runs_repo: Repository fixture
        """
        with pytest.raises(ValueError, match="Workflow run not found"):
            runs_repo.delete("nonexistent")

    def test_update_run_completion_with_all_fields(self, runs_repo, temp_engine) -> None:
        """Test that update_run_completion sets all completion metrics.

        Args:
            runs_repo: Repository fixture
            temp_engine: Engine fixture for direct query
        """
        run = WorkflowRunRecord(
            id="test-run",
            workflow_name="test_workflow",
            status="running",
        )
        runs_repo.add(run)

        # Update with completion metrics
        runs_repo.update_run_completion(
            run_id="test-run",
            status="completed",
            duration_seconds=5.5,
            total_tokens=1000,
            total_cost_usd=0.0015,
            outputs='{"result": "done"}',
        )

        # Verify the update
        with Session(temp_engine) as session:
            updated = session.get(WorkflowRunRecord, "test-run")
            assert updated.status == "completed"
            assert updated.completed_at is not None
            assert updated.duration_seconds == 5.5
            assert updated.total_tokens == 1000
            assert updated.total_cost_usd == 0.0015
            assert updated.outputs == '{"result": "done"}'

    def test_update_run_completion_with_error_message(self, runs_repo, temp_engine) -> None:
        """Test that update_run_completion sets error message on failure.

        Args:
            runs_repo: Repository fixture
            temp_engine: Engine fixture for direct query
        """
        run = WorkflowRunRecord(
            id="test-run",
            workflow_name="test_workflow",
            status="running",
        )
        runs_repo.add(run)

        # Update with failure status
        runs_repo.update_run_completion(
            run_id="test-run",
            status="failed",
            duration_seconds=2.0,
            total_tokens=0,
            total_cost_usd=0.0,
            error_message="Something went wrong",
        )

        # Verify the update
        with Session(temp_engine) as session:
            updated = session.get(WorkflowRunRecord, "test-run")
            assert updated.status == "failed"
            assert updated.completed_at is not None
            assert updated.duration_seconds == 2.0
            assert updated.error_message == "Something went wrong"

    def test_update_run_completion_nonexistent_run_raises_value_error(
        self, runs_repo
    ) -> None:
        """Test that updating completion for non-existent run raises ValueError.

        Args:
            runs_repo: Repository fixture
        """
        with pytest.raises(ValueError, match="Workflow run not found"):
            runs_repo.update_run_completion(
                run_id="nonexistent",
                status="completed",
                duration_seconds=1.0,
                total_tokens=100,
                total_cost_usd=0.0001,
            )


class TestSQLiteExecutionStateRepo:
    """Tests for SQLiteExecutionStateRepository."""

    def test_save_and_get_latest_state(self, runs_repo, states_repo) -> None:
        """Test saving state and retrieving the latest.

        Args:
            runs_repo: Repository fixture for creating run
            states_repo: State repository fixture
        """
        # First create a workflow run
        run = WorkflowRunRecord(
            id="test-run",
            workflow_name="test_workflow",
            status="running",
        )
        runs_repo.add(run)

        # Save state
        state_data = {"counter": 1, "message": "hello"}
        states_repo.save_state("test-run", state_data, "node1")

        # Get latest state
        retrieved = states_repo.get_latest_state("test-run")

        assert retrieved is not None
        assert retrieved == state_data

    def test_get_latest_state_nonexistent_run_returns_none(
        self, runs_repo, states_repo
    ) -> None:
        """Test that getting state for non-existent run returns None.

        Args:
            runs_repo: Repository fixture (not used)
            states_repo: State repository fixture
        """
        result = states_repo.get_latest_state("nonexistent-run")
        assert result is None

    def test_save_state_for_nonexistent_run_raises_value_error(
        self, states_repo
    ) -> None:
        """Test that saving state for non-existent run raises ValueError.

        Args:
            states_repo: State repository fixture
        """
        with pytest.raises(ValueError, match="Workflow run not found"):
            states_repo.save_state("nonexistent-run", {}, "node1")

    def test_get_state_history(self, runs_repo, states_repo) -> None:
        """Test retrieving full state history for a run.

        Args:
            runs_repo: Repository fixture for creating run
            states_repo: State repository fixture
        """
        # Create workflow run
        run = WorkflowRunRecord(
            id="test-run",
            workflow_name="test_workflow",
            status="running",
        )
        runs_repo.add(run)

        # Save multiple states
        states_repo.save_state("test-run", {"step": 1}, "node1")
        states_repo.save_state("test-run", {"step": 2}, "node2")
        states_repo.save_state("test-run", {"step": 3}, "node3")

        # Get history
        history = states_repo.get_state_history("test-run")

        assert len(history) == 3
        assert history[0]["node_id"] == "node1"
        assert history[0]["state_data"]["step"] == 1
        assert history[1]["node_id"] == "node2"
        assert history[1]["state_data"]["step"] == 2
        assert history[2]["node_id"] == "node3"
        assert history[2]["state_data"]["step"] == 3

    def test_get_state_history_empty_for_new_run(self, runs_repo, states_repo) -> None:
        """Test that state history is empty for a run with no states.

        Args:
            runs_repo: Repository fixture for creating run
            states_repo: State repository fixture
        """
        run = WorkflowRunRecord(
            id="test-run",
            workflow_name="test_workflow",
            status="running",
        )
        runs_repo.add(run)

        history = states_repo.get_state_history("test-run")

        assert history == []

    def test_get_state_history_round_trips_json(self, runs_repo, states_repo) -> None:
        """Test that state data survives JSON round-trip.

        Args:
            runs_repo: Repository fixture for creating run
            states_repo: State repository fixture
        """
        run = WorkflowRunRecord(
            id="test-run",
            workflow_name="test_workflow",
            status="running",
        )
        runs_repo.add(run)

        # Complex state with nested structures
        original_state = {
            "numbers": [1, 2, 3],
            "nested": {"key": "value", "another": 42},
            "bool": True,
            "null": None,
        }

        states_repo.save_state("test-run", original_state, "node1")

        history = states_repo.get_state_history("test-run")

        assert len(history) == 1
        assert history[0]["state_data"] == original_state
