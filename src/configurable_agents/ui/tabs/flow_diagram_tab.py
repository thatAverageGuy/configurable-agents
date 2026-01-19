"""
Flow Diagram Tab

Visualizes the flow structure using Mermaid diagrams.
Shows execution flow and crew details with error handling.
"""

import gradio as gr
from .base_tab import BaseTab
from ...core.flow_visualizer import generate_mermaid_diagram, generate_crew_diagram
from ..error_handler import ui_error_handler, track_performance
from ..utils import UIFeedback


class FlowDiagramTab(BaseTab):
    """Flow diagram tab for visualizing workflow structure."""
    
    def render(self) -> None:
        """Render flow diagram tab content."""
        
        with gr.Column():
            gr.Markdown("## 🎨 Flow Visualization")
            gr.Markdown("Visual representation of your agent workflow")
            
            # Refresh button
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh Diagram", variant="secondary")
            
            gr.Markdown("---")
            
            # Main flow diagram
            gr.Markdown("### 📈 Execution Flow")
            gr.Markdown("Shows the complete execution path from start to finish")
            
            self.flow_diagram = gr.Code(
                label="Flow Diagram (Mermaid)",
                language="markdown",
                value="graph TD\n    Start([No Config Loaded])",
                lines=15
            )
            
            gr.Markdown("""
            💡 **Tip:** Copy the Mermaid code above and paste it into [mermaid.live](https://mermaid.live) 
            to see the rendered diagram, or use a Mermaid preview extension in your IDE.
            """)
            
            gr.Markdown("---")
            
            # Crew diagrams
            gr.Markdown("### 👥 Crew Details")
            gr.Markdown("Expand each crew to see agents, tasks, and relationships")
            
            self.crew_diagrams = gr.HTML(
                value="<p>Load a configuration to see crew diagrams</p>"
            )
            
            # Wire up refresh
            refresh_btn.click(
                fn=self.refresh_diagrams,
                inputs=[],
                outputs=[self.flow_diagram, self.crew_diagrams]
            )
    
    @ui_error_handler("Failed to refresh diagrams")
    @track_performance("Refresh Diagrams")
    def refresh_diagrams(self):
        """
        Refresh flow and crew diagrams.
        
        Returns:
            Tuple of (flow_diagram, crew_diagrams_html)
        """
        config = self.get_current_config()
        
        if not config:
            UIFeedback.warning("No configuration loaded")
            return (
                "graph TD\n    Start([No Config Loaded])",
                "<p style='color: orange;'>⚠️ No configuration loaded. Load a config in the Config Editor tab.</p>"
            )
        
        with self.with_loading("Generating diagrams..."):
            # Convert FlowConfig to dict format for visualizer
            config_dict = self.config_service.to_dict(config)
            
            # Generate main flow diagram
            try:
                flow_diagram = generate_mermaid_diagram(config_dict)
                self.logger.info("Generated main flow diagram")
            except Exception as e:
                self.logger.error(f"Error generating flow diagram: {e}", exc_info=True)
                flow_diagram = f"graph TD\n    Error[Error: {str(e)}]"
                UIFeedback.error("Failed to generate flow diagram")
            
            # Generate crew diagrams
            crew_diagrams_html = "<div>"
            
            for crew_name, crew_config in config.crews.items():
                # Convert crew to dict format
                crew_dict = {
                    'agents': [
                        {
                            'id': agent.id,
                            'role': agent.role,
                            'tools': agent.tools
                        }
                        for agent in crew_config.agents
                    ],
                    'tasks': [
                        {
                            'id': task.id,
                            'agent': task.agent
                        }
                        for task in crew_config.tasks
                    ],
                    'execution': {
                        'type': crew_config.execution.type,
                        'tasks': crew_config.execution.tasks
                    }
                }
                
                try:
                    crew_diagram = generate_crew_diagram(crew_dict, crew_name)
                    
                    crew_diagrams_html += f"""
                    <details style="margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                        <summary style="cursor: pointer; font-weight: bold;">
                            🔍 {crew_name.replace('_', ' ').title()}
                        </summary>
                        <pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; margin-top: 10px; overflow-x: auto;">
{crew_diagram}
                        </pre>
                        <p style="font-size: 0.9em; color: #666; margin-top: 10px;">
                            📝 Copy this Mermaid code to <a href="https://mermaid.live" target="_blank">mermaid.live</a> to visualize
                        </p>
                    </details>
                    """
                except Exception as e:
                    self.logger.error(f"Error generating crew diagram for {crew_name}: {e}", exc_info=True)
                    crew_diagrams_html += f"""
                    <div style="color: red; padding: 10px; margin: 10px 0; border: 1px solid red; border-radius: 5px;">
                        ❌ Error generating diagram for {crew_name}: {str(e)}
                    </div>
                    """
            
            crew_diagrams_html += "</div>"
        
        UIFeedback.success("Diagrams refreshed")
        
        return (flow_diagram, crew_diagrams_html)