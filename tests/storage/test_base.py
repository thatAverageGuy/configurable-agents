"""Tests for abstract storage repository interfaces.

Tests that abstract interfaces enforce correct usage and cannot be
instantiated directly without implementation.

Updated in UI Redesign (2026-02-13):
- AbstractWorkflowRunRepository → AbstractExecutionRepository
"""

import pytest

from configurable_agents.storage.base import (
    AbstractExecutionStateRepository,
    AbstractExecutionRepository,
)


class TestAbstractExecutionRepository:
    """Tests for AbstractExecutionRepository."""

    def test_cannot_instantiate_abstract_execution_repository(self) -> None:
        """Test that abstract repository cannot be instantiated directly."""
        with pytest.raises(TypeError, match="abstract"):
            AbstractExecutionRepository()  # type: ignore

    def test_concrete_implementation_can_be_instantiated(self) -> None:
        """Test that concrete implementation with all methods can be instantiated."""

        class ConcreteRepo(AbstractExecutionRepository):
            """Complete implementation of all abstract methods."""

            def add(self, execution) -> None:
                pass

            def get(self, execution_id: str):
                return None

            def list_by_workflow(self, workflow_name: str, limit: int = 100):
                return []

            def update_status(self, execution_id: str, status: str) -> None:
                pass

            def delete(self, execution_id: str) -> None:
                pass

            def update_execution_completion(
                self,
                execution_id: str,
                status: str,
                duration_seconds: float,
                total_tokens: int,
                total_cost_usd: float,
                outputs: str = None,
                error_message: str = None,
                bottleneck_info: str = None,
            ) -> None:
                pass

        # Should not raise
        repo = ConcreteRepo()
        assert repo is not None


class TestAbstractExecutionStateRepository:
    """Tests for AbstractExecutionStateRepository."""

    def test_cannot_instantiate_abstract_execution_state_repository(
        self,
    ) -> None:
        """Test that abstract repository cannot be instantiated directly."""
        with pytest.raises(TypeError, match="abstract"):
            AbstractExecutionStateRepository()  # type: ignore

    def test_concrete_implementation_can_be_instantiated(self) -> None:
        """Test that concrete implementation with all methods can be instantiated."""

        class ConcreteRepo(AbstractExecutionStateRepository):
            """Complete implementation of all abstract methods."""

            def save_state(self, execution_id: str, state_data, node_id: str) -> None:
                pass

            def get_latest_state(self, execution_id: str):
                return None

            def get_state_history(self, execution_id: str):
                return []

        # Should not raise
        repo = ConcreteRepo()
        assert repo is not None
