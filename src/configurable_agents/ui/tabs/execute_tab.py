"""
Execute Tab

Allows users to configure inputs and execute flows.
Shows progress and redirects to results.
"""

import gradio as gr
from .base_tab import BaseTab


class ExecuteTab(BaseTab):
    """Execute tab for running flows."""
    
    def render(self) -> None:
        """Render execute tab content."""
        
        with gr.Column():
            gr.Markdown("## 🚀 Execute Flow")
            gr.Markdown("Configure inputs and run your agent workflow")
            
            gr.Markdown("---")
            
            # Validation status
            gr.Markdown("### ✅ Pre-flight Check")
            self.preflight_status = gr.HTML(
                value=self.show_info("Validation status will appear here")
            )
            
            gr.Markdown("---")
            
            # Input configuration
            gr.Markdown("### ⚙️ Flow Inputs")
            gr.Markdown("Configure the inputs for your flow execution")
            
            # Topic input (for article generation flow)
            self.topic_input = gr.Textbox(
                label="Topic",
                placeholder="Enter a topic (e.g., 'AI in Healthcare')",
                value="AI in Healthcare"
            )
            
            # Add more dynamic inputs here based on flow requirements
            
            gr.Markdown("---")
            
            # Execution controls
            gr.Markdown("### 🎯 Execution")
            
            with gr.Row():
                self.validate_btn = gr.Button("🔍 Validate Config", variant="secondary")
                self.execute_btn = gr.Button("▶️ Run Flow", variant="primary", size="lg")
            
            # Progress and status
            self.execution_status = gr.HTML(value="")
            self.progress_bar = gr.Progress()
            
            # Wire up buttons
            self.validate_btn.click(
                fn=self.validate_config,
                inputs=[],
                outputs=[self.preflight_status]
            )
            
            self.execute_btn.click(
                fn=self.execute_flow,
                inputs=[self.topic_input],
                outputs=[self.execution_status]
            )
    
    def validate_config(self):
        """
        Validate the current configuration.
        
        Returns:
            HTML formatted validation status
        """
        config = self.get_current_config()
        
        if not config:
            return self.show_error("No configuration loaded. Please load a config first.")
        
        validation_result = self.validation_service.validate_config(config)
        
        if validation_result.is_valid:
            if validation_result.warnings:
                summary = self.validation_service.get_validation_summary(validation_result)
                return self.show_warning(f"Valid with warnings:\n{summary}")
            else:
                return self.show_success("✅ Configuration is valid and ready to execute!")
        else:
            summary = self.validation_service.get_validation_summary(validation_result)
            return self.show_error(f"Configuration has errors:\n{summary}")
    
    def execute_flow(self, topic: str):
        """
        Execute the flow with given inputs.
        
        Args:
            topic: Topic input for the flow
            
        Returns:
            HTML formatted execution status
        """
        config = self.get_current_config()
        
        if not config:
            return self.show_error("No configuration loaded. Please load a config first.")
        
        # Validate first
        validation_result = self.validation_service.validate_config(config)
        if not validation_result.is_valid:
            return self.show_error("Cannot execute - configuration has validation errors. Fix them first.")
        
        # Prepare inputs
        inputs = {"topic": topic}
        
        try:
            self.logger.info(f"Starting flow execution with inputs: {inputs}")
            
            # Execute flow
            result = self.execution_service.execute_flow(config, inputs)
            
            # Store result in state for Results tab
            self.state_service.set('last_execution_result', result)
            
            if result.status == 'success':
                return self.show_success(
                    f"✅ Flow completed successfully!\n"
                    f"Execution ID: {result.execution_id}\n"
                    f"Duration: {result.duration_seconds:.2f}s\n"
                    f"Check the Results tab for output."
                )
            else:
                return self.show_error(
                    f"❌ Flow execution failed:\n{result.error}"
                )
        
        except Exception as e:
            self.logger.error(f"Execution error: {e}", exc_info=True)
            return self.show_error(f"Execution error: {str(e)}")