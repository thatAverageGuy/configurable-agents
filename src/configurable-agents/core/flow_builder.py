"""
Flow Builder Module

This module dynamically creates CrewAI Flow classes from YAML configuration.
It handles flow construction, method creation, decorator application, and routing logic.
"""

from typing import Type, Dict, Any, Callable, Optional, List
from pydantic import BaseModel, Field
from crewai.flow.flow import Flow, start, listen, router


def build_flow_class(config: dict) -> Type[Flow]:
    """
    Build a dynamic Flow class from configuration.
    
    Args:
        config: Complete flow configuration dictionary
        
    Returns:
        Dynamically created Flow class ready for instantiation
    """
    # TODO: validate_config_schema(config)
    
    # Extract configuration sections
    flow_config = config.get('flow', {})
    state_config = config.get('state', {})
    steps_config = config.get('steps', [])
    crews_config = config.get('crews', {})
    
    # Create the state class
    StateClass = _create_state_class(state_config)
    
    # Build all flow methods (step methods + router methods)
    methods = _build_flow_methods(steps_config, crews_config)
    
    # Apply decorators to methods
    _apply_decorators(methods, steps_config)
    
    # Create the Flow class dynamically
    flow_class_name = flow_config.get('name', 'DynamicFlow').replace(' ', '_').replace('-', '_')
    
    # Build class attributes
    class_attrs = {
        '__module__': __name__,
        '__doc__': flow_config.get('description', 'Dynamically generated flow'),
        'crews_config': crews_config,
        'steps_config': steps_config,
        **methods
    }
    
    # Create the Flow class using type()
    DynamicFlowClass = type(
        flow_class_name,
        (Flow[StateClass],),
        class_attrs
    )
    
    return DynamicFlowClass


def _create_state_class(state_config: dict) -> Type[BaseModel]:
    """
    Create a Pydantic BaseModel for flow state.
    
    Args:
        state_config: State configuration from YAML
        
    Returns:
        Pydantic BaseModel class for state management
    """
    common_vars = state_config.get('common_vars', [])
    
    # Build field definitions
    fields = {}
    
    # Add common variables
    if 'execution_id' in common_vars:
        fields['execution_id'] = (str, Field(default=''))
    if 'execution_status' in common_vars:
        fields['execution_status'] = (str, Field(default=''))
    if 'execution_message' in common_vars:
        fields['execution_message'] = (str, Field(default=''))
    if 'timestamp' in common_vars:
        fields['timestamp'] = (str, Field(default=''))
    if 'current_step' in common_vars:
        fields['current_step'] = (str, Field(default=''))
    
    # Add custom_var as a dictionary
    # ALWAYS add custom_var - it's the runtime data dictionary
    fields['custom_var'] = (Dict[str, Any], Field(default_factory=dict))
    
    # Create the state class dynamically
    StateClass = type(
        'FlowState',
        (BaseModel,),
        {
            '__annotations__': {k: v[0] for k, v in fields.items()},
            **{k: v[1] for k, v in fields.items()}
        }
    )
    
    return StateClass


def _build_flow_methods(steps_config: List[dict], crews_config: dict) -> Dict[str, Callable]:
    """
    Build all flow methods (step execution + routers) from configuration.
    
    Args:
        steps_config: List of step configurations
        crews_config: Dictionary of crew configurations
        
    Returns:
        Dictionary of method names to method functions
    """
    methods = {}
    
    # Find the starting step
    start_step = None
    for step in steps_config:
        if step.get('is_start', False):
            start_step = step
            break
    
    if not start_step:
        raise ValueError("No step marked with 'is_start: true' found in configuration")
    
    # Build method chain starting from start_step
    current_step = start_step
    processed_steps = set()
    
    while current_step:
        step_id = current_step['id']
        
        # Avoid infinite loops
        if step_id in processed_steps:
            raise ValueError(f"Circular reference detected in flow steps: {step_id}")
        processed_steps.add(step_id)
        
        # Create step execution method
        step_method = _create_step_method(current_step, crews_config, steps_config)
        methods[step_id] = step_method
        
        # Create router method for this step
        router_method = _create_router_method(step_id, steps_config)
        methods[f"route_after_{step_id}"] = router_method
        
        # Move to next step
        next_step_id = current_step.get('next_step')
        if next_step_id is None:
            break
        
        # Find next step in config
        current_step = None
        for step in steps_config:
            if step['id'] == next_step_id:
                current_step = step
                break
        
        if current_step is None and next_step_id is not None:
            raise ValueError(f"Next step '{next_step_id}' not found in configuration")
    
    return methods


