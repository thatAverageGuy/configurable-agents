"""
Config Editor Tab

Full visual configuration editor with CRUD for flows, crews, agents, tasks, and steps.
This replaces the minimal config_editor_tab.py with comprehensive functionality.
"""

import gradio as gr
import yaml
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from .base_tab import BaseTab
from ...domain import (
    FlowConfig, StepConfig, CrewConfig, AgentConfig, TaskConfig, 
    LLMConfig, ExecutionConfig, FlowMetadata, StateConfig
)
from ..error_handler import ui_error_handler, track_performance
from ..utils import UIFeedback, validate_file_upload, safe_file_operation
from ...utils.id_generator import generate_unique_id, parse_key_value_text
from ...core.tool_registry import list_available_tools
import tempfile


class ConfigEditorTab(BaseTab):
    """Config editor tab with full visual CRUD operations."""
    
    def render(self) -> None:
        """Render complete config editor with all tabs and functionality."""
        
        with gr.Column():
            gr.Markdown("## ⚙️ Configuration Editor")
            gr.Markdown("Visual editor for complete workflow configuration")
            
            # Validation status banner
            self.validation_status = gr.HTML(value="")
            
            gr.Markdown("---")
            
            # Main editing tabs
            with gr.Tabs() as self.main_tabs:
                
                # FLOW SETTINGS TAB
                with gr.Tab("🎯 Flow Settings"):
                    self._render_flow_settings_tab()
                
                # STEPS TAB
                with gr.Tab("📋 Steps"):
                    self._render_steps_tab()
                
                # CREWS TAB
                with gr.Tab("👥 Crews"):
                    self._render_crews_tab()
                
                # YAML VIEW TAB
                with gr.Tab("📄 YAML View"):
                    self._render_yaml_tab()
            
            gr.Markdown("---")
            
            # Global action buttons
            self._render_global_actions()
    
    # ========== FLOW SETTINGS TAB ==========
    
    def _render_flow_settings_tab(self) -> None:
        """Render flow-level metadata and defaults editor."""
        
        gr.Markdown("### Flow Metadata")
        
        self.flow_name = gr.Textbox(
            label="Flow Name",
            placeholder="my_workflow",
            info="Unique name for this flow"
        )
        
        self.flow_description = gr.Textbox(
            label="Description",
            placeholder="What does this flow do?",
            lines=3
        )
        
        gr.Markdown("---")
        gr.Markdown("### Global LLM Defaults")
        
        with gr.Row():
            self.default_temperature = gr.Slider(
                0.0, 1.0, 0.7, 0.1,
                label="Temperature",
                info="Default creativity level"
            )
            
            self.default_max_tokens = gr.Number(
                value=4000,
                label="Max Tokens",
                info="Default token limit"
            )
        
        self.default_model = gr.Textbox(
            label="Model Override",
            placeholder="Leave empty to use MODEL env var",
            info="Optional: gemini-2.5-flash-lite, etc."
        )
        
        with gr.Row():
            save_flow_btn = gr.Button("💾 Save Flow Settings", variant="primary")
            load_flow_btn = gr.Button("🔄 Load Current", variant="secondary")
        
        self.flow_settings_status = gr.HTML()
        
        # Wire up buttons
        save_flow_btn.click(
            fn=self.save_flow_settings,
            inputs=[self.flow_name, self.flow_description, self.default_temperature, 
                    self.default_max_tokens, self.default_model],
            outputs=[self.flow_settings_status]
        )
        
        load_flow_btn.click(
            fn=self.load_flow_settings,
            inputs=[],
            outputs=[self.flow_name, self.flow_description, self.default_temperature,
                     self.default_max_tokens, self.default_model]
        )
    
    # ========== STEPS TAB ==========
    
    def _render_steps_tab(self) -> None:
        """Render steps editor with full CRUD."""
        
        gr.Markdown("### Steps - Execution Flow")
        gr.Markdown("Define the sequence of execution steps")
        
        # Step selector and actions
        with gr.Row():
            self.step_selector = gr.Dropdown(
                label="Select Step",
                choices=[],
                value=None,
                scale=3
            )
            
            add_step_btn = gr.Button("➕", scale=1, variant="primary")
            delete_step_btn = gr.Button("🗑️", scale=1, variant="stop")
            refresh_step_btn = gr.Button("🔄", scale=1)
        
        self.step_status = gr.HTML()
        
        gr.Markdown("---")
        gr.Markdown("### Step Configuration")
        
        self.step_id = gr.Textbox(label="Step ID", placeholder="step_1")
        
        self.step_is_start = gr.Checkbox(
            label="⭐ Start Step",
            value=False,
            info="Only one step can be marked as start"
        )
        
        self.step_crew = gr.Dropdown(
            label="Assigned Crew",
            choices=[],
            value=None,
            info="Which crew executes this step"
        )
        
        self.step_next = gr.Dropdown(
            label="Next Step",
            choices=["None (End)"],
            value="None (End)",
            info="Routing after completion"
        )
        
        self.step_inputs = gr.TextArea(
            label="Inputs (key: value)",
            placeholder="topic: {state.custom_var.topic}",
            lines=4,
            info="Template inputs for this step"
        )
        
        self.step_output = gr.Textbox(
            label="Output Path",
            placeholder="state.custom_var.result",
            info="Where to store step output"
        )
        
        save_step_btn = gr.Button("💾 Save Step", variant="primary")
        
        # Event handlers
        add_step_btn.click(
            fn=self.add_step,
            outputs=[self.step_status, self.step_selector, self.step_crew, self.step_next]
        )
        
        delete_step_btn.click(
            fn=self.delete_step,
            inputs=[self.step_selector],
            outputs=[self.step_status, self.step_selector]
        )
        
        refresh_step_btn.click(
            fn=self.refresh_steps,
            outputs=[self.step_selector, self.step_crew, self.step_next]
        )
        
        self.step_selector.change(
            fn=self.load_step,
            inputs=[self.step_selector],
            outputs=[self.step_id, self.step_is_start, self.step_crew, 
                     self.step_next, self.step_inputs, self.step_output]
        )
        
        save_step_btn.click(
            fn=self.save_step,
            inputs=[self.step_selector, self.step_id, self.step_is_start, 
                    self.step_crew, self.step_next, self.step_inputs, self.step_output],
            outputs=[self.step_status]
        )
    
    # ========== CREWS TAB ==========
    
    def _render_crews_tab(self) -> None:
        """Render crews editor with nested agents and tasks."""
        
        gr.Markdown("### Crews - Agent Teams")
        
        # Crew selector
        with gr.Row():
            self.crew_selector = gr.Dropdown(
                label="Select Crew",
                choices=[],
                value=None,
                scale=3
            )
            
            add_crew_btn = gr.Button("➕", scale=1, variant="primary")
            delete_crew_btn = gr.Button("🗑️", scale=1, variant="stop")
            refresh_crew_btn = gr.Button("🔄", scale=1)
        
        self.crew_status = gr.HTML()
        
        gr.Markdown("---")
        
        # Crew configuration tabs
        with gr.Tabs():
            
            with gr.Tab("⚙️ Crew Settings"):
                self._render_crew_settings()
            
            with gr.Tab("🤖 Agents"):
                self._render_agents_editor()
            
            with gr.Tab("📋 Tasks"):
                self._render_tasks_editor()
        
        # Wire up crew-level events
        add_crew_btn.click(
            fn=self.add_crew,
            outputs=[self.crew_status, self.crew_selector]
        )
        
        delete_crew_btn.click(
            fn=self.delete_crew,
            inputs=[self.crew_selector],
            outputs=[self.crew_status, self.crew_selector]
        )
        
        refresh_crew_btn.click(
            fn=self.refresh_crews,
            outputs=[self.crew_selector]
        )
    
    def _render_crew_settings(self) -> None:
        """Render crew-level LLM configuration."""
        
        gr.Markdown("### Crew LLM Overrides")
        gr.Markdown("Optional: Override global defaults for this crew")
        
        with gr.Row():
            self.crew_temperature = gr.Slider(0.0, 1.0, 0.7, 0.1, label="Temperature")
            self.crew_max_tokens = gr.Number(value=4000, label="Max Tokens")
        
        self.crew_model = gr.Textbox(
            label="Model Override",
            placeholder="Optional crew-specific model"
        )
        
        save_crew_btn = gr.Button("💾 Save Crew Settings", variant="primary")
        self.crew_settings_status = gr.HTML()
        
        save_crew_btn.click(
            fn=self.save_crew_settings,
            inputs=[self.crew_selector, self.crew_temperature, 
                    self.crew_max_tokens, self.crew_model],
            outputs=[self.crew_settings_status]
        )
        
        # Auto-load when crew changes
        self.crew_selector.change(
            fn=self.load_crew_settings,
            inputs=[self.crew_selector],
            outputs=[self.crew_temperature, self.crew_max_tokens, self.crew_model]
        )
    
    def _render_agents_editor(self) -> None:
        """Render agents editor within selected crew."""
        
        gr.Markdown("### Agents in This Crew")
        
        with gr.Row():
            self.agent_selector = gr.Dropdown(
                label="Select Agent",
                choices=[],
                value=None,
                scale=3
            )
            
            add_agent_btn = gr.Button("➕", scale=1, variant="primary")
            delete_agent_btn = gr.Button("🗑️", scale=1, variant="stop")
        
        self.agent_status = gr.HTML()
        
        gr.Markdown("---")
        
        self.agent_id = gr.Textbox(label="Agent ID", placeholder="researcher")
        self.agent_role = gr.Textbox(label="Role", placeholder="Senior Researcher")
        self.agent_goal = gr.TextArea(label="Goal", lines=2)
        self.agent_backstory = gr.TextArea(label="Backstory", lines=3)
        
        gr.Markdown("**Tools**")
        self.agent_tools = gr.CheckboxGroup(
            choices=list_available_tools(),
            label="Available Tools"
        )
        
        with gr.Accordion("⚙️ Agent LLM Overrides", open=False):
            with gr.Row():
                self.agent_temperature = gr.Slider(0.0, 1.0, 0.7, 0.1, label="Temperature")
            self.agent_model = gr.Textbox(label="Model Override", placeholder="Optional")
        
        save_agent_btn = gr.Button("💾 Save Agent", variant="primary")
        
        # Events
        add_agent_btn.click(
            fn=self.add_agent,
            inputs=[self.crew_selector],
            outputs=[self.agent_status, self.agent_selector]
        )
        
        delete_agent_btn.click(
            fn=self.delete_agent,
            inputs=[self.crew_selector, self.agent_selector],
            outputs=[self.agent_status, self.agent_selector]
        )
        
        self.agent_selector.change(
            fn=self.load_agent,
            inputs=[self.crew_selector, self.agent_selector],
            outputs=[self.agent_id, self.agent_role, self.agent_goal, 
                     self.agent_backstory, self.agent_tools, 
                     self.agent_temperature, self.agent_model]
        )
        
        save_agent_btn.click(
            fn=self.save_agent,
            inputs=[self.crew_selector, self.agent_selector, self.agent_id, 
                    self.agent_role, self.agent_goal, self.agent_backstory,
                    self.agent_tools, self.agent_temperature, self.agent_model],
            outputs=[self.agent_status]
        )
    
    def _render_tasks_editor(self) -> None:
        """Render tasks editor within selected crew."""
        
        gr.Markdown("### Tasks in This Crew")
        
        with gr.Row():
            self.task_selector = gr.Dropdown(
                label="Select Task",
                choices=[],
                value=None,
                scale=3
            )
            
            add_task_btn = gr.Button("➕", scale=1, variant="primary")
            delete_task_btn = gr.Button("🗑️", scale=1, variant="stop")
        
        self.task_status = gr.HTML()
        
        gr.Markdown("---")
        
        self.task_id = gr.Textbox(label="Task ID", placeholder="research_task")
        self.task_description = gr.TextArea(label="Description", lines=4)
        self.task_expected = gr.TextArea(label="Expected Output", lines=2)
        
        self.task_agent = gr.Dropdown(
            label="Assigned Agent",
            choices=[],
            value=None
        )
        
        with gr.Accordion("⚙️ Task LLM Overrides", open=False):
            with gr.Row():
                self.task_temperature = gr.Slider(0.0, 1.0, 0.7, 0.1, label="Temperature")
            self.task_model = gr.Textbox(label="Model Override", placeholder="Optional")
        
        save_task_btn = gr.Button("💾 Save Task", variant="primary")
        
        # Events
        add_task_btn.click(
            fn=self.add_task,
            inputs=[self.crew_selector],
            outputs=[self.task_status, self.task_selector]
        )
        
        delete_task_btn.click(
            fn=self.delete_task,
            inputs=[self.crew_selector, self.task_selector],
            outputs=[self.task_status, self.task_selector]
        )
        
        self.task_selector.change(
            fn=self.load_task,
            inputs=[self.crew_selector, self.task_selector],
            outputs=[self.task_id, self.task_description, self.task_expected,
                     self.task_agent, self.task_temperature, self.task_model]
        )
        
        save_task_btn.click(
            fn=self.save_task,
            inputs=[self.crew_selector, self.task_selector, self.task_id,
                    self.task_description, self.task_expected, self.task_agent,
                    self.task_temperature, self.task_model],
            outputs=[self.task_status]
        )
        
        # Update agent choices when crew changes
        self.crew_selector.change(
            fn=self.get_crew_agents,
            inputs=[self.crew_selector],
            outputs=[self.task_agent, self.agent_selector, self.task_selector]
        )
    
    # ========== YAML VIEW TAB ==========
    
    def _render_yaml_tab(self) -> None:
        """Render YAML view/edit tab."""
        
        gr.Markdown("### Raw YAML Configuration")
        
        self.yaml_editor = gr.Code(
            label="YAML",
            language="yaml",
            value="# No configuration loaded",
            lines=20
        )
        
        with gr.Row():
            load_yaml_btn = gr.Button("📥 Load from YAML", variant="primary")
            refresh_yaml_btn = gr.Button("🔄 Refresh YAML", variant="secondary")
        
        self.yaml_status = gr.HTML()
        
        load_yaml_btn.click(
            fn=self.load_from_yaml,
            inputs=[self.yaml_editor],
            outputs=[self.yaml_status]
        )
        
        refresh_yaml_btn.click(
            fn=self.refresh_yaml,
            outputs=[self.yaml_editor]
        )
    
    # ========== GLOBAL ACTIONS ==========
    
    def _render_global_actions(self) -> None:
        """Render global action buttons."""
        
        gr.Markdown("### 💾 Global Actions")
        
        with gr.Row():
            self.validate_all_btn = gr.Button("🔍 Validate Config", variant="secondary")
            self.download_yaml_btn = gr.Button("⬇️ Download YAML", variant="secondary")
            self.upload_yaml_btn = gr.Button("📤 Upload YAML", variant="secondary")
            self.reset_default_btn = gr.Button("🔄 Load Default", variant="secondary")
        
        self.download_file = gr.File(label="Download", visible=False)
        self.upload_file = gr.File(
            label="Upload",
            file_types=[".yaml", ".yml"],
            visible=False
        )
        
        # Wire up
        self.validate_all_btn.click(
            fn=self.validate_all,
            outputs=[self.validation_status]
        )
        
        self.download_yaml_btn.click(
            fn=self.prepare_download,
            outputs=[self.download_file]
        )
        
        self.upload_yaml_btn.click(
            fn=lambda: gr.update(visible=True),
            outputs=[self.upload_file]
        )
        
        self.upload_file.upload(
            fn=self.load_uploaded_config,
            inputs=[self.upload_file],
            outputs=[self.validation_status]
        )
        
        self.reset_default_btn.click(
            fn=self.load_default_config,
            outputs=[self.validation_status]
        )
    
    # ========== IMPLEMENTATION METHODS ==========
    # All the @ui_error_handler decorated methods follow...
    
    @ui_error_handler("Failed to save flow settings")
    @track_performance("Save Flow Settings")
    def save_flow_settings(self, name, desc, temp, tokens, model):
        """Save flow-level settings."""
        config = self.get_current_config()
        if not config:
            return self.show_error("No config loaded")
        
        # Update config
        config.flow.name = name or "unnamed_flow"
        config.flow.description = desc or ""
        config.defaults.temperature = temp
        config.defaults.max_tokens = int(tokens) if tokens else None
        config.defaults.model = model if model else None
        
        self.set_current_config(config)
        UIFeedback.success("Flow settings saved")
        return self.show_success("✅ Flow settings saved")
    
    @ui_error_handler("Failed to load flow settings")
    def load_flow_settings(self):
        """Load current flow settings into form."""
        config = self.get_current_config()
        if not config:
            return ("", "", 0.7, 4000, "")
        
        return (
            config.flow.name,
            config.flow.description,
            config.defaults.temperature,
            config.defaults.max_tokens or 4000,
            config.defaults.model or ""
        )
    
    # ===== STEP METHODS =====
    
    @ui_error_handler("Failed to add step")
    def add_step(self):
        """Add a new step."""
        config = self.get_current_config()
        if not config:
            return self.show_error("No config loaded"), gr.update(), gr.update(), gr.update()
        
        # Generate unique ID
        existing_ids = [s.id for s in config.steps]
        new_id = generate_unique_id("new_step", existing_ids)
        
        # Get first crew if available
        crew_ref = list(config.crews.keys())[0] if config.crews else ""
        
        # Create step
        new_step = StepConfig(
            id=new_id,
            type="crew",
            crew_ref=crew_ref,
            is_start=len(config.steps) == 0,  # First step is start
            next_step=None,
            inputs={},
            output_to_state=f"state.custom_var.{new_id}_output"
        )
        
        config.steps.append(new_step)
        self.set_current_config(config)
        
        UIFeedback.success(f"Added step: {new_id}")
        
        step_choices = [s.id for s in config.steps]
        crew_choices = list(config.crews.keys())
        next_choices = ["None (End)"] + step_choices
        
        return (
            self.show_success(f"✅ Added step: {new_id}"),
            gr.update(choices=step_choices, value=new_id),
            gr.update(choices=crew_choices),
            gr.update(choices=next_choices)
        )
    
    @ui_error_handler("Failed to delete step")
    def delete_step(self, step_id):
        """Delete a step with dependency checking."""
        if not step_id:
            return self.show_warning("No step selected"), gr.update()
        
        config = self.get_current_config()
        if not config:
            return self.show_error("No config loaded"), gr.update()
        
        # Check dependencies
        can_delete, dependent_steps = self.validation_service.can_delete_step(config, step_id)
        
        if not can_delete:
            UIFeedback.error(f"Cannot delete - used by {len(dependent_steps)} steps")
            return (
                self.show_error(
                    f"Cannot delete step '{step_id}' - "
                    f"these steps route to it: {', '.join(dependent_steps)}"
                ),
                gr.update()
            )
        
        # Delete step
        config.steps = [s for s in config.steps if s.id != step_id]
        self.set_current_config(config)
        
        UIFeedback.success(f"Deleted step: {step_id}")
        
        step_choices = [s.id for s in config.steps]
        return (
            self.show_success(f"✅ Deleted step: {step_id}"),
            gr.update(choices=step_choices, value=None)
        )
    
    @ui_error_handler("Failed to refresh steps")
    def refresh_steps(self):
        """Refresh step dropdowns."""
        config = self.get_current_config()
        if not config:
            return gr.update(choices=[]), gr.update(choices=[]), gr.update(choices=["None (End)"])
        
        step_choices = [s.id for s in config.steps]
        crew_choices = list(config.crews.keys())
        next_choices = ["None (End)"] + step_choices
        
        return (
            gr.update(choices=step_choices),
            gr.update(choices=crew_choices),
            gr.update(choices=next_choices)
        )
    
    @ui_error_handler("Failed to load step")
    def load_step(self, step_id):
        """Load step into editor form."""
        if not step_id:
            return ("", False, None, "None (End)", "", "")
        
        config = self.get_current_config()
        if not config:
            return ("", False, None, "None (End)", "", "")
        
        step = config.get_step(step_id)
        if not step:
            return ("", False, None, "None (End)", "", "")
        
        # Format inputs
        inputs_text = "\n".join([f"{k}: {v}" for k, v in step.inputs.items()])
        
        # Format next_step
        next_display = step.next_step if step.next_step else "None (End)"
        
        return (
            step.id,
            step.is_start,
            step.crew_ref,
            next_display,
            inputs_text,
            step.output_to_state
        )
    
    @ui_error_handler("Failed to save step")
    def save_step(self, old_id, new_id, is_start, crew_ref, next_step, inputs_text, output):
        """Save step changes."""
        if not old_id:
            return self.show_warning("No step selected")
        
        config = self.get_current_config()
        if not config:
            return self.show_error("No config loaded")
        
        # Find step
        step = config.get_step(old_id)
        if not step:
            return self.show_error(f"Step '{old_id}' not found")
        
        # Parse inputs
        try:
            inputs_dict = parse_key_value_text(inputs_text) if inputs_text else {}
        except Exception as e:
            return self.show_error(f"Invalid inputs format: {e}")
        
        # Update step
        step.id = new_id or old_id
        step.is_start = is_start
        step.crew_ref = crew_ref or ""
        step.next_step = None if next_step == "None (End)" else next_step
        step.inputs = inputs_dict
        step.output_to_state = output or ""
        
        # If marked as start, unmark others
        if is_start:
            for s in config.steps:
                if s.id != step.id:
                    s.is_start = False
        
        self.set_current_config(config)
        UIFeedback.success(f"Saved step: {step.id}")
        return self.show_success(f"✅ Saved step: {step.id}")
    
    # ===== CREW METHODS =====
    
    @ui_error_handler("Failed to add crew")
    def add_crew(self):
        """Add a new crew."""
        config = self.get_current_config()
        if not config:
            return self.show_error("No config loaded"), gr.update()
        
        # Generate unique name
        existing_names = list(config.crews.keys())
        new_name = generate_unique_id("new_crew", existing_names)
        
        # Create crew with defaults
        new_crew = CrewConfig(
            agents=[],
            tasks=[],
            execution=ExecutionConfig(type="sequential", tasks=[]),
            llm=LLMConfig(temperature=0.7)
        )
        
        config.crews[new_name] = new_crew
        self.set_current_config(config)
        
        UIFeedback.success(f"Added crew: {new_name}")
        
        crew_choices = list(config.crews.keys())
        return (
            self.show_success(f"✅ Added crew: {new_name}"),
            gr.update(choices=crew_choices, value=new_name)
        )
    
    @ui_error_handler("Failed to delete crew")
    def delete_crew(self, crew_name):
        """Delete a crew with dependency checking."""
        if not crew_name:
            return self.show_warning("No crew selected"), gr.update()
        
        config = self.get_current_config()
        if not config:
            return self.show_error("No config loaded"), gr.update()
        
        # Check dependencies
        can_delete, dependent_steps = self.validation_service.can_delete_crew(config, crew_name)
        
        if not can_delete:
            UIFeedback.error(f"Cannot delete - used by {len(dependent_steps)} steps")
            return (
                self.show_error(
                    f"Cannot delete crew '{crew_name}' - "
                    f"these steps reference it: {', '.join(dependent_steps)}"
                ),
                gr.update()
            )
        
        # Delete crew
        del config.crews[crew_name]
        self.set_current_config(config)
        
        UIFeedback.success(f"Deleted crew: {crew_name}")
        
        crew_choices = list(config.crews.keys())
        return (
            self.show_success(f"✅ Deleted crew: {crew_name}"),
            gr.update(choices=crew_choices, value=None)
        )
    
    @ui_error_handler("Failed to refresh crews")
    def refresh_crews(self):
        """Refresh crew dropdown."""
        config = self.get_current_config()
        if not config:
            return gr.update(choices=[])
        
        return gr.update(choices=list(config.crews.keys()))
    
    @ui_error_handler("Failed to save crew settings")
    def save_crew_settings(self, crew_name, temp, tokens, model):
        """Save crew-level LLM settings."""
        if not crew_name:
            return self.show_warning("No crew selected")
        
        config = self.get_current_config()
        if not config:
            return self.show_error("No config loaded")
        
        crew = config.get_crew(crew_name)
        if not crew:
            return self.show_error(f"Crew '{crew_name}' not found")
        
        # Update LLM config
        if not crew.llm:
            crew.llm = LLMConfig()
        
        crew.llm.temperature = temp
        crew.llm.max_tokens = int(tokens) if tokens else None
        crew.llm.model = model if model else None
        
        self.set_current_config(config)
        UIFeedback.success(f"Saved settings for {crew_name}")
        return self.show_success(f"✅ Saved {crew_name} settings")
    
    @ui_error_handler("Failed to load crew settings")
    def load_crew_settings(self, crew_name):
        """Load crew LLM settings."""
        if not crew_name:
            return (0.7, 4000, "")
        
        config = self.get_current_config()
        if not config:
            return (0.7, 4000, "")
        
        crew = config.get_crew(crew_name)
        if not crew or not crew.llm:
            return (0.7, 4000, "")
        
        return (
            crew.llm.temperature,
            crew.llm.max_tokens or 4000,
            crew.llm.model or ""
        )
    
    # ===== AGENT METHODS =====
    
    @ui_error_handler("Failed to add agent")
    def add_agent(self, crew_name):
        """Add agent to crew."""
        if not crew_name:
            return self.show_warning("No crew selected"), gr.update()
        
        config = self.get_current_config()
        crew = config.get_crew(crew_name)
        if not crew:
            return self.show_error(f"Crew '{crew_name}' not found"), gr.update()
        
        # Generate unique ID
        existing_ids = [a.id for a in crew.agents]
        new_id = generate_unique_id("new_agent", existing_ids)
        
        # Create agent
        new_agent = AgentConfig(
            id=new_id,
            role="New Agent",
            goal="Define agent goal",
            backstory="Define agent backstory",
            tools=[],
            llm=None
        )
        
        crew.agents.append(new_agent)
        self.set_current_config(config)
        
        UIFeedback.success(f"Added agent: {new_id}")
        
        agent_choices = [a.id for a in crew.agents]
        return (
            self.show_success(f"✅ Added agent: {new_id}"),
            gr.update(choices=agent_choices, value=new_id)
        )
    
    @ui_error_handler("Failed to delete agent")
    def delete_agent(self, crew_name, agent_id):
        """Delete agent with dependency checking."""
        if not crew_name or not agent_id:
            return self.show_warning("No crew/agent selected"), gr.update()
        
        config = self.get_current_config()
        crew = config.get_crew(crew_name)
        if not crew:
            return self.show_error(f"Crew '{crew_name}' not found"), gr.update()
        
        # Check dependencies
        can_delete, dependent_tasks = self.validation_service.can_delete_agent(crew, agent_id)
        
        if not can_delete:
            UIFeedback.error(f"Cannot delete - used by {len(dependent_tasks)} tasks")
            return (
                self.show_error(
                    f"Cannot delete agent '{agent_id}' - "
                    f"these tasks depend on it: {', '.join(dependent_tasks)}"
                ),
                gr.update()
            )
        
        # Delete agent
        crew.agents = [a for a in crew.agents if a.id != agent_id]
        self.set_current_config(config)
        
        UIFeedback.success(f"Deleted agent: {agent_id}")
        
        agent_choices = [a.id for a in crew.agents]
        return (
            self.show_success(f"✅ Deleted agent: {agent_id}"),
            gr.update(choices=agent_choices, value=None)
        )
    
    @ui_error_handler("Failed to load agent")
    def load_agent(self, crew_name, agent_id):
        """Load agent into form."""
        if not crew_name or not agent_id:
            return ("", "", "", "", [], 0.7, "")
        
        config = self.get_current_config()
        crew = config.get_crew(crew_name)
        if not crew:
            return ("", "", "", "", [], 0.7, "")
        
        agent = crew.get_agent(agent_id)
        if not agent:
            return ("", "", "", "", [], 0.7, "")
        
        return (
            agent.id,
            agent.role,
            agent.goal,
            agent.backstory,
            agent.tools,
            agent.llm.temperature if agent.llm else 0.7,
            agent.llm.model if agent.llm else ""
        )
    
    @ui_error_handler("Failed to save agent")
    def save_agent(self, crew_name, old_id, new_id, role, goal, backstory, tools, temp, model):
        """Save agent changes."""
        if not crew_name or not old_id:
            return self.show_warning("No crew/agent selected")
        
        config = self.get_current_config()
        crew = config.get_crew(crew_name)
        if not crew:
            return self.show_error(f"Crew '{crew_name}' not found")
        
        agent = crew.get_agent(old_id)
        if not agent:
            return self.show_error(f"Agent '{old_id}' not found")
        
        # Update agent
        agent.id = new_id or old_id
        agent.role = role or "New Agent"
        agent.goal = goal or "Define goal"
        agent.backstory = backstory or "Define backstory"
        agent.tools = tools or []
        
        # Update LLM if specified
        if temp != 0.7 or model:
            if not agent.llm:
                agent.llm = LLMConfig()
            agent.llm.temperature = temp
            agent.llm.model = model if model else None
        
        self.set_current_config(config)
        UIFeedback.success(f"Saved agent: {agent.id}")
        return self.show_success(f"✅ Saved agent: {agent.id}")
    
    # ===== TASK METHODS =====
    
    @ui_error_handler("Failed to add task")
    def add_task(self, crew_name):
        """Add task to crew."""
        if not crew_name:
            return self.show_warning("No crew selected"), gr.update()
        
        config = self.get_current_config()
        crew = config.get_crew(crew_name)
        if not crew:
            return self.show_error(f"Crew '{crew_name}' not found"), gr.update()
        
        # Get first agent if available
        agent_id = crew.agents[0].id if crew.agents else ""
        
        # Generate unique ID
        existing_ids = [t.id for t in crew.tasks]
        new_id = generate_unique_id("new_task", existing_ids)
        
        # Create task
        new_task = TaskConfig(
            id=new_id,
            description="Define task description",
            expected_output="Define expected output",
            agent=agent_id,
            context=[],
            output_model=None,
            llm=None
        )
        
        crew.tasks.append(new_task)
        
        # Add to execution order
        crew.execution.tasks.append(new_id)
        
        self.set_current_config(config)
        
        UIFeedback.success(f"Added task: {new_id}")
        
        task_choices = [t.id for t in crew.tasks]
        return (
            self.show_success(f"✅ Added task: {new_id}"),
            gr.update(choices=task_choices, value=new_id)
        )
    
    @ui_error_handler("Failed to delete task")
    def delete_task(self, crew_name, task_id):
        """Delete task."""
        if not crew_name or not task_id:
            return self.show_warning("No crew/task selected"), gr.update()
        
        config = self.get_current_config()
        crew = config.get_crew(crew_name)
        if not crew:
            return self.show_error(f"Crew '{crew_name}' not found"), gr.update()
        
        # Delete task
        crew.tasks = [t for t in crew.tasks if t.id != task_id]
        
        # Remove from execution order
        crew.execution.tasks = [t for t in crew.execution.tasks if t != task_id]
        
        self.set_current_config(config)
        
        UIFeedback.success(f"Deleted task: {task_id}")
        
        task_choices = [t.id for t in crew.tasks]
        return (
            self.show_success(f"✅ Deleted task: {task_id}"),
            gr.update(choices=task_choices, value=None)
        )
    
    @ui_error_handler("Failed to load task")
    def load_task(self, crew_name, task_id):
        """Load task into form."""
        if not crew_name or not task_id:
            return ("", "", "", None, 0.7, "")
        
        config = self.get_current_config()
        crew = config.get_crew(crew_name)
        if not crew:
            return ("", "", "", None, 0.7, "")
        
        task = crew.get_task(task_id)
        if not task:
            return ("", "", "", None, 0.7, "")
        
        return (
            task.id,
            task.description,
            task.expected_output,
            task.agent,
            task.llm.temperature if task.llm else 0.7,
            task.llm.model if task.llm else ""
        )
    
    @ui_error_handler("Failed to save task")
    def save_task(self, crew_name, old_id, new_id, desc, expected, agent, temp, model):
        """Save task changes."""
        if not crew_name or not old_id:
            return self.show_warning("No crew/task selected")
        
        config = self.get_current_config()
        crew = config.get_crew(crew_name)
        if not crew:
            return self.show_error(f"Crew '{crew_name}' not found")
        
        task = crew.get_task(old_id)
        if not task:
            return self.show_error(f"Task '{old_id}' not found")
        
        # Update task
        task.id = new_id or old_id
        task.description = desc or "Define description"
        task.expected_output = expected or "Define output"
        task.agent = agent or ""
        
        # Update LLM if specified
        if temp != 0.7 or model:
            if not task.llm:
                task.llm = LLMConfig()
            task.llm.temperature = temp
            task.llm.model = model if model else None
        
        self.set_current_config(config)
        UIFeedback.success(f"Saved task: {task.id}")
        return self.show_success(f"✅ Saved task: {task.id}")
    
    @ui_error_handler("Failed to get crew agents")
    def get_crew_agents(self, crew_name):
        """Get list of agents in crew for task assignment."""
        if not crew_name:
            return gr.update(choices=[]), gr.update(choices=[]), gr.update(choices=[])
        
        config = self.get_current_config()
        crew = config.get_crew(crew_name)
        if not crew:
            return gr.update(choices=[]), gr.update(choices=[]), gr.update(choices=[])
        
        agent_choices = [a.id for a in crew.agents]
        task_choices = [t.id for t in crew.tasks]
        
        return (
            gr.update(choices=agent_choices),
            gr.update(choices=agent_choices),
            gr.update(choices=task_choices)
        )
    
    # ===== YAML AND VALIDATION METHODS =====
    
    @ui_error_handler("Failed to refresh YAML")
    def refresh_yaml(self):
        """Refresh YAML view from current config."""
        config = self.get_current_config()
        if not config:
            return "# No configuration loaded"
        
        config_dict = self.config_service.to_dict(config)
        yaml_text = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
        return yaml_text
    
    @ui_error_handler("Failed to load from YAML")
    def load_from_yaml(self, yaml_text):
        """Load config from YAML text."""
        if not yaml_text or yaml_text.startswith("#"):
            return self.show_warning("No YAML to load")
        
        try:
            data = yaml.safe_load(yaml_text)
            config = self.config_service.load_from_dict(data)
            self.set_current_config(config)
            
            UIFeedback.success("Loaded from YAML")
            return self.show_success("✅ Loaded configuration from YAML")
        except yaml.YAMLError as e:
            UIFeedback.error("YAML parsing error")
            return self.show_error(f"YAML parsing error: {e}")
    
    @ui_error_handler("Failed to validate")
    def validate_all(self):
        """Validate entire configuration."""
        is_valid, validation_html = self.validate_current_config()
        return validation_html
    
    @ui_error_handler("Failed to prepare download")
    def prepare_download(self):
        """Prepare config for download."""
        config = self.get_current_config()
        if not config:
            UIFeedback.warning("No config to download")
            return None
        
        with self.with_loading("Preparing download..."):
            config_dict = self.config_service.to_dict(config)
            yaml_text = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
            
            def create_temp_file():
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.yaml',
                    delete=False,
                    prefix=f"{config.flow.name.replace(' ', '_')}_"
                ) as f:
                    f.write(yaml_text)
                    return f.name
            
            file_path = safe_file_operation(create_temp_file, None, "Failed to create file")
        
        if file_path:
            UIFeedback.success("Download ready")
        
        return file_path
    
    @ui_error_handler("Failed to load uploaded config")
    def load_uploaded_config(self, file_obj):
        """Load uploaded YAML file."""
        if not file_obj:
            return self.show_warning("No file uploaded")
        
        is_valid, error_msg = validate_file_upload(
            file_obj,
            allowed_extensions=['.yaml', '.yml'],
            max_size_mb=10
        )
        
        if not is_valid:
            UIFeedback.error(error_msg)
            return self.show_error(error_msg)
        
        try:
            with self.with_loading("Loading configuration..."):
                config = self.config_service.load_from_file(file_obj)
                self.set_current_config(config)
            
            UIFeedback.success(f"Loaded: {config.flow.name}")
            return self.show_success(f"✅ Loaded: {config.flow.name}")
        except Exception as e:
            UIFeedback.error("Failed to load config")
            return self.show_error(f"Error: {e}")
    
    @ui_error_handler("Failed to load default config")
    def load_default_config(self):
        """Load default article generation config."""
        try:
            with self.with_loading("Loading default configuration..."):
                default_path = Path(__file__).parent.parent.parent / "article_generation_flow.yaml"
                
                if not default_path.exists():
                    return self.show_error("Default config not found")
                
                config = self.config_service.load_from_file(str(default_path))
                self.set_current_config(config)
            
            UIFeedback.success("Default config loaded")
            return self.show_success(f"✅ Loaded: {config.flow.name}")
        except Exception as e:
            UIFeedback.error("Failed to load default")
            return self.show_error(f"Error: {e}")