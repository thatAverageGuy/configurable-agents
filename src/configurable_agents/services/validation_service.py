"""
Validation Service

Provides validation services for configurations.
Wraps domain validator with service-level concerns.
"""

from typing import List, Tuple

from ..domain import (
    FlowConfig,
    CrewConfig,
    ValidationResult,
    ConfigValidator,
)
from ..config import get_logger

logger = get_logger(__name__)


class ValidationService:
    """Service for validating configurations."""
    
    def __init__(self):
        """Initialize validation service."""
        self.validator = ConfigValidator()
        self.logger = logger
    
    def validate_config(self, config: FlowConfig) -> ValidationResult:
        """
        Validate a complete flow configuration.
        
        Args:
            config: FlowConfig to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        self.logger.info(f"Validating config: {config.flow.name}")
        result = self.validator.validate(config)
        
        if result.is_valid:
            self.logger.info("✅ Configuration is valid")
        else:
            self.logger.warning(f"❌ Configuration has {len(result.errors)} error(s)")
            for error in result.errors:
                self.logger.warning(f"  - {error.message}")
        
        if result.warnings:
            self.logger.info(f"⚠️  Configuration has {len(result.warnings)} warning(s)")
            for warning in result.warnings:
                self.logger.info(f"  - {warning.message}")
        
        return result
    
    def can_delete_crew(self, config: FlowConfig, crew_name: str) -> Tuple[bool, List[str]]:
        """
        Check if a crew can be safely deleted.
        
        Args:
            config: Flow configuration
            crew_name: Name of crew to check
            
        Returns:
            Tuple of (can_delete, list_of_dependent_steps)
        """
        can_delete, dependent_steps = self.validator.can_delete_crew(config, crew_name)
        
        if can_delete:
            self.logger.info(f"✅ Crew '{crew_name}' can be safely deleted")
        else:
            self.logger.warning(
                f"❌ Crew '{crew_name}' cannot be deleted. "
                f"Dependent steps: {', '.join(dependent_steps)}"
            )
        
        return can_delete, dependent_steps
    
    def can_delete_agent(self, crew: CrewConfig, agent_id: str) -> Tuple[bool, List[str]]:
        """
        Check if an agent can be safely deleted.
        
        Args:
            crew: Crew configuration
            agent_id: ID of agent to check
            
        Returns:
            Tuple of (can_delete, list_of_dependent_tasks)
        """
        can_delete, dependent_tasks = self.validator.can_delete_agent(crew, agent_id)
        
        if can_delete:
            self.logger.info(f"✅ Agent '{agent_id}' can be safely deleted")
        else:
            self.logger.warning(
                f"❌ Agent '{agent_id}' cannot be deleted. "
                f"Dependent tasks: {', '.join(dependent_tasks)}"
            )
        
        return can_delete, dependent_tasks
    
    def can_delete_step(self, config: FlowConfig, step_id: str) -> Tuple[bool, List[str]]:
        """
        Check if a step can be safely deleted.
        
        Args:
            config: Flow configuration
            step_id: ID of step to check
            
        Returns:
            Tuple of (can_delete, list_of_dependent_steps)
        """
        can_delete, dependent_steps = self.validator.can_delete_step(config, step_id)
        
        if can_delete:
            self.logger.info(f"✅ Step '{step_id}' can be safely deleted")
        else:
            self.logger.warning(
                f"❌ Step '{step_id}' cannot be deleted. "
                f"Other steps route to it: {', '.join(dependent_steps)}"
            )
        
        return can_delete, dependent_steps
    
    def get_validation_summary(self, result: ValidationResult) -> str:
        """
        Get a formatted summary of validation results.
        
        Args:
            result: ValidationResult to summarize
            
        Returns:
            Formatted string summary
        """
        if result.is_valid:
            summary = "✅ Configuration is valid\n"
            if result.warnings:
                summary += f"\n⚠️  {len(result.warnings)} warning(s):\n"
                summary += result.format_warnings()
            return summary
        else:
            summary = f"❌ Configuration has {len(result.errors)} error(s):\n\n"
            summary += result.format_errors()
            
            if result.warnings:
                summary += f"\n\n⚠️  {len(result.warnings)} warning(s):\n"
                summary += result.format_warnings()
            
            return summary