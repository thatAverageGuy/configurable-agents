#!/usr/bin/env python3
"""
Launch script for Configurable Agent Platform

Quick way to start the Gradio UI.
"""

if __name__ == "__main__":
    from src.configurable_agents.ui import launch_app
    
    # Launch with default settings
    launch_app()