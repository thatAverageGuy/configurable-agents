"""
Crew Builder Module

This module builds CrewAI Crew instances from YAML configuration.
Handles agent creation, task creation, LLM configuration, and crew assembly.
"""

import os
from typing import Dict, Any, List, Optional
from crewai import Agent, Task, Crew, Process
from pydantic import BaseModel
from core.tool_registry import get_tool
from core.model_builder import build_pydantic_model
from core.utils import resolve_template
from dotenv import load_dotenv
load_dotenv()

def build_crew(crew_config: dict, inputs: Dict[str, Any]) -> Crew:
    """
    Build a Crew from configuration.
    
    Args:
        crew_config: Crew configuration dictionary
        inputs: Input values for template resolution
        
    Returns:
        Configured Crew instance
    """
    # Get LLM configuration (crew-level)
    crew_llm_config = crew_config.get('llm', {})
    
    # Build agents
    agents = []
    agents_map = {}
    for agent_config in crew_config.get('agents', []):
        agent = build_agent(agent_config, crew_llm_config, inputs)
        agents.append(agent)
        agents_map[agent_config['id']] = agent
    
    # Build tasks
    tasks = []
    for task_config in crew_config.get('tasks', []):
        task = build_task(task_config, agents_map, crew_llm_config, inputs)
        tasks.append(task)
    
    # Get execution configuration
    execution_config = crew_config.get('execution', {})
    execution_type = execution_config.get('type', 'sequential')
    
    # Determine process type
    if execution_type == 'sequential':
        process = Process.sequential
        manager_llm = None
        manager_agent = None
    elif execution_type == 'hierarchical':
        process = Process.hierarchical
        
        # Get manager configuration
        manager_agent_id = execution_config.get('manager_agent')
        if manager_agent_id:
            manager_agent = agents_map.get(manager_agent_id)
        else:
            manager_agent = None
        
        # Get manager LLM
        manager_llm_config = execution_config.get('manager_llm', crew_llm_config)
        manager_llm = build_llm(manager_llm_config) if manager_llm_config else None
    else:
        raise ValueError(f"Unsupported execution type: {execution_type}")
    
    # Create crew
    crew_kwargs = {
        'agents': agents,
        'tasks': tasks,
        'process': process,
        'verbose': True
    }
    
    if execution_type == 'hierarchical':
        if manager_llm:
            crew_kwargs['manager_llm'] = manager_llm
        if manager_agent:
            crew_kwargs['manager_agent'] = manager_agent
    
    crew = Crew(**crew_kwargs)
    
    return crew


def build_agent(agent_config: dict, crew_llm_config: dict, inputs: Dict[str, Any]) -> Agent:
    """
    Build an Agent from configuration.
    
    Args:
        agent_config: Agent configuration dictionary
        crew_llm_config: Crew-level LLM configuration
        inputs: Input values for template resolution
        
    Returns:
        Configured Agent instance
    """
    # Resolve templates in agent config
    role = resolve_template_string(agent_config.get('role', ''), inputs)
    goal = resolve_template_string(agent_config.get('goal', ''), inputs)
    backstory = resolve_template_string(agent_config.get('backstory', ''), inputs)
    
    # Get tools
    tool_names = agent_config.get('tools', [])
    tools = [get_tool(tool_name) for tool_name in tool_names]
    
    # Get LLM configuration (agent-level overrides crew-level)
    agent_llm_config = agent_config.get('llm', crew_llm_config)
    llm = build_llm(agent_llm_config) if agent_llm_config else None
    
    # Build agent
    agent_kwargs = {
        'role': role,
        'goal': goal,
        'backstory': backstory,
        'tools': tools,
        'verbose': True
    }
    
    if llm:
        agent_kwargs['llm'] = llm
    
    agent = Agent(**agent_kwargs)
    
    return agent


def build_task(task_config: dict, agents_map: Dict[str, Agent], 
               crew_llm_config: dict, inputs: Dict[str, Any]) -> Task:
    """
    Build a Task from configuration.
    
    Args:
        task_config: Task configuration dictionary
        agents_map: Map of agent IDs to Agent instances
        crew_llm_config: Crew-level LLM configuration
        inputs: Input values for template resolution
        
    Returns:
        Configured Task instance
    """
    # Resolve templates in task config
    description = resolve_template_string(task_config.get('description', ''), inputs)
    expected_output = resolve_template_string(task_config.get('expected_output', ''), inputs)
    
    # Get agent
    agent_id = task_config.get('agent')
    if agent_id not in agents_map:
        raise ValueError(f"Agent '{agent_id}' not found for task '{task_config.get('id')}'")
    agent = agents_map[agent_id]
    
    # Build output model if specified
    output_model = None
    output_model_config = task_config.get('output_model')
    if output_model_config:
        output_model = build_pydantic_model(output_model_config)
    
    # Get LLM configuration (task-level overrides agent/crew-level)
    task_llm_config = task_config.get('llm', crew_llm_config)
    llm = build_llm(task_llm_config) if task_llm_config else None
    
    # Build task
    task_kwargs = {
        'description': description,
        'expected_output': expected_output,
        'agent': agent
    }
    
    if output_model:
        task_kwargs['output_pydantic'] = output_model
    
    if llm:
        task_kwargs['llm'] = llm
    
    task = Task(**task_kwargs)
    
    return task


def build_llm(llm_config: dict) -> Any:
    """
    Build an LLM instance from configuration.
    
    Args:
        llm_config: LLM configuration dictionary
        
    Returns:
        LLM instance (LangChain LLM object)
    """
    # provider = llm_config.get('provider', 'openai')
    # model = llm_config.get('model', 'gpt-4o')
    # temperature = llm_config.get('temperature', 0.7)
    # max_tokens = llm_config.get('max_tokens')
    
    # if provider == 'openai':
    #     from langchain_openai import ChatOpenAI
        
    #     llm_kwargs = {
    #         'model': model,
    #         'temperature': temperature
    #     }
    #     if max_tokens:
    #         llm_kwargs['max_tokens'] = max_tokens
        
    #     return ChatOpenAI(**llm_kwargs)
    
    # elif provider == 'anthropic':
    #     from langchain_anthropic import ChatAnthropic
        
    #     llm_kwargs = {
    #         'model': model,
    #         'temperature': temperature
    #     }
    #     if max_tokens:
    #         llm_kwargs['max_tokens'] = max_tokens
        
    #     return ChatAnthropic(**llm_kwargs)
    
    # else:
    #     raise ValueError(f"Unsupported LLM provider: {provider}")
    model = os.getenv("MODEL")


def resolve_template_string(template: str, inputs: Dict[str, Any]) -> str:
    """
    Resolve template strings with input values.
    
    Supports patterns like: {company_name}, {topic}, {research_report}
    
    Args:
        template: Template string with placeholders
        inputs: Dictionary of input values
        
    Returns:
        Resolved string
    """
    if not template:
        return template
    
    result = template
    for key, value in inputs.items():
        placeholder = f"{{{key}}}"
        if placeholder in result:
            result = result.replace(placeholder, str(value))
    
    return result