"""
Entry point for running configurable-agents as a module.

Usage:
    python -m configurable_agents run workflow.yaml --input topic="AI"
    python -m configurable_agents validate workflow.yaml
"""

import sys

from configurable_agents.cli import main

if __name__ == "__main__":
    sys.exit(main())
