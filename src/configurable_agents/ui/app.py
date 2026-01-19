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


def load_default_config_on_startup(config_service, state_service):
    """
    Load default configuration on application startup.
    
    Looks for article_generation_flow.yaml and loads it automatically.
    
    Args:
        config_service: ConfigService instance
        state_service: StateService instance
    """
    try:
        # Look for default config
        default_path = Path(__file__).parent.parent / "article_generation_flow.yaml"
        
        if default_path.exists():
            logger.info(f"Loading default config from: {default_path}")
            config = config_service.load_from_file(str(default_path))
            state_service.set('current_config', config)
            logger.info(f"Default config loaded: {config.flow.name}")
            return True
        else:
            logger.info("No default config found at startup")
            return False
    
    except Exception as e:
        logger.error(f"Failed to load default config on startup: {e}")
        return False


def create_app(load_default: bool = True) -> gr.Blocks:
    """
    Create the Gradio application.
    
    Args:
        load_default: If True, attempts to load default config on startup
    
    Returns:
        Configured Gradio Blocks application
    """
    # Initialize services
    config_service = ConfigService()
    validation_service = ValidationService()
    execution_service = ExecutionService()
    state_service = get_state_service()
    
    logger.info("Initializing Gradio application...")
    
    # Load default config if requested
    if load_default:
        default_loaded = load_default_config_on_startup(config_service, state_service)
        if default_loaded:
            logger.info("✅ Default configuration loaded on startup")
    
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
            <a href="https://docs.anthropic.com" target="_blank">Documentation</a> | 
            <a href="https://github.com/yourusername/configurable-agents" target="_blank">GitHub</a>
        </div>
        """)
    
    logger.info("Gradio application created successfully")
    
    return app


def launch_app(
    server_name: str = "0.0.0.0",
    server_port: int = None,
    share: bool = False,
    auth: tuple = None,
    load_default: bool = True
) -> None:
    """
    Launch the Gradio application.
    
    Args:
        server_name: Server hostname (default: 0.0.0.0)
        server_port: Server port (default: from settings or 7860)
        share: Whether to create a public share link
        auth: Optional tuple of (username, password) for authentication
        load_default: If True, loads default config on startup
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
    app = create_app(load_default=load_default)
    
    logger.info(f"Launching Gradio app on {server_name}:{server_port}")
    logger.info(f"Share mode: {share}")
    logger.info(f"Authentication: {'Enabled' if auth else 'Disabled'}")
    logger.info(f"Default config loading: {'Enabled' if load_default else 'Disabled'}")
    
    app.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        auth=auth,
        # show_api=True,  # Enable API mode for future Phase 6
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
    parser.add_argument(
        "--no-default-config",
        action="store_true",
        help="Don't load default config on startup"
    )
    
    args = parser.parse_args()
    
    # Convert auth to tuple if provided
    auth = tuple(args.auth) if args.auth else None
    
    launch_app(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        auth=auth,
        load_default=not args.no_default_config
    )


if __name__ == "__main__":
    main()