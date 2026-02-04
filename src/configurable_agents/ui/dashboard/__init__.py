"""FastAPI + HTMX orchestration dashboard for real-time workflow monitoring.

Provides a unified view of running workflows, registered agents, and MLFlow
observability with server-side rendering and HTMX for dynamic updates.
"""

from configurable_agents.ui.dashboard.app import DashboardApp, create_dashboard_app

__all__ = ["DashboardApp", "create_dashboard_app"]
