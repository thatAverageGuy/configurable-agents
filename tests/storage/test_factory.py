"""Tests for storage backend factory function.

Tests that the factory correctly creates repositories based on
configuration and handles errors appropriately.

Updated in UI Redesign (2026-02-13):
- SQLiteWorkflowRunRepository → SQLiteExecutionRepository
- Returns 7 repositories (removed orchestrator)
- Table names: workflow_runs → executions, agents → deployments
"""

import pytest
from sqlalchemy import inspect

from configurable_agents.config.schema import StorageConfig
from configurable_agents.storage import create_storage_backend
from configurable_agents.storage.sqlite import (
    SQLiteExecutionStateRepository,
    SQLiteExecutionRepository,
    SqliteDeploymentRepository,
)


class TestFactory:
    """Tests for create_storage_backend factory function."""

    def test_default_config_creates_sqlite_repos(self, tmp_path) -> None:
        """Test that default config creates SQLite repositories.

        Args:
            tmp_path: pytest fixture for temporary directory
        """
        # Use default config (None) - returns 7 repos (no orchestrator)
        (
            execution_repo,
            states_repo,
            deployment_repo,
            chat_repo,
            webhook_repo,
            memory_repo,
            workflow_reg_repo,
        ) = create_storage_backend()

        assert isinstance(execution_repo, SQLiteExecutionRepository)
        assert isinstance(states_repo, SQLiteExecutionStateRepository)
        assert isinstance(deployment_repo, SqliteDeploymentRepository)

    def test_explicit_sqlite_config_creates_repos(self, tmp_path) -> None:
        """Test that explicit SQLite config creates repositories.

        Args:
            tmp_path: pytest fixture for temporary directory
        """
        db_path = tmp_path / "test.db"
        config = StorageConfig(backend="sqlite", path=str(db_path))

        (
            execution_repo,
            states_repo,
            deployment_repo,
            chat_repo,
            webhook_repo,
            memory_repo,
            workflow_reg_repo,
        ) = create_storage_backend(config)

        assert isinstance(execution_repo, SQLiteExecutionRepository)
        assert isinstance(states_repo, SQLiteExecutionStateRepository)
        assert isinstance(deployment_repo, SqliteDeploymentRepository)

    def test_factory_creates_tables_automatically(self, tmp_path) -> None:
        """Test that factory automatically creates database tables.

        Args:
            tmp_path: pytest fixture for temporary directory
        """
        db_path = tmp_path / "test.db"
        config = StorageConfig(backend="sqlite", path=str(db_path))

        (
            execution_repo,
            states_repo,
            deployment_repo,
            chat_repo,
            webhook_repo,
            memory_repo,
            workflow_reg_repo,
        ) = create_storage_backend(config)

        # Check that tables exist by inspecting the engine
        inspector = inspect(execution_repo.engine)
        table_names = inspector.get_table_names()

        # Updated table names
        assert "executions" in table_names
        assert "execution_states" in table_names
        assert "deployments" in table_names

    def test_unsupported_backend_raises_value_error(self) -> None:
        """Test that unsupported backend raises ValueError."""
        config = StorageConfig(backend="postgresql", path="localhost:5432")

        with pytest.raises(ValueError, match="Unsupported storage backend"):
            create_storage_backend(config)

    def test_connection_string_style_sqlite_backend(self, tmp_path) -> None:
        """Test that connection string style SQLite backend works.

        Args:
            tmp_path: pytest fixture for temporary directory
        """
        db_path = tmp_path / "test.db"
        config = StorageConfig(backend=f"sqlite:///{db_path}", path=str(db_path))

        (
            execution_repo,
            states_repo,
            deployment_repo,
            chat_repo,
            webhook_repo,
            memory_repo,
            workflow_reg_repo,
        ) = create_storage_backend(config)

        assert isinstance(execution_repo, SQLiteExecutionRepository)
        assert isinstance(states_repo, SQLiteExecutionStateRepository)
        assert isinstance(deployment_repo, SqliteDeploymentRepository)
