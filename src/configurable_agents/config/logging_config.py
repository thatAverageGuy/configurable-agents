"""
Logging Configuration

Sets up structured logging for the application.
Logs to both console and file with different formats and levels.
"""

import logging
import logging.config
from pathlib import Path
from typing import Dict, Any


def get_logging_config(log_dir: str = "logs", log_level: str = "INFO") -> Dict[str, Any]:
    """
    Get logging configuration dictionary.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Logging configuration dictionary
    """
    # Create logs directory if it doesn't exist
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(levelname)s | %(message)s'
            },
            'json': {
                'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'simple',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': log_level,
                'formatter': 'detailed',
                'filename': f'{log_dir}/configurable_agents.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': f'{log_dir}/errors.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            }
        },
        'loggers': {
            'configurable_agents': {
                'level': log_level,
                'handlers': ['console', 'file', 'error_file'],
                'propagate': False
            },
            'configurable_agents.core': {
                'level': log_level,
                'handlers': ['file'],
                'propagate': False
            },
            'configurable_agents.services': {
                'level': log_level,
                'handlers': ['file'],
                'propagate': False
            },
            'configurable_agents.ui': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            }
        },
        'root': {
            'level': 'WARNING',
            'handlers': ['console']
        }
    }


def setup_logging(log_dir: str = "logs", log_level: str = "INFO") -> None:
    """
    Set up application logging.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level
    """
    config = get_logging_config(log_dir, log_level)
    logging.config.dictConfig(config)
    
    # Log startup
    logger = logging.getLogger('configurable_agents')
    logger.info("="*60)
    logger.info("Configurable Agents - Starting Up")
    logger.info(f"Log Level: {log_level}")
    logger.info(f"Log Directory: {log_dir}")
    logger.info("="*60)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name: Name of the module (use __name__)
        
    Returns:
        Configured logger
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting process")
    """
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class that provides a logger to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")