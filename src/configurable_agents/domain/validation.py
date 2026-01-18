"""
Configuration Validation

Comprehensive validation logic for flow configurations.
Validates structural integrity, dependencies, and business rules.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

from .config import FlowConfig, CrewConfig, StepConfig
from .exceptions import ConfigValidationError


class ErrorType(Enum):
    """Types of validation errors."""
    
    MISSING_START = "missing_start"
    MULTIPLE_STARTS = "multiple_starts"
    BROKEN_REFERENCE = "broken_reference"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    MISSING_ASSIGNMENT = "missing_assignment"
    INVALID_VALUE = "invalid_value"


@dataclass
class ValidationError:
    """A single validation error with context."""
    
    type: ErrorType
    message: str
    location: str  # e.g., "steps.research_topic", "crews.writer.agents[0]"
    suggestion: str
    
    def format(self) -> str:
        """Format error for display."""
        return f"❌ {self.message}\n   Location: {self.location}\n   💡 {self.suggestion}"


@dataclass
class ValidationWarning:
    """A validation warning (non-blocking)."""
    
    message: str
    location: str
    suggestion: str
    
    def format(self) -> str:
        """Format warning for display."""
        return f"⚠️  {self.message}\n   Location: {self.location}\n   💡 {self.suggestion}"


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    
    def add_error(self, error: ValidationError) -> None:
        """Add an error and mark as invalid."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: ValidationWarning) -> None:
        """Add a warning (doesn't affect validity)."""
        self.warnings.append(warning)
    
    def format_errors(self) -> str:
        """Format all errors for display."""
        if not self.errors:
            return "✅ No errors found"
        
        return "\n\n".join(error.format() for error in self.errors)
    
    def format_warnings(self) -> str:
        """Format all warnings for display."""
        if not self.warnings:
            return ""
        
        return "\n\n".join(warning.format() for warning in self.warnings)


