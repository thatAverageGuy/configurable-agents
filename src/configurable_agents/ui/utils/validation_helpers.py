"""
Validation UI Helpers

Utilities for displaying validation feedback in real-time.
"""

from typing import Tuple, List, Optional
from ...domain import FlowConfig
from ...services import ValidationService


def format_validation_badge(is_valid: bool, error_count: int = 0, warning_count: int = 0) -> str:
    """
    Create a compact validation status badge.
    
    Args:
        is_valid: Whether config is valid
        error_count: Number of errors
        warning_count: Number of warnings
        
    Returns:
        HTML badge string
    """
    if is_valid:
        if warning_count > 0:
            color = "#ff9800"
            icon = "⚠️"
            text = f"Valid ({warning_count} warnings)"
        else:
            color = "#4caf50"
            icon = "✅"
            text = "Valid"
    else:
        color = "#f44336"
        icon = "❌"
        text = f"{error_count} error{'s' if error_count != 1 else ''}"
    
    return f"""
    <span style="
        display: inline-block;
        background: {color};
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: bold;
    ">
        {icon} {text}
    </span>
    """


def check_delete_safety(
    validation_service: ValidationService,
    config: FlowConfig,
    entity_type: str,
    entity_id: str,
    crew_name: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Check if entity can be safely deleted and return user-friendly message.
    
    Args:
        validation_service: ValidationService instance
        config: Current FlowConfig
        entity_type: 'step', 'crew', 'agent', or 'task'
        entity_id: ID of entity to delete
        crew_name: Required for agent/task deletion
        
    Returns:
        Tuple of (can_delete, html_message)
    """
    if entity_type == 'step':
        can_delete, deps = validation_service.can_delete_step(config, entity_id)
        
        if can_delete:
            return True, f"""
            <div style="color: #4caf50; padding: 8px; background: #e8f5e9; border-radius: 4px;">
                ✅ Safe to delete - no dependencies
            </div>
            """
        else:
            return False, f"""
            <div style="color: #f44336; padding: 8px; background: #ffebee; border-radius: 4px;">
                ❌ Cannot delete: {len(deps)} step(s) route to this step<br>
                <strong>Dependent steps:</strong> {', '.join(deps)}<br>
                <em>💡 Update their routing first</em>
            </div>
            """
    
    elif entity_type == 'crew':
        can_delete, deps = validation_service.can_delete_crew(config, entity_id)
        
        if can_delete:
            return True, f"""
            <div style="color: #4caf50; padding: 8px; background: #e8f5e9; border-radius: 4px;">
                ✅ Safe to delete - no dependencies
            </div>
            """
        else:
            return False, f"""
            <div style="color: #f44336; padding: 8px; background: #ffebee; border-radius: 4px;">
                ❌ Cannot delete: {len(deps)} step(s) use this crew<br>
                <strong>Dependent steps:</strong> {', '.join(deps)}<br>
                <em>💡 Reassign them to another crew first</em>
            </div>
            """
    
    elif entity_type == 'agent':
        if not crew_name:
            return False, "<div style='color: red;'>Error: crew_name required for agent deletion</div>"
        
        crew = config.get_crew(crew_name)
        if not crew:
            return False, f"<div style='color: red;'>Error: Crew '{crew_name}' not found</div>"
        
        can_delete, deps = validation_service.can_delete_agent(crew, entity_id)
        
        if can_delete:
            return True, f"""
            <div style="color: #4caf50; padding: 8px; background: #e8f5e9; border-radius: 4px;">
                ✅ Safe to delete - no dependencies
            </div>
            """
        else:
            return False, f"""
            <div style="color: #f44336; padding: 8px; background: #ffebee; border-radius: 4px;">
                ❌ Cannot delete: {len(deps)} task(s) assigned to this agent<br>
                <strong>Dependent tasks:</strong> {', '.join(deps)}<br>
                <em>💡 Reassign them to another agent first</em>
            </div>
            """
    
    else:
        return True, ""


def get_real_time_validation_feedback(
    validation_service: ValidationService,
    config: FlowConfig,
    entity_type: str,
    entity_id: str
) -> str:
    """
    Get real-time validation feedback for an entity being edited.
    
    Args:
        validation_service: ValidationService instance
        config: Current FlowConfig
        entity_type: Type of entity
        entity_id: ID of entity
        
    Returns:
        HTML feedback string
    """
    # Quick validation of the specific entity
    result = validation_service.validate_config(config)
    
    # Filter errors relevant to this entity
    relevant_errors = [
        err for err in result.errors
        if entity_id in err.location
    ]
    
    if not relevant_errors:
        return format_validation_badge(True, 0, 0)
    
    # Build error list
    error_html = "<ul style='margin: 5px 0; padding-left: 20px;'>"
    for err in relevant_errors[:3]:  # Show max 3
        error_html += f"<li style='color: #d32f2f;'>{err.message}</li>"
    
    if len(relevant_errors) > 3:
        error_html += f"<li style='color: #666;'>...and {len(relevant_errors) - 3} more</li>"
    
    error_html += "</ul>"
    
    return f"""
    <div style="background: #ffebee; border: 1px solid #ef5350; border-radius: 4px; padding: 10px; margin: 5px 0;">
        {format_validation_badge(False, len(relevant_errors), 0)}
        {error_html}
    </div>
    """