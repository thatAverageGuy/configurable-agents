"""Agent memory module.

Provides persistent, namespaced key-value storage for agents to maintain
state across workflow executions.

Public API:
    - AgentMemory: Main memory class with dict-like reads and explicit writes
    - MemoryStore: Low-level storage access
    - memory_context: Context manager for automatic cleanup

Example:
    >>> from configurable_agents.memory import AgentMemory
    >>> memory = AgentMemory(agent_id="my_agent", repo=memory_repo)
    >>> memory.write("last_query", "AI safety")
    >>> result = memory["last_query"]
"""

from configurable_agents.memory.store import (
    AgentMemory,
    MemoryStore,
    memory_context,
)

__all__ = [
    "AgentMemory",
    "MemoryStore",
    "memory_context",
]
