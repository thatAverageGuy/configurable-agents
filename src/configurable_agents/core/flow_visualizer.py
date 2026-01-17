"""
Flow Visualizer Module

Generates visual flowchart diagrams from flow configuration using Mermaid syntax.
"""

from typing import Dict, List, Any


def generate_mermaid_diagram(config: dict) -> str:
    """
    Generate a Mermaid flowchart diagram from flow configuration.
    
    Args:
        config: Complete flow configuration dictionary
        
    Returns:
        Mermaid diagram syntax as string
    """
    flow_config = config.get('flow', {})
    steps_config = config.get('steps', [])
    crews_config = config.get('crews', {})
    
    # Start building Mermaid diagram
    lines = ["graph TD"]
    
    # Find the start step
    start_step = None
    for step in steps_config:
        if step.get('is_start', False):
            start_step = step
            break
    
    if not start_step:
        return "graph TD\n    Error[No start step found]"
    
    # Add START node
    lines.append(f"    Start([START]) --> {start_step['id']}")
    
    # Track processed steps to avoid duplicates
    processed_steps = set()
    
    # Build the flow chain
    current_step = start_step
    while current_step:
        step_id = current_step['id']
        
        # Avoid infinite loops
        if step_id in processed_steps:
            break
        processed_steps.add(step_id)
        
        # Get step details
        step_type = current_step.get('type', 'crew')
        crew_ref = current_step.get('crew_ref', 'Unknown')
        next_step_id = current_step.get('next_step')
        
        # Create node label with crew info - simple one-line format
        display_name = step_id.replace('_', ' ').title()
        label = f"{display_name} - Crew: {crew_ref}"
        lines.append(f'    {step_id}["{label}"]')
        
        # Add edge to next step or END
        if next_step_id:
            lines.append(f"    {step_id} --> {next_step_id}")
            
            # Find next step in config
            next_step = None
            for step in steps_config:
                if step['id'] == next_step_id:
                    next_step = step
                    break
            current_step = next_step
        else:
            # This is the end of the flow
            lines.append(f"    {step_id} --> End([END])")
            break
    
    # Add styling
    lines.extend([
        "",
        "    classDef startEnd fill:#90EE90,stroke:#2d6a2d,stroke-width:2px",
        "    classDef stepNode fill:#87CEEB,stroke:#4682B4,stroke-width:2px",
        "    class Start,End startEnd"
    ])
    
    if processed_steps:
        lines.append(f"    class {','.join(processed_steps)} stepNode")
    
    return "\n".join(lines)


def generate_crew_diagram(crew_config: dict, crew_name: str) -> str:
    """
    Generate a detailed diagram for a single crew showing agents and tasks.
    
    Args:
        crew_config: Single crew configuration
        crew_name: Name of the crew
        
    Returns:
        Mermaid diagram syntax as string
    """
    agents = crew_config.get('agents', [])
    tasks = crew_config.get('tasks', [])
    execution = crew_config.get('execution', {})
    
    lines = ["graph LR"]
    # Use identifier-safe subgraph name
    subgraph_id = crew_name.replace('_', '')
    display_name = crew_name.replace('_', ' ').title()
    lines.append(f"    subgraph {subgraph_id}[{display_name}]")
    
    # Add agents
    for agent in agents:
        agent_id = agent['id']
        agent_role = agent.get('role', 'Agent')
        tools = agent.get('tools', [])
        
        # Create clean label - simple one-line format
        if tools:
            tools_str = ', '.join(tools)
            label = f"{agent_role} - Tools: {tools_str}"
        else:
            label = agent_role
        
        lines.append(f'        {agent_id}["{label}"]')
    
    # Add tasks
    for task in tasks:
        task_id = task['id']
        agent_id = task.get('agent', 'unknown')
        
        # Task node
        task_display = task_id.replace('_', ' ').title()
        lines.append(f'        {task_id}["{task_display}"]')
        
        # Connect task to agent
        if agent_id and agent_id in [a['id'] for a in agents]:
            lines.append(f"        {agent_id} -.->|executes| {task_id}")
    
    # Add task flow
    execution_type = execution.get('type', 'sequential')
    task_order = execution.get('tasks', [])
    
    if execution_type == 'sequential' and len(task_order) > 1:
        for i in range(len(task_order) - 1):
            lines.append(f"        {task_order[i]} --> {task_order[i+1]}")
    
    lines.append("    end")
    
    # Add styling
    lines.extend([
        "",
        "    classDef agentNode fill:#FFD700,stroke:#B8860B,stroke-width:2px",
        "    classDef taskNode fill:#98FB98,stroke:#228B22,stroke-width:2px"
    ])
    
    agent_ids = [a['id'] for a in agents]
    task_ids = [t['id'] for t in tasks]
    
    if agent_ids:
        lines.append(f"    class {','.join(agent_ids)} agentNode")
    if task_ids:
        lines.append(f"    class {','.join(task_ids)} taskNode")
    
    return "\n".join(lines)


def get_flow_summary(config: dict) -> Dict[str, Any]:
    """
    Get a summary of the flow configuration.
    
    Args:
        config: Complete flow configuration
        
    Returns:
        Dictionary with flow summary stats
    """
    flow_config = config.get('flow', {})
    steps_config = config.get('steps', [])
    crews_config = config.get('crews', {})
    
    # Count agents and tasks
    total_agents = 0
    total_tasks = 0
    
    for crew_name, crew_config in crews_config.items():
        total_agents += len(crew_config.get('agents', []))
        total_tasks += len(crew_config.get('tasks', []))
    
    return {
        'flow_name': flow_config.get('name', 'Unnamed Flow'),
        'description': flow_config.get('description', ''),
        'num_steps': len(steps_config),
        'num_crews': len(crews_config),
        'num_agents': total_agents,
        'num_tasks': total_tasks,
        'crew_names': list(crews_config.keys())
    }
