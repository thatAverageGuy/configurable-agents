"""
Main Entry Point for Configurable Agents

This module loads YAML configuration and executes dynamically built flows.
"""
import asyncio
import yaml
from datetime import datetime
import uuid
from pathlib import Path
from typing import Dict, Any
import os
from dotenv import load_dotenv
from configurable_agents.core.flow_builder import build_flow_class

load_dotenv()

def load_config(config_path: str) -> dict:
    """Load YAML configuration from file."""
    with open(config_path, 'r', encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


async def run_flow(config: Dict[str, Any], initial_inputs: Dict[str, Any] = None) -> Any:
    """Run a flow from configuration."""
    FlowClass = build_flow_class(config)
    flow_instance = FlowClass()
    
    # Initialize state
    flow_instance.state.execution_id = str(uuid.uuid4())
    flow_instance.state.timestamp = datetime.now().isoformat()
    flow_instance.state.execution_status = "running"
    flow_instance.state.execution_message = ""
    
    if initial_inputs:
        flow_instance.state.custom_var.update(initial_inputs)
    
    print(f"[Main] Starting flow: {config['flow']['name']}")
    print(f"[Main] Execution ID: {flow_instance.state.execution_id}")
    print(f"[Main] Initial inputs: {initial_inputs}")
    
    try:
        result = await flow_instance.kickoff_async()
        flow_instance.state.execution_status = "success"
        flow_instance.state.execution_message = "Flow completed successfully"
        
        print(f"[Main] Flow completed successfully")
        print(f"[Main] Final state: {flow_instance.state.dict()}")
        
        return flow_instance.state.custom_var
        
    except Exception as e:
        flow_instance.state.execution_status = "error"
        flow_instance.state.execution_message = str(e)
        print(f"[Main] Flow failed with error: {e}")
        raise


async def run_flow_from_file(config_path: str, initial_inputs: Dict[str, Any] = None) -> Any:
    """Load config from file and run flow."""
    config = load_config(config_path)
    return await run_flow(config, initial_inputs)


# ========== NEW: Standard CrewAI entry point ==========
async def kickoff():
    """
    Standard entry point for 'crewai run' command.
    
    Looks for:
    1. FLOW_CONFIG env var pointing to YAML file
    2. Or defaults to 'article_generation_flow.yaml' in same directory
    
    Initial inputs can be provided via environment variables prefixed with FLOW_INPUT_
    Example: FLOW_INPUT_topic="AI in Healthcare"
    """
    # Get config path from environment or use default
    config_path = os.getenv('FLOW_CONFIG', 'article_generation_flow.yaml')
    
    # If relative path, make it relative to this file's directory
    if not os.path.isabs(config_path):
        base_dir = Path(__file__).parent
        config_path = base_dir / config_path
    
    # Gather inputs from environment variables
    initial_inputs = {}
    for key, value in os.environ.items():
        if key.startswith('FLOW_INPUT_'):
            input_key = key.replace('FLOW_INPUT_', '').lower()
            initial_inputs[input_key] = value
    
    print(f"[kickoff] Config: {config_path}")
    print(f"[kickoff] Inputs: {initial_inputs}")
    
    # Run the flow
    result = await run_flow_from_file(str(config_path), initial_inputs)
    
    print("\n" + "="*80)
    print("FLOW EXECUTION COMPLETE")
    print("="*80)
    print(f"Result: {result}")
    
    return result


async def main():
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
    result = await run_flow_from_file(config_path, initial_inputs)
    
    print("\n" + "="*80)
    print("FLOW EXECUTION COMPLETE")
    print("="*80)
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())