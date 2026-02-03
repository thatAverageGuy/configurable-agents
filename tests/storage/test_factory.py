"""Tests for storage backend factory function.

Tests that the factory correctly creates repositories based on
configuration and handles errors appropriately.
"""

import pytest
from sqlalchemy import inspect

from configurable_agents.config.schema import StorageConfig
from configurable_agents.storage import create_storage_backend
from configurable_agents.storage.sqlite import (
    SQLiteExecutionStateRepository,
    SQLiteWorkflowRunRepository,
)


class TestFactory:
    """Tests for create_storage_backend factory function."""

    def test_default_config_creates_sqlite_repos(self, tmp_path) -> None:
        """Test that default config creates SQLite repositories.

        Args:
            tmp_path: pytest fixture for temporary directory
        """
        # Use default config (None)
        runs_repo, states_repo, agents_repo, chat_repo, webhook_repo = create_storage_backend()

        assert isinstance(runs_repo, SQLiteWorkflowRunRepository)
        assert isinstance(states_repo, SQLiteExecutionStateRepository)

    def test_explicit_sqlite_config_creates_repos(self, tmp_path) -> None:
        """Test that explicit SQLite config creates repositories.

        Args:
            tmp_path: pytest fixture for temporary directory
        """
        db_path = tmp_path / "test.db"
        config = StorageConfig(backend="sqlite", path=str(db_path))

        runs_repo, states_repo, agents_repo, chat_repo, webhook_repo = create_storage_backend(config)

        assert isinstance(runs_repo, SQLiteWorkflowRunRepository)
        assert isinstance(states_repo, SQLiteExecutionStateRepository)

    def test_factory_creates_tables_automatically(self, tmp_path) -> None:
        """Test that factory automatically creates database tables.

        Args:
            tmp_path: pytest fixture for temporary directory
        """
        db_path = tmp_path / "test.db"
        config = StorageConfig(backend="sqlite", path=str(db_path))

        runs_repo, states_repo, agents_repo, chat_repo, webhook_repo = create_storage_backend(config)

        # Check that tables exist by inspecting the engine
        inspector = inspect(runs_repo.engine)
        table_names = inspector.get_table_names()

        assert "workflow_runs" in table_names
        assert "execution_states" in table_names

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

        runs_repo, states_repo, agents_repo, chat_repo, webhook_repo = create_storage_backend(config)

        assert isinstance(runs_repo, SQLiteWorkflowRunRepository)
        assert isinstance(states_repo, SQLiteExecutionStateRepository)
