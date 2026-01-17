"""
Main Entry Point for Configurable Agents

This module loads YAML configuration and executes dynamically built flows.
"""

import yaml
from datetime import datetime
import uuid
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
from core.flow_builder import build_flow_class

load_dotenv()

def load_config(config_path: str) -> dict:
    """
    Load YAML configuration from file.
    
    Args:
        config_path: Path to YAML config file
        
    Returns:
        Configuration dictionary
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def run_flow(config: Dict[str, Any], initial_inputs: Dict[str, Any] = None) -> Any:
    """
    Run a flow from configuration.
    
    Args:
        config: Flow configuration dictionary
        initial_inputs: Initial input values to populate state.custom_var
        
    Returns:
        Flow execution result
    """
    # TODO: validate_config_schema(config)
    
    # Build the Flow class
    FlowClass = build_flow_class(config)
    
    # Instantiate the flow
    flow_instance = FlowClass()
    
    # Initialize state with common vars
    flow_instance.state.execution_id = str(uuid.uuid4())
    flow_instance.state.timestamp = datetime.now().isoformat()
    flow_instance.state.execution_status = "running"
    flow_instance.state.execution_message = ""
    
    # Populate custom_var with initial inputs
    if initial_inputs:
        flow_instance.state.custom_var.update(initial_inputs)
    
    print(f"[Main] Starting flow: {config['flow']['name']}")
    print(f"[Main] Execution ID: {flow_instance.state.execution_id}")
    print(f"[Main] Initial inputs: {initial_inputs}")
    
    try:
        # Kickoff the flow
        result = flow_instance.kickoff()
        
        # Update execution status
        flow_instance.state.execution_status = "success"
        flow_instance.state.execution_message = "Flow completed successfully"
        
        print(f"[Main] Flow completed successfully")
        print(f"[Main] Final state: {flow_instance.state.dict()}")
        
        return result
        
    except Exception as e:
        # Update execution status
        flow_instance.state.execution_status = "error"
        flow_instance.state.execution_message = str(e)
        
        print(f"[Main] Flow failed with error: {e}")
        raise


def run_flow_from_file(config_path: str, initial_inputs: Dict[str, Any] = None) -> Any:
    """
    Load config from file and run flow.
    
    Args:
        config_path: Path to YAML config file
        initial_inputs: Initial input values
        
    Returns:
        Flow execution result
    """
    config = load_config(config_path)
    return run_flow(config, initial_inputs)


def main():
    """Main function for CLI execution."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python main.py <config_path> [--topic <topic>]")
        print("Example: python main.py article_flow.yaml --topic 'AI in Healthcare'")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    # Parse simple CLI arguments
    initial_inputs = {}
    i = 2
    while i < len(sys.argv):
        if sys.argv[i].startswith('--'):
            key = sys.argv[i][2:]
            if i + 1 < len(sys.argv):
                value = sys.argv[i + 1]
                initial_inputs[key] = value
                i += 2
            else:
                i += 1
        else:
            i += 1
    
    # Run the flow
    result = run_flow_from_file(config_path, initial_inputs)
    
    print("\n" + "="*80)
    print("FLOW EXECUTION COMPLETE")
    print("="*80)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()