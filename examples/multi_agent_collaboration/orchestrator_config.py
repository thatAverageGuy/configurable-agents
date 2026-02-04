#!/usr/bin/env python
"""
Orchestrator configuration example for multi-agent collaboration.

This script demonstrates how to configure and use the orchestrator
for agent discovery and coordination.
"""

import asyncio
from configurable_agents.orchestrator import (
    AgentRegistryOrchestratorClient,
    OrchestratorService
)

def discover_agents_example():
    """Example: Discover agents from registry."""
    print("=== Agent Discovery Example ===\n")

    # Connect to registry
    client = AgentRegistryOrchestratorClient(
        registry_url="http://localhost:8000"
    )

    # Find all research agents
    research_agents = client.discover_agents(
        metadata_filter={"capability": "research"}
    )

    print(f"Found {len(research_agents)} research agents:")
    for agent in research_agents:
        print(f"  - {agent['name']}: {agent['metadata']}")

    # Find specific specialist
    analysts = client.discover_agents(
        metadata_filter={"specialty": "data_synthesis"}
    )

    print(f"\nFound {len(analysts)} data synthesis specialists")
    return research_agents + analysts


def orchestrate_workflow_example(agents):
    """Example: Orchestrate workflow across multiple agents."""
    print("\n=== Workflow Orchestration Example ===\n")

    # Create orchestrator service
    orchestrator = OrchestratorService(
        registry_url="http://localhost:8000"
    )

    # Define work items
    work_items = [
        {
            "task": "research_topic",
            "agent_type": "research",
            "input": {"topic": "AI agent frameworks"}
        },
        {
            "task": "analyze_data",
            "agent_type": "analysis",
            "input": {"data": "research findings"}
        }
    ]

    # Execute with parallel agents
    results = orchestrator.execute_parallel(
        work_items=work_items,
        max_parallel=5,
        timeout=300
    )

    print(f"Executed {len(results)} tasks:")
    for result in results:
        print(f"  - {result['task']}: {result['status']}")

    return results


def agent_health_example():
    """Example: Monitor agent health."""
    print("\n=== Agent Health Monitoring ===\n")

    client = AgentRegistryOrchestratorClient(
        registry_url="http://localhost:8000"
    )

    # Get all active agents
    active_agents = client.discover_agents(active_only=True)

    print(f"Active agents: {len(active_agents)}")
    for agent in active_agents:
        last_heartbeat = agent.get("last_heartbeat", "Unknown")
        status = "✓ Healthy" if last_heartbeat != "Unknown" else "✗ Unhealthy"
        print(f"  - {agent['name']}: {status}")


def filter_by_metadata_example():
    """Example: Filter agents by complex metadata."""
    print("\n=== Metadata Filtering Example ===\n")

    client = AgentRegistryOrchestratorClient(
        registry_url="http://localhost:8000"
    )

    # Find agents with multiple metadata criteria
    qualified_agents = client.discover_agents(
        metadata_filter={
            "capability": "research",
            "tier": "premium"
        }
    )

    print(f"Qualified agents (research + premium): {len(qualified_agents)}")
    for agent in qualified_agents:
        print(f"  - {agent['name']}: {agent['metadata']}")


if __name__ == "__main__":
    print("Multi-Agent Orchestrator Configuration Examples")
    print("=" * 50)

    try:
        # Run examples
        agents = discover_agents_example()
        orchestrate_workflow_example(agents)
        agent_health_example()
        filter_by_metadata_example()

        print("\n" + "=" * 50)
        print("All examples completed successfully!")

    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("1. Agent registry is running (port 8000)")
        print("2. Agents are registered")
        print("3. Network connectivity is available")
