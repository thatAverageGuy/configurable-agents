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

def validate_config(config: dict) -> tuple[bool, list[str]]:
    """
    Validate configuration for broken dependencies.
    
    Returns:
        (is_valid, list_of_issues)
    """
    issues = []
    
    crews = config.get('crews', {})
    steps = config.get('steps', [])
    
    # Validate steps reference valid crews
    for step in steps:
        step_id = step.get('id', 'unknown')
        crew_ref = step.get('crew_ref')
        
        if crew_ref and crew_ref not in crews:
            issues.append(f"❌ Step '{step_id}' references non-existent crew '{crew_ref}'")
    
    # Validate tasks reference valid agents
    for crew_name, crew_config in crews.items():
        agents = crew_config.get('agents', [])
        tasks = crew_config.get('tasks', [])
        agent_ids = [a.get('id') for a in agents]
        
        for task in tasks:
            task_id = task.get('id', 'unknown')
            task_agent = task.get('agent')
            
            if task_agent and task_agent not in agent_ids:
                issues.append(f"❌ Task '{task_id}' in '{crew_name}' references non-existent agent '{task_agent}'")
    
    # Validate at least one start step exists
    has_start = any(step.get('is_start', False) for step in steps)
    if not has_start:
        issues.append("❌ No step marked as 'is_start: true'")
    
    # Validate step routing (next_step references)
    step_ids = [s.get('id') for s in steps]
    for step in steps:
        next_step = step.get('next_step')
        if next_step and next_step not in step_ids:
            issues.append(f"❌ Step '{step.get('id')}' routes to non-existent step '{next_step}'")
    
    is_valid = len(issues) == 0
    return is_valid, issues

def show_validation_status(config: dict):
    """Display validation status with warnings."""
    is_valid, issues = validate_config(config)
    
    if is_valid:
        st.success("✅ Configuration is valid and ready to execute")
        return True
    else:
        st.error("⚠️ Configuration has issues that must be fixed before execution:")
        for issue in issues:
            st.warning(issue)
        
        with st.expander("🔧 How to Fix", expanded=True):
            st.markdown("""
            **Common fixes:**
            - If a step references a deleted crew: reassign it to an existing crew or delete the step
            - If a task references a deleted agent: reassign it to an existing agent or delete the task
            - If routing is broken: update the 'next_step' value or set it to null for the final step
            - Make sure at least one step has 'is_start: true'
            """)
        
        return False

def generate_unique_id(base_name: str, existing_ids: list[str]) -> str:
    """
    Generate a unique ID by appending numbers if needed.
    
    Args:
        base_name: Base name for the ID (e.g., 'new_agent')
        existing_ids: List of existing IDs to check against
        
    Returns:
        Unique ID string
    """
    if base_name not in existing_ids:
        return base_name
    
    counter = 1
    while f"{base_name}_{counter}" in existing_ids:
        counter += 1
    
    return f"{base_name}_{counter}"

def create_default_agent(agent_id: str) -> dict:
    """
    Create a default agent configuration.
    
    Args:
        agent_id: ID for the new agent
        
    Returns:
        Agent configuration dictionary
    """
    return {
        'id': agent_id,
        'role': 'New Agent Role',
        'goal': 'Define what this agent should achieve',
        'backstory': 'Add background and expertise for this agent',
        'tools': [],
        'llm': {}
    }

def create_default_task(task_id: str, default_agent: str = '') -> dict:
    """
    Create a default task configuration.
    
    Args:
        task_id: ID for the new task
        default_agent: Default agent to assign (if available)
        
    Returns:
        Task configuration dictionary
    """
    return {
        'id': task_id,
        'description': 'Describe what this task should accomplish',
        'expected_output': 'Describe the expected output format and content',
        'agent': default_agent,
        'llm': {}
    }

