"""
Model Builder Module

This module dynamically creates Pydantic models from YAML configuration.
Used for structured task outputs.
"""

from typing import Type, Dict, Any, get_args
from pydantic import BaseModel, Field


def build_pydantic_model(model_config: dict) -> Type[BaseModel]:
    """
    Build a Pydantic model from configuration.
    
    Args:
        model_config: Model configuration with name and fields
        
    Returns:
        Dynamically created Pydantic BaseModel class
        
    Example config:
        {
            "name": "ArticleOutput",
            "fields": [
                {"name": "article", "type": "str", "description": "The article text"},
                {"name": "score", "type": "int", "description": "Quality score"}
            ]
        }
    """
    model_name = model_config.get('name', 'DynamicModel')
    fields_config = model_config.get('fields', [])
    
    # Build field definitions
    fields = {}
    annotations = {}
    
    for field_config in fields_config:
        field_name = field_config['name']
        field_type_str = field_config['type']
        field_description = field_config.get('description', '')
        
        # Parse type string to Python type
        field_type = parse_type_string(field_type_str)
        
        # Create field with description
        fields[field_name] = Field(description=field_description)
        annotations[field_name] = field_type
    
    # Create the model class dynamically
    model_class = type(
        model_name,
        (BaseModel,),
        {
            '__annotations__': annotations,
            **fields
        }
    )
    
    return model_class


def parse_type_string(type_str: str) -> Type:
    """
    Parse a type string into a Python type.
    
    Supports:
    - Basic types: str, int, float, bool
    - List types: list[str], list[int], list[dict]
    - Dict type: dict
    
    Args:
        type_str: Type as string
        
    Returns:
        Python type
    """
    type_str = type_str.strip()
    
    # Basic types
    if type_str == 'str':
        return str
    elif type_str == 'int':
        return int
    elif type_str == 'float':
        return float
    elif type_str == 'bool':
        return bool
    elif type_str == 'dict':
        return dict
    
    # List types
    elif type_str.startswith('list[') and type_str.endswith(']'):
        inner_type_str = type_str[5:-1]
        inner_type = parse_type_string(inner_type_str)
        return list[inner_type]
    
    # Fallback to string if unknown
    else:
        print(f"Warning: Unknown type '{type_str}', defaulting to str")
        return str