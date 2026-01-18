"""
Domain Layer

This module contains the core domain models, validation logic, and business rules.
Models are pure Python dataclasses with no dependencies on external frameworks.
"""

from .config import (
    FlowConfig,
    StepConfig,
    CrewConfig,
    AgentConfig,
    TaskConfig,
    LLMConfig,
    ExecutionConfig,
)
from .validation import (
    ValidationResult,
    ValidationError,
    ValidationWarning,
    ConfigValidator,
)
from .exceptions import (
    ConfigValidationError,
    CrewNotFoundError,
    AgentNotFoundError,
    TaskNotFoundError,
    StepNotFoundError,
    AgentDependencyError,
    CrewDependencyError,
    StepDependencyError,
)

__all__ = [
    # Config models
    "FlowConfig",
    "StepConfig",
    "CrewConfig",
    "AgentConfig",
    "TaskConfig",
    "LLMConfig",
    "ExecutionConfig",
    # Validation
    "ValidationResult",
    "ValidationError",
    "ValidationWarning",
    "ConfigValidator",
    # Exceptions
    "ConfigValidationError",
    "CrewNotFoundError",
    "AgentNotFoundError",
    "TaskNotFoundError",
    "StepNotFoundError",
    "AgentDependencyError",
    "CrewDependencyError",
    "StepDependencyError",
]