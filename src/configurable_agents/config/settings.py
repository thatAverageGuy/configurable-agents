"""
Application Settings

Centralized configuration management using environment variables.
All settings are loaded from .env file or system environment.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class LLMSettings:
    """LLM provider settings."""
    
    google_api_key: str
    serper_api_key: Optional[str] = None
    default_model: str = "gemini-2.5-flash-lite"
    default_temperature: float = 0.7
    default_max_tokens: int = 4000
    
    def __post_init__(self):
        """Validate required settings."""
        if not self.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found in environment. "
                "Set it in .env file or as environment variable."
            )


@dataclass
class AppSettings:
    """Application settings."""
    
    app_name: str = "Configurable Agents"
    version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    log_dir: str = "logs"
    
    # Gradio UI settings
    ui_port: int = 7860
    ui_share: bool = False
    ui_auth: Optional[tuple[str, str]] = None  # (username, password)
    
    # File paths
    config_dir: Path = Path("configs")
    output_dir: Path = Path("outputs")
    
    def __post_init__(self):
        """Create required directories."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class Settings:
    """Complete application settings."""
    
    app: AppSettings
    llm: LLMSettings
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """
        Load settings from environment variables.
        
        Returns:
            Settings instance
            
        Raises:
            ValueError: If required environment variables are missing
        """
        # LLM settings
        llm_settings = LLMSettings(
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
            serper_api_key=os.getenv("SERPER_API_KEY"),
            default_model=os.getenv("MODEL", "gemini-2.5-flash-lite"),
            default_temperature=float(os.getenv("DEFAULT_TEMPERATURE", "0.7")),
            default_max_tokens=int(os.getenv("DEFAULT_MAX_TOKENS", "4000")),
        )
        
        # App settings
        app_settings = AppSettings(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_dir=os.getenv("LOG_DIR", "logs"),
            ui_port=int(os.getenv("UI_PORT", "7860")),
            ui_share=os.getenv("UI_SHARE", "false").lower() == "true",
        )
        
        # UI auth (optional)
        ui_username = os.getenv("UI_USERNAME")
        ui_password = os.getenv("UI_PASSWORD")
        if ui_username and ui_password:
            app_settings.ui_auth = (ui_username, ui_password)
        
        return cls(app=app_settings, llm=llm_settings)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance.
    
    Returns:
        Settings instance
        
    Example:
        >>> settings = get_settings()
        >>> print(settings.llm.default_model)
    """
    global _settings
    
    if _settings is None:
        _settings = Settings.from_env()
    
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment.
    
    Useful for testing or when .env file changes.
    
    Returns:
        New settings instance
    """
    global _settings
    
    load_dotenv(override=True)
    _settings = Settings.from_env()
    
    return _settings