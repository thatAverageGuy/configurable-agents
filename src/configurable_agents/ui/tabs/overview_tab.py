# src/configurable_agents/ui/tabs/overview_tab.py
"""
Overview Tab - Enhanced with Auto-Refresh

Displays summary with automatic updates when config changes.
"""

import gradio as gr
from .base_tab import BaseTab
from ..error_handler import ui_error_handler, track_performance
from ..utils import UIFeedback


class OverviewTab(BaseTab):
    """Overview tab with reactive auto-refresh."""
    
    def render(self) -> None:
        """Render overview tab content."""
        
        with gr.Column():
            gr.Markdown("## 📊 Flow Overview")
            gr.Markdown("Summary of your current agent workflow configuration")
            
            # Metrics row
            with gr.Row():
                self.steps_metric = gr.Textbox(
                    label="Steps",
                    value="0",
                    interactive=False,
                    scale=1
                )
                self.crews_metric = gr.Textbox(
                    label="Crews",
                    value="0",
                    interactive=False,
                    scale=1
                )
                self.agents_metric = gr.Textbox(
                    label="Agents",
                    value="0",
                    interactive=False,
                    scale=1
                )
                self.tasks_metric = gr.Textbox(
                    label="Tasks",
                    value="0",
                    interactive=False,
                    scale=1
                )
            
            gr.Markdown("---")
            
            # Flow details
            gr.Markdown("### 🎯 Flow Details")
            
            self.flow_name = gr.Textbox(
                label="Flow Name",
                value="No config loaded",
                interactive=False
            )
            
            self.flow_description = gr.Textbox(
                label="Description",
                value="",
                interactive=False,
                lines=3
            )
            
            self.crew_list = gr.Textbox(
                label="Crews",
                value="",
                interactive=False,
                lines=2
            )
            
            gr.Markdown("---")
            
            # Validation status
            gr.Markdown("### ✅ Validation Status")
            
            self.validation_status = gr.HTML(
                value=self.show_info("Load a configuration to see validation status")
            )
            
            # Refresh button
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh Overview", variant="primary")
            
            # Wire up manual refresh
            refresh_btn.click(
                fn=self.refresh_overview,
                inputs=[],
                outputs=[
                    self.steps_metric,
                    self.crews_metric,
                    self.agents_metric,
                    self.tasks_metric,
                    self.flow_name,
                    self.flow_description,
                    self.crew_list,
                    self.validation_status
                ]
            )
            
            # ========== NEW: Auto-refresh setup ==========
            # Store components for auto-refresh
            self._output_components = [
                self.steps_metric,
                self.crews_metric,
                self.agents_metric,
                self.tasks_metric,
                self.flow_name,
                self.flow_description,
                self.crew_list,
                self.validation_status
            ]
            
            # Initial load
            self.load_and_display_overview()
    
    def on_config_changed(self, new_config) -> None:
        """
        AUTO-REFRESH when config changes.
        
        This is called automatically by BaseTab when StateService
        notifies of config changes.
        """
        self.logger.info("Config changed - auto-refreshing overview")
        self.load_and_display_overview()
    
    def load_and_display_overview(self) -> None:
        """Load overview data and update all components."""
        try:
            values = self.refresh_overview()
            
            # Update all components
            for component, value in zip(self._output_components, values):
                component.value = value
                
        except Exception as e:
            self.logger.error(f"Error in auto-refresh: {e}", exc_info=True)
    
    @ui_error_handler("Failed to refresh overview")
    @track_performance("Refresh Overview")
    def refresh_overview(self):
        """
        Refresh overview with current config.
        
        Returns:
            Tuple of updated values for all outputs
        """
        config = self.get_current_config()
        
        if not config:
            UIFeedback.warning("No configuration loaded")
            return (
                "0", "0", "0", "0",
                "No config loaded",
                "",
                "",
                self.show_warning("Load a config in the Config Editor tab to get started")
            )
        
        with self.with_loading("Refreshing overview..."):
            # Calculate metrics
            num_steps = len(config.steps)
            num_crews = len(config.crews)
            num_agents = config.count_agents()
            num_tasks = config.count_tasks()
            
            # Get crew names
            crew_names = ", ".join(config.get_crew_names())
            
            # Validate config (uses cached validation if available)
            is_valid, validation_html = self.validate_current_config()
        
        UIFeedback.success("Overview refreshed")
        
        return (
            str(num_steps),
            str(num_crews),
            str(num_agents),
            str(num_tasks),
            config.flow.name,
            config.flow.description,
            crew_names,
            validation_html
        )