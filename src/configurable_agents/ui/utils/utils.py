"""
UI Utilities

Helper functions and utilities for Gradio UI components.
Includes feedback, formatting, and common UI operations.
"""

import gradio as gr
from typing import Optional, Callable, Any
from datetime import datetime
from pathlib import Path

from ...config import get_logger

logger = get_logger(__name__)


class UIFeedback:
    """
    Provides user feedback mechanisms for the UI.
    
    Uses Gradio's built-in notification system for non-blocking feedback.
    """
    
    @staticmethod
    def success(message: str, duration: int = 3) -> None:
        """
        Show a success notification.
        
        Args:
            message: Success message
            duration: How long to show (seconds)
        """
        try:
            gr.Info(f"✅ {message}", duration=duration)
        except Exception as e:
            logger.warning(f"Could not show success notification: {e}")
    
    @staticmethod
    def error(message: str, duration: int = 5) -> None:
        """
        Show an error notification.
        
        Args:
            message: Error message
            duration: How long to show (seconds)
        """
        try:
            gr.Error(f"❌ {message}", duration=duration)
        except Exception as e:
            logger.warning(f"Could not show error notification: {e}")
    
    @staticmethod
    def warning(message: str, duration: int = 4) -> None:
        """
        Show a warning notification.
        
        Args:
            message: Warning message
            duration: How long to show (seconds)
        """
        try:
            gr.Warning(f"⚠️ {message}", duration=duration)
        except Exception as e:
            logger.warning(f"Could not show warning notification: {e}")
    
    @staticmethod
    def info(message: str, duration: int = 3) -> None:
        """
        Show an info notification.
        
        Args:
            message: Info message
            duration: How long to show (seconds)
        """
        try:
            gr.Info(f"ℹ️ {message}", duration=duration)
        except Exception as e:
            logger.warning(f"Could not show info notification: {e}")


class LoadingState:
    """
    Context manager for showing loading states in UI.
    
    Example:
        ```python
        with LoadingState("Loading configuration..."):
            config = load_config()
        ```
    """
    
    def __init__(self, message: str = "Loading..."):
        """
        Initialize loading state.
        
        Args:
            message: Loading message to display
        """
        self.message = message
        self.logger = get_logger(__name__)
    
    def __enter__(self):
        """Show loading message."""
        self.logger.info(f"Loading: {self.message}")
        UIFeedback.info(self.message, duration=1)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Hide loading message."""
        if exc_type is None:
            self.logger.info(f"Loaded: {self.message}")
        return False


def safe_file_operation(
    operation: Callable,
    file_path: str,
    error_message: str = "File operation failed"
) -> Optional[Any]:
    """
    Safely perform a file operation with error handling.
    
    Args:
        operation: Function to perform on file
        file_path: Path to file
        error_message: Error message if operation fails
        
    Returns:
        Result of operation or None if failed
    """
    try:
        path = Path(file_path)
        
        # Check file exists (for read operations)
        if not path.exists() and 'read' in operation.__name__:
            UIFeedback.error(f"File not found: {file_path}")
            return None
        
        # Perform operation
        result = operation(file_path)
        return result
        
    except PermissionError:
        UIFeedback.error(f"Permission denied: {file_path}")
        logger.error(f"Permission denied accessing {file_path}")
        return None
    
    except Exception as e:
        UIFeedback.error(f"{error_message}: {str(e)}")
        logger.error(f"File operation failed: {e}", exc_info=True)
        return None


def format_timestamp(dt: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a timestamp for display.
    
    Args:
        dt: Datetime to format (default: now)
        format_str: Format string
        
    Returns:
        Formatted timestamp string
    """
    if dt is None:
        dt = datetime.now()
    
    return dt.strftime(format_str)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} PB"


