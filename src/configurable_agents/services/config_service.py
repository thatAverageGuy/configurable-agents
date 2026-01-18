"""
Configuration Service

Handles CRUD operations for flow configurations.
Provides high-level API for config management.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import asdict

from ..domain import (
    FlowConfig,
    CrewConfig,
    AgentConfig,
    TaskConfig,
    StepConfig,
    LLMConfig,
    FlowMetadata,
    StateConfig,
    ExecutionConfig,
    InvalidYAMLError,
    CrewNotFoundError,
    AgentNotFoundError,
    TaskNotFoundError,
    StepNotFoundError,
)
from ..config import get_logger

logger = get_logger(__name__)


class ConfigService:
    """Service for managing flow configurations."""
    
    def __init__(self):
        """Initialize config service."""
        self.logger = logger
    
    # ==================== LOAD / SAVE ====================
    
    def load_from_file(self, config_path: str) -> FlowConfig:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            FlowConfig instance
            
        Raises:
            InvalidYAMLError: If YAML parsing fails
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            self.logger.info(f"Loaded config from {config_path}")
            return self._dict_to_config(data)
            
        except yaml.YAMLError as e:
            raise InvalidYAMLError(config_path, e)
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            raise
    
    def save_to_file(self, config: FlowConfig, output_path: str) -> None:
        """
        Save configuration to YAML file.
        
        Args:
            config: FlowConfig to save
            output_path: Output file path
        """
        try:
            data = self._config_to_dict(config)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"Saved config to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            raise
    
    def load_from_dict(self, data: Dict[str, Any]) -> FlowConfig:
        """
        Load configuration from dictionary.
        
        Args:
            data: Configuration as dictionary
            
        Returns:
            FlowConfig instance
        """
        return self._dict_to_config(data)
    
    def to_dict(self, config: FlowConfig) -> Dict[str, Any]:
        """
        Convert FlowConfig to dictionary.
        
        Args:
            config: FlowConfig instance
            
        Returns:
            Configuration as dictionary
        """
        return self._config_to_dict(config)
    
    # ==================== CREW OPERATIONS ====================
    
    def add_crew(self, config: FlowConfig, crew_name: str, crew: CrewConfig) -> FlowConfig:
        """
        Add a new crew to configuration.
        
        Args:
            config: FlowConfig instance
            crew_name: Name for the new crew
            crew: CrewConfig instance
            
        Returns:
            Updated FlowConfig
        """
        config.crews[crew_name] = crew
        self.logger.info(f"Added crew: {crew_name}")
        return config
    
    def update_crew(self, config: FlowConfig, crew_name: str, crew: CrewConfig) -> FlowConfig:
        """
        Update an existing crew.
        
        Args:
            config: FlowConfig instance
            crew_name: Name of crew to update
            crew: Updated CrewConfig
            
        Returns:
            Updated FlowConfig
            
        Raises:
            CrewNotFoundError: If crew doesn't exist
        """
        if crew_name not in config.crews:
            raise CrewNotFoundError(crew_name, config.get_crew_names())
        
        config.crews[crew_name] = crew
        self.logger.info(f"Updated crew: {crew_name}")
        return config
    
    def delete_crew(self, config: FlowConfig, crew_name: str) -> FlowConfig:
        """
        Delete a crew from configuration.
        
        Args:
            config: FlowConfig instance
            crew_name: Name of crew to delete
            
        Returns:
            Updated FlowConfig
            
        Raises:
            CrewNotFoundError: If crew doesn't exist
        """
        if crew_name not in config.crews:
            raise CrewNotFoundError(crew_name, config.get_crew_names())
        
        del config.crews[crew_name]
        self.logger.info(f"Deleted crew: {crew_name}")
        return config
    
    # ==================== AGENT OPERATIONS ====================
    
    def add_agent(self, config: FlowConfig, crew_name: str, agent: AgentConfig) -> FlowConfig:
        """
        Add an agent to a crew.
        
        Args:
            config: FlowConfig instance
            crew_name: Name of crew
            agent: AgentConfig instance
            
        Returns:
            Updated FlowConfig
            
        Raises:
            CrewNotFoundError: If crew doesn't exist
        """
        crew = config.get_crew(crew_name)
        if not crew:
            raise CrewNotFoundError(crew_name, config.get_crew_names())
        
        crew.agents.append(agent)
        self.logger.info(f"Added agent {agent.id} to crew {crew_name}")
        return config
    
    def update_agent(
        self,
        config: FlowConfig,
        crew_name: str,
        agent_id: str,
        updated_agent: AgentConfig
    ) -> FlowConfig:
        """
        Update an agent in a crew.
        
        Args:
            config: FlowConfig instance
            crew_name: Name of crew
            agent_id: ID of agent to update
            updated_agent: Updated AgentConfig
            
        Returns:
            Updated FlowConfig
            
        Raises:
            CrewNotFoundError: If crew doesn't exist
            AgentNotFoundError: If agent doesn't exist
        """
        crew = config.get_crew(crew_name)
        if not crew:
            raise CrewNotFoundError(crew_name, config.get_crew_names())
        
        for i, agent in enumerate(crew.agents):
            if agent.id == agent_id:
                crew.agents[i] = updated_agent
                self.logger.info(f"Updated agent {agent_id} in crew {crew_name}")
                return config
        
        raise AgentNotFoundError(agent_id, crew_name, crew.get_agent_ids())
    
    def delete_agent(self, config: FlowConfig, crew_name: str, agent_id: str) -> FlowConfig:
        """
        Delete an agent from a crew.
        
        Args:
            config: FlowConfig instance
            crew_name: Name of crew
            agent_id: ID of agent to delete
            
        Returns:
            Updated FlowConfig
            
        Raises:
            CrewNotFoundError: If crew doesn't exist
            AgentNotFoundError: If agent doesn't exist
        """
        crew = config.get_crew(crew_name)
        if not crew:
            raise CrewNotFoundError(crew_name, config.get_crew_names())
        
        for i, agent in enumerate(crew.agents):
            if agent.id == agent_id:
                crew.agents.pop(i)
                self.logger.info(f"Deleted agent {agent_id} from crew {crew_name}")
                return config
        
        raise AgentNotFoundError(agent_id, crew_name, crew.get_agent_ids())
    
    # ==================== TASK OPERATIONS ====================
    
    def add_task(self, config: FlowConfig, crew_name: str, task: TaskConfig) -> FlowConfig:
        """
        Add a task to a crew.
        
        Args:
            config: FlowConfig instance
            crew_name: Name of crew
            task: TaskConfig instance
            
        Returns:
            Updated FlowConfig
            
        Raises:
            CrewNotFoundError: If crew doesn't exist
        """
        crew = config.get_crew(crew_name)
        if not crew:
            raise CrewNotFoundError(crew_name, config.get_crew_names())
        
        crew.tasks.append(task)
        self.logger.info(f"Added task {task.id} to crew {crew_name}")
        return config
    
    def update_task(
        self,
        config: FlowConfig,
        crew_name: str,
        task_id: str,
        updated_task: TaskConfig
    ) -> FlowConfig:
        """
        Update a task in a crew.
        
        Args:
            config: FlowConfig instance
            crew_name: Name of crew
            task_id: ID of task to update
            updated_task: Updated TaskConfig
            
        Returns:
            Updated FlowConfig
            
        Raises:
            CrewNotFoundError: If crew doesn't exist
            TaskNotFoundError: If task doesn't exist
        """
        crew = config.get_crew(crew_name)
        if not crew:
            raise CrewNotFoundError(crew_name, config.get_crew_names())
        
        for i, task in enumerate(crew.tasks):
            if task.id == task_id:
                crew.tasks[i] = updated_task
                self.logger.info(f"Updated task {task_id} in crew {crew_name}")
                return config
        
        raise TaskNotFoundError(task_id, crew_name, crew.get_task_ids())
    
    def delete_task(self, config: FlowConfig, crew_name: str, task_id: str) -> FlowConfig:
        """
        Delete a task from a crew.
        
        Args:
            config: FlowConfig instance
            crew_name: Name of crew
            task_id: ID of task to delete
            
        Returns:
            Updated FlowConfig
            
        Raises:
            CrewNotFoundError: If crew doesn't exist
            TaskNotFoundError: If task doesn't exist
        """
        crew = config.get_crew(crew_name)
        if not crew:
            raise CrewNotFoundError(crew_name, config.get_crew_names())
        
        for i, task in enumerate(crew.tasks):
            if task.id == task_id:
                crew.tasks.pop(i)
                self.logger.info(f"Deleted task {task_id} from crew {crew_name}")
                return config
        
        raise TaskNotFoundError(task_id, crew_name, crew.get_task_ids())
    
    # ==================== STEP OPERATIONS ====================
    
    def add_step(self, config: FlowConfig, step: StepConfig) -> FlowConfig:
        """
        Add a step to flow.
        
        Args:
            config: FlowConfig instance
            step: StepConfig instance
            
        Returns:
            Updated FlowConfig
        """
        config.steps.append(step)
        self.logger.info(f"Added step: {step.id}")
        return config
    
    def update_step(self, config: FlowConfig, step_id: str, updated_step: StepConfig) -> FlowConfig:
        """
        Update a step in flow.
        
        Args:
            config: FlowConfig instance
            step_id: ID of step to update
            updated_step: Updated StepConfig
            
        Returns:
            Updated FlowConfig
            
        Raises:
            StepNotFoundError: If step doesn't exist
        """
        for i, step in enumerate(config.steps):
            if step.id == step_id:
                config.steps[i] = updated_step
                self.logger.info(f"Updated step: {step_id}")
                return config
        
        raise StepNotFoundError(step_id, config.get_step_ids())
    
    def delete_step(self, config: FlowConfig, step_id: str) -> FlowConfig:
        """
        Delete a step from flow.
        
        Args:
            config: FlowConfig instance
            step_id: ID of step to delete
            
        Returns:
            Updated FlowConfig
            
        Raises:
            StepNotFoundError: If step doesn't exist
        """
        for i, step in enumerate(config.steps):
            if step.id == step_id:
                config.steps.pop(i)
                self.logger.info(f"Deleted step: {step_id}")
                return config
        
        raise StepNotFoundError(step_id, config.get_step_ids())
    
    # ==================== CONVERSION HELPERS ====================
    
    def _dict_to_config(self, data: Dict[str, Any]) -> FlowConfig:
        """Convert dictionary to FlowConfig."""
        # Parse flow metadata
        flow_data = data.get('flow', {})
        flow = FlowMetadata(
            name=flow_data.get('name', 'Unnamed Flow'),
            description=flow_data.get('description', '')
        )
        
        # Parse defaults
        defaults_data = data.get('defaults', {}).get('llm', {})
        defaults = LLMConfig(
            provider=defaults_data.get('provider', 'google'),
            model=defaults_data.get('model'),
            temperature=defaults_data.get('temperature', 0.7),
            max_tokens=defaults_data.get('max_tokens')
        )
        
        # Parse state
        state_data = data.get('state', {})
        state = StateConfig(
            common_vars=state_data.get('common_vars', [])
        ) if state_data else None
        
        # Parse steps
        steps = []
        for step_data in data.get('steps', []):
            steps.append(StepConfig(
                id=step_data['id'],
                type=step_data.get('type', 'crew'),
                crew_ref=step_data.get('crew_ref', ''),
                is_start=step_data.get('is_start', False),
                next_step=step_data.get('next_step'),
                inputs=step_data.get('inputs', {}),
                output_to_state=step_data.get('output_to_state', '')
            ))
        
        # Parse crews
        crews = {}
        for crew_name, crew_data in data.get('crews', {}).items():
            # Parse agents
            agents = []
            for agent_data in crew_data.get('agents', []):
                agent_llm = None
                if 'llm' in agent_data:
                    agent_llm = LLMConfig(**agent_data['llm'])
                
                agents.append(AgentConfig(
                    id=agent_data['id'],
                    role=agent_data['role'],
                    goal=agent_data['goal'],
                    backstory=agent_data['backstory'],
                    tools=agent_data.get('tools', []),
                    llm=agent_llm
                ))
            
            # Parse tasks
            tasks = []
            for task_data in crew_data.get('tasks', []):
                task_llm = None
                if 'llm' in task_data:
                    task_llm = LLMConfig(**task_data['llm'])
                
                tasks.append(TaskConfig(
                    id=task_data['id'],
                    description=task_data['description'],
                    expected_output=task_data['expected_output'],
                    agent=task_data['agent'],
                    context=task_data.get('context', []),
                    output_model=task_data.get('output_model'),
                    llm=task_llm
                ))
            
            # Parse execution
            execution_data = crew_data.get('execution', {})
            execution = ExecutionConfig(
                type=execution_data.get('type', 'sequential'),
                tasks=execution_data.get('tasks', []),
                manager_agent=execution_data.get('manager_agent'),
                manager_llm=LLMConfig(**execution_data['manager_llm']) if 'manager_llm' in execution_data else None
            )
            
            # Parse crew LLM
            crew_llm = None
            if 'llm' in crew_data:
                crew_llm = LLMConfig(**crew_data['llm'])
            
            crews[crew_name] = CrewConfig(
                agents=agents,
                tasks=tasks,
                execution=execution,
                llm=crew_llm
            )
        
        return FlowConfig(
            flow=flow,
            steps=steps,
            crews=crews,
            defaults=defaults,
            state=state
        )
    
    def _config_to_dict(self, config: FlowConfig) -> Dict[str, Any]:
        """Convert FlowConfig to dictionary (for YAML export)."""
        result = {
            'flow': {
                'name': config.flow.name,
                'description': config.flow.description
            },
            'defaults': {
                'llm': self._llm_to_dict(config.defaults)
            }
        }
        
        # Add state if present
        if config.state:
            result['state'] = {
                'common_vars': config.state.common_vars
            }
        
        # Add steps
        result['steps'] = [
            {
                'id': step.id,
                'is_start': step.is_start,
                'type': step.type,
                'crew_ref': step.crew_ref,
                'next_step': step.next_step,
                'inputs': step.inputs,
                'output_to_state': step.output_to_state
            }
            for step in config.steps
        ]
        
        # Add crews
        result['crews'] = {}
        for crew_name, crew in config.crews.items():
            crew_dict = {}
            
            if crew.llm:
                crew_dict['llm'] = self._llm_to_dict(crew.llm)
            
            crew_dict['agents'] = [
                {
                    'id': agent.id,
                    'role': agent.role,
                    'goal': agent.goal,
                    'backstory': agent.backstory,
                    'tools': agent.tools,
                    **(({'llm': self._llm_to_dict(agent.llm)} if agent.llm else {}))
                }
                for agent in crew.agents
            ]
            
            crew_dict['tasks'] = [
                {
                    'id': task.id,
                    'description': task.description,
                    'expected_output': task.expected_output,
                    'agent': task.agent,
                    'context': task.context,
                    **(({'output_model': task.output_model} if task.output_model else {})),
                    **(({'llm': self._llm_to_dict(task.llm)} if task.llm else {}))
                }
                for task in crew.tasks
            ]
            
            crew_dict['execution'] = {
                'type': crew.execution.type,
                'tasks': crew.execution.tasks,
                **(({'manager_agent': crew.execution.manager_agent} if crew.execution.manager_agent else {})),
                **(({'manager_llm': self._llm_to_dict(crew.execution.manager_llm)} if crew.execution.manager_llm else {}))
            }
            
            result['crews'][crew_name] = crew_dict
        
        return result
    
    def _llm_to_dict(self, llm: LLMConfig) -> Dict[str, Any]:
        """Convert LLMConfig to dictionary."""
        result = {
            'provider': llm.provider,
            'temperature': llm.temperature,
        }
        
        if llm.model:
            result['model'] = llm.model
        
        if llm.max_tokens:
            result['max_tokens'] = llm.max_tokens
        
        return result