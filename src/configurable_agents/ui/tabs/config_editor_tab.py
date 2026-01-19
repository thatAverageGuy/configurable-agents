"""
Config Editor Tab

Simple configuration editor for loading, creating, and managing configs.
Provides YAML upload/download and basic config management with comprehensive error handling.
"""

import gradio as gr
import yaml
from pathlib import Path
from .base_tab import BaseTab
from ...domain import FlowConfig
from ..error_handler import ui_error_handler, track_performance
from ..utils import UIFeedback, validate_file_upload, safe_file_operation
import tempfile


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
    
    @ui_error_handler("Failed to load configuration")
    @track_performance("Load Config")
    def load_config(self, file_obj):
        """
        Load configuration from uploaded file.
        
        Args:
            file_obj: Uploaded file object
            
        Returns:
            Tuple of (yaml_text, status_html, stats_text)
        """
        if not file_obj:
            UIFeedback.warning("No file uploaded")
            return (
                "# No file uploaded",
                self.show_error("Please upload a YAML file"),
                "No config loaded"
            )
        
        # Validate file upload
        is_valid, error_msg = validate_file_upload(
            file_obj,
            allowed_extensions=['.yaml', '.yml'],
            max_size_mb=10
        )
        
        if not is_valid:
            UIFeedback.error("Invalid file")
            return (
                "# Invalid file",
                self.show_error(error_msg),
                "Invalid file"
            )
        
        try:
            with self.with_loading("Loading configuration..."):
                # Read file
                def read_file():
                    with open(file_obj, 'r', encoding='utf-8') as f:
                        return f.read()
                
                yaml_text = safe_file_operation(
                    read_file,
                    None,
                    "Failed to read file"
                )
                
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
                UIFeedback.success(f"Config '{config.flow.name}' loaded successfully!")
                status = self.show_success("✅ Config loaded and validated successfully!")
            else:
                UIFeedback.warning(f"Config loaded but has {len(validation_result.errors)} error(s)")
                status = self.show_warning(
                    f"⚠️ Config loaded but has {len(validation_result.errors)} validation error(s). "
                    f"Fix them before executing."
                )
            
            return (yaml_text, status, stats)
        
        except yaml.YAMLError as e:
            UIFeedback.error("YAML parsing error")
            return (
                "# Error parsing YAML",
                self.show_error(f"YAML parsing error: {str(e)}", include_suggestion=True),
                "Parse error"
            )
        except Exception as e:
            self.logger.error(f"Error loading config: {e}", exc_info=True)
            UIFeedback.error("Failed to load config")
            return (
                "# Error loading config",
                self.show_error(f"Error: {str(e)}", include_suggestion=True),
                "Load error"
            )
    
    @ui_error_handler("Failed to save configuration")
    @track_performance("Save Config")
    def save_config(self, yaml_text: str):
        """
        Save edited configuration.
        
        Args:
            yaml_text: YAML configuration text
            
        Returns:
            Status HTML
        """
        if not yaml_text or yaml_text.startswith("# No"):
            UIFeedback.warning("No configuration to save")
            return self.show_error("No configuration to save")
        
        try:
            with self.with_loading("Saving configuration..."):
                # Parse YAML
                data = yaml.safe_load(yaml_text)
                config = self.config_service.load_from_dict(data)
                
                # Validate
                validation_result = self.validation_service.validate_config(config)
                
                # Store in state
                self.set_current_config(config)
            
            if validation_result.is_valid:
                UIFeedback.success("Configuration saved!")
                return self.show_success("✅ Configuration saved successfully!")
            else:
                UIFeedback.warning(f"Saved with {len(validation_result.errors)} error(s)")
                return self.show_warning(
                    f"⚠️ Configuration saved but has {len(validation_result.errors)} validation error(s). "
                    f"Check the Overview tab for details."
                )
        
        except yaml.YAMLError as e:
            UIFeedback.error("YAML parsing error")
            return self.show_error(f"YAML parsing error: {str(e)}", include_suggestion=True)
        except Exception as e:
            self.logger.error(f"Error saving config: {e}", exc_info=True)
            UIFeedback.error("Failed to save config")
            return self.show_error(f"Error: {str(e)}", include_suggestion=True)
    
    @ui_error_handler("Failed to prepare download")
    @track_performance("Prepare Download")
    def prepare_download(self):
        """
        Prepare current config for download.
        
        Returns:
            File path for download or None
        """
        config = self.get_current_config()
        
        if not config:
            UIFeedback.warning("No configuration to download")
            return None
        
        try:
            with self.with_loading("Preparing download..."):
                # Convert to YAML
                config_dict = self.config_service.to_dict(config)
                yaml_text = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
                
                # Create temp file
                def create_temp_file():
                    with tempfile.NamedTemporaryFile(
                        mode='w',
                        suffix='.yaml',
                        delete=False,
                        prefix=f"{config.flow.name.replace(' ', '_')}_"
                    ) as f:
                        f.write(yaml_text)
                        return f.name
                
                file_path = safe_file_operation(
                    create_temp_file,
                    None,
                    "Failed to create download file"
                )
            
            if file_path:
                UIFeedback.success("Download prepared")
            
            return file_path
        
        except Exception as e:
            self.logger.error(f"Error preparing download: {e}", exc_info=True)
            UIFeedback.error("Failed to prepare download")
            return None
    
    @ui_error_handler("Failed to load default configuration")
    @track_performance("Load Default Config")
    def load_default_config(self):
        """
        Load the default article generation config.
        
        Returns:
            Tuple of (yaml_text, status_html, stats_text)
        """
        try:
            with self.with_loading("Loading default configuration..."):
                # Look for default config
                default_path = Path(__file__).parent.parent.parent / "article_generation_flow.yaml"
                
                if not default_path.exists():
                    UIFeedback.error("Default config not found")
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
            
            UIFeedback.success("Default configuration loaded!")
            
            return (
                yaml_text,
                self.show_success("✅ Default configuration loaded!"),
                stats
            )
        
        except Exception as e:
            self.logger.error(f"Error loading default config: {e}", exc_info=True)
            UIFeedback.error("Failed to load default config")
            return (
                "# Error loading default",
                self.show_error(f"Error: {str(e)}", include_suggestion=True),
                "Error"
            )