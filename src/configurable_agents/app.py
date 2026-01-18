"""
Streamlit UI for Configurable Agent Flows

Simple interface to configure and run agent workflows.
Pre-loaded with article generation flow as default.
"""

import streamlit as st
import yaml
from pathlib import Path
from configurable_agents.main import run_flow
from configurable_agents.core.flow_visualizer import (
    generate_mermaid_diagram,
    generate_crew_diagram,
    get_flow_summary
)
import os
from dotenv import load_dotenv

# Import streamlit-mermaid for rendering diagrams
try:
    from streamlit_mermaid import st_mermaid
    MERMAID_AVAILABLE = True
except ImportError:
    MERMAID_AVAILABLE = False
    st.warning("⚠️ streamlit-mermaid not installed. Diagrams will show as code. Install with: pip install streamlit-mermaid")

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

# Main area - Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "⚙️ Config Editor", "🎨 Flow Diagram", "🚀 Execute", "📊 Results"])

# ==================== TAB 1: OVERVIEW ====================
with tab1:
    st.header("📊 Flow Overview")
    
    # Get flow summary
    summary = get_flow_summary(st.session_state.config)
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Steps", summary['num_steps'], help="Number of execution steps in the flow")
    
    with col2:
        st.metric("Crews", summary['num_crews'], help="Number of agent crews")
    
    with col3:
        st.metric("Agents", summary['num_agents'], help="Total number of agents across all crews")
    
    with col4:
        st.metric("Tasks", summary['num_tasks'], help="Total number of tasks across all crews")
    
    st.markdown("---")
    
    # Flow details
    st.subheader("🎯 Flow Details")
    st.write(f"**Name:** {summary['flow_name']}")
    st.write(f"**Description:** {summary['description']}")
    st.write(f"**Crews:** {', '.join(summary['crew_names'])}")
    
    st.markdown("---")
    
    # Current configuration
    st.subheader("⚙️ Current Configuration")
    st.info(f"**Topic:** {topic}")
    st.caption(f"Model: {selected_model} | Temperature: {temperature} | Max Tokens: {max_tokens}")

