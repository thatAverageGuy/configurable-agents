"""
UI Error Handler

Provides decorators and utilities for graceful error handling in UI components.
Ensures errors are logged, displayed to users, and handled gracefully.
"""

import functools
import traceback
from typing import Callable, Any, Optional
from datetime import datetime

from ..config import get_logger

logger = get_logger(__name__)


def ui_error_handler(
    fallback_message: str = "An error occurred",
    log_error: bool = True,
    show_traceback: bool = False
):
    """
    Decorator for handling errors in UI action functions.
    
    Catches exceptions, logs them, and returns user-friendly error messages.
    
    Args:
        fallback_message: Default error message to show user
        log_error: Whether to log the error (default: True)
        show_traceback: Whether to include traceback in user message (default: False)
        
    Returns:
        Decorated function that handles errors gracefully
        
    Example:
        ```python
        @ui_error_handler("Failed to load config")
        def load_config(file_path):
            # ... might raise errors
            return config
        ```
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log the error
                if log_error:
                    logger.error(
                        f"Error in {func.__name__}: {str(e)}",
                        exc_info=True
                    )
                
                # Build user-friendly error message
                error_msg = f"{fallback_message}: {str(e)}"
                
                if show_traceback:
                    tb = traceback.format_exc()
                    error_msg += f"\n\nDetails:\n{tb}"
                
                # Return error message (formatted for Gradio)
                return format_error_for_display(error_msg)
        
        return wrapper
    return decorator


def async_ui_error_handler(
    fallback_message: str = "An error occurred",
    log_error: bool = True
):
    """
    Async version of ui_error_handler.
    
    For use with async UI action functions.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(
                        f"Error in {func.__name__}: {str(e)}",
                        exc_info=True
                    )
                
                error_msg = f"{fallback_message}: {str(e)}"
                return format_error_for_display(error_msg)
        
        return wrapper
    return decorator


def format_error_for_display(message: str) -> str:
    """
    Format an error message for display in Gradio.
    
    Args:
        message: Error message
        
    Returns:
        HTML formatted error message
    """
    # Escape HTML special chars
    message = message.replace("<", "&lt;").replace(">", "&gt;")
    
    return f"""
    <div style="
        color: #d32f2f;
        background: #ffebee;
        border: 1px solid #ef5350;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    ">
        <strong>❌ Error</strong>
        <p style="margin-top: 10px; white-space: pre-wrap;">{message}</p>
    </div>
    """


def format_success_for_display(message: str) -> str:
    """
    Format a success message for display in Gradio.
    
    Args:
        message: Success message
        
    Returns:
        HTML formatted success message
    """
    return f"""
    <div style="
        color: #2e7d32;
        background: #e8f5e9;
        border: 1px solid #66bb6a;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    ">
        <strong>✅ Success</strong>
        <p style="margin-top: 10px;">{message}</p>
    </div>
    """


def format_warning_for_display(message: str) -> str:
    """
    Format a warning message for display in Gradio.
    
    Args:
        message: Warning message
        
    Returns:
        HTML formatted warning message
    """
    return f"""
    <div style="
        color: #f57c00;
        background: #fff3e0;
        border: 1px solid #ffb74d;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    ">
        <strong>⚠️ Warning</strong>
        <p style="margin-top: 10px;">{message}</p>
    </div>
    """


def format_info_for_display(message: str) -> str:
    """
    Format an info message for display in Gradio.
    
    Args:
        message: Info message
        
    Returns:
        HTML formatted info message
    """
    return f"""
    <div style="
        color: #0277bd;
        background: #e1f5fe;
        border: 1px solid #4fc3f7;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    ">
        <strong>ℹ️ Info</strong>
        <p style="margin-top: 10px;">{message}</p>
    </div>
    """


class ErrorRecovery:
    """
    Provides error recovery suggestions based on error types.
    """
    
    @staticmethod
    def get_suggestion(error: Exception) -> str:
        """
        Get a recovery suggestion for an error.
        
        Args:
            error: Exception that occurred
            
        Returns:
            User-friendly suggestion
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        # YAML parsing errors
        if "yaml" in error_msg.lower():
            return (
                "💡 YAML syntax error detected. "
                "Check for:\n"
                "  • Missing colons after keys\n"
                "  • Incorrect indentation (use spaces, not tabs)\n"
                "  • Missing quotes around special characters\n"
                "  • Unclosed brackets or braces"
            )
        
        # File not found
        if "FileNotFoundError" in error_type or "not found" in error_msg.lower():
            return (
                "💡 File not found. "
                "Verify:\n"
                "  • The file path is correct\n"
                "  • The file exists in the expected location\n"
                "  • You have permission to access the file"
            )
        
        # API key errors
        if "api" in error_msg.lower() and "key" in error_msg.lower():
            return (
                "💡 API key issue detected. "
                "Check:\n"
                "  • GOOGLE_API_KEY is set in .env file\n"
                "  • API key is valid and not expired\n"
                "  • You have sufficient API quota"
            )
        
        # Validation errors
        if "validation" in error_msg.lower():
            return (
                "💡 Configuration validation failed. "
                "Review:\n"
                "  • All required fields are present\n"
                "  • Crews referenced by steps exist\n"
                "  • Agents referenced by tasks exist\n"
                "  • At least one step has 'is_start: true'"
            )
        
        # Network errors
        if any(x in error_msg.lower() for x in ["connection", "timeout", "network"]):
            return (
                "💡 Network issue detected. "
                "Try:\n"
                "  • Check your internet connection\n"
                "  • Verify firewall settings\n"
                "  • Check if the API endpoint is accessible\n"
                "  • Retry the operation"
            )
        
        # Permission errors
        if "permission" in error_msg.lower():
            return (
                "💡 Permission denied. "
                "Ensure:\n"
                "  • You have read/write permissions\n"
                "  • The file/directory is not locked\n"
                "  • You're running with appropriate privileges"
            )
        
        # Default suggestion
        return (
            "💡 Try:\n"
            "  • Review the error message above\n"
            "  • Check the logs for more details\n"
            "  • Verify your configuration is valid\n"
            "  • Restart the application if needed"
        )


class PerformanceLogger:
    """
    Tracks and logs performance metrics for UI actions.
    """
    
    def __init__(self, action_name: str):
        """
        Initialize performance logger.
        
        Args:
            action_name: Name of the action being tracked
        """
        self.action_name = action_name
        self.start_time = None
        self.logger = get_logger(__name__)
    
    def __enter__(self):
        """Start timing."""
        self.start_time = datetime.now()
        self.logger.debug(f"Starting: {self.action_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log results."""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.info(f"Completed: {self.action_name} in {duration:.2f}s")
        else:
            self.logger.warning(f"Failed: {self.action_name} after {duration:.2f}s")
        
        return False  # Don't suppress exceptions


def track_performance(action_name: str):
    """
    Decorator to track performance of UI actions.
    
    Args:
        action_name: Name of the action
        
    Example:
        ```python
        @track_performance("Load Config")
        def load_config(file_path):
            # ... operation
            return config
        ```
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with PerformanceLogger(action_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator