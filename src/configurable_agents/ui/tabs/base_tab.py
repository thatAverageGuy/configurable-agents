"""
Base Tab Interface

Abstract base class for all tab components.
Provides plugin architecture for easy extensibility.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import gradio as gr

from ...services import ConfigService, ValidationService, ExecutionService, StateService
from ...config import get_logger


class BaseTab(ABC):
    """
    Abstract base class for tab components.
    
    All tabs inherit from this and implement the render() method.
    Services are injected for clean dependency management.
    """
    
    def __init__(
        self,
        config_service: ConfigService,
        validation_service: ValidationService,
        execution_service: ExecutionService,
        state_service: StateService
    ):
        """
        Initialize tab with service dependencies.
        
        Args:
            config_service: Service for config operations
            validation_service: Service for validation
            execution_service: Service for flow execution
            state_service: Service for state management
        """
        self.config_service = config_service
        self.validation_service = validation_service
        self.execution_service = execution_service
        self.state_service = state_service
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    def render(self) -> None:
        """
        Render the tab content.
        
        This method should create all Gradio components for the tab.
        Called during app initialization.
        """
        pass
    
    def get_current_config(self):
        """
        Get the current configuration from state.
        
        Returns:
            FlowConfig instance or None
        """
        return self.state_service.get('current_config')
    
    def set_current_config(self, config) -> None:
        """
        Update the current configuration in state.
        
        Args:
            config: FlowConfig instance
        """
        self.state_service.set('current_config', config)
        self.logger.info(f"Config updated: {config.flow.name}")
    
    def show_error(self, message: str) -> str:
        """
        Format an error message for display.
        
        Args:
            message: Error message
            
        Returns:
            Formatted HTML error
        """
        return f'<div style="color: red; padding: 10px; border: 1px solid red; border-radius: 5px;">❌ {message}</div>'
    
    def show_success(self, message: str) -> str:
        """
        Format a success message for display.
        
        Args:
            message: Success message
            
        Returns:
            Formatted HTML success
        """
        return f'<div style="color: green; padding: 10px; border: 1px solid green; border-radius: 5px;">✅ {message}</div>'
    
    def show_warning(self, message: str) -> str:
        """
        Format a warning message for display.
        
        Args:
            message: Warning message
            
        Returns:
            Formatted HTML warning
        """
        return f'<div style="color: orange; padding: 10px; border: 1px solid orange; border-radius: 5px;">⚠️ {message}</div>'
    
    def show_info(self, message: str) -> str:
        """
        Format an info message for display.
        
        Args:
            message: Info message
            
        Returns:
            Formatted HTML info
        """
        return f'<div style="color: blue; padding: 10px; border: 1px solid blue; border-radius: 5px;">ℹ️ {message}</div>'