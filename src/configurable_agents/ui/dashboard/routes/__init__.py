"""Dashboard routes for workflow and agent monitoring.

Exports route modules for the dashboard application.
"""

from configurable_agents.ui.dashboard.routes.workflows import router as workflows_router
from configurable_agents.ui.dashboard.routes.agents import router as agents_router
from configurable_agents.ui.dashboard.routes.metrics import router as metrics_router
from configurable_agents.ui.dashboard.routes.optimization import router as optimization_router

__all__ = [
    "workflows_router",
    "agents_router",
    "metrics_router",
    "optimization_router",
]
