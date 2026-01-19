# src/configurable_agents/ui/tabs/execute_tab.py
"""
Execute Tab - Enhanced with Reactive Validation

Real-time validation checks before execution.
"""

import gradio as gr
from typing import Dict, Any
from .base_tab import BaseTab
from ..error_handler import ui_error_handler, track_performance
from ..utils import UIFeedback
from ...utils.id_generator import parse_key_value_text


class ExecuteTab(BaseTab):
    """Execute tab with reactive validation status."""
    
    def render(self) -> None:
        """Render execute tab content."""
        
        with gr.Column():
            gr.Markdown("## 🚀 Execute Flow")
            gr.Markdown("Configure inputs and run your agent workflow")
            
            gr.Markdown("---")
            
            # Pre-flight validation status
            gr.Markdown("### ✅ Pre-flight Check")
            self.preflight_status = gr.HTML(
                value=self._get_preflight_status()
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
            
            These will be available in your flow as `{state.custom_var.topic}`, etc.
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
    
    def on_config_changed(self, new_config) -> None:
        """AUTO-UPDATE pre-flight status when config changes."""
        self.logger.info("Config changed - updating pre-flight status")
        try:
            self.preflight_status.value = self._get_preflight_status()
        except Exception as e:
            self.logger.error(f"Error updating pre-flight: {e}", exc_info=True)
    
    def _get_preflight_status(self) -> str:
        """Get current pre-flight validation status."""
        config = self.get_current_config()
        
        if not config:
            return """
            <div style="background: #ffebee; border: 1px solid #ef5350; padding: 12px; border-radius: 6px;">
                ❌ No configuration loaded - cannot execute
            </div>
            """
        
        # Get cached validation
        cached_validation = self.state_service.get('last_validation')
        if not cached_validation:
            cached_validation = self.validation_service.validate_config(config)
            self.state_service.set('last_validation', cached_validation)
        
        if cached_validation.is_valid:
            if cached_validation.warnings:
                return f"""
                <div style="background: #fff3e0; border: 1px solid #ffb74d; padding: 12px; border-radius: 6px;">
                    ⚠️ Ready to execute (with {len(cached_validation.warnings)} warning(s))
                </div>
                """
            else:
                return """
                <div style="background: #e8f5e9; border: 1px solid #66bb6a; padding: 12px; border-radius: 6px;">
                    ✅ Ready to execute
                </div>
                """
        else:
            error_count = len(cached_validation.errors)
            return f"""
            <div style="background: #ffebee; border: 1px solid #ef5350; padding: 12px; border-radius: 6px;">
                ❌ Cannot execute - {error_count} validation error(s) detected
                <br><small>Fix errors in Config Editor tab first</small>
            </div>
            """
    
    @ui_error_handler("Validation check failed")
    @track_performance("Validate Config")
    def validate_config(self):
        """Validate the current configuration."""
        config = self.get_current_config()
        
        if not config:
            UIFeedback.warning("No configuration loaded")
            return self.show_error("No configuration loaded. Please load a config first.")
        
        with self.with_loading("Validating configuration..."):
            # Force fresh validation
            validation_result = self.validation_service.validate_config(config)
            self.state_service.set('last_validation', validation_result)
        
        # Update pre-flight display
        return self._get_preflight_status()
    
    def parse_inputs(self, inputs_text: str) -> Dict[str, Any]:
        """Parse input text into dictionary."""
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
        """Execute the flow with given inputs."""
        config = self.get_current_config()
        
        if not config:
            UIFeedback.error("No configuration loaded")
            return self.show_error("No configuration loaded. Please load a config first.")
        
        # Validate first
        cached_validation = self.state_service.get('last_validation')
        if not cached_validation:
            cached_validation = self.validation_service.validate_config(config)
        
        if not cached_validation.is_valid:
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
                f"key2: value2"
            )
        
        try:
            self.logger.info(f"Starting flow execution with inputs: {inputs}")
            
            # Show starting notification
            if inputs:
                inputs_summary = ", ".join([f"{k}='{v}'" for k, v in inputs.items()])
                UIFeedback.info(f"Starting flow with: {inputs_summary}")
            else:
                UIFeedback.info("Starting flow execution (no inputs)")
            
            # Execute flow
            with self.with_loading("Executing flow... This may take a few minutes"):
                result = self.execution_service.execute_flow(config, inputs)
            
            # Store result for Results tab
            self.state_service.set('last_execution_result', result)
            
            if result.status == 'success':
                UIFeedback.success("Flow completed successfully!")
                
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