def can_delete_agent(agent_id: str, tasks: list[dict]) -> tuple[bool, list[str]]:
    """
    Check if an agent can be safely deleted.
    
    Args:
        agent_id: ID of the agent to delete
        tasks: List of tasks in the crew
        
    Returns:
        (can_delete, list_of_dependent_tasks)
    """
    dependent_tasks = []
    for task in tasks:
        if task.get('agent') == agent_id:
            dependent_tasks.append(task.get('id', 'unknown'))
    
    can_delete = len(dependent_tasks) == 0
    return can_delete, dependent_tasks

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
    
    # ============ ADD THIS ============
    # Show validation status
    is_valid, issues = validate_config(st.session_state.config)
    
    if is_valid:
        st.success("✅ Configuration is valid")
    else:
        st.error(f"⚠️ Found {len(issues)} issue(s) - fix before execution")
        with st.expander("❌ Issues Found", expanded=False):
            for issue in issues:
                st.warning(issue)
    
    st.markdown("---")
    # ============ END ADDITION ============

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

            # Add Agent Button
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button(f"➕ Add Agent", key=f"add_agent_{crew_name}", use_container_width=True):
                    # Generate unique agent ID
                    existing_agent_ids = [a.get('id', '') for a in agents]
                    new_agent_id = generate_unique_id('new_agent', existing_agent_ids)
                    
                    # Create new agent with default values
                    new_agent = create_default_agent(new_agent_id)
                    agents.append(new_agent)
                    
                    st.success(f"✅ Added agent: {new_agent_id}")
                    st.rerun()

            st.markdown("---")

            # Edit existing agents
            for idx, agent in enumerate(agents):
                agent_id = agent.get('id', f'agent_{idx}')
                
                with st.container():
                    # Agent header with delete button
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.markdown(f"**Agent:** `{agent_id}` - {agent.get('role', 'Unknown Role')}")
                    
                    with col2:
                        # Check if agent can be deleted
                        tasks = crew_config.get('tasks', [])
                        can_delete, dependent_tasks = can_delete_agent(agent_id, tasks)
                        
                        delete_button_disabled = not can_delete
                        delete_help = f"⚠️ Cannot delete: Tasks {', '.join(dependent_tasks)} depend on this agent" if not can_delete else "Delete this agent"
                        
                        if st.button(
                            "🗑️ Delete", 
                            key=f"delete_agent_{crew_name}_{agent_id}",
                            use_container_width=True,
                            disabled=delete_button_disabled,
                            help=delete_help
                        ):
                            # Confirm deletion
                            agents.remove(agent)
                            st.success(f"✅ Deleted agent: {agent_id}")
                            st.rerun()
                    
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
                    
                    # Tool selection (your existing code)
                    st.markdown("**Tools**")
                    from configurable_agents.core.tool_registry import list_available_tools

                    try:
                        available_tools = list_available_tools()
                        current_tools = agent.get('tools', [])
                        
                        if available_tools:
                            num_cols = 3
                            cols = st.columns(num_cols)
                            
                            selected_tools = []
                            for tool_idx, tool_name in enumerate(available_tools):
                                col_idx = tool_idx % num_cols
                                with cols[col_idx]:
                                    is_selected = st.checkbox(
                                        tool_name,
                                        value=tool_name in current_tools,
                                        key=f"{crew_name}_{agent_id}_tool_{tool_name}",
                                        help=f"Enable {tool_name} for this agent"
                                    )
                                    if is_selected:
                                        selected_tools.append(tool_name)
                            
                            agent['tools'] = selected_tools
                            
                            if selected_tools:
                                st.caption(f"✅ Selected: {', '.join(selected_tools)}")
                            else:
                                st.caption("⚠️ No tools selected")
                        else:
                            st.warning("No tools available in registry")
                            
                    except Exception as e:
                        st.error(f"Error loading tools: {str(e)}")
                    
                    # Agent LLM settings (your existing code)
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

            # Add Task Button
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button(f"➕ Add Task", key=f"add_task_{crew_name}", use_container_width=True):
                    # Generate unique task ID
                    existing_task_ids = [t.get('id', '') for t in tasks]
                    new_task_id = generate_unique_id('new_task', existing_task_ids)
                    
                    # Get first available agent as default
                    agent_ids = [a.get('id', '') for a in agents]
                    default_agent = agent_ids[0] if agent_ids else ''
                    
                    # Create new task with default values
                    new_task = create_default_task(new_task_id, default_agent)
                    tasks.append(new_task)
                    
                    st.success(f"✅ Added task: {new_task_id}")
                    st.rerun()

            st.markdown("---")

            # Edit existing tasks
            for idx, task in enumerate(tasks):
                task_id = task.get('id', f'task_{idx}')
                
                with st.container():
                    # Task header with delete button
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.markdown(f"**Task:** `{task_id}`")
                    
                    with col2:
                        if st.button(
                            "🗑️ Delete", 
                            key=f"delete_task_{crew_name}_{task_id}",
                            use_container_width=True,
                            help="Delete this task"
                        ):
                            # Confirm deletion
                            tasks.remove(task)
                            st.success(f"✅ Deleted task: {task_id}")
                            st.rerun()
                    
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
                    
                    if agent_ids:
                        task_agent = st.selectbox(
                            "Assigned Agent",
                            options=agent_ids,
                            index=agent_ids.index(current_agent) if current_agent in agent_ids else 0,
                            key=f"{crew_name}_{task_id}_agent",
                            help="Which agent executes this task"
                        )
                        task['agent'] = task_agent
                    else:
                        st.warning("⚠️ No agents available. Add an agent first!")
                        task['agent'] = ''
                    
                    # Task LLM settings (your existing code)
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
    
    # ============ ADD VALIDATION CHECK ============
    # Validate configuration before showing run button
    is_valid = show_validation_status(st.session_state.config)
    # ============ END ADDITION ============

    with col2:
        run_button = st.button(
            "▶️ Run Flow", 
            type="primary", 
            use_container_width=True,
            disabled=not is_valid,  # ← ADD THIS
            help="Fix configuration issues before running" if not is_valid else "Execute the flow"  # ← ADD THIS
        )

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
