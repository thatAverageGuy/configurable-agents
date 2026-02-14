"""Dashboard routes for execution and deployment monitoring.

Exports route modules for the dashboard application.

Updated in UI Redesign (2026-02-13):
- workflows_router → executions_router
- agents_router → deployments_router
- orchestrator_router REMOVED (merged into deployments)
"""

from configurable_agents.ui.dashboard.routes.executions import router as executions_router
from configurable_agents.ui.dashboard.routes.deployments import router as deployments_router
from configurable_agents.ui.dashboard.routes.metrics import router as metrics_router
from configurable_agents.ui.dashboard.routes.status import router as status_router

# Backward-compatible aliases
workflows_router = executions_router
agents_router = deployments_router

__all__ = [
    # New names
    "executions_router",
    "deployments_router",
    "metrics_router",
    "status_router",
    # Backward-compatible aliases
    "workflows_router",
    "agents_router",
]
