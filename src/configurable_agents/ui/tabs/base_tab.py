"""
Base Tab Interface - Enhanced with Reactive State

Abstract base class with reactive state subscriptions and real-time validation.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, List
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
    Abstract base class for tab components with reactive state and validation.
    
    New Features (Phase 1.5 Enhancement):
    - Automatic state change subscriptions
    - Real-time validation on config changes
    - Tab-to-tab synchronization via events
    """
    
    def __init__(
        self,
        config_service: ConfigService,
        validation_service: ValidationService,
        execution_service: ExecutionService,
        state_service: StateService
    ):
        """Initialize tab with service dependencies."""
        self.config_service = config_service
        self.validation_service = validation_service
        self.execution_service = execution_service
        self.state_service = state_service
        self.logger = get_logger(self.__class__.__name__)
        
        # Track if tab has been rendered
        self._rendered = False
        
        # Store refresh callbacks for reactive updates
        self._refresh_callbacks: List[Callable] = []
        
        # Subscribe to config changes
        self._setup_state_subscriptions()
        
        self.logger.info(f"Initialized {self.__class__.__name__}")
    
    def _setup_state_subscriptions(self) -> None:
        """
        Setup reactive state subscriptions.
        
        Tabs can override on_config_changed() to customize behavior.
        """
        def handle_config_change(event):
            """Handle config changes from state service."""
            if event.key == 'current_config':
                self.logger.debug(f"{self.__class__.__name__}: Config changed")
                try:
                    self.on_config_changed(event.new_value)
                except Exception as e:
                    self.logger.error(f"Error in on_config_changed: {e}", exc_info=True)
        
        self.state_service.subscribe('current_config', handle_config_change)
    
    def on_config_changed(self, new_config) -> None:
        """
        Called when config changes in state.
        
        Override this in subclasses to handle config changes.
        Default: triggers all registered refresh callbacks.
        
        Args:
            new_config: New FlowConfig instance
        """
        self.logger.debug(f"{self.__class__.__name__}: on_config_changed triggered")
        
        # Trigger all registered refresh callbacks
        for callback in self._refresh_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"Error in refresh callback: {e}", exc_info=True)
    
    def register_refresh_callback(self, callback: Callable) -> None:
        """
        Register a callback to be called when config changes.
        
        Used by tabs to auto-refresh their UI when config changes.
        
        Args:
            callback: Function to call on config change
        """
        self._refresh_callbacks.append(callback)
        self.logger.debug(f"Registered refresh callback: {callback.__name__}")
    
    @abstractmethod
    def render(self) -> None:
        """Render the tab content. Must be implemented by subclasses."""
        pass
    
    def safe_render(self) -> None:
        """Safely render the tab with error handling."""
        try:
            self.render()
            self._rendered = True
            self.logger.info(f"Rendered {self.__class__.__name__} successfully")
        except Exception as e:
            self.logger.error(f"Failed to render {self.__class__.__name__}: {e}", exc_info=True)
            
            with gr.Column():
                gr.Markdown(f"## ❌ Error Rendering {self.__class__.__name__}")
                gr.HTML(format_error_for_display(
                    f"Failed to render tab: {str(e)}\n\n"
                    f"{ErrorRecovery.get_suggestion(e)}"
                ))
    
    # ========== Enhanced State Management ==========
    
    @ui_error_handler("Failed to get configuration")
    def get_current_config(self):
        """Get the current configuration from state with error handling."""
        config = self.state_service.get('current_config')
        
        if config is None:
            self.logger.debug("No config in state")
        else:
            self.logger.debug(f"Retrieved config: {config.flow.name}")
        
        return config
    
    @ui_error_handler("Failed to save configuration")
    def set_current_config(self, config, trigger_validation: bool = True) -> None:
        """
        Update config in state and optionally trigger validation.
        
        Args:
            config: FlowConfig instance to store
            trigger_validation: If True, validates config and stores validation result
        """
        if config is None:
            self.logger.warning("Attempted to set None config")
            return
        
        # Validate if requested
        if trigger_validation:
            validation_result = self.validation_service.validate_config(config)
            self.state_service.set('last_validation', validation_result)
            
            if not validation_result.is_valid:
                self.logger.warning(f"Config has {len(validation_result.errors)} validation errors")
        
        # Update config (this triggers subscriptions)
        self.state_service.set('current_config', config)
        self.logger.info(f"Config updated: {config.flow.name}")
        
        # Show feedback
        UIFeedback.success(f"Configuration updated: {config.flow.name}")
    
    # ========== Validation Helpers (Enhanced) ==========
    
    def validate_current_config(self) -> tuple[bool, str]:
        """
        Validate the current configuration with caching.
        
        Returns:
            Tuple of (is_valid, message_html)
        """
        config = self.get_current_config()
        
        if not config:
            return False, self.show_warning("No configuration loaded")
        
        try:
            # Check if we have cached validation
            cached_validation = self.state_service.get('last_validation')
            
            # Use cached if available, otherwise validate
            if cached_validation:
                validation_result = cached_validation
                self.logger.debug("Using cached validation result")
            else:
                validation_result = self.validation_service.validate_config(config)
                self.state_service.set('last_validation', validation_result)
            
            if validation_result.is_valid:
                if validation_result.warnings:
                    message = f"✅ Valid (with {len(validation_result.warnings)} warning(s))"
                    return True, self.show_warning(message)
                else:
                    return True, self.show_success("Configuration is valid")
            else:
                summary = self.validation_service.get_validation_summary(validation_result)
                return False, self.show_error(summary, include_suggestion=False)
        
        except Exception as e:
            self.logger.error(f"Validation error: {e}", exc_info=True)
            return False, self.show_error(f"Validation failed: {str(e)}")
    
    def get_validation_for_entity(
        self,
        entity_type: str,
        entity_id: str
    ) -> tuple[bool, List[str]]:
        """
        Get validation errors for a specific entity.
        
        Args:
            entity_type: 'step', 'crew', 'agent', or 'task'
            entity_id: ID of the entity
            
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        cached_validation = self.state_service.get('last_validation')
        
        if not cached_validation:
            return True, []
        
        # Filter errors for this entity
        errors = []
        for error in cached_validation.errors:
            if entity_id in error.location:
                errors.append(error.message)
        
        return len(errors) == 0, errors
    
    # ========== Message Formatting ==========
    
    def show_error(self, message: str, include_suggestion: bool = True) -> str:
        """Format an error message for display with optional recovery suggestion."""
        if DebugMode.is_enabled():
            self.logger.debug(f"Showing error: {message}")
        
        full_message = message
        
        if include_suggestion:
            try:
                exception = Exception(message)
                suggestion = ErrorRecovery.get_suggestion(exception)
                full_message = f"{message}\n\n{suggestion}"
            except Exception as e:
                self.logger.debug(f"Could not generate suggestion: {e}")
        
        return format_error_for_display(full_message)
    
    def show_success(self, message: str) -> str:
        """Format a success message for display."""
        if DebugMode.is_enabled():
            self.logger.debug(f"Showing success: {message}")
        return format_success_for_display(message)
    
    def show_warning(self, message: str) -> str:
        """Format a warning message for display."""
        if DebugMode.is_enabled():
            self.logger.debug(f"Showing warning: {message}")
        return format_warning_for_display(message)
    
    def show_info(self, message: str) -> str:
        """Format an info message for display."""
        if DebugMode.is_enabled():
            self.logger.debug(f"Showing info: {message}")
        return format_info_for_display(message)
    
    # ========== Helper Methods ==========
    
    def with_loading(self, message: str = "Loading..."):
        """Context manager for showing loading state."""
        return LoadingState(message)
    
    def track_action(self, action_name: str):
        """Decorator to track performance of an action."""
        return track_performance(action_name)
    
    def safe_execute(
        self,
        func: Callable,
        fallback_message: str = "Operation failed",
        *args,
        **kwargs
    ) -> Any:
        """Safely execute a function with error handling."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"{fallback_message}: {e}", exc_info=True)
            UIFeedback.error(f"{fallback_message}: {str(e)}")
            return None
    
    @property
    def is_rendered(self) -> bool:
        """Check if tab has been rendered successfully."""
        return self._rendered
    
    def __repr__(self) -> str:
        """String representation of tab."""
        return f"{self.__class__.__name__}(rendered={self._rendered})"