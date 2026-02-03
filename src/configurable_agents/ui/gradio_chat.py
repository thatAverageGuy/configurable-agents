"""Gradio ChatInterface for workflow config generation.

This module provides a conversational UI for generating valid YAML workflow
configs through natural language interaction. Users describe their desired
workflow and receive validated configs ready to run.

Features:
    - Streaming LLM responses
    - Session persistence across browser refreshes
    - Config validation against WorkflowConfig schema
    - Download generated YAML files
"""

import asyncio
import json
import re
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple

import gradio as gr
import yaml

from configurable_agents.config.schema import WorkflowConfig
from configurable_agents.llm import create_llm, stream_chat
from configurable_agents.storage.base import ChatSessionRepository


# System prompt for config generation
CONFIG_GENERATION_PROMPT = """You are a YAML config generator for Configurable Agents.

Your task is to generate valid workflow configuration YAML based on user descriptions.
The config must follow schema v1.0 format.

Schema v1.0 format:
```yaml
schema_version: "1.0"
flow:
  name: string                    # Unique workflow identifier
  description: optional string    # Human-readable description
  version: optional string        # Semantic version

state:
  fields:
    field_name:
      type: str|int|float|bool|list|dict|object
      required: boolean
      default: optional value
      description: optional string

nodes:
  - id: string                   # Must be valid Python identifier
    description: optional string
    inputs:
      local_var: state_reference  # Map inputs to state fields
    prompt: string                # Prompt template with {placeholders}
    output_schema:
      type: object|str|int|etc
      fields:                     # Required if type=object
        - name: string
          type: string
          description: optional string
    outputs:
      - state_field_to_update
    tools: optional list
    llm:                          # Optional LLM override
      provider: openai|anthropic|google|ollama
      model: string
      temperature: optional float
      max_tokens: optional int

edges:
  - from: START                   # First edge starts from START
    to: first_node_id
  - from: node_id
    to: next_node_id
  - from: last_node_id
    to: END                       # Last edge goes to END

# Optional sections
optimization:                     # DSPy optimization (v0.3+)
  enabled: boolean
  strategy: string
  metric: string
  max_demos: int

config:                          # Infrastructure settings
  llm:
    provider: string
    model: string
  execution:
    timeout: int
    max_retries: int
  observability:
    mlflow:
      enabled: boolean
      tracking_uri: string
    logging:
      level: DEBUG|INFO|WARNING|ERROR
```

Important constraints:
1. schema_version must be exactly "1.0"
2. flow.name must be non-empty
3. state must have at least one field
4. At least one node and one edge are required
5. node.id must be a valid Python identifier (alphanumeric + underscore, no spaces)
6. All edges must form a valid path from START to END
7. Output schema with type="object" must have fields defined

Only return the YAML code block. No explanations outside the YAML.
Ensure the YAML is valid and can be parsed by yaml.safe_load().
"""


