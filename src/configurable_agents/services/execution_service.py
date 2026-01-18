"""
Execution Service

Handles flow execution and result management.
Wraps the core execution engine with service-level concerns.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from ..domain import FlowConfig, ExecutionError
from ..config import get_logger
from ..core.flow_builder import build_flow_class

logger = get_logger(__name__)


@dataclass
class FlowResult:
    """Result of flow execution."""
    
    execution_id: str
    status: str  # 'success', 'error', 'running'
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    output: Optional[Any] = None
    error: Optional[str] = None
    state: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'execution_id': self.execution_id,
            'status': self.status,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_seconds': self.duration_seconds,
            'output': self.output,
            'error': self.error,
            'state': self.state
        }


class ExecutionService:
    """Service for executing flows."""
    
    def __init__(self):
        """Initialize execution service."""
        self.logger = logger
    
    def execute_flow(
        self,
        config: FlowConfig,
        inputs: Dict[str, Any],
        execution_id: Optional[str] = None
    ) -> FlowResult:
        """
        Execute a flow from configuration.
        
        Args:
            config: Flow configuration
            inputs: Initial inputs for the flow
            execution_id: Optional execution ID (generates one if not provided)
            
        Returns:
            FlowResult with execution details
        """
        # Generate execution ID if not provided
        if not execution_id:
            execution_id = str(uuid4())
        
        start_time = datetime.now()
        start_time_iso = start_time.isoformat()
        
        self.logger.info(f"Starting flow execution: {execution_id}")
        self.logger.info(f"Flow: {config.flow.name}")
        self.logger.info(f"Inputs: {inputs}")
        
        try:
            # Convert FlowConfig to dict format expected by build_flow_class
            config_dict = self._config_to_execution_dict(config)
            
            # Build the Flow class
            FlowClass = build_flow_class(config_dict)
            
            # Instantiate flow
            flow_instance = FlowClass()
            
            # Initialize state
            flow_instance.state.execution_id = execution_id
            flow_instance.state.timestamp = start_time_iso
            flow_instance.state.execution_status = "running"
            flow_instance.state.execution_message = ""
            
            # Set initial inputs in custom_var
            if inputs:
                flow_instance.state.custom_var.update(inputs)
            
            # Execute flow
            self.logger.info(f"Executing flow...")
            result = flow_instance.kickoff()
            
            # Calculate duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Extract final state
            final_state = flow_instance.state.dict() if hasattr(flow_instance.state, 'dict') else {}
            
            self.logger.info(f"Flow completed successfully in {duration:.2f}s")
            
            return FlowResult(
                execution_id=execution_id,
                status='success',
                start_time=start_time_iso,
                end_time=end_time.isoformat(),
                duration_seconds=duration,
                output=result.raw if hasattr(result, 'raw') else result,
                state=final_state
            )
            
        except ExecutionError as e:
            # Already wrapped - just handle it
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Flow execution failed at step '{e.step_id}': {e.original_error}", exc_info=True)
            
            return FlowResult(
                execution_id=execution_id,
                status='error',
                start_time=start_time_iso,
                end_time=end_time.isoformat(),
                duration_seconds=duration,
                error=str(e)
            )
            
        except Exception as e:
            # Generic error - try to determine step from state
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Try to get current step from state
            step_id = "unknown"
            try:
                if 'flow_instance' in locals():
                    step_id = getattr(flow_instance.state, 'current_step', 'unknown')
            except:
                pass
            
            self.logger.error(f"Flow execution failed: {e}", exc_info=True)
            
            # Wrap in ExecutionError for consistency
            execution_error = ExecutionError(step_id, e)
            
            return FlowResult(
                execution_id=execution_id,
                status='error',
                start_time=start_time_iso,
                end_time=end_time.isoformat(),
                duration_seconds=duration,
                error=str(execution_error)
            )
        
    def dry_run(self, config: FlowConfig) -> Dict[str, Any]:
        """
        Perform a dry run of the flow (validate without executing).
        
        Args:
            config: Flow configuration
            
        Returns:
            Dictionary with dry run results
        """
        self.logger.info("Performing dry run...")
        
        try:
            # Convert to execution dict
            config_dict = self._config_to_execution_dict(config)
            
            # Try to build Flow class (validates structure)
            FlowClass = build_flow_class(config_dict)
            
            # Instantiate (validates state)
            flow_instance = FlowClass()
            
            # Get execution plan
            steps = config.steps
            start_step = config.get_start_step()
            
            execution_plan = []
            current_step = start_step
            visited = set()
            
            while current_step and current_step.id not in visited:
                visited.add(current_step.id)
                execution_plan.append({
                    'step_id': current_step.id,
                    'crew': current_step.crew_ref,
                    'type': current_step.type
                })
                
                # Get next step
                if current_step.next_step:
                    current_step = config.get_step(current_step.next_step)
                else:
                    break
            
            self.logger.info("Dry run successful")
            
            return {
                'status': 'valid',
                'flow_name': config.flow.name,
                'total_steps': len(steps),
                'execution_plan': execution_plan,
                'total_agents': config.count_agents(),
                'total_tasks': config.count_tasks()
            }
            
        except Exception as e:
            self.logger.error(f"Dry run failed: {e}")
            return {
                'status': 'invalid',
                'error': str(e)
            }
    
    def _config_to_execution_dict(self, config: FlowConfig) -> Dict[str, Any]:
        """
        Convert FlowConfig to dict format expected by build_flow_class.
        
        Args:
            config: FlowConfig instance
            
        Returns:
            Dictionary in the format expected by core execution engine
        """
        result = {
            'flow': {
                'name': config.flow.name,
                'description': config.flow.description
            },
            'defaults': {
                'llm': {
                    'provider': config.defaults.provider,
                    'temperature': config.defaults.temperature,
                }
            }
        }
        
        if config.defaults.model:
            result['defaults']['llm']['model'] = config.defaults.model
        if config.defaults.max_tokens:
            result['defaults']['llm']['max_tokens'] = config.defaults.max_tokens
        
        # Add state
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
                crew_dict['llm'] = {
                    'temperature': crew.llm.temperature,
                }
                if crew.llm.model:
                    crew_dict['llm']['model'] = crew.llm.model
                if crew.llm.max_tokens:
                    crew_dict['llm']['max_tokens'] = crew.llm.max_tokens
            
            crew_dict['agents'] = []
            for agent in crew.agents:
                agent_dict = {
                    'id': agent.id,
                    'role': agent.role,
                    'goal': agent.goal,
                    'backstory': agent.backstory,
                    'tools': agent.tools,
                }
                if agent.llm:
                    agent_dict['llm'] = {
                        'temperature': agent.llm.temperature,
                    }
                    if agent.llm.model:
                        agent_dict['llm']['model'] = agent.llm.model
                crew_dict['agents'].append(agent_dict)
            
            crew_dict['tasks'] = []
            for task in crew.tasks:
                task_dict = {
                    'id': task.id,
                    'description': task.description,
                    'expected_output': task.expected_output,
                    'agent': task.agent,
                }
                if task.context:
                    task_dict['context'] = task.context
                if task.output_model:
                    task_dict['output_model'] = task.output_model
                if task.llm:
                    task_dict['llm'] = {
                        'temperature': task.llm.temperature,
                    }
                    if task.llm.model:
                        task_dict['llm']['model'] = task.llm.model
                crew_dict['tasks'].append(task_dict)
            
            crew_dict['execution'] = {
                'type': crew.execution.type,
                'tasks': crew.execution.tasks,
            }
            if crew.execution.manager_agent:
                crew_dict['execution']['manager_agent'] = crew.execution.manager_agent
            if crew.execution.manager_llm:
                crew_dict['execution']['manager_llm'] = {
                    'temperature': crew.execution.manager_llm.temperature,
                }
                if crew.execution.manager_llm.model:
                    crew_dict['execution']['manager_llm']['model'] = crew.execution.manager_llm.model
            
            result['crews'][crew_name] = crew_dict
        
        return result