class ConfigValidator:
    """Validates flow configurations comprehensively."""
    
    def validate(self, config: FlowConfig) -> ValidationResult:
        """
        Validate complete configuration.
        
        Args:
            config: Flow configuration to validate
            
        Returns:
            ValidationResult with all errors and warnings
        """
        result = ValidationResult(is_valid=True)
        
        # Validate steps
        self._validate_steps(config, result)
        
        # Validate crews
        self._validate_crews(config, result)
        
        # Validate cross-references
        self._validate_references(config, result)
        
        # Validate routing
        self._validate_routing(config, result)
        
        return result
    
    def _validate_steps(self, config: FlowConfig, result: ValidationResult) -> None:
        """Validate step configuration."""
        if not config.steps:
            result.add_error(ValidationError(
                type=ErrorType.MISSING_ASSIGNMENT,
                message="No steps defined in flow",
                location="steps",
                suggestion="Add at least one step to the flow"
            ))
            return
        
        # Check for exactly one start step
        start_steps = [s for s in config.steps if s.is_start]
        
        if len(start_steps) == 0:
            result.add_error(ValidationError(
                type=ErrorType.MISSING_START,
                message="No step marked as start step",
                location="steps",
                suggestion="Add 'is_start: true' to exactly one step"
            ))
        elif len(start_steps) > 1:
            step_ids = [s.id for s in start_steps]
            result.add_error(ValidationError(
                type=ErrorType.MULTIPLE_STARTS,
                message=f"Multiple start steps found: {', '.join(step_ids)}",
                location="steps",
                suggestion="Only one step can have 'is_start: true'"
            ))
        
        # Validate individual steps
        for step in config.steps:
            if not step.crew_ref:
                result.add_error(ValidationError(
                    type=ErrorType.MISSING_ASSIGNMENT,
                    message=f"Step '{step.id}' has no crew assigned",
                    location=f"steps.{step.id}",
                    suggestion="Set 'crew_ref' to a valid crew name"
                ))
    
    def _validate_crews(self, config: FlowConfig, result: ValidationResult) -> None:
        """Validate crew configurations."""
        if not config.crews:
            result.add_error(ValidationError(
                type=ErrorType.MISSING_ASSIGNMENT,
                message="No crews defined in configuration",
                location="crews",
                suggestion="Add at least one crew"
            ))
            return
        
        for crew_name, crew in config.crews.items():
            # Check for agents
            if not crew.agents:
                result.add_warning(ValidationWarning(
                    message=f"Crew '{crew_name}' has no agents",
                    location=f"crews.{crew_name}",
                    suggestion="Add at least one agent to this crew"
                ))
            
            # Check for tasks
            if not crew.tasks:
                result.add_warning(ValidationWarning(
                    message=f"Crew '{crew_name}' has no tasks",
                    location=f"crews.{crew_name}",
                    suggestion="Add at least one task to this crew"
                ))
            
            # Validate tasks reference valid agents
            agent_ids = crew.get_agent_ids()
            for task in crew.tasks:
                if task.agent not in agent_ids:
                    result.add_error(ValidationError(
                        type=ErrorType.BROKEN_REFERENCE,
                        message=f"Task '{task.id}' references non-existent agent '{task.agent}'",
                        location=f"crews.{crew_name}.tasks.{task.id}",
                        suggestion=f"Change 'agent' to one of: {', '.join(agent_ids)}" if agent_ids else "Add an agent first"
                    ))
            
            # Validate context references
            task_ids = crew.get_task_ids()
            for task in crew.tasks:
                for context_task_id in task.context:
                    if context_task_id not in task_ids:
                        result.add_error(ValidationError(
                            type=ErrorType.BROKEN_REFERENCE,
                            message=f"Task '{task.id}' context references non-existent task '{context_task_id}'",
                            location=f"crews.{crew_name}.tasks.{task.id}",
                            suggestion=f"Remove '{context_task_id}' from context or add this task"
                        ))
    
    def _validate_references(self, config: FlowConfig, result: ValidationResult) -> None:
        """Validate cross-references between entities."""
        crew_names = config.get_crew_names()
        step_ids = config.get_step_ids()
        
        # Validate step → crew references
        for step in config.steps:
            if step.crew_ref and step.crew_ref not in crew_names:
                result.add_error(ValidationError(
                    type=ErrorType.BROKEN_REFERENCE,
                    message=f"Step '{step.id}' references non-existent crew '{step.crew_ref}'",
                    location=f"steps.{step.id}",
                    suggestion=f"Change 'crew_ref' to one of: {', '.join(crew_names)}" if crew_names else "Add a crew first"
                ))
    
    def _validate_routing(self, config: FlowConfig, result: ValidationResult) -> None:
        """Validate step routing and check for cycles."""
        step_ids = config.get_step_ids()
        
        # Validate next_step references
        for step in config.steps:
            if step.next_step and step.next_step not in step_ids:
                result.add_error(ValidationError(
                    type=ErrorType.BROKEN_REFERENCE,
                    message=f"Step '{step.id}' routes to non-existent step '{step.next_step}'",
                    location=f"steps.{step.id}",
                    suggestion=f"Change 'next_step' to one of: {', '.join(step_ids)} or set to null for end of flow"
                ))
        
        # Check for circular dependencies
        start_step = config.get_start_step()
        if start_step:
            visited = set()
            path = []
            
            if self._has_cycle(config, start_step.id, visited, path):
                cycle_path = " → ".join(path)
                result.add_error(ValidationError(
                    type=ErrorType.CIRCULAR_DEPENDENCY,
                    message=f"Circular dependency detected: {cycle_path}",
                    location="steps",
                    suggestion="Remove circular routing by changing 'next_step' values"
                ))
    
    def _has_cycle(
        self,
        config: FlowConfig,
        current_id: str,
        visited: set,
        path: List[str]
    ) -> bool:
        """
        Check for cycles in step routing using DFS.
        
        Args:
            config: Flow configuration
            current_id: Current step ID
            visited: Set of visited step IDs
            path: Current path for cycle detection
            
        Returns:
            True if cycle detected, False otherwise
        """
        if current_id in path:
            path.append(current_id)
            return True
        
        if current_id in visited:
            return False
        
        visited.add(current_id)
        path.append(current_id)
        
        step = config.get_step(current_id)
        if step and step.next_step:
            if self._has_cycle(config, step.next_step, visited, path):
                return True
        
        path.pop()
        return False
    
    def can_delete_crew(
        self,
        config: FlowConfig,
        crew_name: str
    ) -> tuple[bool, List[str]]:
        """
        Check if a crew can be safely deleted.
        
        Args:
            config: Flow configuration
            crew_name: Name of crew to delete
            
        Returns:
            Tuple of (can_delete, list_of_dependent_steps)
        """
        dependent_steps = []
        
        for step in config.steps:
            if step.crew_ref == crew_name:
                dependent_steps.append(step.id)
        
        can_delete = len(dependent_steps) == 0
        return can_delete, dependent_steps
    
    def can_delete_agent(
        self,
        crew: CrewConfig,
        agent_id: str
    ) -> tuple[bool, List[str]]:
        """
        Check if an agent can be safely deleted.
        
        Args:
            crew: Crew configuration
            agent_id: ID of agent to delete
            
        Returns:
            Tuple of (can_delete, list_of_dependent_tasks)
        """
        dependent_tasks = []
        
        for task in crew.tasks:
            if task.agent == agent_id:
                dependent_tasks.append(task.id)
        
        can_delete = len(dependent_tasks) == 0
        return can_delete, dependent_tasks
    
    def can_delete_step(
        self,
        config: FlowConfig,
        step_id: str
    ) -> tuple[bool, List[str]]:
        """
        Check if a step can be safely deleted.
        
        Args:
            config: Flow configuration
            step_id: ID of step to delete
            
        Returns:
            Tuple of (can_delete, list_of_dependent_steps)
        """
        dependent_steps = []
        
        for step in config.steps:
            if step.next_step == step_id:
                dependent_steps.append(step.id)
        
        can_delete = len(dependent_steps) == 0
        return can_delete, dependent_steps