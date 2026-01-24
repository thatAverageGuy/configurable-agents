"""Sanity tests to verify project setup"""

import configurable_agents


def test_package_version():
    """Test that package version is defined"""
    assert hasattr(configurable_agents, "__version__")
    assert configurable_agents.__version__ == "0.1.0-dev"


def test_imports():
    """Test that all submodules can be imported"""
    from configurable_agents import config
    from configurable_agents import core
    from configurable_agents import llm
    from configurable_agents import tools
    from configurable_agents import runtime

    # Basic smoke test - modules exist
    assert config is not None
    assert core is not None
    assert llm is not None
    assert tools is not None
    assert runtime is not None


def test_logging_config():
    """Test that logging configuration module exists"""
    from configurable_agents import logging_config

    assert hasattr(logging_config, "setup_logging")
    assert hasattr(logging_config, "get_logger")
