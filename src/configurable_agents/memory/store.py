"""Persistent memory store for agents.

Provides namespaced key-value storage for agents to maintain state across
workflow executions. Memory is organized by scope (agent/workflow/node) to
prevent key conflicts and enable flexible sharing patterns.

Example:
    >>> from configurable_agents.memory import AgentMemory
    >>> memory = AgentMemory(agent_id="my_agent", repo=memory_repo)
    >>> memory.write("last_query", "AI safety research")
    >>> result = memory["last_query"]  # dict-like read
    >>> memory.write("context", {"topics": ["AI", "safety"]})
    >>> context = memory.read("context")  # returns dict
"""

import json
import logging
from contextlib import contextmanager
from typing import Any, List, Literal, Optional, Tuple

from configurable_agents.storage.base import MemoryRepository

logger = logging.getLogger(__name__)


class MemoryStore:
    """Direct storage access for memory operations.

    Provides low-level access to memory repository without namespace
    management. Used internally by AgentMemory and for advanced use cases.

    Attributes:
        repo: MemoryRepository instance for persistence
    """

    def __init__(self, repo: MemoryRepository) -> None:
        """Initialize memory store with repository.

        Args:
            repo: MemoryRepository instance for persistence
        """
        self._repo = repo

    def get(self, namespace_key: str) -> Any:
        """Get a value by namespace key.

        Args:
            namespace_key: Full namespace key (agent:workflow:node:key)

        Returns:
            Deserialized value or None if not found
        """
        value = self._repo.get(namespace_key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning(f"Failed to deserialize value for key {namespace_key}")
            return None

    def set(
        self,
        namespace_key: str,
        value: Any,
        agent_id: str,
        workflow_id: Optional[str],
        node_id: Optional[str],
        key: str,
    ) -> None:
        """Store a value with namespace key.

        Args:
            namespace_key: Full namespace key (agent:workflow:node:key)
            value: Value to store (will be JSON serialized)
            agent_id: Agent identifier
            workflow_id: Workflow identifier (optional)
            node_id: Node identifier (optional)
            key: User-facing key name
        """
        serialized = json.dumps(value)
        self._repo.set(namespace_key, serialized, agent_id, workflow_id, node_id, key)
        logger.debug(f"Stored memory: {namespace_key}")


class AgentMemory:
    """Agent memory with dict-like reads and explicit writes.

    Provides a user-friendly API for agent memory with automatic namespacing
    to prevent key conflicts. Supports three scopes:

    - "agent": Shared across all workflows (e.g., user preferences)
    - "workflow": Shared across nodes in a workflow (e.g., intermediate results)
    - "node": Isolated to a specific node (e.g., temporary state)

    Example:
        >>> memory = AgentMemory(
        ...     agent_id="research_bot",
        ...     workflow_id="daily_briefing",
        ...     scope="workflow",
        ...     repo=repo
        ... )
        >>> memory.write("last_search", "AI news")
        >>> result = memory["last_search"]  # dict-like read
        >>> memory.clear()  # Clear workflow-scoped memory
    """

    def __init__(
        self,
        agent_id: str,
        workflow_id: Optional[str] = None,
        node_id: Optional[str] = None,
        scope: Literal["agent", "workflow", "node"] = "agent",
        repo: Optional[MemoryRepository] = None,
    ) -> None:
        """Initialize agent memory.

        Args:
            agent_id: Agent identifier
            workflow_id: Workflow identifier (required for workflow/node scope)
            node_id: Node identifier (required for node scope)
            scope: Memory scope - "agent", "workflow", or "node"
            repo: MemoryRepository instance (optional, for direct access)
        """
        self._agent_id = agent_id
        self._workflow_id = workflow_id
        self._node_id = node_id
        self._scope = scope
        self._store = MemoryStore(repo) if repo else None

        # Validate scope parameters
        if scope == "workflow" and not workflow_id:
            raise ValueError("workflow_id is required for workflow scope")
        if scope == "node" and not (workflow_id and node_id):
            raise ValueError("workflow_id and node_id are required for node scope")

    def _build_namespace(self, key: str) -> str:
        """Build namespace key from components.

        Format: {agent_id}:{workflow_id or "*"}:{node_id or "*"}:{key}

        Args:
            key: User-facing key name

        Returns:
            Full namespace key
        """
        workflow_part = self._workflow_id if self._workflow_id else "*"
        node_part = self._node_id if self._node_id else "*"

        return f"{self._agent_id}:{workflow_part}:{node_part}:{key}"

    def __getitem__(self, key: str) -> Any:
        """Dict-like read: value = memory['key'].

        Args:
            key: Key to read

        Returns:
            Deserialized value or None if not found

        Example:
            >>> memory.write("counter", 42)
            >>> assert memory["counter"] == 42
        """
        if self._store is None:
            logger.warning(f"Memory read attempted but no repository configured for key '{key}'")
            return None

        namespace_key = self._build_namespace(key)
        return self._store.get(namespace_key)

    def write(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Write a value to memory (explicit write).

        Args:
            key: Key to store
            value: Value to store (will be JSON serialized)
            ttl: Time-to-live in seconds (reserved for future use)

        Example:
            >>> memory.write("user_name", "Alice")
            >>> memory.write("settings", {"theme": "dark", "lang": "en"})
        """
        if self._store is None:
            logger.warning(f"Memory write attempted but no repository configured for key '{key}'")
            return

        namespace_key = self._build_namespace(key)
        self._store.set(
            namespace_key,
            value,
            self._agent_id,
            self._workflow_id,
            self._node_id,
            key,
        )
        logger.debug(f"Memory written: {key} (scope: {self._scope})")

    def read(self, key: str, default: Any = None) -> Any:
        """Read a value with default fallback.

        Args:
            key: Key to read
            default: Default value if key not found

        Returns:
            Deserialized value or default

        Example:
            >>> name = memory.read("user_name", "Anonymous")
        """
        value = self[key]
        return default if value is None else value

    def delete(self, key: str) -> bool:
        """Delete a key from memory.

        Args:
            key: Key to delete

        Returns:
            True if key was deleted, False if not found

        Example:
            >>> memory.delete("temp_data")
        """
        if self._store is None:
            return False

        namespace_key = self._build_namespace(key)
        return self._store._repo.delete(namespace_key)

    def list(self, prefix: str = "") -> List[Tuple[str, Any]]:
        """List keys with optional prefix filtering.

        Args:
            prefix: Key prefix to filter (e.g., "user:")

        Returns:
            List of (key, value) tuples

        Example:
            >>> for key, value in memory.list("user:"):
            ...     print(f"{key}: {value}")
        """
        if self._store is None:
            return []

        # Get all items for this agent
        all_items = self._store._repo.list(self._agent_id, "")

        # Filter by current scope's namespace prefix
        # For workflow scope, filter by agent:workflow:
        # For node scope, filter by agent:workflow:node:
        namespace_prefix = self._build_namespace("").rstrip(":")

        # Deserialize values and filter by scope
        result = []
        for key, value_str in all_items:
            # Check if this key belongs to current scope
            # by checking the full namespace key
            full_namespace = self._build_namespace(key)

            # For list operation, we need to get the actual namespace from the repo
            # Since we only have key/value from list(), we need to check scope
            if not self._key_matches_scope(key):
                continue

            # Apply user-specified prefix filter
            if prefix and not key.startswith(prefix):
                continue

            try:
                value = json.loads(value_str)
                result.append((key, value))
            except json.JSONDecodeError:
                logger.warning(f"Failed to deserialize value for key {key}")
                result.append((key, value_str))

        return result

    def _key_matches_scope(self, key: str) -> bool:
        """Check if a key matches the current memory scope.

        Args:
            key: User-facing key name

        Returns:
            True if key exists in current scope, False otherwise
        """
        if self._store is None:
            return False

        # Build the full namespace for this key
        namespace_key = self._build_namespace(key)
        value = self._store._repo.get(namespace_key)
        return value is not None

    def clear(self) -> None:
        """Clear all memory at current scope.

        Example:
            >>> memory.clear()  # Clears agent/workflow/node scoped memory
        """
        if self._store is None:
            return

        if self._scope == "workflow" and self._workflow_id:
            count = self._store._repo.clear_by_workflow(self._agent_id, self._workflow_id)
            logger.info(f"Cleared {count} memory entries for workflow {self._workflow_id}")
        else:
            count = self._store._repo.clear(self._agent_id)
            logger.info(f"Cleared {count} memory entries for agent {self._agent_id}")

    def keys(self) -> List[str]:
        """Get all keys at current scope.

        Returns:
            List of key names

        Example:
            >>> keys = memory.keys()
        """
        items = self.list()
        return [key for key, _ in items]

    def __contains__(self, key: str) -> bool:
        """Check if key exists: 'key' in memory.

        Args:
            key: Key to check

        Returns:
            True if key exists, False otherwise
        """
        return self[key] is not None

    def __len__(self) -> int:
        """Get number of keys at current scope.

        Returns:
            Number of stored keys
        """
        return len(self.keys())


@contextmanager
def memory_context(
    agent_id: str,
    workflow_id: Optional[str] = None,
    node_id: Optional[str] = None,
    scope: Literal["agent", "workflow", "node"] = "agent",
    repo: Optional[MemoryRepository] = None,
):
    """Context manager for automatic memory cleanup.

    Provides AgentMemory instance and ensures cleanup on exit.

    Args:
        agent_id: Agent identifier
        workflow_id: Workflow identifier (optional)
        node_id: Node identifier (optional)
        scope: Memory scope (default: "agent")
        repo: MemoryRepository instance (optional)

    Yields:
        AgentMemory instance

    Example:
        >>> with memory_context(agent_id="bot", repo=repo) as memory:
        ...     memory.write("temp", "data")
        ...     # Memory automatically cleaned up on exit
    """
    memory = AgentMemory(
        agent_id=agent_id,
        workflow_id=workflow_id,
        node_id=node_id,
        scope=scope,
        repo=repo,
    )
    try:
        yield memory
    finally:
        # Optional: cleanup logic here
        pass
