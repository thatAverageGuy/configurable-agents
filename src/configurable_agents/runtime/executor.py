"""Runtime executor for workflow execution."""

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import ValidationError as PydanticValidationError

from configurable_agents.config import (
    WorkflowConfig,
    parse_config_file,
    validate_config,
    ValidationError,
)
from configurable_agents.core import build_graph, build_state_model
from configurable_agents.runtime.feature_gate import (
    UnsupportedFeatureError,
    validate_runtime_support,
)

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Base exception for execution errors."""

    def __init__(
        self,
        message: str,
        phase: str = None,
        original_error: Exception = None,
    ):
        super().__init__(message)
        self.phase = phase
        self.original_error = original_error


class ConfigLoadError(ExecutionError):
    """Error loading or parsing config file."""

    pass


class ConfigValidationError(ExecutionError):
    """Error validating config."""

    pass


class StateInitializationError(ExecutionError):
    """Error initializing workflow state."""

    pass


class GraphBuildError(ExecutionError):
    """Error building execution graph."""

    pass


class WorkflowExecutionError(ExecutionError):
    """Error during workflow execution."""

    pass


def run_workflow(
    config_path: str,
    inputs: Dict[str, Any],
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Execute workflow from config file and return final state.

    Args:
        config_path: Path to YAML or JSON config file
        inputs: Initial state inputs as dict
        verbose: Enable verbose logging (DEBUG level)

    Returns:
        Final workflow state as dict

    Raises:
        ConfigLoadError: Failed to load or parse config file
        ConfigValidationError: Config validation failed
        StateInitializationError: Failed to initialize state
        GraphBuildError: Failed to build execution graph
        WorkflowExecutionError: Workflow execution failed

    Example:
        >>> result = run_workflow("article_writer.yaml", {"topic": "AI Safety"})
        >>> print(result["article"])
    """
    # Set log level
    if verbose:
        logging.getLogger("configurable_agents").setLevel(logging.DEBUG)

    logger.info(f"Loading workflow config from: {config_path}")

    # Phase 1: Load and parse config
    try:
        config_dict = parse_config_file(config_path)
    except FileNotFoundError as e:
        raise ConfigLoadError(
            f"Config file not found: {config_path}",
            phase="config_load",
            original_error=e,
        )
    except Exception as e:
        raise ConfigLoadError(
            f"Failed to parse config file: {e}",
            phase="config_parse",
            original_error=e,
        )

    # Phase 2: Parse into Pydantic model
    try:
        config = WorkflowConfig(**config_dict)
    except PydanticValidationError as e:
        raise ConfigValidationError(
            f"Config schema validation failed:\n{e}",
            phase="schema_validation",
            original_error=e,
        )

    # Phase 3: Run workflow from config
    return run_workflow_from_config(config, inputs, verbose=verbose)


