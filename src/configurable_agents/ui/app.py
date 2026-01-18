"""
Main Gradio Application

Assembles all tabs and services into a complete application.
Entry point for the Gradio UI.
"""

import gradio as gr
from pathlib import Path

from ..services import (
    ConfigService,
    ValidationService,
    ExecutionService,
    StateService,
    get_state_service
)
from ..config import setup_logging, get_settings, get_logger
from .tabs import (
    OverviewTab,
    ConfigEditorTab,
    FlowDiagramTab,
    ExecuteTab,
    ResultsTab
)

logger = get_logger(__name__)


def create_app() -> gr.Blocks:
    """
    Create the Gradio application.
    
    Returns:
        Configured Gradio Blocks application
    """
    # Initialize services
    config_service = ConfigService()
    validation_service = ValidationService()
    execution_service = ExecutionService()
    state_service = get_state_service()
    
    logger.info("Initializing Gradio application...")
    
    # Create Gradio app
    with gr.Blocks(
        title="Configurable Agent Platform",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container {
            max-width: 1400px !important;
        }
        """
    ) as app:
        
        # Header
        gr.Markdown("""
        # 🤖 Configurable Agent Platform
        
        **Runtime-configurable AI agent workflows** powered by CrewAI
        
        Build, configure, and execute multi-agent workflows without writing code.
        """)
        
        gr.Markdown("---")
        
        # Create tabs
        with gr.Tabs() as tabs:
            
            # Overview Tab
            with gr.Tab("📊 Overview"):
                overview_tab = OverviewTab(
                    config_service,
                    validation_service,
                    execution_service,
                    state_service
                )
                overview_tab.render()
            
            # Config Editor Tab
            with gr.Tab("⚙️ Config Editor"):
                config_editor_tab = ConfigEditorTab(
                    config_service,
                    validation_service,
                    execution_service,
                    state_service
                )
                config_editor_tab.render()
            
            # Flow Diagram Tab
            with gr.Tab("🎨 Flow Diagram"):
                flow_diagram_tab = FlowDiagramTab(
                    config_service,
                    validation_service,
                    execution_service,
                    state_service
                )
                flow_diagram_tab.render()
            
            # Execute Tab
            with gr.Tab("🚀 Execute"):
                execute_tab = ExecuteTab(
                    config_service,
                    validation_service,
                    execution_service,
                    state_service
                )
                execute_tab.render()
            
            # Results Tab
            with gr.Tab("📊 Results"):
                results_tab = ResultsTab(
                    config_service,
                    validation_service,
                    execution_service,
                    state_service
                )
                results_tab.render()
        
        # Footer
        gr.Markdown("---")
        gr.Markdown("""
        <div style="text-align: center; color: #666; font-size: 0.9em;">
            Built with ❤️ using CrewAI Flows | 
            <a href="https://docs.claude.com" target="_blank">Documentation</a> | 
            <a href="https://github.com" target="_blank">GitHub</a>
        </div>
        """)
    
    logger.info("Gradio application created successfully")
    
    return app


def launch_app(
    server_name: str = "0.0.0.0",
    server_port: int = None,
    share: bool = False,
    auth: tuple = None
) -> None:
    """
    Launch the Gradio application.
    
    Args:
        server_name: Server hostname (default: 0.0.0.0)
        server_port: Server port (default: from settings or 7860)
        share: Whether to create a public share link
        auth: Optional tuple of (username, password) for authentication
    """
    # Setup logging
    settings = get_settings()
    setup_logging(settings.app.log_dir, settings.app.log_level)
    
    logger.info("="*60)
    logger.info("Configurable Agent Platform - Starting")
    logger.info("="*60)
    
    # Get port from settings if not specified
    if server_port is None:
        server_port = settings.app.ui_port
    
    # Get auth from settings if not specified
    if auth is None and settings.app.ui_auth:
        auth = settings.app.ui_auth
    
    # Create and launch app
    app = create_app()
    
    logger.info(f"Launching Gradio app on {server_name}:{server_port}")
    logger.info(f"Share mode: {share}")
    logger.info(f"Authentication: {'Enabled' if auth else 'Disabled'}")
    
    app.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        auth=auth,
        show_api=True,  # Enable API mode for future Phase 6
        prevent_thread_lock=False
    )


def main():
    """Main entry point for CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Launch Configurable Agent Platform"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Server hostname (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Server port (default: from settings or 7860)"
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public share link"
    )
    parser.add_argument(
        "--auth",
        nargs=2,
        metavar=("USERNAME", "PASSWORD"),
        help="Enable authentication with username and password"
    )
    
    args = parser.parse_args()
    
    # Convert auth to tuple if provided
    auth = tuple(args.auth) if args.auth else None
    
    launch_app(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        auth=auth
    )


if __name__ == "__main__":
    main()