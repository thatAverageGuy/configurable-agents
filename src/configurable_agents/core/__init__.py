"""
Configurable Agents Core Module

Dynamic, runtime-configurable CrewAI agent system.
"""

from .flow_builder import build_flow_class
from .crew_builder import build_crew
from .model_builder import build_pydantic_model
from .tool_registry import get_tool, list_available_tools
from .utils import resolve_template, get_nested_value, set_nested_value
from .flow_visualizer import generate_mermaid_diagram, generate_crew_diagram, get_flow_summary

__all__ = [
    'build_flow_class',
    'build_crew',
    'build_pydantic_model',
    'get_tool',
    'list_available_tools',
    'resolve_template',
    'get_nested_value',
    'set_nested_value',
    'generate_mermaid_diagram',
    'generate_crew_diagram',
    'get_flow_summary',
]