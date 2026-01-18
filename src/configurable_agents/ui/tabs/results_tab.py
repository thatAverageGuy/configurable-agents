"""
Results Tab

Displays results from flow execution.
Shows output, metrics, and provides download options.
"""

import gradio as gr
from .base_tab import BaseTab


class ResultsTab(BaseTab):
    """Results tab for displaying execution output."""
    
    def render(self) -> None:
        """Render results tab content."""
        
        with gr.Column():
            gr.Markdown("## 📊 Execution Results")
            gr.Markdown("View output and metrics from your flow execution")
            
            # Refresh button
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh Results", variant="secondary")
            
            gr.Markdown("---")
            
            # Execution summary
            gr.Markdown("### 📈 Execution Summary")
            
            with gr.Row():
                self.exec_id = gr.Textbox(
                    label="Execution ID",
                    value="No execution yet",
                    interactive=False,
                    scale=2
                )
                self.exec_status = gr.Textbox(
                    label="Status",
                    value="N/A",
                    interactive=False,
                    scale=1
                )
                self.exec_duration = gr.Textbox(
                    label="Duration (s)",
                    value="N/A",
                    interactive=False,
                    scale=1
                )
            
            gr.Markdown("---")
            
            # Output display
            gr.Markdown("### 📝 Output")
            
            self.output_display = gr.Textbox(
                label="Flow Output",
                value="No results available. Run a flow to see output here.",
                interactive=False,
                lines=15
            )
            
            # Download button
            with gr.Row():
                self.download_btn = gr.Button("⬇️ Download Output", variant="primary")
            
            self.download_file = gr.File(
                label="Download",
                visible=False
            )
            
            gr.Markdown("---")
            
            # Error display (if any)
            self.error_display = gr.HTML(value="")
            
            # Wire up refresh
            refresh_btn.click(
                fn=self.refresh_results,
                inputs=[],
                outputs=[
                    self.exec_id,
                    self.exec_status,
                    self.exec_duration,
                    self.output_display,
                    self.error_display
                ]
            )
            
            # Wire up download
            self.download_btn.click(
                fn=self.prepare_download,
                inputs=[],
                outputs=[self.download_file]
            )
    
    def refresh_results(self):
        """
        Refresh results display with latest execution.
        
        Returns:
            Tuple of updated values
        """
        result = self.state_service.get('last_execution_result')
        
        if not result:
            return (
                "No execution yet",
                "N/A",
                "N/A",
                "No results available. Run a flow in the Execute tab to see output here.",
                ""
            )
        
        # Extract output
        output_text = "No output"
        if result.output:
            # Try to format output nicely
            if hasattr(result.output, 'dict'):
                import json
                output_text = json.dumps(result.output.dict(), indent=2)
            elif hasattr(result.output, '__dict__'):
                import json
                output_text = json.dumps(result.output.__dict__, indent=2)
            else:
                output_text = str(result.output)
        
        # Error display
        error_html = ""
        if result.status == 'error':
            error_html = self.show_error(f"Error: {result.error}")
        
        return (
            result.execution_id,
            result.status,
            f"{result.duration_seconds:.2f}" if result.duration_seconds else "N/A",
            output_text,
            error_html
        )
    
    def prepare_download(self):
        """
        Prepare output for download.
        
        Returns:
            File path for download
        """
        result = self.state_service.get('last_execution_result')
        
        if not result or not result.output:
            return None
        
        # Create temp file with output
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            if hasattr(result.output, 'dict'):
                json.dump(result.output.dict(), f, indent=2)
            elif hasattr(result.output, '__dict__'):
                json.dump(result.output.__dict__, f, indent=2)
            else:
                f.write(str(result.output))
            
            return f.name