def run_workflow_from_config(
    config: WorkflowConfig,
    inputs: Dict[str, Any],
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Execute workflow from pre-loaded config and return final state.

    Args:
        config: Validated WorkflowConfig instance
        inputs: Initial state inputs as dict
        verbose: Enable verbose logging (DEBUG level)

    Returns:
        Final workflow state as dict

    Raises:
        ConfigValidationError: Config validation failed
        StateInitializationError: Failed to initialize state
        GraphBuildError: Failed to build execution graph
        WorkflowExecutionError: Workflow execution failed

    Example:
        >>> config = WorkflowConfig(**config_dict)
        >>> result = run_workflow_from_config(config, {"topic": "AI"})
    """
    # Set log level
    if verbose:
        logging.getLogger("configurable_agents").setLevel(logging.DEBUG)

    workflow_name = config.flow.name
    logger.info(f"Executing workflow: {workflow_name}")

    start_time = time.time()

    # Phase 1: Validate config (comprehensive validation)
    try:
        logger.debug("Validating config...")
        validate_config(config)
        logger.debug("Config validation passed")
    except ValidationError as e:
        raise ConfigValidationError(
            f"Config validation failed: {e}",
            phase="config_validation",
            original_error=e,
        )

    # Phase 2: Check runtime support (feature gating)
    try:
        logger.debug("Checking runtime support...")
        validate_runtime_support(config)
        logger.debug("Runtime support check passed")
    except UnsupportedFeatureError as e:
        raise ConfigValidationError(
            f"Unsupported features detected: {e}",
            phase="feature_gating",
            original_error=e,
        )

    # Phase 3: Build state model
    try:
        logger.debug("Building state model...")
        state_model = build_state_model(config.state)
        logger.debug(f"State model built: {state_model.__name__}")
    except Exception as e:
        raise GraphBuildError(
            f"Failed to build state model: {e}",
            phase="state_model_build",
            original_error=e,
        )

    # Phase 4: Initialize state with inputs
    try:
        logger.debug(f"Initializing state with inputs: {list(inputs.keys())}")
        initial_state = state_model(**inputs)
        logger.debug(f"Initial state created: {initial_state}")
    except PydanticValidationError as e:
        raise StateInitializationError(
            f"Failed to initialize state with provided inputs:\n{e}\n\n"
            f"Provided inputs: {list(inputs.keys())}\n"
            f"Required fields: {[name for name, field in state_model.model_fields.items() if field.is_required()]}",
            phase="state_initialization",
            original_error=e,
        )
    except Exception as e:
        raise StateInitializationError(
            f"Failed to initialize state: {e}",
            phase="state_initialization",
            original_error=e,
        )

    # Phase 5: Build and compile graph
    try:
        logger.debug("Building execution graph...")
        graph = build_graph(config, state_model, config.config)
        logger.debug("Graph built and compiled successfully")
    except Exception as e:
        raise GraphBuildError(
            f"Failed to build execution graph: {e}",
            phase="graph_build",
            original_error=e,
        )

    # Phase 6: Execute graph
    try:
        logger.info(f"Starting workflow execution: {workflow_name}")
        logger.debug(f"Initial state: {initial_state}")

        # LangGraph's invoke() returns dict, not BaseModel
        final_state = graph.invoke(initial_state)

        execution_time = time.time() - start_time
        logger.info(
            f"Workflow completed successfully: {workflow_name} "
            f"(duration: {execution_time:.2f}s)"
        )
        logger.debug(f"Final state: {final_state}")

        return final_state

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            f"Workflow execution failed: {workflow_name} "
            f"(duration: {execution_time:.2f}s)"
        )
        raise WorkflowExecutionError(
            f"Workflow execution failed: {e}",
            phase="workflow_execution",
            original_error=e,
        )


def validate_workflow(config_path: str) -> bool:
    """
    Validate workflow config without executing it.

    Args:
        config_path: Path to YAML or JSON config file

    Returns:
        True if validation passes

    Raises:
        ConfigLoadError: Failed to load or parse config file
        ConfigValidationError: Config validation failed

    Example:
        >>> validate_workflow("article_writer.yaml")
        True
    """
    logger.info(f"Validating workflow config: {config_path}")

    # Phase 1: Load and parse config
    try:
        config_dict = parse_config_file(config_path)
    except FileNotFoundError as e:
        raise ConfigLoadError(
            f"Config file not found: {config_path}",
            phase="config_load",
            original_error=e,
        )
    except Exception as e:
        raise ConfigLoadError(
            f"Failed to parse config file: {e}",
            phase="config_parse",
            original_error=e,
        )

    # Phase 2: Parse into Pydantic model
    try:
        config = WorkflowConfig(**config_dict)
    except PydanticValidationError as e:
        raise ConfigValidationError(
            f"Config schema validation failed:\n{e}",
            phase="schema_validation",
            original_error=e,
        )

    # Phase 3: Validate config
    try:
        validate_config(config)
        logger.info("Config validation passed")
    except ValidationError as e:
        raise ConfigValidationError(
            f"Config validation failed: {e}",
            phase="config_validation",
            original_error=e,
        )

    # Phase 4: Check runtime support
    try:
        validate_runtime_support(config)
        logger.info("Runtime support check passed")
    except UnsupportedFeatureError as e:
        raise ConfigValidationError(
            f"Unsupported features detected: {e}",
            phase="feature_gating",
            original_error=e,
        )

    logger.info("Validation complete: config is valid")
    return True
