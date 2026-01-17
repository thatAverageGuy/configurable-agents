"""
Streamlit UI for Configurable Agent Flows

Simple interface to configure and run agent workflows.
Pre-loaded with article generation flow as default.
"""

import streamlit as st
import yaml
from pathlib import Path
from configurable_agents.main import run_flow
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Configurable Agent Flow Runner",
    page_icon="🎯",
    layout="wide"
)

# Title
st.title("🎯 Configurable Agent Flow Runner")
st.markdown("Generate AI-validated articles using dynamic agent workflows")

# Load default config
@st.cache_data
def load_default_config():
    """Load the article generation flow config as default."""
    config_path = Path(__file__).parent / "article_generation_flow.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# Initialize session state
if 'config' not in st.session_state:
    st.session_state.config = load_default_config()
if 'result' not in st.session_state:
    st.session_state.result = None
if 'execution_complete' not in st.session_state:
    st.session_state.execution_complete = False

# Sidebar - Configuration
st.sidebar.header("⚙️ Configuration")

# Topic input
topic = st.sidebar.text_input(
    "Topic",
    value="AI in Healthcare",
    help="The topic to research and write an article about"
)

# Temperature slider
temperature = st.sidebar.slider(
    "LLM Temperature",
    min_value=0.0,
    max_value=1.0,
    value=0.7,
    step=0.1,
    help="Controls randomness in LLM outputs. Lower = more focused, Higher = more creative"
)

# Model selection
model_options = [
    "gemini-2.0-flash-exp",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.5-flash-lite"
]
selected_model = st.sidebar.selectbox(
    "LLM Model",
    options=model_options,
    index=0,
    help="Select the Google Gemini model to use"
)

st.sidebar.markdown("---")

# Advanced settings (collapsible)
with st.sidebar.expander("🔧 Advanced Settings"):
    max_tokens = st.number_input(
        "Max Tokens",
        min_value=1000,
        max_value=8000,
        value=4000,
        step=500,
        help="Maximum tokens for LLM outputs"
    )
    
    research_temp = st.number_input(
        "Research Crew Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.1,
        help="Temperature override for research crew (leave at 0.5 for factual research)"
    )
    
    writer_temp = st.number_input(
        "Writer Crew Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.8,
        step=0.1,
        help="Temperature override for writer crew (higher for more creative writing)"
    )

st.sidebar.markdown("---")

# View config button
if st.sidebar.button("📄 View Full YAML Config"):
    with st.sidebar.expander("Current Configuration", expanded=True):
        st.code(yaml.dump(st.session_state.config, default_flow_style=False), language="yaml")

# Main area - Run Flow
st.header("🚀 Execute Flow")

col1, col2 = st.columns([3, 1])

with col1:
    st.info(f"**Current Topic:** {topic}")
    st.caption(f"Model: {selected_model} | Temperature: {temperature} | Max Tokens: {max_tokens}")

with col2:
    run_button = st.button("▶️ Run Flow", type="primary", use_container_width=True)

# Execute flow
if run_button:
    st.session_state.execution_complete = False
    st.session_state.result = None
    
    # Update config with user inputs
    config = st.session_state.config.copy()
    
    # Apply global defaults
    config['defaults']['llm']['model'] = selected_model
    config['defaults']['llm']['temperature'] = temperature
    config['defaults']['llm']['max_tokens'] = max_tokens
    
    # Apply crew-specific overrides if advanced settings used
    if 'crews' in config:
        if 'research_crew' in config['crews']:
            config['crews']['research_crew']['llm'] = {
                'temperature': research_temp
            }
        if 'writer_crew' in config['crews']:
            config['crews']['writer_crew']['llm'] = {
                'temperature': writer_temp
            }
    
    # Show execution steps
    st.markdown("---")
    st.subheader("📋 Execution Progress")
    
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    
    # Run flow with progress
    with st.spinner("🔄 Running flow... This may take a few minutes."):
        try:
            # Set environment variable for model
            os.environ['MODEL'] = selected_model
            
            progress_placeholder.progress(0.1)
            status_placeholder.info("🔍 Initializing flow...")
            
            # Execute flow
            progress_placeholder.progress(0.3)
            status_placeholder.info("🔍 Research crew working...")
            
            result = run_flow(config, {"topic": topic})
            
            progress_placeholder.progress(1.0)
            status_placeholder.success("✅ Flow completed!")
            
            st.session_state.result = result
            st.session_state.execution_complete = True
            st.success("✅ Flow completed successfully!")
            
        except Exception as e:
            progress_placeholder.empty()
            status_placeholder.empty()
            st.error(f"❌ Flow execution failed: {str(e)}")
            st.exception(e)

# Display results
if st.session_state.execution_complete and st.session_state.result:
    st.markdown("---")
    st.header("📊 Results")
    
    result = st.session_state.result
    
    # Access the final output from state
    # The result should have the ArticleValidationOutput structure
    try:
        # Try to get pydantic output if available
        if hasattr(result, 'pydantic') and result.pydantic:
            output = result.pydantic
            
            # Create three columns for the output
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col3:
                # Display humanness score with visual
                st.metric(
                    "Humanness Score",
                    f"{output.humanness_score}/10",
                    help="1 = Obviously AI, 10 = Indistinguishable from human"
                )
                
                # Visual gauge
                score_percent = output.humanness_score / 10.0
                st.progress(score_percent)
                
                # Color-coded assessment
                if output.humanness_score >= 8:
                    st.success("🎉 Excellent!")
                elif output.humanness_score >= 6:
                    st.info("👍 Good")
                else:
                    st.warning("⚠️ Needs work")
            
            # Display article in first two columns
            with col1:
                st.subheader("📝 Generated Article")
            with col2:
                # Download button
                st.download_button(
                    label="⬇️ Download Article",
                    data=output.article,
                    file_name=f"article_{topic.replace(' ', '_')}.txt",
                    mime="text/plain"
                )
            
            # Full width article display
            st.markdown("---")
            article_container = st.container()
            with article_container:
                st.markdown(output.article)
            
            # Collapsible feedback section
            st.markdown("---")
            with st.expander("💬 Detailed Validation Feedback", expanded=True):
                st.info(output.feedback)
            
        else:
            # Fallback: display raw result
            st.subheader("📄 Raw Output")
            if hasattr(result, 'raw'):
                st.text_area("Result Text", result.raw, height=400)
            else:
                st.write(result)
                
    except Exception as e:
        st.error(f"Error displaying results: {str(e)}")
        st.write("Raw result:", result)

# Footer
st.markdown("---")
st.caption("Built with CrewAI Flows | Dynamic Runtime-Configurable Agent System")
