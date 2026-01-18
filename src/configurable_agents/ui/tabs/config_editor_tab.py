"""
Config Editor Tab

Simple configuration editor for loading, creating, and managing configs.
Provides YAML upload/download and basic config management.
"""

import gradio as gr
import yaml
from pathlib import Path
from .base_tab import BaseTab
from ...domain import FlowConfig


class ConfigEditorTab(BaseTab):
    """Config editor tab for managing configurations."""
    
    def render(self) -> None:
        """Render config editor tab content."""
        
        with gr.Column():
            gr.Markdown("## ⚙️ Configuration Management")
            gr.Markdown("Load, create, and manage your flow configurations")
            
            gr.Markdown("---")
            
            # Load/Save section
            gr.Markdown("### 📁 Load Configuration")
            
            with gr.Row():
                self.config_file = gr.File(
                    label="Upload YAML Config",
                    file_types=[".yaml", ".yml"]
                )
                load_btn = gr.Button("📤 Load Config", variant="primary")
            
            self.load_status = gr.HTML(value="")
            
            gr.Markdown("---")
            
            # Config viewer/editor
            gr.Markdown("### 📝 Configuration (YAML)")
            gr.Markdown("View and edit your configuration")
            
            self.config_editor = gr.Code(
                label="YAML Configuration",
                language="yaml",
                value="# No configuration loaded\n# Upload a YAML file to get started",
                lines=20
            )
            
            # Action buttons
            with gr.Row():
                save_btn = gr.Button("💾 Save Changes", variant="primary")
                download_btn = gr.Button("⬇️ Download YAML", variant="secondary")
                reset_btn = gr.Button("🔄 Load Default", variant="secondary")
            
            self.save_status = gr.HTML(value="")
            self.download_file = gr.File(label="Download", visible=False)
            
            gr.Markdown("---")
            
            # Quick stats
            gr.Markdown("### 📊 Configuration Stats")
            
            with gr.Row():
                self.stats_text = gr.Textbox(
                    label="Current Config Summary",
                    value="No config loaded",
                    interactive=False,
                    lines=3
                )
            
            # Wire up events
            load_btn.click(
                fn=self.load_config,
                inputs=[self.config_file],
                outputs=[self.config_editor, self.load_status, self.stats_text]
            )
            
            save_btn.click(
                fn=self.save_config,
                inputs=[self.config_editor],
                outputs=[self.save_status]
            )
            
            download_btn.click(
                fn=self.prepare_download,
                inputs=[],
                outputs=[self.download_file]
            )
            
            reset_btn.click(
                fn=self.load_default_config,
                inputs=[],
                outputs=[self.config_editor, self.load_status, self.stats_text]
            )
    
    def load_config(self, file_obj):
        """
        Load configuration from uploaded file.
        
        Args:
            file_obj: Uploaded file object
            
        Returns:
            Tuple of (yaml_text, status_html, stats_text)
        """
        if not file_obj:
            return (
                "# No file uploaded",
                self.show_error("Please upload a YAML file"),
                "No config loaded"
            )
        
        try:
            # Read file
            with open(file_obj, 'r', encoding='utf-8') as f:
                yaml_text = f.read()
            
            # Parse and validate
            data = yaml.safe_load(yaml_text)
            config = self.config_service.load_from_dict(data)
            
            # Validate
            validation_result = self.validation_service.validate_config(config)
            
            # Store in state
            self.set_current_config(config)
            
            # Generate stats
            stats = (
                f"Name: {config.flow.name}\n"
                f"Steps: {len(config.steps)} | Crews: {len(config.crews)} | "
                f"Agents: {config.count_agents()} | Tasks: {config.count_tasks()}"
            )
            
            if validation_result.is_valid:
                status = self.show_success("✅ Config loaded and validated successfully!")
            else:
                status = self.show_warning(
                    f"⚠️ Config loaded but has {len(validation_result.errors)} validation error(s)"
                )
            
            return (yaml_text, status, stats)
        
        except yaml.YAMLError as e:
            return (
                "# Error parsing YAML",
                self.show_error(f"YAML parsing error: {str(e)}"),
                "Parse error"
            )
        except Exception as e:
            self.logger.error(f"Error loading config: {e}", exc_info=True)
            return (
                "# Error loading config",
                self.show_error(f"Error: {str(e)}"),
                "Load error"
            )
    
    def save_config(self, yaml_text: str):
        """
        Save edited configuration.
        
        Args:
            yaml_text: YAML configuration text
            
        Returns:
            Status HTML
        """
        if not yaml_text or yaml_text.startswith("# No"):
            return self.show_error("No configuration to save")
        
        try:
            # Parse YAML
            data = yaml.safe_load(yaml_text)
            config = self.config_service.load_from_dict(data)
            
            # Validate
            validation_result = self.validation_service.validate_config(config)
            
            # Store in state
            self.set_current_config(config)
            
            if validation_result.is_valid:
                return self.show_success("✅ Configuration saved successfully!")
            else:
                return self.show_warning(
                    f"⚠️ Configuration saved but has {len(validation_result.errors)} validation error(s)"
                )
        
        except yaml.YAMLError as e:
            return self.show_error(f"YAML parsing error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error saving config: {e}", exc_info=True)
            return self.show_error(f"Error: {str(e)}")
    
    def prepare_download(self):
        """
        Prepare current config for download.
        
        Returns:
            File path for download
        """
        config = self.get_current_config()
        
        if not config:
            return None
        
        # Convert to YAML
        import tempfile
        
        config_dict = self.config_service.to_dict(config)
        yaml_text = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
        
        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False,
            prefix=f"{config.flow.name.replace(' ', '_')}_"
        ) as f:
            f.write(yaml_text)
            return f.name
    
    def load_default_config(self):
        """
        Load the default article generation config.
        
        Returns:
            Tuple of (yaml_text, status_html, stats_text)
        """
        try:
            # Look for default config
            default_path = Path(__file__).parent.parent.parent / "article_generation_flow.yaml"
            
            if not default_path.exists():
                return (
                    "# Default config not found",
                    self.show_error("Default configuration file not found"),
                    "Error"
                )
            
            # Load it
            config = self.config_service.load_from_file(str(default_path))
            
            # Convert to YAML text
            config_dict = self.config_service.to_dict(config)
            yaml_text = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
            
            # Store in state
            self.set_current_config(config)
            
            # Generate stats
            stats = (
                f"Name: {config.flow.name}\n"
                f"Steps: {len(config.steps)} | Crews: {len(config.crews)} | "
                f"Agents: {config.count_agents()} | Tasks: {config.count_tasks()}"
            )
            
            return (
                yaml_text,
                self.show_success("✅ Default configuration loaded!"),
                stats
            )
        
        except Exception as e:
            self.logger.error(f"Error loading default config: {e}", exc_info=True)
            return (
                "# Error loading default",
                self.show_error(f"Error: {str(e)}"),
                "Error"
            )