"""
Base Tab Interface

Abstract base class for all tab components with comprehensive error handling.
Provides plugin architecture for easy extensibility.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
import gradio as gr

from ...services import ConfigService, ValidationService, ExecutionService, StateService
from ...config import get_logger
from ..error_handler import (
    ui_error_handler,
    track_performance,
    ErrorRecovery,
    format_error_for_display,
    format_success_for_display,
    format_warning_for_display,
    format_info_for_display
)
from ..utils import UIFeedback, LoadingState, DebugMode


class BaseTab(ABC):
    """
    Abstract base class for tab components with error handling.
    
    All tabs inherit from this and implement the render() method.
    Services are injected for clean dependency management.
    
    Features:
    - Automatic error handling with decorators
    - Performance tracking
    - User feedback mechanisms (toasts)
    - Loading state management
    - Debug mode support
    - Smart error recovery suggestions
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
        
        # Track if tab has been rendered
        self._rendered = False
        
        self.logger.info(f"Initialized {self.__class__.__name__}")
    
    @abstractmethod
    def render(self) -> None:
        """
        Render the tab content.
        
        This method should create all Gradio components for the tab.
        Called during app initialization.
        
        Must be implemented by all subclasses.
        """
        pass
    
    def safe_render(self) -> None:
        """
        Safely render the tab with error handling.
        
        Wraps the render() method to catch any exceptions during rendering.
        If rendering fails, displays error message in the tab.
        """
        try:
            self.render()
            self._rendered = True
            self.logger.info(f"Rendered {self.__class__.__name__} successfully")
        except Exception as e:
            self.logger.error(f"Failed to render {self.__class__.__name__}: {e}", exc_info=True)
            
            # Show error in UI
            with gr.Column():
                gr.Markdown(f"## ❌ Error Rendering {self.__class__.__name__}")
                gr.HTML(format_error_for_display(
                    f"Failed to render tab: {str(e)}\n\n"
                    f"{ErrorRecovery.get_suggestion(e)}"
                ))
    
    # ========== State Management (Enhanced) ==========
    
    @ui_error_handler("Failed to get configuration")
    def get_current_config(self):
        """
        Get the current configuration from state with error handling.
        
        Returns:
            FlowConfig instance or None if not found
            
        Note:
            Errors are automatically logged and handled by decorator.
        """
        config = self.state_service.get('current_config')
        
        if config is None:
            self.logger.debug("No config in state")
        else:
            self.logger.debug(f"Retrieved config: {config.flow.name}")
        
        return config
    
    @ui_error_handler("Failed to save configuration")
    def set_current_config(self, config) -> None:
        """
        Update the current configuration in state with error handling.
        
        Args:
            config: FlowConfig instance to store
            
        Note:
            Shows success toast notification to user.
            Errors are automatically logged and handled by decorator.
        """
        if config is None:
            self.logger.warning("Attempted to set None config")
            return
        
        self.state_service.set('current_config', config)
        self.logger.info(f"Config updated: {config.flow.name}")
        
        # Show success notification to user
        UIFeedback.success(f"Configuration loaded: {config.flow.name}")
    
    # ========== Message Formatting (Enhanced) ==========
    
    def show_error(self, message: str, include_suggestion: bool = True) -> str:
        """
        Format an error message for display with optional recovery suggestion.
        
        Args:
            message: Error message to display
            include_suggestion: Whether to include recovery suggestion (default: True)
            
        Returns:
            Formatted HTML error message
            
        Note:
            Recovery suggestions are context-aware based on error type.
        """
        if DebugMode.is_enabled():
            self.logger.debug(f"Showing error: {message}")
        
        full_message = message
        
        # Add smart recovery suggestion
        if include_suggestion:
            try:
                # Create exception from message for suggestion
                exception = Exception(message)
                suggestion = ErrorRecovery.get_suggestion(exception)
                full_message = f"{message}\n\n{suggestion}"
            except Exception as e:
                # Fallback if suggestion generation fails
                self.logger.debug(f"Could not generate suggestion: {e}")
        
        return format_error_for_display(full_message)
    
    def show_success(self, message: str) -> str:
        """
        Format a success message for display.
        
        Args:
            message: Success message
            
        Returns:
            Formatted HTML success message
        """
        if DebugMode.is_enabled():
            self.logger.debug(f"Showing success: {message}")
        
        return format_success_for_display(message)
    
    def show_warning(self, message: str) -> str:
        """
        Format a warning message for display.
        
        Args:
            message: Warning message
            
        Returns:
            Formatted HTML warning message
        """
        if DebugMode.is_enabled():
            self.logger.debug(f"Showing warning: {message}")
        
        return format_warning_for_display(message)
    
    def show_info(self, message: str) -> str:
        """
        Format an info message for display.
        
        Args:
            message: Info message
            
        Returns:
            Formatted HTML info message
        """
        if DebugMode.is_enabled():
            self.logger.debug(f"Showing info: {message}")
        
        return format_info_for_display(message)
    
    # ========== Helper Methods (New in Step 5) ==========
    
    def with_loading(self, message: str = "Loading..."):
        """
        Context manager for showing loading state.
        
        Args:
            message: Loading message to display
            
        Returns:
            LoadingState context manager
            
        Example:
            ```python
            with self.with_loading("Loading config..."):
                config = self.config_service.load_from_file(path)
            ```
        """
        return LoadingState(message)
    
    def track_action(self, action_name: str):
        """
        Decorator to track performance of an action.
        
        Args:
            action_name: Name of the action for logging
            
        Returns:
            Decorator function that tracks performance
            
        Example:
            ```python
            @self.track_action("Load Config")
            def load_config(self, file_path):
                # ... operation
                pass
            ```
        """
        return track_performance(action_name)
    
    def safe_execute(
        self,
        func: Callable,
        fallback_message: str = "Operation failed",
        *args,
        **kwargs
    ) -> Any:
        """
        Safely execute a function with error handling.
        
        Args:
            func: Function to execute
            fallback_message: Error message if function fails
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Function result or None if failed
            
        Example:
            ```python
            result = self.safe_execute(
                self.config_service.load_from_file,
                "Failed to load config",
                file_path
            )
            ```
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"{fallback_message}: {e}", exc_info=True)
            UIFeedback.error(f"{fallback_message}: {str(e)}")
            return None
    
    # ========== Validation Helpers (New in Step 5) ==========
    
    def validate_current_config(self) -> tuple[bool, str]:
        """
        Validate the current configuration.
        
        Returns:
            Tuple of (is_valid, message_html) where:
            - is_valid: True if config is valid, False otherwise
            - message_html: Formatted HTML message with validation results
            
        Example:
            ```python
            is_valid, message = self.validate_current_config()
            if not is_valid:
                return message  # Show error to user
            ```
        """
        config = self.get_current_config()
        
        if not config:
            return False, self.show_warning("No configuration loaded")
        
        try:
            validation_result = self.validation_service.validate_config(config)
            
            if validation_result.is_valid:
                if validation_result.warnings:
                    message = f"✅ Valid (with {len(validation_result.warnings)} warning(s))"
                    return True, self.show_warning(message)
                else:
                    return True, self.show_success("Configuration is valid")
            else:
                # Get detailed summary
                summary = self.validation_service.get_validation_summary(validation_result)
                return False, self.show_error(summary, include_suggestion=False)
        
        except Exception as e:
            self.logger.error(f"Validation error: {e}", exc_info=True)
            return False, self.show_error(f"Validation failed: {str(e)}")
    
    # ========== Convenience Properties ==========
    
    @property
    def is_rendered(self) -> bool:
        """Check if tab has been rendered successfully."""
        return self._rendered
    
    def __repr__(self) -> str:
        """String representation of tab."""
        return f"{self.__class__.__name__}(rendered={self._rendered})"