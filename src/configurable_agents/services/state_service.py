"""
State Service

Manages application state for the UI.
Provides reactive state updates and subscriptions.
"""

from typing import Any, Callable, Dict, Optional, List
from dataclasses import dataclass, field
from copy import deepcopy

from ..config import get_logger

logger = get_logger(__name__)


@dataclass
class StateChangeEvent:
    """Event representing a state change."""
    
    key: str
    old_value: Any
    new_value: Any
    timestamp: str
    
    def __str__(self) -> str:
        return f"StateChange(key={self.key}, old={self.old_value}, new={self.new_value})"


class StateService:
    """Service for managing application state."""
    
    def __init__(self):
        """Initialize state service."""
        self._state: Dict[str, Any] = {}
        self._subscribers: Dict[str, List[Callable[[StateChangeEvent], None]]] = {}
        self.logger = logger
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from state.
        
        Args:
            key: State key (supports dot notation: 'user.name')
            default: Default value if key not found
            
        Returns:
            State value or default
        """
        try:
            return self._get_nested(key)
        except KeyError:
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in state.
        
        Args:
            key: State key (supports dot notation: 'user.name')
            value: Value to set
        """
        old_value = self.get(key)
        
        # Set the value
        self._set_nested(key, value)
        
        # Notify subscribers
        self._notify_subscribers(key, old_value, value)
        
        self.logger.debug(f"State updated: {key} = {value}")
    
    def delete(self, key: str) -> None:
        """
        Delete a value from state.
        
        Args:
            key: State key to delete
        """
        old_value = self.get(key)
        
        try:
            parts = key.split('.')
            current = self._state
            
            for part in parts[:-1]:
                current = current[part]
            
            del current[parts[-1]]
            
            # Notify subscribers
            self._notify_subscribers(key, old_value, None)
            
            self.logger.debug(f"State deleted: {key}")
            
        except KeyError:
            pass  # Key doesn't exist, nothing to delete
    
    def clear(self) -> None:
        """Clear all state."""
        self._state.clear()
        self._subscribers.clear()
        self.logger.info("State cleared")
    
    def subscribe(self, key: str, callback: Callable[[StateChangeEvent], None]) -> None:
        """
        Subscribe to state changes for a specific key.
        
        Args:
            key: State key to watch
            callback: Function to call when key changes
        """
        if key not in self._subscribers:
            self._subscribers[key] = []
        
        self._subscribers[key].append(callback)
        self.logger.debug(f"Subscribed to state key: {key}")
    
    def unsubscribe(self, key: str, callback: Callable[[StateChangeEvent], None]) -> None:
        """
        Unsubscribe from state changes.
        
        Args:
            key: State key
            callback: Callback function to remove
        """
        if key in self._subscribers:
            try:
                self._subscribers[key].remove(callback)
                self.logger.debug(f"Unsubscribed from state key: {key}")
            except ValueError:
                pass  # Callback not found
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all state as a dictionary.
        
        Returns:
            Copy of entire state
        """
        return deepcopy(self._state)
    
    def update(self, updates: Dict[str, Any]) -> None:
        """
        Update multiple state values at once.
        
        Args:
            updates: Dictionary of key-value pairs to update
        """
        for key, value in updates.items():
            self.set(key, value)
    
    def has(self, key: str) -> bool:
        """
        Check if a key exists in state.
        
        Args:
            key: State key to check
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            self._get_nested(key)
            return True
        except KeyError:
            return False
    
    # ==================== PRIVATE METHODS ====================
    
    def _get_nested(self, key: str) -> Any:
        """Get nested value using dot notation."""
        parts = key.split('.')
        current = self._state
        
        for part in parts:
            current = current[part]
        
        return current
    
    def _set_nested(self, key: str, value: Any) -> None:
        """Set nested value using dot notation."""
        parts = key.split('.')
        current = self._state
        
        # Navigate to parent
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set value
        current[parts[-1]] = value
    
    def _notify_subscribers(self, key: str, old_value: Any, new_value: Any) -> None:
        """Notify subscribers of state changes."""
        from datetime import datetime
        
        event = StateChangeEvent(
            key=key,
            old_value=old_value,
            new_value=new_value,
            timestamp=datetime.now().isoformat()
        )
        
        # Notify exact key subscribers
        if key in self._subscribers:
            for callback in self._subscribers[key]:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"Error in state subscriber callback: {e}", exc_info=True)
        
        # Notify wildcard subscribers (future feature)
        if '*' in self._subscribers:
            for callback in self._subscribers['*']:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"Error in wildcard subscriber callback: {e}", exc_info=True)


# Global state service instance
_state_service: Optional[StateService] = None


def get_state_service() -> StateService:
    """
    Get the global state service instance.
    
    Returns:
        StateService instance
    """
    global _state_service
    
    if _state_service is None:
        _state_service = StateService()
    
    return _state_service


def reset_state_service() -> None:
    """Reset the global state service (useful for testing)."""
    global _state_service
    _state_service = None