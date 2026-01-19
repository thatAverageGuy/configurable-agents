"""
Execute Tab

Allows users to configure inputs and execute flows.
Simple key-value input approach matching main.py pattern.
"""

import gradio as gr
from typing import Dict, Any
from .base_tab import BaseTab
from ..error_handler import ui_error_handler, track_performance
from ..utils import UIFeedback
from ...utils.id_generator import parse_key_value_text


class ExecuteTab(BaseTab):
    """Execute tab for running flows with flexible key-value inputs."""
    
    def render(self) -> None:
        """Render execute tab content."""
        
        with gr.Column():
            gr.Markdown("## 🚀 Execute Flow")
            gr.Markdown("Configure inputs and run your agent workflow")
            
            gr.Markdown("---")
            
            # Validation status
            gr.Markdown("### ✅ Pre-flight Check")
            self.preflight_status = gr.HTML(
                value=self.show_info("Load a configuration to see validation status")
            )
            
            gr.Markdown("---")
            
            # Input configuration
            gr.Markdown("### ⚙️ Flow Inputs")
            gr.Markdown("""
            Provide inputs as **key: value** pairs, one per line.
            
            **Example:**
            ```
            topic: AI in Healthcare
            company: Anthropic
            year: 2024
            ```
            
            These will be available in your flow as `{state.custom_var.topic}`, `{state.custom_var.company}`, etc.
            """)
            
            self.inputs_text = gr.TextArea(
                label="Flow Inputs (key: value format)",
                placeholder="topic: AI in Healthcare\ncompany: Anthropic\nyear: 2024",
                value="",
                lines=8,
                info="Enter one input per line in 'key: value' format"
            )
            
            # Quick examples
            with gr.Accordion("📝 Quick Examples", open=False):
                gr.Markdown("""
                **Article Generation:**
                ```
                topic: AI in Healthcare
                ```
                
                **Company Analysis:**
                ```
                company: Anthropic
                industry: AI
                year: 2024
                ```
                
                **Research Report:**
                ```
                topic: Climate Change
                depth: comprehensive
                sources: 10
                ```
                
                **No Inputs:**
                Leave empty if your flow doesn't need inputs
                """)
            
            gr.Markdown("---")
            
            # Execution controls
            gr.Markdown("### 🎯 Execution")
            
            with gr.Row():
                self.validate_btn = gr.Button("🔍 Validate Config", variant="secondary")
                self.execute_btn = gr.Button("▶️ Run Flow", variant="primary", size="lg")
            
            # Progress and status
            self.execution_status = gr.HTML(value="")
            
            # Wire up buttons
            self.validate_btn.click(
                fn=self.validate_config,
                inputs=[],
                outputs=[self.preflight_status]
            )
            
            self.execute_btn.click(
                fn=self.execute_flow,
                inputs=[self.inputs_text],
                outputs=[self.execution_status]
            )
    
    @ui_error_handler("Validation check failed")
    @track_performance("Validate Config")
    def validate_config(self):
        """
        Validate the current configuration.
        
        Returns:
            HTML formatted validation status
        """
        config = self.get_current_config()
        
        if not config:
            UIFeedback.warning("No configuration loaded")
            return self.show_error("No configuration loaded. Please load a config first.")
        
        with self.with_loading("Validating configuration..."):
            validation_result = self.validation_service.validate_config(config)
        
        if validation_result.is_valid:
            if validation_result.warnings:
                summary = self.validation_service.get_validation_summary(validation_result)
                UIFeedback.warning(f"Valid with {len(validation_result.warnings)} warning(s)")
                return self.show_warning(f"Valid with warnings:\n{summary}")
            else:
                UIFeedback.success("Configuration is valid!")
                return self.show_success("✅ Configuration is valid and ready to execute!")
        else:
            summary = self.validation_service.get_validation_summary(validation_result)
            UIFeedback.error(f"Configuration has {len(validation_result.errors)} error(s)")
            return self.show_error(f"Configuration has errors:\n{summary}", include_suggestion=True)
    
    def parse_inputs(self, inputs_text: str) -> Dict[str, Any]:
        """
        Parse input text into dictionary.
        
        Uses the parse_key_value_text utility from utils module.
        
        Args:
            inputs_text: Text with key: value pairs
            
        Returns:
            Dictionary of parsed inputs
        """
        if not inputs_text or not inputs_text.strip():
            return {}
        
        try:
            inputs = parse_key_value_text(inputs_text)
            self.logger.info(f"Parsed inputs: {inputs}")
            return inputs
        except Exception as e:
            self.logger.error(f"Error parsing inputs: {e}")
            raise ValueError(f"Failed to parse inputs: {str(e)}")
    
    @ui_error_handler("Flow execution failed")
    @track_performance("Execute Flow")
    def execute_flow(self, inputs_text: str):
        """
        Execute the flow with given inputs.
        
        Args:
            inputs_text: Input text in key: value format
            
        Returns:
            HTML formatted execution status
        """
        config = self.get_current_config()
        
        if not config:
            UIFeedback.error("No configuration loaded")
            return self.show_error("No configuration loaded. Please load a config first.")
        
        # Validate first
        validation_result = self.validation_service.validate_config(config)
        if not validation_result.is_valid:
            UIFeedback.error("Cannot execute - configuration has errors")
            return self.show_error(
                "Cannot execute - configuration has validation errors. Fix them first.",
                include_suggestion=True
            )
        
        # Parse inputs
        try:
            inputs = self.parse_inputs(inputs_text)
        except ValueError as e:
            UIFeedback.error("Invalid input format")
            return self.show_error(
                f"Invalid input format: {str(e)}\n\n"
                f"Expected format:\n"
                f"key1: value1\n"
                f"key2: value2\n\n"
                f"Example:\n"
                f"topic: AI in Healthcare\n"
                f"company: Anthropic"
            )
        
        try:
            self.logger.info(f"Starting flow execution with inputs: {inputs}")
            
            # Show starting notification
            if inputs:
                inputs_summary = ", ".join([f"{k}='{v}'" for k, v in inputs.items()])
                UIFeedback.info(f"Starting flow with: {inputs_summary}")
            else:
                UIFeedback.info("Starting flow execution (no inputs)")
            
            # Execute flow with loading state
            # This matches the pattern in main.py:
            # flow_instance.state.custom_var.update(initial_inputs)
            with self.with_loading("Executing flow... This may take a few minutes"):
                result = self.execution_service.execute_flow(config, inputs)
            
            # Store result in state for Results tab
            self.state_service.set('last_execution_result', result)
            
            if result.status == 'success':
                UIFeedback.success("Flow completed successfully!")
                
                # Format inputs display
                inputs_display = "\n".join([f"  - {k}: {v}" for k, v in inputs.items()]) if inputs else "  (none)"
                
                return self.show_success(
                    f"✅ Flow completed successfully!\n\n"
                    f"**Execution ID:** {result.execution_id}\n"
                    f"**Duration:** {result.duration_seconds:.2f}s\n"
                    f"**Inputs:**\n{inputs_display}\n\n"
                    f"📊 Check the **Results** tab for detailed output."
                )
            else:
                UIFeedback.error("Flow execution failed")
                return self.show_error(
                    f"Flow execution failed:\n\n{result.error}",
                    include_suggestion=True
                )
        
        except Exception as e:
            self.logger.error(f"Execution error: {e}", exc_info=True)
            UIFeedback.error("Flow execution encountered an error")
            return self.show_error(
                f"Execution error: {str(e)}",
                include_suggestion=True
            )