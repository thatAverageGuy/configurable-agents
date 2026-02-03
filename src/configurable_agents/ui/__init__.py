"""UI components for configurable-agents.

Provides web-based interfaces for monitoring and managing workflows,
including the orchestration dashboard with real-time updates.
"""

from configurable_agents.ui.dashboard import DashboardApp, create_dashboard_app

__all__ = ["DashboardApp", "create_dashboard_app"]
