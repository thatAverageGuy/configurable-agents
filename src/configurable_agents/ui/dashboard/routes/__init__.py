"""Dashboard routes for workflow and agent monitoring.

Exports route modules for the dashboard application.
"""

from configurable_agents.ui.dashboard.routes.workflows import router as workflows_router
from configurable_agents.ui.dashboard.routes.agents import router as agents_router
from configurable_agents.ui.dashboard.routes.metrics import router as metrics_router
from configurable_agents.ui.dashboard.routes.orchestrator import router as orchestrator_router
from configurable_agents.ui.dashboard.routes.status import router as status_router

__all__ = [
    "workflows_router",
    "agents_router",
    "metrics_router",
    "orchestrator_router",
    "status_router",
]
