"""
Flow Diagram Tab

Visualizes the flow structure using Mermaid diagrams.
Shows execution flow and crew details.
"""

import gradio as gr
from .base_tab import BaseTab
from ...core.flow_visualizer import generate_mermaid_diagram, generate_crew_diagram


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
                language="mermaid",
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
    
    def refresh_diagrams(self):
        """
        Refresh flow and crew diagrams.
        
        Returns:
            Tuple of (flow_diagram, crew_diagrams_html)
        """
        config = self.get_current_config()
        
        if not config:
            return (
                "graph TD\n    Start([No Config Loaded])",
                "<p style='color: orange;'>⚠️ No configuration loaded</p>"
            )
        
        # Convert FlowConfig to dict format for visualizer
        config_dict = self.config_service.to_dict(config)
        
        # Generate main flow diagram
        try:
            flow_diagram = generate_mermaid_diagram(config_dict)
        except Exception as e:
            self.logger.error(f"Error generating flow diagram: {e}")
            flow_diagram = f"graph TD\n    Error[Error: {str(e)}]"
        
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
                    <pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; margin-top: 10px;">
{crew_diagram}
                    </pre>
                </details>
                """
            except Exception as e:
                self.logger.error(f"Error generating crew diagram for {crew_name}: {e}")
                crew_diagrams_html += f"""
                <div style="color: red; padding: 10px;">
                    Error generating diagram for {crew_name}: {str(e)}
                </div>
                """
        
        crew_diagrams_html += "</div>"
        
        return (flow_diagram, crew_diagrams_html)