class GradioChatUI:
    """Gradio ChatInterface for config generation.

    Provides a conversational UI for generating workflow configs with:
    - Streaming LLM responses
    - Session persistence via ChatSessionRepository
    - Config validation against WorkflowConfig schema
    - Download and validate buttons

    Attributes:
        llm_client: LLM instance for config generation
        session_repo: ChatSessionRepository for persistence
        config_schema: WorkflowConfig class for validation
    """

    def __init__(
        self,
        llm_client: Any,
        session_repo: ChatSessionRepository,
        config_schema: Optional[type] = None,
    ):
        """Initialize the Gradio Chat UI.

        Args:
            llm_client: LLM instance (from create_llm)
            session_repo: ChatSessionRepository for persistence
            config_schema: WorkflowConfig class (defaults to WorkflowConfig)
        """
        self.llm_client = llm_client
        self.session_repo = session_repo
        self.config_schema = config_schema or WorkflowConfig

    def _build_conversation_context(
        self, history: List[Tuple[str, str]]
    ) -> str:
        """Format conversation history into context string.

        Args:
            history: List of (user_message, assistant_message) tuples

        Returns:
            Formatted context string with last 5 messages
        """
        if not history:
            return "This is the start of our conversation."

        context_parts = []
        for i, (user_msg, asst_msg) in enumerate(history[-5:]):
            if user_msg:
                context_parts.append(f"User: {user_msg}")
            if asst_msg:
                # Truncate assistant messages for context efficiency
                truncated = asst_msg[:300] + "..." if len(asst_msg) > 300 else asst_msg
                context_parts.append(f"Assistant: {truncated}")

        return "\n".join(context_parts) if context_parts else "New conversation."

    def _extract_yaml_block(self, text: str) -> Optional[str]:
        """Extract YAML code block from markdown text.

        Args:
            text: Text that may contain a YAML code block

        Returns:
            YAML content if found, None otherwise
        """
        # Try markdown code block format
        patterns = [
            r"```yaml\n(.*?)\n```",  # ```yaml ... ```
            r"```YAML\n(.*?)\n```",  # ```YAML ... ```
            r"```\n(.*?)\n```",      # ``` ... ``` (no language)
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()

        # If no code blocks, try to find YAML-like content
        # (starts with schema_version or flow:)
        yaml_match = re.search(
            r"(schema_version:.*?)(?:\n\n|\Z)", text, re.DOTALL
        )
        if yaml_match:
            return yaml_match.group(1).strip()

        return None

    def _validate_generated_config(self, yaml_content: str) -> Tuple[bool, str]:
        """Validate generated YAML against WorkflowConfig schema.

        Args:
            yaml_content: YAML string to validate

        Returns:
            Tuple of (is_valid, error_message_or_yaml)
        """
        try:
            # Parse YAML
            config_dict = yaml.safe_load(yaml_content)

            if not isinstance(config_dict, dict):
                return False, "Config must be a dictionary/object"

            # Validate against schema
            self.config_schema(**config_dict)
            return True, yaml_content

        except yaml.YAMLError as e:
            return False, f"YAML parsing error: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"

    def _get_or_create_session_id(self, request: gr.Request) -> str:
        """Get or create session ID from request.

        Args:
            request: Gradio Request object

        Returns:
            Session ID string
        """
        # Derive session_id from client info
        if request and request.client:
            client_host = request.client.host
            client_port = getattr(request.client, "port", None)
            base_id = f"{client_host}:{client_port}" if client_port else client_host
        else:
            base_id = "unknown"

        # Try to load existing session
        try:
            sessions = self.session_repo.list_recent_sessions(base_id, limit=1)
            if sessions:
                return sessions[0]["session_id"]
        except Exception:
            pass

        # Create new session
        return self.session_repo.create_session(base_id)

    def generate_config(
        self,
        message: str,
        history: List[Tuple[str, str]],
        request: gr.Request,
    ) -> Generator[str, None, None]:
        """Generate workflow config from user description.

        Args:
            message: User's workflow description
            history: Conversation history
            request: Gradio Request object for session tracking

        Yields:
            Streaming response chunks
        """
        if not message or not message.strip():
            yield "Please describe the workflow you want to create."
            return

        # Get or create session
        try:
            session_id = self._get_or_create_session_id(request)
        except Exception as e:
            yield f"Session error: {e}"
            return

        # Save user message
        try:
            self.session_repo.add_message(session_id, "user", message)
        except Exception:
            pass  # Non-fatal

        # Build conversation context
        context = self._build_conversation_context(history)

        # Prepare full prompt
        full_prompt = f"{context}\n\nUser: {message}"

        # Stream response
        response_text = ""

        # Since stream_chat is async, we need to run it in an event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            async def collect_response():
                chunks = []
                async for chunk in stream_chat(
                    self.llm_client,
                    message,
                    history,
                    system_prompt=CONFIG_GENERATION_PROMPT,
                ):
                    chunks.append(chunk)
                return "".join(chunks)

            response_text = loop.run_until_complete(collect_response())
        except Exception as e:
            yield f"Error generating config: {e}"
            return

        # Yield streaming response (simulate streaming by yielding parts)
        # Since we collected the full response above, we'll yield it in chunks
        chunk_size = 50
        for i in range(0, len(response_text), chunk_size):
            yield response_text[: i + chunk_size]

        # Extract and validate YAML
        yaml_content = self._extract_yaml_block(response_text)

        if yaml_content:
            # Validate config
            is_valid, result = self._validate_generated_config(yaml_content)

            if is_valid:
                # Save config to session
                try:
                    self.session_repo.update_config(session_id, yaml_content)
                    self.session_repo.add_message(
                        session_id,
                        "assistant",
                        response_text,
                        metadata={"has_config": True, "config_valid": True},
                    )
                except Exception:
                    pass

                # Return success message with YAML
                final_message = (
                    f"{response_text}\n\n"
                    f"---\n\n"
                    f"✅ **Config is valid!** You can:\n"
                    f"- Click **Download YAML** to save the file\n"
                    f"- Copy the YAML above and save as `workflow.yaml`\n"
                    f"- Run with: `configurable-agents run workflow.yaml`"
                )
                yield final_message
            else:
                # Validation failed
                error_message = (
                    f"{response_text}\n\n"
                    f"---\n\n"
                    f"❌ **Validation failed:** {result}\n\n"
                    f"Please try again or clarify your requirements."
                )
                yield error_message
        else:
            # No YAML found
            no_yaml_message = (
                f"{response_text}\n\n"
                f"---\n\n"
                f"⚠️ No YAML config found in response. "
                f"Please ask specifically for a YAML configuration."
            )
            yield no_yaml_message

    def download_config(self, history: List[Tuple[str, str]]) -> Optional[str]:
        """Extract and download the last generated config.

        Args:
            history: Conversation history

        Returns:
            Path to temporary YAML file, or None if no config found
        """
        if not history:
            return None

        # Get last assistant message
        last_message = history[-1][1] if history[-1][1] else None
        if not last_message and len(history) > 1:
            last_message = history[-2][1]

        if not last_message:
            return None

        # Extract YAML
        yaml_content = self._extract_yaml_block(last_message)
        if not yaml_content:
            return None

        # Write to temp file
        try:
            fd, path = tempfile.mkstemp(suffix=".yaml", prefix="workflow_")
            with open(path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
            return path
        except Exception:
            return None

    def validate_config(self, history: List[Tuple[str, str]]) -> str:
        """Validate the last generated config.

        Args:
            history: Conversation history

        Returns:
            Validation status message
        """
        if not history:
            return "No conversation to validate."

        # Get last assistant message
        last_message = history[-1][1] if history[-1][1] else None
        if not last_message and len(history) > 1:
            last_message = history[-2][1]

        if not last_message:
            return "No config found to validate."

        # Extract YAML
        yaml_content = self._extract_yaml_block(last_message)
        if not yaml_content:
            return "No YAML found in last message."

        # Validate
        is_valid, result = self._validate_generated_config(yaml_content)

        if is_valid:
            return "✅ Config is valid! Ready to run."
        else:
            return f"❌ Validation failed: {result}"

    def create_interface(self) -> gr.Blocks:
        """Create and return the Gradio ChatInterface.

        Returns:
            Configured Gradio Blocks interface
        """
        # Custom CSS for clean UI (no emoji in raw output, but we use them in markdown)
        custom_css = """
        .gradio-container {
            max-width: 900px !important;
        }
        .chatbot {
            min-height: 400px;
        }
        .message.user {
            background-color: #f0f0f0;
        }
        .message.assistant {
            background-color: #e3f2fd;
        }
        """

        with gr.Blocks(
            title="Configurable Agents - Config Generator",
        ) as interface:
            gr.Markdown(
                "# Configurable Agents - Config Generator\n\n"
                "Describe your workflow in plain English. "
                "Get valid, runnable YAML configuration."
            )

            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.ChatInterface(
                        fn=self.generate_config,
                        additional_inputs=[],
                        examples=[
                            "Research a topic and write a 500-word article with sources",
                            "Analyze sentiment of customer reviews and categorize them",
                            "Summarize a long document into bullet points",
                            "Create a workflow that fetches data from an API and processes it",
                        ],
                        cache_examples=False,
                    )

                with gr.Column(scale=1):
                    gr.Markdown("### Actions")
                    download_btn = gr.Button("Download YAML", variant="primary")
                    validate_btn = gr.Button("Validate Config")
                    status_output = gr.Textbox(
                        label="Status",
                        interactive=False,
                        lines=3,
                    )

            # Wire up buttons
            download_btn.click(
                fn=lambda h: self.download_config(h),
                inputs=[chatbot.chatbot],
                outputs=gr.File(),
            )

            validate_btn.click(
                fn=lambda h: self.validate_config(h),
                inputs=[chatbot.chatbot],
                outputs=status_output,
            )

            # Session info
            gr.Markdown(
                "---\n\n"
                "**Note:** Your conversation is saved automatically. "
                "Close and reopen this page to continue where you left off."
            )

        return interface

    def launch(
        self,
        server_name: str = "0.0.0.0",
        server_port: int = 7860,
        share: bool = False,
        **kwargs,
    ) -> None:
        """Launch the Gradio server.

        Args:
            server_name: Host to bind to (default: 0.0.0.0)
            server_port: Port to listen on (default: 7860)
            share: Whether to create a public link (default: False)
            **kwargs: Additional arguments passed to gr.Blocks.launch()
        """
        # Custom CSS for clean UI
        custom_css = """
        .gradio-container {
            max-width: 900px !important;
        }
        .chatbot {
            min-height: 400px;
        }
        .message.user {
            background-color: #f0f0f0;
        }
        .message.assistant {
            background-color: #e3f2fd;
        }
        """

        interface = self.create_interface()
        interface.launch(
            server_name=server_name,
            server_port=server_port,
            share=share,
            theme=gr.themes.Soft(),
            css=custom_css,
            **kwargs,
        )


def create_gradio_chat_ui(
    llm_config: Optional[Any] = None,
    global_config: Optional[Any] = None,
    session_repo: Optional[ChatSessionRepository] = None,
) -> GradioChatUI:
    """Factory function to create GradioChatUI.

    Args:
        llm_config: LLMConfig for the chat LLM
        global_config: Global config with LLM settings
        session_repo: ChatSessionRepository (creates new if None)

    Returns:
        Configured GradioChatUI instance

    Example:
        >>> from configurable_agents.ui import create_gradio_chat_ui
        >>> ui = create_gradio_chat_ui()
        >>> ui.launch()
    """
    # Create LLM client
    llm_client = create_llm(llm_config, global_config)

    # Create session repository if not provided
    if session_repo is None:
        from configurable_agents.storage import create_storage_backend
        _, _, _, session_repo, _ = create_storage_backend()

    return GradioChatUI(llm_client, session_repo)


if __name__ == "__main__":
    # Launch the UI when run directly
    import sys

    print("Starting Configurable Agents Chat UI...")
    print("Note: Make sure GOOGLE_API_KEY or appropriate LLM env vars are set.")

    ui = create_gradio_chat_ui()
    ui.launch()
