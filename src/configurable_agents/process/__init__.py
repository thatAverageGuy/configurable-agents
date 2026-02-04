"""Process management for multi-service orchestration.

This module provides utilities for spawning and managing multiple services
as separate processes with unified lifecycle control.
"""

from configurable_agents.process.manager import ProcessManager, ServiceSpec

__all__ = ["ProcessManager", "ServiceSpec"]
