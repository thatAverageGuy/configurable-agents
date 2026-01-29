# streamlit_app.py
import streamlit as st
import yaml
import json
from dotenv import load_dotenv
from configurable_agents.runtime import run_workflow_from_config
from configurable_agents.config.schema import WorkflowConfig

# Load environment variables from .env
load_dotenv()

st.set_page_config(page_title="Workflow Executor", layout="wide")
st.title("🔧 Workflow Executor")

# YAML input
yaml_text = st.text_area(
    "Workflow YAML Configuration:",
    height=300,
    placeholder="Paste your workflow YAML here..."
)

# Inputs
st.subheader("Inputs")
inputs_text = st.text_area(
    "Provide inputs (one per line: key=value):",
    height=100,
    placeholder="topic=AI Safety\ncount=5\nenabled=true"
)

# Run button
if st.button("▶️ Run Workflow", type="primary"):
    if not yaml_text.strip():
        st.error("❌ Please provide a workflow YAML configuration")
    else:
        try:
            # Parse YAML to dict
            config_dict = yaml.safe_load(yaml_text)

            # Convert to WorkflowConfig
            config = WorkflowConfig(**config_dict)

            # Parse inputs (same logic as CLI)
            inputs = {}
            if inputs_text.strip():
                for line in inputs_text.strip().split('\n'):
                    line = line.strip()
                    if not line or '=' not in line:
                        continue
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Try JSON parsing for types
                    try:
                        inputs[key] = json.loads(value)
                    except (json.JSONDecodeError, ValueError):
                        inputs[key] = value

            # Execute workflow
            with st.spinner("⚙️ Executing workflow..."):
                result = run_workflow_from_config(config, inputs)

            # Show success
            st.success("✅ Workflow completed successfully!")
            st.json(result)

        except yaml.YAMLError as e:
            st.error(f"❌ Invalid YAML syntax:\n{str(e)}")
        except Exception as e:
            st.error(f"❌ Execution failed:")
            st.code(str(e), language="text")

# Instructions
with st.expander("ℹ️ Instructions"):
    st.markdown("""
    1. Paste your workflow YAML configuration above
    2. Add required inputs (one per line: `key=value`)
    3. Click "Run Workflow"

    **Input parsing:**
    - Strings: `topic=AI Safety`
    - Numbers: `count=5`
    - Booleans: `enabled=true`
    - Lists: `tags=["ai","safety"]`
    - Objects: `config={"key":"value"}`
    """)
