"""Tests for memory store implementation."""

import json
import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from configurable_agents.memory import AgentMemory, MemoryStore, memory_context
from configurable_agents.storage.base import MemoryRepository
from configurable_agents.storage.models import Base, MemoryRecord
from configurable_agents.storage.sqlite import SQLiteMemoryRepository


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")

    # Create tables
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    os.unlink(path)


@pytest.fixture
def memory_repo(temp_db):
    """Create a memory repository for testing."""
    return SQLiteMemoryRepository(temp_db)


@pytest.fixture
def memory_store(memory_repo):
    """Create a memory store for testing."""
    return MemoryStore(memory_repo)


class TestMemoryStore:
    """Tests for MemoryStore class."""

    def test_set_and_get(self, memory_store, memory_repo):
        """Test basic set and get operations."""
        namespace_key = "test_agent:*:*:my_key"
        memory_store.set(
            namespace_key,
            "test_value",
            agent_id="test_agent",
            workflow_id=None,
            node_id=None,
            key="my_key",
        )

        result = memory_store.get(namespace_key)
        assert result == "test_value"

    def test_set_json_serialization(self, memory_store, memory_repo):
        """Test that values are JSON serialized."""
        namespace_key = "test_agent:*:*:complex_key"
        complex_value = {"nested": {"data": [1, 2, 3]}, "string": "test"}

        memory_store.set(
            namespace_key,
            complex_value,
            agent_id="test_agent",
            workflow_id=None,
            node_id=None,
            key="complex_key",
        )

        result = memory_store.get(namespace_key)
        assert result == complex_value

    def test_get_nonexistent_key(self, memory_store):
        """Test getting a nonexistent key returns None."""
        result = memory_store.get("nonexistent:agent:*:*:key")
        assert result is None


class TestAgentMemory:
    """Tests for AgentMemory class."""

    def test_dict_like_read(self, memory_repo):
        """Test dict-like read with __getitem__."""
        memory = AgentMemory(agent_id="test_agent", repo=memory_repo)
        memory.write("test_key", "test_value")

        result = memory["test_key"]
        assert result == "test_value"

    def test_dict_like_read_default(self, memory_repo):
        """Test dict-like read with default value."""
        memory = AgentMemory(agent_id="test_agent", repo=memory_repo)

        result = memory.read("nonexistent_key", default="default_value")
        assert result == "default_value"

    def test_write_simple_value(self, memory_repo):
        """Test writing a simple string value."""
        memory = AgentMemory(agent_id="test_agent", repo=memory_repo)
        memory.write("message", "Hello, World!")

        assert memory["message"] == "Hello, World!"

    def test_write_complex_value(self, memory_repo):
        """Test writing a complex JSON-serializable value."""
        memory = AgentMemory(agent_id="test_agent", repo=memory_repo)
        complex_data = {
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ],
            "count": 2,
        }
        memory.write("user_data", complex_data)

        result = memory["user_data"]
        assert result == complex_data
        assert result["users"][0]["name"] == "Alice"

    def test_delete_key(self, memory_repo):
        """Test deleting a key."""
        memory = AgentMemory(agent_id="test_agent", repo=memory_repo)
        memory.write("temp", "data")

        assert "temp" in memory
        assert memory.delete("temp") is True
        assert "temp" not in memory

    def test_delete_nonexistent_key(self, memory_repo):
        """Test deleting a nonexistent key returns False."""
        memory = AgentMemory(agent_id="test_agent", repo=memory_repo)
        assert memory.delete("nonexistent") is False

    def test_list_keys(self, memory_repo):
        """Test listing all keys."""
        memory = AgentMemory(agent_id="test_agent", repo=memory_repo)
        memory.write("key1", "value1")
        memory.write("key2", "value2")
        memory.write("key3", "value3")

        keys = memory.keys()
        assert set(keys) == {"key1", "key2", "key3"}

    def test_list_with_prefix(self, memory_repo):
        """Test listing keys with prefix filtering."""
        memory = AgentMemory(agent_id="test_agent", repo=memory_repo)
        memory.write("user:name", "Alice")
        memory.write("user:email", "alice@example.com")
        memory.write("system:version", "1.0")

        user_items = memory.list(prefix="user:")
        assert len(user_items) == 2
        keys = [k for k, _ in user_items]
        assert set(keys) == {"user:name", "user:email"}

    def test_contains(self, memory_repo):
        """Test __contains__ for key existence check."""
        memory = AgentMemory(agent_id="test_agent", repo=memory_repo)
        memory.write("existing", "value")

        assert "existing" in memory
        assert "nonexistent" not in memory

    def test_len(self, memory_repo):
        """Test __len__ returns count of keys."""
        memory = AgentMemory(agent_id="test_agent", repo=memory_repo)

        assert len(memory) == 0
        memory.write("key1", "value1")
        assert len(memory) == 1
        memory.write("key2", "value2")
        assert len(memory) == 2

    def test_namespace_builder(self, memory_repo):
        """Test namespace key construction for different scopes."""
        # Agent scope
        agent_memory = AgentMemory(agent_id="bot1", scope="agent", repo=memory_repo)
        assert agent_memory._build_namespace("key") == "bot1:*:*:key"

        # Workflow scope
        workflow_memory = AgentMemory(
            agent_id="bot1", workflow_id="workflow1", scope="workflow", repo=memory_repo
        )
        assert workflow_memory._build_namespace("key") == "bot1:workflow1:*:key"

        # Node scope
        node_memory = AgentMemory(
            agent_id="bot1",
            workflow_id="workflow1",
            node_id="node1",
            scope="node",
            repo=memory_repo,
        )
        assert node_memory._build_namespace("key") == "bot1:workflow1:node1:key"


