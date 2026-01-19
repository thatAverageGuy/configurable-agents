# src/configurable_agents/ui/tabs/results_tab.py
"""
Results Tab - Enhanced with Auto-Refresh

Displays results with automatic updates when execution completes.
"""

import gradio as gr
from .base_tab import BaseTab
from ..error_handler import ui_error_handler, track_performance
from ..utils import UIFeedback, safe_file_operation
import tempfile
import json


class ResultsTab(BaseTab):
    """Results tab with reactive result updates."""
    
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
            
            # Store components for auto-refresh
            self._output_components = [
                self.exec_id,
                self.exec_status,
                self.exec_duration,
                self.output_display,
                self.error_display
            ]
            
            # Subscribe to execution results
            self._setup_result_subscription()
    
    def _setup_result_subscription(self) -> None:
        """Subscribe to execution result changes for auto-refresh."""
        def handle_result_change(event):
            if event.key == 'last_execution_result':
                self.logger.info("Execution result changed - auto-refreshing")
                try:
                    self.load_and_display_results()
                except Exception as e:
                    self.logger.error(f"Error auto-refreshing results: {e}", exc_info=True)
        
        self.state_service.subscribe('last_execution_result', handle_result_change)
    
    def load_and_display_results(self) -> None:
        """Load result data and update all components."""
        try:
            values = self.refresh_results()
            
            for component, value in zip(self._output_components, values):
                component.value = value
                
        except Exception as e:
            self.logger.error(f"Error in auto-refresh: {e}", exc_info=True)
    
    @ui_error_handler("Failed to refresh results")
    @track_performance("Refresh Results")
    def refresh_results(self):
        """Refresh results display with latest execution."""
        result = self.state_service.get('last_execution_result')
        
        if not result:
            UIFeedback.info("No execution results available yet")
            return (
                "No execution yet",
                "N/A",
                "N/A",
                "No results available. Run a flow in the Execute tab to see output here.",
                ""
            )
        
        with self.with_loading("Loading results..."):
            # Extract output
            output_text = "No output"
            if result.output:
                try:
                    if hasattr(result.output, 'dict'):
                        output_text = json.dumps(result.output.dict(), indent=2)
                    elif hasattr(result.output, '__dict__'):
                        output_text = json.dumps(result.output.__dict__, indent=2)
                    else:
                        output_text = str(result.output)
                except Exception as e:
                    self.logger.warning(f"Could not format output as JSON: {e}")
                    output_text = str(result.output)
            
            # Error display
            error_html = ""
            if result.status == 'error':
                error_html = self.show_error(f"Error: {result.error}", include_suggestion=True)
        
        UIFeedback.success("Results refreshed")
        
        return (
            result.execution_id,
            result.status,
            f"{result.duration_seconds:.2f}" if result.duration_seconds else "N/A",
            output_text,
            error_html
        )
    
    @ui_error_handler("Failed to prepare download")
    @track_performance("Prepare Download")
    def prepare_download(self):
        """Prepare output for download."""
        result = self.state_service.get('last_execution_result')
        
        if not result or not result.output:
            UIFeedback.warning("No output available to download")
            return None
        
        with self.with_loading("Preparing download..."):
            def create_output_file():
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    if hasattr(result.output, 'dict'):
                        json.dump(result.output.dict(), f, indent=2)
                    elif hasattr(result.output, '__dict__'):
                        json.dump(result.output.__dict__, f, indent=2)
                    else:
                        f.write(str(result.output))
                    return f.name
            
            file_path = safe_file_operation(
                create_output_file,
                None,
                "Failed to create download file"
            )
        
        if file_path:
            UIFeedback.success("Download prepared")
        
        return file_path