def _create_step_method(step_config: dict, crews_config: dict, steps_config: list) -> Callable:
    """
    Create a step execution method.
    
    Args:
        step_config: Step configuration
        crews_config: All crews configuration
        steps_config: All steps configuration (for context)
        
    Returns:
        Method function that executes the step
    """
    step_id = step_config['id']
    step_type = step_config.get('type', 'crew')
    crew_ref = step_config.get('crew_ref')
    inputs = step_config.get('inputs', {})
    output_to_state = step_config.get('output_to_state', '')
    
    def step_method(self):
        """Dynamically generated step method"""
        from core.crew_builder import build_crew
        from core.utils import resolve_template
        
        print(f"[Flow] Executing step: {step_id}")
        
        # Update current step in state
        self.state.current_step = step_id
        
        if step_type == 'crew':
            # Get crew configuration
            if crew_ref not in crews_config:
                raise ValueError(f"Crew '{crew_ref}' not found in configuration")
            
            crew_config = crews_config[crew_ref]
            
            # Resolve input templates from state
            resolved_inputs = {}
            for key, value in inputs.items():
                resolved_inputs[key] = resolve_template(value, self.state)
            
            # Build and execute crew
            crew = build_crew(crew_config, resolved_inputs)
            result = crew.kickoff(inputs=resolved_inputs)
            
            # Store output in state
            if output_to_state:
                _set_nested_state(self.state, output_to_state, result.raw)
            
            print(f"[Flow] Step '{step_id}' completed successfully")
            
        else:
            raise ValueError(f"Unsupported step type: {step_type}")
    
    # Set method name and docstring
    step_method.__name__ = step_id
    step_method.__doc__ = f"Execute step: {step_id}"
    
    return step_method


def _create_router_method(step_id: str, steps_config: list) -> Callable:
    """
    Create a router method for a step.
    
    Args:
        step_id: ID of the step this router follows
        steps_config: All steps configuration
        
    Returns:
        Router method function
    """
    def router_method(self):
        """Dynamically generated router method"""
        next_step = get_next_step(step_id, steps_config)
        print(f"[Flow] Routing from '{step_id}' to '{next_step}'")
        return next_step
    
    # Set method name
    router_method.__name__ = f"route_after_{step_id}"
    router_method.__doc__ = f"Route after step: {step_id}"
    
    return router_method


def _apply_decorators(methods: Dict[str, Callable], steps_config: List[dict]) -> None:
    """
    Apply decorators to flow methods.
    
    Args:
        methods: Dictionary of method names to method functions
        steps_config: List of step configurations
    """
    # Find start step
    start_step_id = None
    for step in steps_config:
        if step.get('is_start', False):
            start_step_id = step['id']
            break
    
    # Build execution chain
    current_step_id = start_step_id
    previous_step_id = None
    processed = set()
    
    while current_step_id:
        if current_step_id in processed:
            break
        processed.add(current_step_id)
        
        step_method = methods[current_step_id]
        router_method = methods[f"route_after_{current_step_id}"]
        
        # Apply appropriate decorator to step method
        if current_step_id == start_step_id:
            # First step gets @start()
            methods[current_step_id] = start()(step_method)
        else:
            # Subsequent steps get @listen(previous_step)
            if previous_step_id:
                methods[current_step_id] = listen(previous_step_id)(step_method)
        
        # Apply @router decorator to router method
        methods[f"route_after_{current_step_id}"] = router(step_method)(router_method)
        
        # Move to next step
        previous_step_id = current_step_id
        for step in steps_config:
            if step['id'] == current_step_id:
                current_step_id = step.get('next_step')
                break


def get_next_step(current_step_id: str, steps_config: List[dict]) -> Optional[str]:
    """
    Get the next step ID from configuration.
    
    Args:
        current_step_id: ID of the current step
        steps_config: List of step configurations
        
    Returns:
        Next step ID or None if end of flow
    """
    for step in steps_config:
        if step['id'] == current_step_id:
            return step.get('next_step')
    
    return None


def _set_nested_state(state: BaseModel, path: str, value: Any) -> None:
    """
    Set a value in nested state using dot notation.
    
    Example: "state.custom_var.research_report" sets state.custom_var['research_report']
    
    Args:
        state: State object
        path: Dot-separated path (e.g., "state.custom_var.key")
        value: Value to set
    """
    parts = path.split('.')
    
    # Remove 'state' prefix if present
    if parts[0] == 'state':
        parts = parts[1:]
    
    # Navigate to the target
    current = state
    for i, part in enumerate(parts[:-1]):
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict):
            if part not in current:
                current[part] = {}
            current = current[part]
        else:
            raise ValueError(f"Cannot navigate to '{part}' in path '{path}'")
    
    # Set the final value
    final_key = parts[-1]
    if isinstance(current, dict):
        current[final_key] = value
    elif hasattr(current, final_key):
        setattr(current, final_key, value)
    else:
        raise ValueError(f"Cannot set '{final_key}' in path '{path}'")