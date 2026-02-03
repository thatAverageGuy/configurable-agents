"""UI components for configurable-agents.

Provides web-based interfaces for monitoring and managing workflows,
including the Gradio chat UI for config generation and the orchestration
dashboard with real-time updates.
"""

from configurable_agents.ui.dashboard import DashboardApp, create_dashboard_app
from configurable_agents.ui.gradio_chat import (
    GradioChatUI,
    CONFIG_GENERATION_PROMPT,
    create_gradio_chat_ui,
)

__all__ = [
    "DashboardApp",
    "create_dashboard_app",
    "GradioChatUI",
    "create_gradio_chat_ui",
    "CONFIG_GENERATION_PROMPT",
]
