"""Gradio Chat UI for workflow config generation.

Full redesign (T-017):
- Real token-by-token streaming
- Session history sidebar
- Config preview panel (Download / Validate / Run Ephemeral / Deploy)
- LLM provider/model switcher with API key input
- Run dialog: auto-detected ENV vars + workflow inputs
- Deploy dialog: Docker container with fallback to manual instructions
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import gradio as gr
import yaml

from configurable_agents.config.schema import WorkflowConfig
from configurable_agents.llm import create_llm, stream_chat
from configurable_agents.storage.base import ChatSessionRepository

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model catalogue (provider → {env_var, models, default})
# ---------------------------------------------------------------------------
PROVIDER_CATALOGUE: Dict[str, Dict[str, Any]] = {
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "models": ["gpt-5.4", "gpt-5.4-mini", "o3", "o3-pro", "o4-mini"],
        "default": "gpt-5.4",
    },
    "anthropic": {
        "env_var": "ANTHROPIC_API_KEY",
        "models": [
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
        ],
        "default": "claude-sonnet-4-6",
    },
    "google": {
        "env_var": "GOOGLE_API_KEY",
        "models": [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-3.1-pro-preview",
            "gemini-3.1-flash-preview",
        ],
        "default": "gemini-2.5-pro",
    },
    "ollama": {
        "env_var": None,  # No API key required
        "models": [
            "llama3.3:70b",
            "qwen3:32b",
            "deepseek-r1:32b",
            "mistral:latest",
            "phi3:latest",
        ],
        "default": "llama3.3:70b",
    },
}

# Tool → required ENV vars
TOOL_ENV_VARS: Dict[str, List[str]] = {
    "web_search": ["SERPER_API_KEY (default) or TAVILY_API_KEY (set WEB_SEARCH_PROVIDER=tavily)"],
    "serper_search": ["SERPER_API_KEY"],
    "web_scrape": [],
    "http_client": [],
    "file_read": [],
    "file_write": [],
    "file_glob": [],
    "file_move": [],
    "sql_query": [],
    "json_parse": [],
    "yaml_parse": [],
    "shell": [],
    "process": [],
    "env_vars": [],
}

# ---------------------------------------------------------------------------
# System prompt — comprehensive, accurate for current schema
# ---------------------------------------------------------------------------
CONFIG_GENERATION_PROMPT = """You are an expert YAML config generator for Configurable Agents v1.2.

