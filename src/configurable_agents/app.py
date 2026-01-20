import streamlit as st
import yaml
import json
import sys
import os
from dotenv import load_dotenv

# Ensure we can import from the package if running from src root
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(os.path.dirname(current_dir))
if src_dir not in sys.path:
    sys.path.append(src_dir)

from configurable_agents.main import run_flow

# Load environment variables (API keys)
load_dotenv()

st.set_page_config(page_title="Agent Flow Runner", layout="wide")
st.title("⚡ Agent Flow Runner")

# --- Layout ---
col1, col2 = st.columns([1, 1])

# --- Left Column: YAML Config ---
with col1:
    st.subheader("1. Configuration (YAML)")
    
    default_yaml = """flow:
  name: "demo_flow"
  description: "A simple demo flow"

crews:
  research_crew:
    agents:
      - id: researcher
        role: "Researcher"
        goal: "Find information about {topic}"
        backstory: "You are an expert researcher."
        tools: ["serper_search"]
        llm:
          model: "gemini-2.0-flash"
    tasks:
      - id: research_task
        description: "Research {topic} deeply."
        expected_output: "A summary report."
        agent: researcher
    execution:
      type: sequential

steps:
  - id: step_1
    type: crew
    crew_ref: research_crew
    is_start: true
    inputs:
      topic: "{topic}"
"""
    yaml_input = st.text_area("Flow Configuration", value=default_yaml, height=700)

# --- Right Column: Inputs & Execution ---
with col2:
    st.subheader("2. Initial Inputs (JSON)")
    default_inputs = '{\n  "topic": "Agentic Workflows"\n}'
    json_input = st.text_area("JSON Inputs", value=default_inputs, height=200)

    st.subheader("3. Execution")
    run_btn = st.button("🚀 Run Flow", type="primary", use_container_width=True)
    
    output_container = st.container()

    if run_btn:
        with output_container:
            try:
                # 1. Parse Inputs
                inputs = json.loads(json_input)
                
                # 2. Parse YAML
                config = yaml.safe_load(yaml_input)
                
                with st.status("⚙️ Executing Flow...", expanded=True) as status:
                    st.write("Initializing Flow...")
                    
                    # 3. Execute using main.py's logic
                    # This handles state setup, UUID generation, etc.
                    result = run_flow(config, inputs)
                    
                    status.update(label="✅ Flow Completed", state="complete")
                
                # 4. Display Output
                st.success("Execution Successful")
                st.markdown("### Final Output")
                
                # Handle CrewAI output types safely
                final_output = result.raw if hasattr(result, 'raw') else str(result)
                st.markdown(final_output)
                
            except json.JSONDecodeError as e:
                st.error(f"❌ JSON Input Error: {e}")
            except yaml.YAMLError as e:
                st.error(f"❌ YAML Syntax Error: {e}")
            except Exception as e:
                st.error(f"❌ Execution Error: {e}")
                st.exception(e)