"""
Overview Tab

Displays summary information about the current flow configuration.
Shows metrics, flow details, and current settings.
"""

import gradio as gr
from .base_tab import BaseTab
from ...core.flow_visualizer import get_flow_summary


class OverviewTab(BaseTab):
    """Overview tab showing flow summary and metrics."""
    
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
            
            # Wire up refresh
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
    
    def refresh_overview(self):
        """
        Refresh overview with current config.
        
        Returns:
            Tuple of updated values for all outputs
        """
        config = self.get_current_config()
        
        if not config:
            return (
                "0", "0", "0", "0",
                "No config loaded",
                "",
                "",
                self.show_warning("No configuration loaded. Load or create a config to get started.")
            )
        
        # Get summary
        summary = get_flow_summary({'flow': {'name': config.flow.name, 'description': config.flow.description}, 'steps': [], 'crews': {}})
        
        # Calculate metrics
        num_steps = len(config.steps)
        num_crews = len(config.crews)
        num_agents = config.count_agents()
        num_tasks = config.count_tasks()
        
        # Get crew names
        crew_names = ", ".join(config.get_crew_names())
        
        # Validate config
        validation_result = self.validation_service.validate_config(config)
        
        if validation_result.is_valid:
            if validation_result.warnings:
                validation_html = self.show_warning(
                    f"Valid with {len(validation_result.warnings)} warning(s)"
                )
            else:
                validation_html = self.show_success("Configuration is valid")
        else:
            validation_html = self.show_error(
                f"Configuration has {len(validation_result.errors)} error(s)"
            )
        
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