Your job: generate valid, runnable workflow YAML configs from user descriptions, explain what is and isn't possible, and help users iterate.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FULL SCHEMA REFERENCE (schema_version: "1.0")
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```yaml
schema_version: "1.0"   # REQUIRED, exactly this value

flow:
  name: my_workflow       # REQUIRED — unique, valid Python identifier
  description: "..."      # optional
  version: "1.0.0"        # optional

state:
  fields:
    field_name:
      type: str | int | float | bool | list | dict | object  # REQUIRED
      required: true | false      # REQUIRED
      default: <value>            # optional — if required=false, provide a default
      description: "..."          # optional
      reducer: append | replace   # optional, list fields only
                                  # append (default): new items appended — use for parallel fan-in
                                  # replace: list replaced entirely — use for retry/loop buffers

nodes:
  - id: node_id           # REQUIRED — valid Python identifier (letters, digits, underscores only)
    description: "..."    # optional
    inputs:               # optional — map local names to state fields
      local_name: state_field_name
    prompt: |             # REQUIRED — Jinja2 template, use {local_name} for inputs
      Do something with {local_name}.
    output_schema:        # REQUIRED
      type: object        # or str, int, float, bool, list
      fields:             # REQUIRED when type=object
        - name: field_name
          type: str       # str, int, float, bool, list, dict
          description: "..."
    outputs:              # REQUIRED — state fields to update from output_schema fields
      - state_field_name  # maps output_schema field of same name → state field
    tools:                # optional — list tool names as strings
      - web_search
      - file_read
    llm:                  # optional — override global LLM for this node
      provider: openai | anthropic | google | ollama
      model: model-name
      temperature: 0.7    # optional, 0.0–2.0
      max_tokens: 2048    # optional
    memory:               # optional — persistent memory for this node
      enabled: true
      default_scope: agent | workflow | node
      extract_facts: false   # true = extra LLM call to extract facts (costs more)
      extraction_model: gpt-5.4-mini  # optional — cheaper model for extraction

edges:
  - from: START           # REQUIRED — first edge from START
    to: first_node_id
  - from: node_id
    to: next_node_id
  - from: last_node_id
    to: END               # REQUIRED — last edge to END

  # Conditional routing:
  - from: decision_node
    to: path_a_node
    condition:
      field: state_field_name   # state field to evaluate
      operator: eq | ne | gt | lt | gte | lte | contains | not_contains | in | not_in | is_none | is_not_none
      value: expected_value
    routes:
      - condition:
          field: field_name
          operator: eq
          value: "yes"
        to: node_a
      - condition:
          field: field_name
          operator: eq
          value: "no"
        to: node_b
      - to: default_node    # default route — no condition, always last

  # Loop edges (retry / iteration):
  - from: process_node
    to: check_node
  - from: check_node       # Loop back OR exit
    loop:
      condition_field: keep_going     # state bool: true = loop, false = exit
      max_iterations: 5               # safety limit
      back_to: process_node           # which node to loop back to
    to: final_node                    # where to go when loop exits

  # Parallel (fork-join):
  - from: START
    to: [branch_a, branch_b, branch_c]   # fan-out: list means parallel
  - from: branch_a
    to: join_node
  - from: branch_b
    to: join_node
  - from: branch_c
    to: join_node                         # fan-in: multiple edges to same node

config:                   # optional — global defaults
  llm:
    provider: openai | anthropic | google | ollama
    model: model-name
    temperature: 0.7
    max_tokens: 4096
  execution:
    timeout: 300          # seconds
    max_retries: 3
  observability:
    mlflow:
      enabled: true
      tracking_uri: sqlite:///mlflow.db
    logging:
      level: INFO         # DEBUG | INFO | WARNING | ERROR
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AVAILABLE TOOLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Web:    web_search, web_scrape, http_client
File:   file_read, file_write, file_glob, file_move
Data:   sql_query, json_parse, yaml_parse, dataframe_to_csv
System: shell, process, env_vars

Tool ENV vars:
- web_search → SERPER_API_KEY (default) or TAVILY_API_KEY (set WEB_SEARCH_PROVIDER=tavily)
- All others → no API key needed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LLM PROVIDERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- openai    → OPENAI_API_KEY  (models: gpt-5.4, gpt-5.4-mini, o3, o4-mini)
- anthropic → ANTHROPIC_API_KEY (models: claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5-20251001)
- google    → GOOGLE_API_KEY  (models: gemini-2.5-pro, gemini-2.5-flash, gemini-3.1-pro-preview)
- ollama    → no key needed   (models: llama3.3:70b, qwen3:32b, deepseek-r1:32b, mistral:latest)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HARD CONSTRAINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. schema_version must be exactly "1.0"
2. flow.name must be non-empty
3. state must have at least one field
4. At least one node and edges from START to END required
5. node.id must be a valid Python identifier (no spaces, no hyphens)
6. All edge from/to values must reference real node IDs, START, or END
7. output_schema with type=object must define fields
8. outputs list must map to valid state field names
9. reducer=replace only valid on list-type state fields
10. Loop edges require condition_field to be a bool state field
11. Parallel fan-out requires all branches to eventually fan-in to the same node
12. Memory scope: 'agent' persists across runs, 'workflow' for this run only, 'node' isolated
13. extract_facts: false by default — set to true only if you explicitly need fact extraction (doubles LLM cost)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT IS NOT SUPPORTED (do not generate these)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- optimization: section (DSPy/prompt optimization was removed)
- Per-node tool config via YAML (YAML tool config is ignored at runtime)
- A/B testing
- Agent marketplace or cloud hosting
- React/JavaScript frontend components
- Dynamic tool discovery at runtime

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMON PATTERNS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sequential pipeline (A → B → C):
  edges: START→A, A→B, B→C, C→END

Conditional branch (route on output):
  Use routes: with condition on a state field set by the routing node.
  Always include a default route (no condition) as the last route entry.

Retry loop (keep trying until success or max N):
  - Set a bool state field (e.g., success: bool, required: false, default: false)
  - Use loop edge with condition_field: success, max_iterations: 5
  - Set success=true in node output when done
  - Use reducer: replace on list fields that accumulate per-iteration results

Parallel research (fan-out/fan-in):
  - fan-out: one edge from: START, to: [node_a, node_b, node_c]
  - Each parallel node outputs to a shared list state field with reducer: append
  - fan-in: all parallel nodes point to: aggregator_node
  - aggregator_node combines the parallel results

Memory-enabled agent:
  - Set memory.enabled: true on the node
  - Use default_scope: agent for cross-run persistence
  - Keep extract_facts: false unless explicitly requested

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When generating a config:
1. Brief description of what the workflow does (1-2 sentences)
2. The complete YAML config in a ```yaml ... ``` code block
3. Required ENV vars (bullet list)
4. Any important notes or limitations

When a request is impossible or unclear:
- Explain WHY it cannot be done with the current system
- Suggest the closest possible alternative
- Ask clarifying questions if needed

Do NOT generate partial configs or configs with placeholder nodes.
Every generated config must be complete and runnable.
"""


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _extract_yaml_block(text: str) -> Optional[str]:
    """Extract first YAML code block from markdown text."""
    for pattern in [
        r"```yaml\n(.*?)\n```",
        r"```YAML\n(.*?)\n```",
        r"```\n(.*?)\n```",
    ]:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
    # Bare YAML starting with schema_version
    match = re.search(r"(schema_version:.*?)(?:\n\n|\Z)", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _validate_config(yaml_content: str) -> Tuple[bool, str]:
    """Validate YAML against WorkflowConfig schema. Returns (valid, message)."""
    try:
        config_dict = yaml.safe_load(yaml_content)
        if not isinstance(config_dict, dict):
            return False, "Config must be a YAML mapping"
        WorkflowConfig(**config_dict)
        return True, "✅ Config is valid"
    except yaml.YAMLError as e:
        return False, f"❌ YAML parse error: {e}"
    except Exception as e:
        return False, f"❌ Validation error: {e}"


def _detect_env_vars(config_dict: dict) -> List[str]:
    """Return list of ENV var names required by the config."""
    env_vars: list[str] = []

    # Collect all providers used
    providers = set()
    global_llm = config_dict.get("config", {}).get("llm", {})
    if global_llm.get("provider"):
        providers.add(global_llm["provider"])
    for node in config_dict.get("nodes", []):
        node_llm = node.get("llm", {}) or {}
        if node_llm.get("provider"):
            providers.add(node_llm["provider"])

    for provider in sorted(providers):
        info = PROVIDER_CATALOGUE.get(provider, {})
        if info.get("env_var"):
            env_vars.append(info["env_var"])

    # Collect tools
    for node in config_dict.get("nodes", []):
        for tool in node.get("tools", []) or []:
            tool_name = tool if isinstance(tool, str) else (tool.get("name", "") if isinstance(tool, dict) else "")
            for tv in TOOL_ENV_VARS.get(tool_name, []):
                if tv and tv not in env_vars:
                    env_vars.append(tv)

    return env_vars


def _detect_workflow_inputs(config_dict: dict) -> Dict[str, Any]:
    """Return template dict of required workflow inputs (no default, required=true)."""
    inputs = {}
    for field_name, field_cfg in (config_dict.get("state", {}).get("fields", {}) or {}).items():
        if isinstance(field_cfg, dict):
            is_required = field_cfg.get("required", False)
            has_default = "default" in field_cfg
            if is_required and not has_default:
                ftype = field_cfg.get("type", "str")
                # Provide a sensible placeholder by type
                placeholders = {
                    "str": "",
                    "int": 0,
                    "float": 0.0,
                    "bool": False,
                    "list": [],
                    "dict": {},
                    "object": {},
                }
                inputs[field_name] = placeholders.get(ftype, "")
    return inputs


def _build_env_prefill(env_vars: List[str]) -> str:
    """Build KEY= prefill string for the ENV textarea."""
    lines = []
    for var in env_vars:
        # Handle compound entries like "SERPER_API_KEY or TAVILY_API_KEY (set ...)"
        # Extract just the primary key name
        key = var.split("(")[0].split(" or ")[0].strip()
        existing = os.environ.get(key, "")
        lines.append(f"{key}={existing}")
    return "\n".join(lines)


def _parse_env_textarea(text: str) -> Dict[str, str]:
    """Parse KEY=value lines into a dict, skipping blank/comment lines."""
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            result[key.strip()] = val.strip()
    return result


def _create_llm_for_provider(provider: str, model: str, api_key: str):
    """Create an LLM client for the given provider/model, temporarily setting API key."""
    from configurable_agents.config import LLMConfig

    # Temporarily set API key in environment if provided
    env_var = PROVIDER_CATALOGUE.get(provider, {}).get("env_var")
    original = None
    if env_var and api_key:
        original = os.environ.get(env_var)
        os.environ[env_var] = api_key

    try:
        cfg = LLMConfig(provider=provider, model=model)
        client = create_llm(cfg)
    finally:
        # Restore original value
        if env_var:
            if original is None:
                os.environ.pop(env_var, None)
            else:
                os.environ[env_var] = original

    return client


# ---------------------------------------------------------------------------
# Main UI class
# ---------------------------------------------------------------------------

class GradioChatUI:
    """Gradio-based Chat UI for workflow config generation."""

    def __init__(
        self,
        default_llm_client: Any,
        session_repo: ChatSessionRepository,
        dashboard_url: str = "http://localhost:7861",
    ):
        self.default_llm = default_llm_client
        self.session_repo = session_repo
        self.dashboard_url = dashboard_url

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------

    def _new_session_id(self) -> str:
        try:
            return self.session_repo.create_session("local")
        except Exception:
            return str(uuid.uuid4())

    def _list_sessions(self) -> List[Tuple[str, str]]:
        """Return list of (label, session_id) for the sidebar."""
        try:
            sessions = self.session_repo.list_recent_sessions("local", limit=20)
            result = []
            for s in sessions:
                sid = s.get("session_id", "")
                created = s.get("created_at", "")
                if isinstance(created, datetime):
                    label = created.strftime("%Y-%m-%d %H:%M")
                elif isinstance(created, str):
                    label = created[:16]
                else:
                    label = sid[:8]
                result.append((label, sid))
            return result
        except Exception:
            return []

    def _load_session_history(self, session_id: str) -> List[List[str]]:
        """Load chat history for a session as [[user, assistant], ...]."""
        try:
            messages = self.session_repo.get_messages(session_id)
            history = []
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    history.append([content, None])
                elif role == "assistant" and history:
                    history[-1][1] = content
            return history
        except Exception:
            return []

    def _load_session_config(self, session_id: str) -> str:
        """Load last saved config YAML for a session."""
        try:
            session = self.session_repo.get_session(session_id)
            if session is None:
                return ""
            return session.get("generated_config", "") or ""
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Core respond handler (real streaming)
    # ------------------------------------------------------------------

    async def respond(
        self,
        message: str,
        history: List[List[str]],
        session_id: str,
        llm_client_state: Dict[str, Any],
    ) -> AsyncGenerator:
        """Stream LLM response, update chatbot and config preview."""
        if not message or not message.strip():
            yield history, "", gr.update(), gr.update()
            return

        # Resolve LLM client
        llm = llm_client_state.get("client") or self.default_llm

        # Save user message, add to history
        try:
            self.session_repo.add_message(session_id, "user", message)
        except Exception:
            pass

        history = history + [[message, None]]

        # First yield: clear input, show user bubble
        yield history, "", gr.update(), gr.update()

        # Stream response token by token
        response = ""
        try:
            async for chunk in stream_chat(
                llm,
                message,
                history[:-1],   # exclude the pending pair
                system_prompt=CONFIG_GENERATION_PROMPT,
            ):
                response += chunk
                history[-1][1] = response
                yield history, gr.update(), gr.update(), gr.update()
        except Exception as e:
            response = f"⚠️ LLM error: {e}"
            history[-1][1] = response
            yield history, gr.update(), gr.update(), gr.update()
            return

        # Save assistant message
        try:
            self.session_repo.add_message(session_id, "assistant", response)
        except Exception:
            pass

        # Extract YAML and update config preview
        yaml_content = _extract_yaml_block(response)
        if yaml_content:
            valid, status_msg = _validate_config(yaml_content)
            try:
                self.session_repo.update_config(session_id, yaml_content)
            except Exception:
                pass
            yield history, gr.update(), yaml_content, status_msg
        else:
            yield history, gr.update(), gr.update(), gr.update()

    # ------------------------------------------------------------------
    # UI event handlers
    # ------------------------------------------------------------------

    def download_config(self, config_yaml: str) -> Optional[str]:
        """Write config YAML to a temp file and return the path."""
        if not config_yaml or not config_yaml.strip():
            return None
        try:
            fd, path = tempfile.mkstemp(suffix=".yaml", prefix="workflow_")
            with os.fdopen(fd, "w") as f:
                f.write(config_yaml)
            return path
        except Exception:
            return None

    def validate_config_handler(self, config_yaml: str) -> str:
        if not config_yaml or not config_yaml.strip():
            return "⚠️ No config to validate"
        _, msg = _validate_config(config_yaml)
        return msg

    def on_provider_change(self, provider: str):
        """Update model dropdown choices and API key visibility."""
        info = PROVIDER_CATALOGUE.get(provider, {})
        models = info.get("models", [])
        default_model = info.get("default", models[0] if models else "")
        needs_key = info.get("env_var") is not None
        existing_key = os.environ.get(info.get("env_var", ""), "") if needs_key else ""
        return (
            gr.update(choices=models, value=default_model),
            gr.update(visible=needs_key, value=existing_key),
        )

    def apply_llm_config(
        self, provider: str, api_key: str, model: str, llm_state: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], str]:
        """Create a new LLM client with the chosen provider/model/key."""
        try:
            client = _create_llm_for_provider(provider, model, api_key)
            # Persist the key in env for this session
            env_var = PROVIDER_CATALOGUE.get(provider, {}).get("env_var")
            if env_var and api_key:
                os.environ[env_var] = api_key
            llm_state = {"client": client, "provider": provider, "model": model}
            return llm_state, f"✅ Using **{provider} / {model}**"
        except Exception as e:
            return llm_state, f"❌ Failed to load model: {e}"

    def open_run_dialog(self, config_yaml: str):
        """Show Run dialog pre-populated with detected inputs and ENV vars."""
        if not config_yaml or not config_yaml.strip():
            return (
                gr.update(visible=False),
                "",
                "⚠️ Generate a config first",
                "",
            )
        try:
            config_dict = yaml.safe_load(config_yaml)
        except Exception:
            return gr.update(visible=False), "", "❌ Invalid YAML", ""

        # Workflow inputs template
        wf_inputs = _detect_workflow_inputs(config_dict)
        inputs_json = json.dumps(wf_inputs, indent=2) if wf_inputs else "{}"

        # ENV vars
        env_vars = _detect_env_vars(config_dict)
        env_note = (
            "**Detected required ENV vars:**\n" + "\n".join(f"- `{v}`" for v in env_vars)
            if env_vars
            else "_No external ENV vars detected_"
        )
        env_prefill = _build_env_prefill(env_vars)

        return gr.update(visible=True), inputs_json, env_note, env_prefill

    def open_deploy_dialog(self, config_yaml: str, flow_name: str):
        """Show Deploy dialog pre-populated with ENV vars and container name."""
        if not config_yaml or not config_yaml.strip():
            return gr.update(visible=False), "", "⚠️ Generate a config first", "", ""

        try:
            config_dict = yaml.safe_load(config_yaml)
        except Exception:
            return gr.update(visible=False), "", "❌ Invalid YAML", "", ""

        env_vars = _detect_env_vars(config_dict)
        env_note = (
            "**Detected required ENV vars:**\n" + "\n".join(f"- `{v}`" for v in env_vars)
            if env_vars
            else "_No external ENV vars detected_"
        )
        env_prefill = _build_env_prefill(env_vars)

        container_name = (
            config_dict.get("flow", {}).get("name", "my-workflow")
            .replace("_", "-")
            .lower()
        )

        return gr.update(visible=True), container_name, env_note, env_prefill, ""

    async def run_ephemeral(
        self,
        config_yaml: str,
        inputs_json: str,
        env_values: str,
    ) -> AsyncGenerator:
        """Execute workflow in-process and stream status updates."""
        yield "⏳ Preparing..."

        if not config_yaml or not config_yaml.strip():
            yield "❌ No config available"
            return

        # Parse inputs
        try:
            wf_inputs = json.loads(inputs_json) if inputs_json.strip() else {}
        except json.JSONDecodeError as e:
            yield f"❌ Invalid JSON in inputs: {e}"
            return

        # Parse env vars
        env_overrides = _parse_env_textarea(env_values)

        # Write config to temp file
        try:
            fd, temp_path = tempfile.mkstemp(suffix=".yaml", prefix="run_")
            with os.fdopen(fd, "w") as f:
                f.write(config_yaml)
        except Exception as e:
            yield f"❌ Failed to write config: {e}"
            return

        # Apply env overrides
        originals: Dict[str, Optional[str]] = {}
        for k, v in env_overrides.items():
            originals[k] = os.environ.get(k)
            os.environ[k] = v

        yield "⏳ Running workflow (this may take a while)..."

        try:
            from configurable_agents.runtime import run_workflow

            result = await asyncio.to_thread(run_workflow, temp_path, wf_inputs)
            output = json.dumps(result, indent=2, default=str)
            yield f"✅ Workflow completed!\n\n```json\n{output}\n```"
        except Exception as e:
            yield f"❌ Workflow failed:\n\n```\n{e}\n```"
        finally:
            # Restore env
            for k, orig in originals.items():
                if orig is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = orig
            # Cleanup temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    async def deploy_workflow(
        self,
        config_yaml: str,
        container_name: str,
        api_port: int,
        env_values: str,
    ) -> AsyncGenerator:
        """Generate artifacts, build Docker image, and run container."""
        yield "⏳ Generating deployment artifacts..."

        if not config_yaml or not config_yaml.strip():
            yield "❌ No config available"
            return

        # Write config to temp file
        try:
            fd, temp_path = tempfile.mkstemp(suffix=".yaml", prefix="deploy_")
            with os.fdopen(fd, "w") as f:
                f.write(config_yaml)
        except Exception as e:
            yield f"❌ Failed to write config: {e}"
            return

        output_dir = Path(tempfile.mkdtemp(prefix="deploy_artifacts_"))
        env_overrides = _parse_env_textarea(env_values)

        try:
            from configurable_agents.deploy import generate_deployment_artifacts

            artifacts = generate_deployment_artifacts(
                config_path=temp_path,
                output_dir=output_dir,
                api_port=int(api_port),
                container_name=container_name or None,
            )
            yield f"✅ Artifacts generated at:\n`{output_dir}`\n\nFiles: {', '.join(p.name for p in artifacts.values())}\n\n⏳ Building Docker image..."
        except Exception as e:
            yield f"❌ Artifact generation failed:\n```\n{e}\n```"
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            return

        # Build env-file content for docker run
        env_file_path = output_dir / ".env.run"
        try:
            with open(env_file_path, "w") as f:
                for k, v in env_overrides.items():
                    f.write(f"{k}={v}\n")
        except Exception:
            pass

        # Check Docker is available
        try:
            subprocess.run(
                ["docker", "info"],
                check=True,
                capture_output=True,
                timeout=5,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            yield (
                f"⚠️ **Docker is not available** — artifacts are ready but couldn't auto-deploy.\n\n"
                f"**Error**: `{e}`\n\n"
                f"**Artifacts at**: `{output_dir}`\n\n"
                f"**To deploy manually**:\n"
                f"```bash\ncd {output_dir}\ndocker compose up --build -d\n```\n\n"
                f"Or without Docker Compose:\n"
                f"```bash\ncd {output_dir}\ndocker build -t {container_name or 'workflow'} .\n"
                f"docker run -p {int(api_port)}:{int(api_port)} "
                f"--env-file .env.run {container_name or 'workflow'}\n```"
            )
            return

        # Build and run
        img_name = (container_name or "workflow").lower().replace("_", "-")
        yield f"⏳ Building image `{img_name}`..."
        try:
            build_result = subprocess.run(
                ["docker", "build", "-t", img_name, "."],
                cwd=str(output_dir),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if build_result.returncode != 0:
                raise RuntimeError(build_result.stderr[-2000:])
        except Exception as e:
            yield (
                f"❌ **Docker build failed**.\n\n```\n{e}\n```\n\n"
                f"**Artifacts at**: `{output_dir}`\n"
                f"**Manual build**: `cd {output_dir} && docker build -t {img_name} .`"
            )
            return

        yield f"✅ Image built. Starting container `{img_name}`..."

        try:
            run_cmd = [
                "docker", "run", "-d",
                "--name", img_name,
                "-p", f"{int(api_port)}:{int(api_port)}",
                "--env-file", str(env_file_path),
                img_name,
            ]
            run_result = subprocess.run(
                run_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if run_result.returncode != 0:
                raise RuntimeError(run_result.stderr[-1000:])
            container_id = run_result.stdout.strip()[:12]
            yield (
                f"🚀 **Container running!**\n\n"
                f"- Container ID: `{container_id}`\n"
                f"- API: `http://localhost:{int(api_port)}`\n"
                f"- Docs: `http://localhost:{int(api_port)}/docs`\n"
                f"- Health: `http://localhost:{int(api_port)}/health`\n\n"
                f"```bash\ndocker logs {img_name}  # view logs\n"
                f"docker stop {img_name}  # stop\n```"
            )
        except Exception as e:
            yield (
                f"❌ **Container start failed**.\n\n```\n{e}\n```\n\n"
                f"**Manual start**: `docker run -p {int(api_port)}:{int(api_port)} "
                f"--env-file {env_file_path} {img_name}`"
            )
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Interface construction
    # ------------------------------------------------------------------

    def create_interface(self) -> gr.Blocks:
        # Initial model list for default provider (google)
        initial_provider = "google"
        initial_models = PROVIDER_CATALOGUE[initial_provider]["models"]
        initial_model = PROVIDER_CATALOGUE[initial_provider]["default"]
        all_providers = list(PROVIDER_CATALOGUE.keys())

        with gr.Blocks(
            title="Configurable Agents — Config Generator",
            theme=gr.themes.Soft(),
            css="""
            .panel-header { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; }
            .session-label { font-size: 0.75rem; color: #6b7280; }
            .config-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
            #run-dialog, #deploy-dialog { border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; background: #f9fafb; }
            .status-ok { color: #059669; }
            .status-err { color: #dc2626; }
            """,
        ) as interface:

            # ── Hidden state ────────────────────────────────────────────
            session_id_state = gr.State(self._new_session_id())
            llm_client_state = gr.State({"client": None})

            # ── Header ──────────────────────────────────────────────────
            with gr.Row(equal_height=True):
                gr.Markdown("# ⚙ Configurable Agents — Config Generator")
                dashboard_btn = gr.Button(
                    "Open Dashboard ↗",
                    variant="secondary",
                    size="sm",
                    link=self.dashboard_url,
                )

            # ── LLM Config bar ──────────────────────────────────────────
            with gr.Row():
                provider_dd = gr.Dropdown(
                    choices=all_providers,
                    value=initial_provider,
                    label="Provider",
                    scale=1,
                )
                api_key_in = gr.Textbox(
                    value=os.environ.get("GOOGLE_API_KEY", ""),
                    type="password",
                    label="API Key",
                    placeholder="Paste API key…",
                    scale=2,
                    visible=True,
                )
                model_dd = gr.Dropdown(
                    choices=initial_models,
                    value=initial_model,
                    label="Model",
                    scale=2,
                )
                apply_btn = gr.Button("Apply", variant="primary", scale=1)
                llm_status = gr.Markdown("_Using default LLM_", scale=2)

            # ── Main 3-column layout ────────────────────────────────────
            with gr.Row():

                # ── LEFT: Session History ────────────────────────────────
                with gr.Column(scale=1, min_width=180):
                    gr.Markdown("### Sessions", elem_classes=["panel-header"])
                    new_chat_btn = gr.Button("＋ New Chat", variant="primary", size="sm")
                    session_dd = gr.Dropdown(
                        choices=[],
                        value=None,
                        label="Recent sessions",
                        allow_custom_value=False,
                        interactive=True,
                    )

                # ── MIDDLE: Chat ─────────────────────────────────────────
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(
                        label="Conversation",
                        height=480,
                        show_label=False,
                        bubble_full_width=False,
                    )
                    msg_input = gr.Textbox(
                        placeholder="Describe your workflow… (Shift+Enter for newline)",
                        lines=2,
                        max_lines=6,
                        show_label=False,
                        submit_btn=False,
                    )
                    with gr.Row():
                        send_btn = gr.Button("Send ▶", variant="primary")
                        clear_btn = gr.Button("Clear", variant="secondary")

                # ── RIGHT: Config Preview ────────────────────────────────
                with gr.Column(scale=2, min_width=280):
                    gr.Markdown("### Config Preview", elem_classes=["panel-header"])
                    config_preview = gr.Code(
                        language="yaml",
                        lines=16,
                        label="Generated YAML",
                        interactive=True,
                    )
                    validate_status = gr.Markdown("_Generate a config to see validation status_")

                    with gr.Row(elem_classes=["config-actions"]):
                        validate_btn = gr.Button("Validate", size="sm")
                        download_btn = gr.Button("Download YAML", size="sm")
                    file_output = gr.File(visible=False, label="YAML file")

                    run_btn = gr.Button("▶ Run Ephemeral", variant="secondary")
                    deploy_btn = gr.Button("🚀 Deploy", variant="secondary")

                    # ── Run dialog ───────────────────────────────────────
                    with gr.Group(visible=False, elem_id="run-dialog") as run_group:
                        gr.Markdown("**▶ Run Ephemeral**")
                        gr.Markdown("_Workflow inputs (required fields with no default):_")
                        run_inputs_box = gr.Code(
                            language="json",
                            label="Inputs (JSON)",
                            lines=4,
                            value="{}",
                        )
                        run_env_note = gr.Markdown("")
                        run_env_box = gr.Textbox(
                            label="ENV Values (KEY=value, one per line)",
                            lines=4,
                            placeholder="OPENAI_API_KEY=sk-...",
                        )
                        with gr.Row():
                            run_execute_btn = gr.Button("▶ Execute", variant="primary", size="sm")
                            run_cancel_btn = gr.Button("Cancel", size="sm")
                        run_output = gr.Markdown("")

                    # ── Deploy dialog ────────────────────────────────────
                    with gr.Group(visible=False, elem_id="deploy-dialog") as deploy_group:
                        gr.Markdown("**🚀 Deploy to Docker**")
                        with gr.Row():
                            deploy_name_box = gr.Textbox(
                                label="Container name",
                                placeholder="my-workflow",
                                scale=2,
                            )
                            deploy_port_box = gr.Number(
                                label="API port",
                                value=8000,
                                precision=0,
                                scale=1,
                            )
                        deploy_env_note = gr.Markdown("")
                        deploy_env_box = gr.Textbox(
                            label="ENV Values (KEY=value, one per line)",
                            lines=4,
                            placeholder="OPENAI_API_KEY=sk-...",
                        )
                        with gr.Row():
                            deploy_execute_btn = gr.Button("🚀 Deploy", variant="primary", size="sm")
                            deploy_cancel_btn = gr.Button("Cancel", size="sm")
                        deploy_output = gr.Markdown("")

            # ──────────────────────────────────────────────────────────────
            # Event wiring
            # ──────────────────────────────────────────────────────────────

            # LLM bar
            provider_dd.change(
                fn=self.on_provider_change,
                inputs=[provider_dd],
                outputs=[model_dd, api_key_in],
            )
            apply_btn.click(
                fn=self.apply_llm_config,
                inputs=[provider_dd, api_key_in, model_dd, llm_client_state],
                outputs=[llm_client_state, llm_status],
            )

            # Chat — send on button or Enter
            send_inputs = [msg_input, chatbot, session_id_state, llm_client_state]
            send_outputs = [chatbot, msg_input, config_preview, validate_status]

            send_btn.click(
                fn=self.respond,
                inputs=send_inputs,
                outputs=send_outputs,
            )
            msg_input.submit(
                fn=self.respond,
                inputs=send_inputs,
                outputs=send_outputs,
            )

            # Clear
            clear_btn.click(
                fn=lambda: ([], "", "", "_Generate a config to see validation status_"),
                outputs=[chatbot, msg_input, config_preview, validate_status],
            )

            # Session history
            def new_chat(current_id):
                new_id = self._new_session_id()
                sessions = self._list_sessions()
                choices = [f"{label} — {sid[:8]}" for label, sid in sessions]
                return [], "", "", "_Generate a config to see validation status_", new_id, gr.update(choices=choices, value=None)

            new_chat_btn.click(
                fn=new_chat,
                inputs=[session_id_state],
                outputs=[chatbot, msg_input, config_preview, validate_status, session_id_state, session_dd],
            )

            def load_session_handler(selected_label):
                if not selected_label:
                    return gr.update(), gr.update()
                # Extract session_id from label (last 8 chars of UUID)
                sid_prefix = selected_label.split("—")[-1].strip()
                sessions = self._list_sessions()
                session_id = None
                for _, sid in sessions:
                    if sid.startswith(sid_prefix) or sid[:8] == sid_prefix:
                        session_id = sid
                        break
                if not session_id:
                    return gr.update(), gr.update()
                history = self._load_session_history(session_id)
                config = self._load_session_config(session_id)
                return history, config

            session_dd.change(
                fn=load_session_handler,
                inputs=[session_dd],
                outputs=[chatbot, config_preview],
            )

            # Config panel buttons
            validate_btn.click(
                fn=self.validate_config_handler,
                inputs=[config_preview],
                outputs=[validate_status],
            )
            download_btn.click(
                fn=self.download_config,
                inputs=[config_preview],
                outputs=[file_output],
            )
            file_output.change(
                fn=lambda f: gr.update(visible=f is not None),
                inputs=[file_output],
                outputs=[file_output],
            )

            # Run dialog
            run_btn.click(
                fn=self.open_run_dialog,
                inputs=[config_preview],
                outputs=[run_group, run_inputs_box, run_env_note, run_env_box],
            )
            run_cancel_btn.click(
                fn=lambda: gr.update(visible=False),
                outputs=[run_group],
            )
            run_execute_btn.click(
                fn=self.run_ephemeral,
                inputs=[config_preview, run_inputs_box, run_env_box],
                outputs=[run_output],
            )

            # Deploy dialog
            deploy_btn.click(
                fn=self.open_deploy_dialog,
                inputs=[config_preview, gr.State("")],
                outputs=[deploy_group, deploy_name_box, deploy_env_note, deploy_env_box, deploy_output],
            )
            deploy_cancel_btn.click(
                fn=lambda: gr.update(visible=False),
                outputs=[deploy_group],
            )
            deploy_execute_btn.click(
                fn=self.deploy_workflow,
                inputs=[config_preview, deploy_name_box, deploy_port_box, deploy_env_box],
                outputs=[deploy_output],
            )

            # On load: populate session list
            def on_load():
                sessions = self._list_sessions()
                choices = [f"{label} — {sid[:8]}" for label, sid in sessions]
                return gr.update(choices=choices, value=None)

            interface.load(fn=on_load, outputs=[session_dd])

        return interface

    def launch(
        self,
        server_name: str = "0.0.0.0",
        server_port: int = 7860,
        share: bool = False,
        **kwargs,
    ) -> None:
        interface = self.create_interface()
        interface.launch(
            server_name=server_name,
            server_port=server_port,
            share=share,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_gradio_chat_ui(
    llm_config: Optional[Any] = None,
    global_config: Optional[Any] = None,
    session_repo: Optional[ChatSessionRepository] = None,
    dashboard_url: Optional[str] = None,
) -> GradioChatUI:
    """Factory function to create GradioChatUI with default wiring."""
    llm_client = create_llm(llm_config, global_config)

    if session_repo is None:
        from configurable_agents.storage import create_storage_backend
        _, _, _, session_repo, _, _, _ = create_storage_backend()

    if dashboard_url is None:
        dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:7861")

    return GradioChatUI(
        default_llm_client=llm_client,
        session_repo=session_repo,
        dashboard_url=dashboard_url,
    )


if __name__ == "__main__":
    ui = create_gradio_chat_ui()
    ui.launch()
