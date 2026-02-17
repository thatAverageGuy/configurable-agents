"""
Runtime feature gating for version-specific features.

Validates that configs only use features available in the current runtime version.
v0.1: Linear flows only
v0.2: Conditional routing, observability
"""

import warnings
from typing import List, Optional

from configurable_agents.config.schema import WorkflowConfig


class UnsupportedFeatureError(Exception):
    """
    Raised when config uses features not available in current runtime version.

    Includes helpful information about when feature will be available and workarounds.
    """

    def __init__(
        self,
        feature: str,
        available_in: str,
        timeline: Optional[str] = None,
        workaround: Optional[str] = None,
        roadmap_link: str = "docs/PROJECT_VISION.md",
    ):
        self.feature = feature
        self.available_in = available_in
        self.timeline = timeline
        self.workaround = workaround
        self.roadmap_link = roadmap_link

        # Build comprehensive error message
        parts = [f"Feature '{feature}' is not supported in v0.1"]
        parts.append(f"Available in: {available_in}")

        if timeline:
            parts.append(f"Estimated timeline: {timeline}")

        if workaround:
            parts.append(f"\nWorkaround: {workaround}")

        parts.append(f"\nSee roadmap: {roadmap_link}")

        super().__init__("\n".join(parts))


def validate_runtime_support(config: WorkflowConfig) -> None:
    """
    Validate that config only uses features supported by current runtime version.

    Checks for:
    - Optimization config (v0.3+ feature) - SOFT BLOCK (warning)
    - Advanced observability (v0.2+ feature) - SOFT BLOCK (warning)

    Args:
        config: Workflow configuration to validate

    Raises:
        UnsupportedFeatureError: If config uses unsupported features (hard blocks only)

    Warnings:
        UserWarning: For soft blocks (features that will be ignored)
    """
    # Check for observability config (v0.2+) - SOFT BLOCK
    _check_observability(config)


def _check_conditional_routing(config: WorkflowConfig) -> None:
    """
    No-op: conditional routing is now supported.

    Previously checked for conditional routing (routes in edges) as a HARD BLOCK.
    This feature is now supported in the current runtime version.
    """
    # Feature is now supported - no-op
    pass


def _check_observability(config: WorkflowConfig) -> None:
    """
    Check for advanced observability config.

    This is a SOFT BLOCK - issues warning for MLFlow, allows basic logging.
    """
    if not config.config or not config.config.observability:
        return

    obs_config = config.config.observability

    # MLFlow observability (v0.1+) - Supported!
    # MLFlow tracking is fully implemented in v0.1 (T-018, T-019, T-020)
    # No warnings needed - feature is production-ready

    # Logging config is OK - we support basic logging in v0.1
    # No warning needed


def get_supported_features() -> dict:
    """
    Get list of features supported in current runtime version.

    Returns:
        Dict mapping feature categories to lists of supported features
    """
    return {
        "version": "0.2.0-dev",
        "flow_control": [
            "Linear workflows (START -> nodes -> END)",
            "Conditional routing (if/else based on state)",
            "Loops and retries (with iteration limits)",
            "Parallel node execution (fan-out/fan-in)",
            "Single entry point",
            "Sequential execution",
        ],
        "state": [
            "Basic types (str, int, float, bool)",
            "Collection types (list, dict, typed variants)",
            "Nested objects",
            "Required and optional fields",
        ],
        "nodes": [
            "LLM prompts with placeholders",
            "Input mappings",
            "Structured outputs (Pydantic schemas)",
            "Tool calling (single tool: serper_search)",
        ],
        "llm": [
            "OpenAI models (GPT-4o, GPT-4o-mini, etc.)",
            "Anthropic models (Claude Sonnet 4, Claude 3.5 Sonnet, etc.)",
            "Google Gemini models",
            "Ollama local models (Llama 3, Mistral, etc.)",
            "Temperature control",
            "Max tokens",
            "Node-level overrides",
        ],
        "validation": [
            "Parse-time validation",
            "Type checking",
            "Graph validation",
            "Cross-reference checks",
            "Route condition validation",
            "Loop config validation",
            "Parallel config validation",
        ],
        "observability": [
            "MLFlow integration",
            "Cost tracking and reporting",
            "Token usage tracking",
            "Workflow and node-level metrics",
            "CLI cost reporting",
        ],
        "not_supported": {
            "v0.4": [
                "Visual workflow editor",
                "One-click deployments",
                "Plugin system",
                "State persistence and resume",
            ],
        },
    }


def check_feature_support(feature_name: str) -> dict:
    """
    Check if a specific feature is supported and when it will be available.

    Args:
        feature_name: Name of feature to check

    Returns:
        Dict with support status and timeline:
        {
            "supported": bool,
            "version": str (current version or when available),
            "timeline": str (if not supported),
        }
    """
    supported = get_supported_features()

    # Check if feature is in supported categories
    for category, features in supported.items():
        if category == "not_supported":
            continue
        if isinstance(features, list) and feature_name in features:
            return {
                "supported": True,
                "version": supported["version"],
                "timeline": "Available now",
            }

    # Check when feature will be available
    if "not_supported" in supported:
        for version, features in supported["not_supported"].items():
            if feature_name in features:
                timeline_map = {
                    "v0.2": "8-12 weeks from initial release",
                    "v0.3": "12-16 weeks from initial release",
                    "v0.4": "16-24 weeks from initial release",
                }
                return {
                    "supported": False,
                    "version": version,
                    "timeline": timeline_map.get(version, "See roadmap"),
                }

    # Unknown feature
    return {
        "supported": False,
        "version": "unknown",
        "timeline": "Not in current roadmap",
    }