class TestNamespaceIsolation:
    """Tests for namespace isolation between scopes."""

    def test_agent_scope_isolation(self, memory_repo):
        """Test agent scope memory is isolated per agent."""
        agent1 = AgentMemory(agent_id="agent1", scope="agent", repo=memory_repo)
        agent2 = AgentMemory(agent_id="agent2", scope="agent", repo=memory_repo)

        agent1.write("shared_key", "agent1_value")
        agent2.write("shared_key", "agent2_value")

        assert agent1["shared_key"] == "agent1_value"
        assert agent2["shared_key"] == "agent2_value"

    def test_workflow_scope_isolation(self, memory_repo):
        """Test workflow scope memory is isolated per workflow."""
        workflow1 = AgentMemory(
            agent_id="agent1", workflow_id="workflow1", scope="workflow", repo=memory_repo
        )
        workflow2 = AgentMemory(
            agent_id="agent1", workflow_id="workflow2", scope="workflow", repo=memory_repo
        )

        workflow1.write("step", "step1")
        workflow2.write("step", "step2")

        assert workflow1["step"] == "step1"
        assert workflow2["step"] == "step2"

    def test_node_scope_isolation(self, memory_repo):
        """Test node scope memory is isolated per node."""
        node1 = AgentMemory(
            agent_id="agent1",
            workflow_id="workflow1",
            node_id="node1",
            scope="node",
            repo=memory_repo,
        )
        node2 = AgentMemory(
            agent_id="agent1",
            workflow_id="workflow1",
            node_id="node2",
            scope="node",
            repo=memory_repo,
        )

        node1.write("temp", "data1")
        node2.write("temp", "data2")

        assert node1["temp"] == "data1"
        assert node2["temp"] == "data2"

    def test_cross_scope_visibility(self, memory_repo):
        """Test that higher scopes don't see lower scope data."""
        agent_memory = AgentMemory(agent_id="agent1", scope="agent", repo=memory_repo)
        workflow_memory = AgentMemory(
            agent_id="agent1", workflow_id="workflow1", scope="workflow", repo=memory_repo
        )
        node_memory = AgentMemory(
            agent_id="agent1",
            workflow_id="workflow1",
            node_id="node1",
            scope="node",
            repo=memory_repo,
        )

        agent_memory.write("key", "agent_value")
        workflow_memory.write("key", "workflow_value")
        node_memory.write("key", "node_value")

        # Each scope only sees its own value
        assert agent_memory["key"] == "agent_value"
        assert workflow_memory["key"] == "workflow_value"
        assert node_memory["key"] == "node_value"


class TestMemoryClear:
    """Tests for memory clearing operations."""

    def test_clear_agent_scope(self, memory_repo):
        """Test clearing all agent-scoped memory."""
        memory = AgentMemory(agent_id="agent1", scope="agent", repo=memory_repo)
        memory.write("key1", "value1")
        memory.write("key2", "value2")

        assert len(memory) == 2
        memory.clear()
        assert len(memory) == 0

    def test_clear_workflow_scope(self, memory_repo):
        """Test clearing workflow-scoped memory."""
        workflow1 = AgentMemory(
            agent_id="agent1", workflow_id="workflow1", scope="workflow", repo=memory_repo
        )
        workflow2 = AgentMemory(
            agent_id="agent1", workflow_id="workflow2", scope="workflow", repo=memory_repo
        )

        workflow1.write("key", "value1")
        workflow2.write("key", "value2")

        # Clear workflow1 only
        workflow1.clear()

        # workflow1 memory should be gone
        assert len(workflow1) == 0
        # workflow2 memory should remain
        assert workflow2["key"] == "value2"


