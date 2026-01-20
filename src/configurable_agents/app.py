import streamlit as st
import yaml
import json
import sys
import os
from dotenv import load_dotenv
import asyncio
# Ensure we can import from the package if running from src root
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(os.path.dirname(current_dir))
if src_dir not in sys.path:
    sys.path.append(src_dir)

from configurable_agents.main import run_flow

# Try importing the spawner, handle cases where dependencies (like docker) might be missing
try:
    from configurable_agents.spawner import spawn_agent_container
    HAS_SPAWNER = True
except ImportError as e:
    HAS_SPAWNER = False
    SPAWNER_ERROR = str(e)

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

    st.subheader("3. Execution (Test Run)")
    run_btn = st.button("🚀 Run Flow Locally", type="primary", use_container_width=True)
    
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
                    result = asyncio.run(run_flow(config, inputs))
                    
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

    # --- Section 4: Deployment (New) ---
    st.divider()
    st.subheader("4. Deployment (Docker)")
    
    if not HAS_SPAWNER:
        st.warning(f"⚠️ Deployment features unavailable. Missing dependencies or file.\nError: {SPAWNER_ERROR}")
    else:
        with st.expander("🚢 Deploy as Persistent Service", expanded=True):
            st.info("This will build a Docker container for this specific agent configuration.")
            
            agent_name = st.text_input("Service Name (for Docker container)", value="my-agent-service")
            
            deploy_btn = st.button("🏗️ Build & Spawn Container", type="secondary", use_container_width=True)
            
            if deploy_btn:
                api_key = os.getenv("GOOGLE_API_KEY")
                
                if not api_key:
                    st.error("❌ GOOGLE_API_KEY not found in environment variables. Cannot start agent.")
                elif not agent_name.strip():
                    st.error("❌ Please provide a name for the agent service.")
                else:
                    try:
                        # Parse YAML first to ensure it's valid before building
                        yaml.safe_load(yaml_input)
                        
                        with st.status("🏗️ Building and Spawning Agent...", expanded=True) as status:
                            st.write("Preparing build context...")
                            st.write("Building Docker image (this may take a minute)...")
                            
                            # Call the spawner
                            endpoint_url = spawn_agent_container(
                                yaml_content=yaml_input,
                                agent_name=agent_name,
                                api_key=api_key
                            )
                            
                            status.update(label="✅ Agent Deployed Successfully!", state="complete")
                        
                        st.success(f"Agent is running at: {endpoint_url}")
                        
                        # Show usage examples
                        st.markdown("### How to trigger this agent:")
                        
                        tab1, tab2 = st.tabs(["cURL", "Python"])
                        
                        with tab1:
                            st.code(f"""curl -X POST "{endpoint_url}/kickoff" \\
     -H "Content-Type: application/json" \\
     -d '{json_input}'""", language="bash")
                            
                        with tab2:
                            st.code(f"""import requests

url = "{endpoint_url}/kickoff"
payload = {{
    "inputs": {json_input}
}}

response = requests.post(url, json=payload)
print(response.json())""", language="python")
                            
                    except yaml.YAMLError as e:
                        st.error(f"❌ YAML Syntax Error: {e}")
                    except Exception as e:
                        st.error(f"❌ Deployment Failed: {e}")
                        st.exception(e)