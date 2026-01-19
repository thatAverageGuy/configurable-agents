"""
Chat-based Configuration Builder

Single-page app with chat interface + live artifact (diagram/YAML).
"""

import gradio as gr
import yaml
import os
from pathlib import Path

from ..services import ConfigService, ValidationService
from ..core.flow_visualizer import generate_mermaid_diagram
from ..config import setup_logging, get_settings, get_logger
from langchain_google_genai import ChatGoogleGenerativeAI

logger = get_logger(__name__)


def create_chat_builder_app() -> gr.Blocks:
    """Create the conversational config builder interface."""
    
    # Initialize services
    config_service = ConfigService()
    validation_service = ValidationService()
    
    # LLM setup
    def get_llm():
        return ChatGoogleGenerativeAI(
            model=os.getenv('MODEL', 'gemini-2.5-flash-lite'),
            temperature=0.7,
            google_api_key=os.getenv('GOOGLE_API_KEY')
        )
    
    # System prompt
    def build_system_prompt(current_config_yaml: str) -> str:
        return f"""You are a CrewAI Flow Configuration Assistant. Your ONLY job is to help users build agent workflows.

Current Configuration:
```yaml
{current_config_yaml}
```

RULES:
1. Ask ONE question at a time to gather requirements
2. After each user response, generate the UPDATED FULL configuration
3. ALWAYS output the complete valid YAML configuration
4. Keep responses concise - brief explanation + YAML block
5. NEVER discuss topics outside flow configuration
6. If user goes off-topic, redirect: "Let's focus on your workflow."

WORKFLOW STRUCTURE:
- flow: name, description
- defaults: llm settings (provider, temperature, max_tokens)
- state: common_vars list
- steps: list of execution steps (id, type, crew_ref, is_start, next_step, inputs, output_to_state)
- crews: dict of crew_name -> agents, tasks, execution

OUTPUT FORMAT:
Brief explanation of what you changed.
```yaml
<FULL UPDATED CONFIG HERE>
```

Remember: ALWAYS include the complete config in the yaml block, not just changes."""

    EMPTY_CONFIG = """flow:
  name: "my_flow"
  description: ""

defaults:
  llm:
    provider: "google"
    temperature: 0.7
    max_tokens: 4000

state:
  common_vars:
    - execution_id
    - current_step

steps: []

crews: {}
"""
    
    with gr.Blocks(title="🤖 Conversational Flow Builder", theme=gr.themes.Soft()) as app:
        
        gr.Markdown("# 🤖 Conversational Flow Builder")
        gr.Markdown("Build your agent workflow through natural conversation")
        
        # Hidden state
        config_state = gr.State(value=None)
        
        with gr.Row():
            # LEFT: Chat Interface (40%)
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    height=600,
                    label="💬 Chat",
                    show_label=True
                )
                
                msg_input = gr.Textbox(
                    placeholder="Describe your workflow... (e.g., 'Create a research and writing flow')",
                    show_label=False,
                    container=False
                )
                
                with gr.Row():
                    send_btn = gr.Button("Send", variant="primary", scale=2)
                    clear_btn = gr.Button("🔄 Start Over", scale=1)
            
            # RIGHT: Artifact (60%)
            with gr.Column(scale=3):
                with gr.Tabs() as artifact_tabs:
                    
                    # Diagram Tab
                    with gr.Tab("📊 Diagram"):
                        diagram_view = gr.Markdown(
                            value="```mermaid\ngraph TD\n    Start([No Config Yet])\n```",
                            label="Flow Visualization"
                        )
                    
                    # YAML Editor Tab
                    with gr.Tab("📝 YAML"):
                        yaml_editor = gr.Code(
                            value=EMPTY_CONFIG,
                            language="yaml",
                            lines=25,
                            label="Configuration"
                        )
                        
                        with gr.Row():
                            apply_btn = gr.Button("✅ Apply Edits", variant="primary")
                            validate_btn = gr.Button("🔍 Validate")
                        
                        validation_output = gr.HTML(value="")
        
        # Bottom Actions
        gr.Markdown("---")
        with gr.Row():
            download_btn = gr.Button("⬇️ Download Config")
            upload_btn = gr.UploadButton("📤 Upload Config", file_types=[".yaml", ".yml"])
            execute_btn = gr.Button("▶️ Execute Flow", variant="primary")
        
        download_file = gr.File(visible=False)
        
        # Chat handler implementation
        def chat_handler(message, history, current_config):
            """Handle chat messages and update config."""
            import re
            
            if not message or not message.strip():
                return history, gr.update(), gr.update(), current_config
            
            try:
                # Get current config as YAML
                if current_config is None:
                    current_yaml = EMPTY_CONFIG
                else:
                    current_yaml = yaml.dump(
                        config_service.to_dict(current_config),
                        default_flow_style=False,
                        sort_keys=False
                    )
                
                # Build prompt
                system_prompt = build_system_prompt(current_yaml)
                
                # Call LLM
                llm = get_llm()
                full_prompt = f"{system_prompt}\n\nUser: {message}"
                
                logger.info(f"Sending to LLM: {message}")
                response = llm.invoke(full_prompt)
                assistant_message = response.content
                
                # Extract YAML from response
                yaml_match = re.search(r'```yaml\s*\n(.*?)\n```', assistant_message, re.DOTALL)
                
                if not yaml_match:
                    # LLM didn't provide YAML, just conversational response
                    # FIX: Use proper message format
                    updated_history = history + [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": assistant_message}
                    ]
                    return updated_history, gr.update(), gr.update(), current_config
                
                updated_yaml = yaml_match.group(1).strip()
                
                # Parse and validate
                try:
                    config_dict = yaml.safe_load(updated_yaml)
                    new_config = config_service.load_from_dict(config_dict)
                    
                    # Validate
                    validation = validation_service.validate_config(new_config)
                    
                    if not validation.is_valid:
                        # Config has errors - ask LLM to fix
                        error_summary = "\n".join([f"- {e.message}" for e in validation.errors[:3]])
                        fix_prompt = f"""The configuration has validation errors:

        {error_summary}

        Please fix these errors and provide the corrected FULL configuration."""
                        
                        logger.warning(f"Config validation failed, asking LLM to fix")
                        fix_response = llm.invoke(f"{system_prompt}\n\n{fix_prompt}")
                        
                        # Try extracting fixed YAML
                        fix_yaml_match = re.search(r'```yaml\s*\n(.*?)\n```', fix_response.content, re.DOTALL)
                        if fix_yaml_match:
                            updated_yaml = fix_yaml_match.group(1).strip()
                            config_dict = yaml.safe_load(updated_yaml)
                            new_config = config_service.load_from_dict(config_dict)
                            assistant_message = fix_response.content
                    
                    # Generate diagram
                    mermaid_code = generate_mermaid_diagram(config_dict)
                    diagram_md = f"```mermaid\n{mermaid_code}\n```"
                    
                    # FIX: Update history with proper format
                    updated_history = history + [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": assistant_message}
                    ]
                    
                    logger.info("Config updated successfully via chat")
                    return updated_history, diagram_md, updated_yaml, new_config
                    
                except yaml.YAMLError as e:
                    # YAML parsing failed
                    error_msg = f"⚠️ The generated YAML has syntax errors: {str(e)}\n\nPlease try rephrasing your request."
                    # FIX: Proper format
                    updated_history = history + [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": error_msg}
                    ]
                    return updated_history, gr.update(), gr.update(), current_config
                
            except Exception as e:
                logger.error(f"Chat handler error: {e}", exc_info=True)
                error_msg = f"❌ Error: {str(e)}\n\nPlease try again."
                # FIX: Proper format
                updated_history = history + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": error_msg}
                ]
                return updated_history, gr.update(), gr.update(), current_config
        
        # Apply manual edits handler
        def apply_edits(yaml_text, current_config):
            """Apply manual YAML edits and regenerate diagram."""
            
            if not yaml_text or not yaml_text.strip():
                return "⚠️ No YAML to apply", gr.update(), current_config
            
            try:
                # Parse YAML
                config_dict = yaml.safe_load(yaml_text)
                new_config = config_service.load_from_dict(config_dict)
                
                # Validate
                validation = validation_service.validate_config(new_config)
                
                if not validation.is_valid:
                    # Show errors
                    error_html = f"""
                    <div style="background: #ffebee; border: 1px solid #ef5350; padding: 12px; border-radius: 6px;">
                        ❌ <strong>Validation Failed</strong><br>
                        {len(validation.errors)} error(s) found:<br>
                        <ul style="margin: 8px 0; padding-left: 20px;">
                    """
                    
                    for error in validation.errors[:5]:
                        error_html += f"<li>{error.message}</li>"
                    
                    if len(validation.errors) > 5:
                        error_html += f"<li>...and {len(validation.errors) - 5} more</li>"
                    
                    error_html += "</ul></div>"
                    
                    logger.warning(f"Manual edit validation failed: {len(validation.errors)} errors")
                    return error_html, gr.update(), current_config
                
                # Generate diagram from valid config
                mermaid_code = generate_mermaid_diagram(config_dict)
                diagram_md = f"```mermaid\n{mermaid_code}\n```"
                
                success_html = """
                <div style="background: #e8f5e9; border: 1px solid #66bb6a; padding: 12px; border-radius: 6px;">
                    ✅ <strong>Config Applied Successfully</strong>
                </div>
                """
                
                logger.info("Manual edits applied successfully")
                return success_html, diagram_md, new_config
                
            except yaml.YAMLError as e:
                error_html = f"""
                <div style="background: #ffebee; border: 1px solid #ef5350; padding: 12px; border-radius: 6px;">
                    ❌ <strong>YAML Syntax Error</strong><br>
                    {str(e)}
                </div>
                """
                logger.error(f"YAML parse error: {e}")
                return error_html, gr.update(), current_config
                
            except Exception as e:
                error_html = f"""
                <div style="background: #ffebee; border: 1px solid #ef5350; padding: 12px; border-radius: 6px;">
                    ❌ <strong>Error</strong><br>
                    {str(e)}
                </div>
                """
                logger.error(f"Apply edits error: {e}", exc_info=True)
                return error_html, gr.update(), current_config
        
        # Clear chat handler
        def clear_chat():
            """Clear chat and reset config"""
            return [], "```mermaid\ngraph TD\n    Start([No Config Yet])\n```", EMPTY_CONFIG, None
        
        # Wire up events
        msg_input.submit(
            fn=chat_handler,
            inputs=[msg_input, chatbot, config_state],
            outputs=[chatbot, diagram_view, yaml_editor, config_state]
        ).then(lambda: "", outputs=msg_input)
        
        send_btn.click(
            fn=chat_handler,
            inputs=[msg_input, chatbot, config_state],
            outputs=[chatbot, diagram_view, yaml_editor, config_state]
        ).then(lambda: "", outputs=msg_input)
        
        apply_btn.click(
            fn=apply_edits,
            inputs=[yaml_editor, config_state],
            outputs=[validation_output, diagram_view, config_state]
        )
        
        clear_btn.click(
            fn=clear_chat,
            outputs=[chatbot, diagram_view, yaml_editor, config_state]
        )
    
    return app


def launch_chat_builder(
    server_name: str = "0.0.0.0",
    server_port: int = 7860,
    share: bool = False
):
    """Launch the chat builder app."""
    
    # Setup logging
    settings = get_settings()
    setup_logging(settings.app.log_dir, settings.app.log_level)
    
    logger.info("="*60)
    logger.info("Chat-based Config Builder - Starting")
    logger.info("="*60)
    
    app = create_chat_builder_app()
    
    app.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        prevent_thread_lock=False
    )


if __name__ == "__main__":
    launch_chat_builder()