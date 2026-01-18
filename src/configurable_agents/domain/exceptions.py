"""
Domain Exceptions

Custom exceptions for domain-specific errors.
These provide clear, actionable error messages to users.
"""

from typing import List, Optional


class ConfigurableAgentsError(Exception):
    """Base exception for all configurable agents errors."""
    
    def __init__(self, message: str, suggestion: Optional[str] = None):
        """
        Initialize exception with message and optional suggestion.
        
        Args:
            message: Error message describing what went wrong
            suggestion: Optional suggestion for how to fix the error
        """
        self.message = message
        self.suggestion = suggestion
        super().__init__(self.format_message())
    
    def format_message(self) -> str:
        """Format the complete error message."""
        if self.suggestion:
            return f"{self.message}\n💡 Suggestion: {self.suggestion}"
        return self.message


class ConfigValidationError(ConfigurableAgentsError):
    """Raised when configuration validation fails."""
    
    def __init__(self, errors: List[str]):
        """
        Initialize with a list of validation errors.
        
        Args:
            errors: List of validation error messages
        """
        self.errors = errors
        message = "Configuration validation failed:\n" + "\n".join(f"  • {e}" for e in errors)
        suggestion = "Fix the validation errors listed above before proceeding."
        super().__init__(message, suggestion)


class CrewNotFoundError(ConfigurableAgentsError):
    """Raised when a referenced crew doesn't exist."""
    
    def __init__(self, crew_name: str, available_crews: List[str]):
        """
        Initialize with crew name and available crews.
        
        Args:
            crew_name: Name of the crew that wasn't found
            available_crews: List of available crew names
        """
        self.crew_name = crew_name
        self.available_crews = available_crews
        
        message = f"Crew '{crew_name}' not found in configuration."
        if available_crews:
            suggestion = f"Available crews: {', '.join(available_crews)}"
        else:
            suggestion = "No crews defined. Add a crew first."
        
        super().__init__(message, suggestion)


class AgentNotFoundError(ConfigurableAgentsError):
    """Raised when a referenced agent doesn't exist."""
    
    def __init__(self, agent_id: str, crew_name: str, available_agents: List[str]):
        """
        Initialize with agent ID, crew name, and available agents.
        
        Args:
            agent_id: ID of the agent that wasn't found
            crew_name: Name of the crew where agent was expected
            available_agents: List of available agent IDs in the crew
        """
        self.agent_id = agent_id
        self.crew_name = crew_name
        self.available_agents = available_agents
        
        message = f"Agent '{agent_id}' not found in crew '{crew_name}'."
        if available_agents:
            suggestion = f"Available agents: {', '.join(available_agents)}"
        else:
            suggestion = f"No agents defined in crew '{crew_name}'. Add an agent first."
        
        super().__init__(message, suggestion)


class TaskNotFoundError(ConfigurableAgentsError):
    """Raised when a referenced task doesn't exist."""
    
    def __init__(self, task_id: str, crew_name: str, available_tasks: List[str]):
        """
        Initialize with task ID, crew name, and available tasks.
        
        Args:
            task_id: ID of the task that wasn't found
            crew_name: Name of the crew where task was expected
            available_tasks: List of available task IDs in the crew
        """
        self.task_id = task_id
        self.crew_name = crew_name
        self.available_tasks = available_tasks
        
        message = f"Task '{task_id}' not found in crew '{crew_name}'."
        if available_tasks:
            suggestion = f"Available tasks: {', '.join(available_tasks)}"
        else:
            suggestion = f"No tasks defined in crew '{crew_name}'. Add a task first."
        
        super().__init__(message, suggestion)


class StepNotFoundError(ConfigurableAgentsError):
    """Raised when a referenced step doesn't exist."""
    
    def __init__(self, step_id: str, available_steps: List[str]):
        """
        Initialize with step ID and available steps.
        
        Args:
            step_id: ID of the step that wasn't found
            available_steps: List of available step IDs
        """
        self.step_id = step_id
        self.available_steps = available_steps
        
        message = f"Step '{step_id}' not found in flow."
        if available_steps:
            suggestion = f"Available steps: {', '.join(available_steps)}"
        else:
            suggestion = "No steps defined. Add a step first."
        
        super().__init__(message, suggestion)


class AgentDependencyError(ConfigurableAgentsError):
    """Raised when trying to delete an agent that has dependent tasks."""
    
    def __init__(self, agent_id: str, dependent_tasks: List[str]):
        """
        Initialize with agent ID and dependent tasks.
        
        Args:
            agent_id: ID of the agent being deleted
            dependent_tasks: List of task IDs that depend on this agent
        """
        self.agent_id = agent_id
        self.dependent_tasks = dependent_tasks
        
        message = f"Cannot delete agent '{agent_id}' - it has dependent tasks."
        suggestion = (
            f"First reassign or delete these tasks: {', '.join(dependent_tasks)}"
        )
        
        super().__init__(message, suggestion)


class CrewDependencyError(ConfigurableAgentsError):
    """Raised when trying to delete a crew that has dependent steps."""
    
    def __init__(self, crew_name: str, dependent_steps: List[str]):
        """
        Initialize with crew name and dependent steps.
        
        Args:
            crew_name: Name of the crew being deleted
            dependent_steps: List of step IDs that reference this crew
        """
        self.crew_name = crew_name
        self.dependent_steps = dependent_steps
        
        message = f"Cannot delete crew '{crew_name}' - it has dependent steps."
        suggestion = (
            f"First reassign or delete these steps: {', '.join(dependent_steps)}"
        )
        
        super().__init__(message, suggestion)


class StepDependencyError(ConfigurableAgentsError):
    """Raised when trying to delete a step that has dependent steps."""
    
    def __init__(self, step_id: str, dependent_steps: List[str]):
        """
        Initialize with step ID and dependent steps.
        
        Args:
            step_id: ID of the step being deleted
            dependent_steps: List of step IDs that route to this step
        """
        self.step_id = step_id
        self.dependent_steps = dependent_steps
        
        message = f"Cannot delete step '{step_id}' - other steps route to it."
        suggestion = (
            f"First update routing for these steps: {', '.join(dependent_steps)}"
        )
        
        super().__init__(message, suggestion)


class ExecutionError(ConfigurableAgentsError):
    """Raised when flow execution fails."""
    
    def __init__(self, step_id: str, original_error: Exception):
        """
        Initialize with step ID and original error.
        
        Args:
            step_id: ID of the step where execution failed
            original_error: The original exception that was raised
        """
        self.step_id = step_id
        self.original_error = original_error
        
        message = f"Execution failed at step '{step_id}': {str(original_error)}"
        suggestion = "Check the logs for detailed error information."
        
        super().__init__(message, suggestion)


class InvalidYAMLError(ConfigurableAgentsError):
    """Raised when YAML parsing fails."""
    
    def __init__(self, file_path: str, yaml_error: Exception):
        """
        Initialize with file path and YAML parsing error.
        
        Args:
            file_path: Path to the YAML file
            yaml_error: The YAML parsing exception
        """
        self.file_path = file_path
        self.yaml_error = yaml_error
        
        message = f"Failed to parse YAML file '{file_path}': {str(yaml_error)}"
        suggestion = "Check for YAML syntax errors (indentation, colons, quotes)."
        
        super().__init__(message, suggestion)