# ==================== TAB 2: CONFIG EDITOR ====================
with tab2:
    st.header("⚙️ Configuration Editor")
    st.caption("Edit agent behaviors, task descriptions, and LLM settings")
    
    # Get config for editing
    config = st.session_state.config
    crews = config.get('crews', {})
    
    # Flow-level settings
    with st.expander("🎯 Flow Settings", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            flow_name = st.text_input(
                "Flow Name",
                value=config['flow']['name'],
                help="Name of the flow"
            )
            config['flow']['name'] = flow_name
        
        with col2:
            flow_desc = st.text_area(
                "Flow Description",
                value=config['flow']['description'],
                height=100,
                help="Description of what this flow does"
            )
            config['flow']['description'] = flow_desc
    
    st.markdown("---")
    
    # Crew-level editing
    st.subheader("👥 Crews Configuration")
    
    for crew_name, crew_config in crews.items():
        with st.expander(f"🔍 {crew_name.replace('_', ' ').title()}", expanded=True):
            st.markdown(f"**Crew:** `{crew_name}`")
            
            # Crew-level LLM settings
            st.markdown("**Crew LLM Settings**")
            col1, col2, col3 = st.columns(3)
            
            crew_llm = crew_config.get('llm', {})
            
            with col1:
                crew_temp = st.number_input(
                    "Temperature",
                    min_value=0.0,
                    max_value=1.0,
                    value=crew_llm.get('temperature', 0.7),
                    step=0.1,
                    key=f"{crew_name}_temp",
                    help="Crew-level temperature override"
                )
                if 'llm' not in crew_config:
                    crew_config['llm'] = {}
                crew_config['llm']['temperature'] = crew_temp
            
            with col2:
                crew_model = st.text_input(
                    "Model Override",
                    value=crew_llm.get('model', ''),
                    key=f"{crew_name}_model",
                    help="Leave empty to use global model"
                )
                if crew_model:
                    crew_config['llm']['model'] = crew_model
            
            with col3:
                crew_max_tokens = st.number_input(
                    "Max Tokens",
                    min_value=100,
                    max_value=8000,
                    value=crew_llm.get('max_tokens', 4000),
                    step=100,
                    key=f"{crew_name}_tokens",
                    help="Max tokens for this crew"
                )
                crew_config['llm']['max_tokens'] = crew_max_tokens
            
            st.markdown("---")
            
            # Agents editing
            st.markdown("### Agents")
            agents = crew_config.get('agents', [])
            
            for idx, agent in enumerate(agents):
                agent_id = agent.get('id', f'agent_{idx}')
                
                with st.container():
                    st.markdown(f"**Agent:** `{agent_id}` - {agent.get('role', 'Unknown Role')}")
                    
                    # Agent role
                    agent_role = st.text_input(
                        "Role",
                        value=agent.get('role', ''),
                        key=f"{crew_name}_{agent_id}_role",
                        help="Agent's role/title"
                    )
                    agent['role'] = agent_role
                    
                    # Agent goal
                    agent_goal = st.text_area(
                        "Goal",
                        value=agent.get('goal', ''),
                        height=80,
                        key=f"{crew_name}_{agent_id}_goal",
                        help="What this agent is trying to achieve"
                    )
                    agent['goal'] = agent_goal
                    
                    # Agent backstory
                    agent_backstory = st.text_area(
                        "Backstory",
                        value=agent.get('backstory', ''),
                        height=100,
                        key=f"{crew_name}_{agent_id}_backstory",
                        help="Agent's background and expertise"
                    )
                    agent['backstory'] = agent_backstory
                    
                    # Agent LLM settings (optional override)
                    with st.expander(f"⚙️ LLM Settings for {agent_id}", expanded=False):
                        agent_llm = agent.get('llm', {})
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            agent_temp = st.number_input(
                                "Temperature Override",
                                min_value=0.0,
                                max_value=1.0,
                                value=agent_llm.get('temperature', 0.7),
                                step=0.1,
                                key=f"{crew_name}_{agent_id}_llm_temp",
                                help="Agent-specific temperature"
                            )
                            if 'llm' not in agent:
                                agent['llm'] = {}
                            agent['llm']['temperature'] = agent_temp
                        
                        with col2:
                            agent_model = st.text_input(
                                "Model Override",
                                value=agent_llm.get('model', ''),
                                key=f"{crew_name}_{agent_id}_llm_model",
                                help="Leave empty to use crew/global model"
                            )
                            if agent_model:
                                agent['llm']['model'] = agent_model
                    
                    st.markdown("---")
            
            # Tasks editing
            st.markdown("### Tasks")
            tasks = crew_config.get('tasks', [])
            
            for idx, task in enumerate(tasks):
                task_id = task.get('id', f'task_{idx}')
                
                with st.container():
                    st.markdown(f"**Task:** `{task_id}`")
                    
                    # Task description
                    task_desc = st.text_area(
                        "Description",
                        value=task.get('description', ''),
                        height=120,
                        key=f"{crew_name}_{task_id}_desc",
                        help="What this task should accomplish"
                    )
                    task['description'] = task_desc
                    
                    # Expected output
                    task_output = st.text_area(
                        "Expected Output",
                        value=task.get('expected_output', ''),
                        height=80,
                        key=f"{crew_name}_{task_id}_output",
                        help="Description of expected output format/content"
                    )
                    task['expected_output'] = task_output
                    
                    # Agent assignment
                    agent_ids = [a.get('id', '') for a in agents]
                    current_agent = task.get('agent', agent_ids[0] if agent_ids else '')
                    
                    task_agent = st.selectbox(
                        "Assigned Agent",
                        options=agent_ids,
                        index=agent_ids.index(current_agent) if current_agent in agent_ids else 0,
                        key=f"{crew_name}_{task_id}_agent",
                        help="Which agent executes this task"
                    )
                    task['agent'] = task_agent
                    
                    # Task LLM settings (optional override)
                    with st.expander(f"⚙️ LLM Settings for {task_id}", expanded=False):
                        task_llm = task.get('llm', {})
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            task_temp = st.number_input(
                                "Temperature Override",
                                min_value=0.0,
                                max_value=1.0,
                                value=task_llm.get('temperature', 0.7),
                                step=0.1,
                                key=f"{crew_name}_{task_id}_llm_temp",
                                help="Task-specific temperature"
                            )
                            if 'llm' not in task:
                                task['llm'] = {}
                            task['llm']['temperature'] = task_temp
                        
                        with col2:
                            task_model = st.text_input(
                                "Model Override",
                                value=task_llm.get('model', ''),
                                key=f"{crew_name}_{task_id}_llm_model",
                                help="Leave empty to use agent/crew/global model"
                            )
                            if task_model:
                                task['llm']['model'] = task_model
                    
                    st.markdown("---")
    
    # Actions
    st.markdown("---")
    st.subheader("💾 Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Reset to Default", use_container_width=True):
            st.session_state.config = load_default_config()
            st.success("✅ Reset to default configuration!")
            st.rerun()
    
    with col2:
        # Download current config
        yaml_str = yaml.dump(st.session_state.config, default_flow_style=False, sort_keys=False)
        st.download_button(
            label="📥 Download YAML",
            data=yaml_str,
            file_name="custom_flow_config.yaml",
            mime="text/yaml",
            use_container_width=True
        )
    
    with col3:
        st.info("Upload coming in Phase 2!")

# ==================== TAB 3: FLOW DIAGRAM ====================
with tab3:
    st.header("🎨 Flow Visualization")
    
    # Generate and display main flow diagram
    st.subheader("📈 Execution Flow")
    st.caption("This diagram shows the complete execution flow from start to finish")
    
    try:
        mermaid_code = generate_mermaid_diagram(st.session_state.config)
        
        if MERMAID_AVAILABLE:
            # Render with streamlit-mermaid component
            st_mermaid(mermaid_code, height=400)
        else:
            # Fallback: show as code block with instructions
            st.code(mermaid_code, language="mermaid")
            st.info("💡 To see rendered diagrams, install: `pip install streamlit-mermaid` and restart the app")
            
    except Exception as e:
        st.error(f"Error generating flow diagram: {str(e)}")
        st.exception(e)
    
    st.markdown("---")
    
    # Crew detail diagrams
    st.subheader("👥 Crew Details")
    st.caption("Expand each crew to see agents, tasks, and their relationships")
    
    crews = st.session_state.config.get('crews', {})
    
    for crew_name, crew_config in crews.items():
        with st.expander(f"🔍 {crew_name.replace('_', ' ').title()}", expanded=False):
            # Get crew info
            agents = crew_config.get('agents', [])
            tasks = crew_config.get('tasks', [])
            
            # Show crew stats
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Agents", len(agents))
            with col2:
                st.metric("Tasks", len(tasks))
            
            # Agent details
            st.markdown("**Agents:**")
            for agent in agents:
                agent_role = agent.get('role', 'Unknown Role')
                agent_tools = agent.get('tools', [])
                tools_str = f"(Tools: {', '.join(agent_tools)})" if agent_tools else "(No tools)"
                st.write(f"- {agent_role} {tools_str}")
            
            # Task details
            st.markdown("**Tasks:**")
            for task in tasks:
                task_id = task.get('id', 'unknown')
                task_agent = task.get('agent', 'unknown')
                st.write(f"- {task_id} (executed by: {task_agent})")
            
            # Crew diagram
            st.markdown("**Crew Diagram:**")
            try:
                crew_diagram = generate_crew_diagram(crew_config, crew_name)
                
                if MERMAID_AVAILABLE:
                    # Render with streamlit-mermaid component
                    st_mermaid(crew_diagram, height=300)
                else:
                    # Fallback: show as code block
                    st.code(crew_diagram, language="mermaid")
                    
            except Exception as e:
                st.error(f"Error generating crew diagram: {str(e)}")

# ==================== TAB 4: EXECUTE ====================
with tab4:
    st.header("🚀 Execute Flow")
    
    # Configuration summary
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
                st.success("✅ Flow completed successfully! Check the Results tab.")
                
            except Exception as e:
                progress_placeholder.empty()
                status_placeholder.empty()
                st.error(f"❌ Flow execution failed: {str(e)}")
                st.exception(e)

# ==================== TAB 5: RESULTS ====================
with tab5:
    st.header("📊 Results")
    
    if st.session_state.execution_complete and st.session_state.result:
        result = st.session_state.result
        
        # Access the final output from state
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
    else:
        st.info("👈 No results yet. Run the flow in the Execute tab to see results here.")

# Footer
st.markdown("---")
st.caption("Built with CrewAI Flows | Dynamic Runtime-Configurable Agent System")
