"""
Test script to visualize the article generation flow.

This demonstrates the flow_visualizer module generating Mermaid diagrams.
"""

import yaml
from pathlib import Path
from configurable_agents.core.flow_visualizer import (
    generate_mermaid_diagram,
    generate_crew_diagram,
    get_flow_summary
)


def main():
    # Load the article generation config
    config_path = Path(__file__).parent / "article_generation_flow.yaml"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print("="*80)
    print("FLOW VISUALIZER TEST")
    print("="*80)
    
    # Get flow summary
    summary = get_flow_summary(config)
    print("\n📊 Flow Summary:")
    print(f"  Name: {summary['flow_name']}")
    print(f"  Description: {summary['description']}")
    print(f"  Steps: {summary['num_steps']}")
    print(f"  Crews: {summary['num_crews']}")
    print(f"  Agents: {summary['num_agents']}")
    print(f"  Tasks: {summary['num_tasks']}")
    print(f"  Crew Names: {', '.join(summary['crew_names'])}")
    
    # Generate main flow diagram
    print("\n" + "="*80)
    print("MAIN FLOW DIAGRAM (Mermaid)")
    print("="*80)
    
    mermaid_diagram = generate_mermaid_diagram(config)
    print(mermaid_diagram)
    
    # Generate crew diagrams
    print("\n" + "="*80)
    print("CREW DIAGRAMS")
    print("="*80)
    
    crews = config.get('crews', {})
    for crew_name, crew_config in crews.items():
        print(f"\n📋 {crew_name.upper()}:")
        print("-" * 80)
        crew_diagram = generate_crew_diagram(crew_config, crew_name)
        print(crew_diagram)
    
    print("\n" + "="*80)
    print("✅ Visualization Complete!")
    print("="*80)
    print("\nTo view these diagrams:")
    print("1. Copy the Mermaid syntax above")
    print("2. Visit: https://mermaid.live/")
    print("3. Paste the code to see the visual diagram")
    print("\nOr integrate with Streamlit using st.markdown() with unsafe_allow_html=True")


if __name__ == "__main__":
    main()