class TestMemoryContext:
    """Tests for memory_context context manager."""

    def test_memory_context_yields_memory(self, memory_repo):
        """Test that memory_context yields an AgentMemory instance."""
        with memory_context(agent_id="test", repo=memory_repo) as memory:
            assert isinstance(memory, AgentMemory)
            memory.write("key", "value")

        # Memory should persist after context exit
        with memory_context(agent_id="test", repo=memory_repo) as memory:
            assert memory["key"] == "value"


class TestMemoryRepository:
    """Tests for SQLiteMemoryRepository implementation."""

    def test_repository_upsert(self, memory_repo):
        """Test that set performs upsert (update existing)."""
        namespace_key = "agent:*:*:key"

        # Initial set (repository expects pre-serialized JSON)
        memory_repo.set(namespace_key, json.dumps("value1"), "agent", None, None, "key")
        result = memory_repo.get(namespace_key)
        assert result == json.dumps("value1")  # JSON serialized

        # Update with new value
        memory_repo.set(namespace_key, json.dumps("value2"), "agent", None, None, "key")
        result = memory_repo.get(namespace_key)
        assert result == json.dumps("value2")

    def test_repository_delete(self, memory_repo):
        """Test deleting from repository."""
        namespace_key = "agent:*:*:key"
        memory_repo.set(namespace_key, json.dumps("value"), "agent", None, None, "key")

        assert memory_repo.get(namespace_key) is not None
        assert memory_repo.delete(namespace_key) is True
        assert memory_repo.get(namespace_key) is None
        assert memory_repo.delete(namespace_key) is False  # Already deleted

    def test_repository_list(self, memory_repo):
        """Test listing keys from repository."""
        # Add multiple keys for same agent (pre-serialized)
        memory_repo.set("agent:*:*:key1", json.dumps("value1"), "agent", None, None, "key1")
        memory_repo.set("agent:*:*:key2", json.dumps("value2"), "agent", None, None, "key2")
        memory_repo.set("agent:*:*:prefix_key", json.dumps("value3"), "agent", None, None, "prefix_key")

        # List all
        all_items = memory_repo.list("agent")
        assert len(all_items) == 3

        # List with prefix
        prefixed = memory_repo.list("agent", "prefix_")
        assert len(prefixed) == 1
        assert prefixed[0][0] == "prefix_key"

    def test_repository_clear(self, memory_repo):
        """Test clearing agent memory."""
        # Add keys for two agents (pre-serialized)
        memory_repo.set("agent1:*:*:key", json.dumps("value1"), "agent1", None, None, "key")
        memory_repo.set("agent2:*:*:key", json.dumps("value2"), "agent2", None, None, "key")

        # Clear agent1
        count = memory_repo.clear("agent1")
        assert count == 1
        assert memory_repo.get("agent1:*:*:key") is None
        assert memory_repo.get("agent2:*:*:key") is not None

    def test_repository_clear_by_workflow(self, memory_repo):
        """Test clearing workflow memory."""
        # Add keys for two workflows of same agent (pre-serialized)
        memory_repo.set("agent:workflow1:*:key", json.dumps("value1"), "agent", "workflow1", None, "key")
        memory_repo.set("agent:workflow2:*:key", json.dumps("value2"), "agent", "workflow2", None, "key")

        # Clear workflow1
        count = memory_repo.clear_by_workflow("agent", "workflow1")
        assert count == 1
        assert memory_repo.get("agent:workflow1:*:key") is None
        assert memory_repo.get("agent:workflow2:*:key") is not None


class TestValidationError:
    """Tests for validation errors."""

    def test_workflow_scope_requires_workflow_id(self, memory_repo):
        """Test that workflow scope requires workflow_id."""
        with pytest.raises(ValueError, match="workflow_id is required"):
            AgentMemory(agent_id="agent", scope="workflow", repo=memory_repo)

    def test_node_scope_requires_workflow_and_node_id(self, memory_repo):
        """Test that node scope requires both workflow_id and node_id."""
        with pytest.raises(ValueError, match="workflow_id and node_id are required"):
            AgentMemory(agent_id="agent", scope="node", repo=memory_repo)

    def test_node_scope_requires_node_id(self, memory_repo):
        """Test that node scope requires node_id."""
        with pytest.raises(ValueError, match="workflow_id and node_id are required"):
            AgentMemory(
                agent_id="agent", workflow_id="workflow", scope="node", repo=memory_repo
            )


class TestMemoryWithoutRepository:
    """Tests for AgentMemory behavior without repository."""

    def test_read_write_without_repository_logs_warning(self, memory_repo, caplog):
        """Test that operations without repository return None/False gracefully."""
        memory = AgentMemory(agent_id="agent", repo=None)

        # These should not raise errors, just log warnings
        assert memory["key"] is None
        assert memory.read("key", "default") == "default"
        assert memory.write("key", "value") is None
        assert memory.delete("key") is False
        assert memory.list() == []
        assert memory.keys() == []
        assert len(memory) == 0