def validate_file_upload(
    file_obj,
    allowed_extensions: list = None,
    max_size_mb: int = None
) -> tuple[bool, str]:
    """
    Validate an uploaded file.
    
    Args:
        file_obj: Uploaded file object
        allowed_extensions: List of allowed extensions (e.g., ['.yaml', '.yml'])
        max_size_mb: Maximum file size in MB
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_obj:
        return False, "No file uploaded"
    
    try:
        file_path = Path(file_obj)
        
        # Check extension
        if allowed_extensions:
            if file_path.suffix.lower() not in allowed_extensions:
                return False, f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        
        # Check size
        if max_size_mb:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > max_size_mb:
                return False, f"File too large. Maximum: {max_size_mb} MB"
        
        return True, ""
    
    except Exception as e:
        return False, f"File validation error: {str(e)}"


def create_progress_html(
    current: int,
    total: int,
    message: str = "",
    show_percentage: bool = True
) -> str:
    """
    Create an HTML progress bar.
    
    Args:
        current: Current progress value
        total: Total value
        message: Message to display
        show_percentage: Whether to show percentage
        
    Returns:
        HTML string for progress bar
    """
    percentage = (current / total * 100) if total > 0 else 0
    
    html = f"""
    <div style="margin: 10px 0;">
        {f'<p style="margin-bottom: 5px;">{message}</p>' if message else ''}
        <div style="
            width: 100%;
            background: #e0e0e0;
            border-radius: 5px;
            overflow: hidden;
        ">
            <div style="
                width: {percentage}%;
                background: #4caf50;
                padding: 5px 10px;
                color: white;
                font-weight: bold;
                text-align: center;
                transition: width 0.3s;
            ">
                {f'{percentage:.1f}%' if show_percentage else ''}
            </div>
        </div>
        <p style="text-align: right; font-size: 0.9em; color: #666; margin-top: 5px;">
            {current} / {total}
        </p>
    </div>
    """
    
    return html


def create_metric_card(
    title: str,
    value: str,
    icon: str = "📊",
    color: str = "#2196F3"
) -> str:
    """
    Create an HTML metric card.
    
    Args:
        title: Metric title
        value: Metric value
        icon: Icon to display
        color: Border color
        
    Returns:
        HTML string for metric card
    """
    return f"""
    <div style="
        border-left: 4px solid {color};
        padding: 15px;
        margin: 10px 0;
        background: #f5f5f5;
        border-radius: 5px;
    ">
        <div style="display: flex; align-items: center;">
            <span style="font-size: 2em; margin-right: 15px;">{icon}</span>
            <div>
                <div style="font-size: 0.9em; color: #666;">{title}</div>
                <div style="font-size: 1.5em; font-weight: bold;">{value}</div>
            </div>
        </div>
    </div>
    """


def create_status_badge(
    status: str,
    details: str = ""
) -> str:
    """
    Create a status badge with optional details.
    
    Args:
        status: Status text (e.g., "success", "error", "running")
        details: Additional details
        
    Returns:
        HTML string for status badge
    """
    # Color mapping
    colors = {
        "success": "#4caf50",
        "error": "#f44336",
        "warning": "#ff9800",
        "info": "#2196f3",
        "running": "#9c27b0",
    }
    
    color = colors.get(status.lower(), "#9e9e9e")
    
    return f"""
    <div style="
        display: inline-block;
        background: {color};
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        margin: 5px 0;
    ">
        {status.upper()}
    </div>
    {f'<p style="color: #666; font-size: 0.9em; margin-top: 5px;">{details}</p>' if details else ''}
    """


class DebugMode:
    """
    Global debug mode state.
    
    When enabled, shows more detailed error messages and logs.
    """
    
    _enabled = False
    
    @classmethod
    def enable(cls):
        """Enable debug mode."""
        cls._enabled = True
        logger.info("Debug mode enabled")
    
    @classmethod
    def disable(cls):
        """Disable debug mode."""
        cls._enabled = False
        logger.info("Debug mode disabled")
    
    @classmethod
    def is_enabled(cls) -> bool:
        """Check if debug mode is enabled."""
        return cls._enabled