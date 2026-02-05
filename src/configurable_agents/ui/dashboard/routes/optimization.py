"""Optimization routes for experiment comparison and prompt application.

Provides endpoints for viewing MLFlow experiments, comparing variants,
and applying optimized prompts back to workflow configurations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from configurable_agents.optimization import ExperimentEvaluator, find_best_variant
from configurable_agents.optimization.ab_test import apply_prompt_to_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/optimization")


class ApplyPromptRequest(BaseModel):
    """Request model for applying optimized prompt."""

    experiment: str = Field(..., description="MLFlow experiment name")
    variant: Optional[str] = Field(None, description="Specific variant name (default: best)")
    workflow_path: str = Field(..., description="Path to workflow YAML file")
    dry_run: bool = Field(False, description="Show diff without applying")


class ExperimentListResponse(BaseModel):
    """Response model for experiment list."""

    experiments: List[Dict[str, Any]]
    mlflow_available: bool


@router.get("/experiments", response_class=HTMLResponse)
async def experiments_list(
    request: Request,
    metric: str = "cost_usd_avg",
):
    """Render experiments list page."""
    templates: Jinja2Templates = request.app.state.templates

    # Get experiment list
    experiments = []
    mlflow_available = False

    # Get MLFlow tracking URI from app state
    mlflow_tracking_uri = getattr(request.app.state, 'mlflow_tracking_uri', None)

    try:
        # Import MLFlow lazily
        import mlflow
        from mlflow.tracking import MlflowClient
        from mlflow.entities import ViewType

        # Pass tracking URI to client if available
        if mlflow_tracking_uri:
            client = MlflowClient(tracking_uri=mlflow_tracking_uri)
        else:
            client = MlflowClient()

        # Get all active experiments
        exp_list = client.search_experiments(view_type=ViewType.ACTIVE_ONLY)

        # Only set mlflow_available = True after successful operation
        mlflow_available = True

        for exp in exp_list:
            # Get run count
            runs = client.search_runs(
                experiment_ids=[exp.experiment_id],
                max_results=1,
            )

            experiments.append({
                "name": exp.name,
                "id": exp.experiment_id,
                "run_count": len(runs) if runs else 0,
                "creation_time": datetime.fromtimestamp(exp.creation_time / 1000) if exp.creation_time else None,
            })

    except ImportError:
        logger.warning("MLFlow not installed or not available")
    except (FileNotFoundError, OSError) as e:
        logger.warning(f"MLFlow filesystem error (backend not configured): {e}")
        mlflow_available = False
    except Exception as e:
        logger.error(f"Failed to list experiments: {e}")
        mlflow_available = False

    return templates.TemplateResponse(
        "experiments.html",
        {
            "request": request,
            "experiments": experiments,
            "mlflow_available": mlflow_available,
        },
    )


@router.get("/experiments.json")
async def experiments_json(
    request: Request,
):
    """Return experiments as JSON (for HTMX refresh)."""
    experiments = []
    mlflow_available = False

    # Get MLFlow tracking URI from app state
    mlflow_tracking_uri = getattr(request.app.state, 'mlflow_tracking_uri', None)

    try:
        import mlflow
        from mlflow.tracking import MlflowClient
        from mlflow.entities import ViewType

        # Pass tracking URI to client if available
        if mlflow_tracking_uri:
            client = MlflowClient(tracking_uri=mlflow_tracking_uri)
        else:
            client = MlflowClient()

        exp_list = client.search_experiments(view_type=ViewType.ACTIVE_ONLY)

        # Only set mlflow_available = True after successful operation
        mlflow_available = True

        for exp in exp_list:
            runs = client.search_runs(
                experiment_ids=[exp.experiment_id],
                max_results=1,
            )

            experiments.append({
                "name": exp.name,
                "id": exp.experiment_id,
                "run_count": len(runs) if runs else 0,
                "creation_time": datetime.fromtimestamp(exp.creation_time / 1000) if exp.creation_time else None,
            })

    except ImportError:
        logger.warning("MLFlow not installed or not available")
    except (FileNotFoundError, OSError) as e:
        logger.warning(f"MLFlow filesystem error (backend not configured): {e}")
        mlflow_available = False
    except Exception as e:
        logger.error(f"Failed to get experiments: {e}")
        mlflow_available = False

    return {"experiments": experiments, "mlflow_available": mlflow_available}


@router.get("/compare", response_class=HTMLResponse)
async def compare_page(
    request: Request,
    experiment: str,
    metric: str = "cost_usd_avg",
):
    """Render comparison page for an experiment."""
    templates: Jinja2Templates = request.app.state.templates

    # Get comparison data
    comparison_data = None
    error = None
    mlflow_available = True  # Assume available until proven otherwise

    # Get MLFlow tracking URI from app state
    mlflow_tracking_uri = getattr(request.app.state, 'mlflow_tracking_uri', None)

    try:
        evaluator = ExperimentEvaluator(mlflow_tracking_uri=mlflow_tracking_uri)
        comparison = evaluator.compare_variants(experiment, metric)

        # Convert to dict for template
        comparison_data = {
            "experiment": comparison.experiment_name,
            "metric": comparison.metric,
            "best_variant": comparison.best_variant,
            "variants": [
                {
                    "name": v.variant_name,
                    "run_count": v.run_count,
                    "metrics": v.metrics,
                }
                for v in comparison.variants
            ],
        }

    except (ImportError, FileNotFoundError, OSError) as e:
        logger.warning(f"MLFlow not available or not configured: {e}")
        mlflow_available = False
        error = "MLFlow is not available or not configured. Please install MLFlow and configure the tracking URI."
    except Exception as e:
        logger.error(f"Failed to get comparison: {e}")
        error = str(e)

    return templates.TemplateResponse(
        "optimization.html",
        {
            "request": request,
            "experiment": experiment,
            "metric": metric,
            "comparison": comparison_data,
            "error": error,
            "mlflow_available": mlflow_available,
        },
    )


@router.get("/compare.json")
async def compare_json(
    request: Request,
    experiment: str,
    metric: str = "cost_usd_avg",
):
    """Return comparison data as JSON (for HTMX refresh)."""
    try:
        evaluator = ExperimentEvaluator()
        comparison = evaluator.compare_variants(experiment, metric)

        return {
            "experiment": comparison.experiment_name,
            "metric": comparison.metric,
            "best_variant": comparison.best_variant,
            "variants": [
                {
                    "name": v.variant_name,
                    "run_count": v.run_count,
                    "metrics": v.metrics,
                }
                for v in comparison.variants
            ],
            "mlflow_available": True,
        }

    except (ImportError, FileNotFoundError, OSError) as e:
        logger.warning(f"MLFlow not available or not configured: {e}")
        return {
            "error": "MLFlow is not available or not configured",
            "mlflow_available": False,
        }
    except Exception as e:
        logger.error(f"Failed to get comparison: {e}")
        return {"error": str(e), "mlflow_available": True}


@router.post("/apply")
async def apply_prompt(request: Request, body: ApplyPromptRequest):
    """Apply optimized prompt to workflow configuration."""
    try:
        # Find best variant if not specified
        variant = body.variant
        prompt = None

        try:
            if not variant:
                best = find_best_variant(body.experiment)
                if best:
                    variant = best.get("variant_name")
                    prompt = best.get("prompt")
                else:
                    return Response(
                        content=f"No variants found in experiment '{body.experiment}'",
                        status_code=404
                    )
            else:
                # Get prompt from MLFlow
                evaluator = ExperimentEvaluator()
                best = evaluator.find_best_variant(body.experiment)
                if best and best.get("variant_name") == variant:
                    prompt = best.get("prompt")
        except (ImportError, FileNotFoundError, OSError) as e:
            logger.warning(f"MLFlow not available for prompt lookup: {e}")
            return Response(
                content="MLFlow is not available or not configured. Cannot retrieve prompts.",
                status_code=503
            )

        if not prompt:
            return Response(
                content=f"Could not retrieve prompt for variant '{variant}'",
                status_code=404
            )

        # Apply prompt (or show diff for dry-run)
        if body.dry_run:
            # Read current workflow to show diff
            from pathlib import Path
            import yaml

            workflow_path = Path(body.workflow_path)
            if not workflow_path.exists():
                return Response(
                    content=f"Workflow file not found: {body.workflow_path}",
                    status_code=404
                )

            with open(workflow_path) as f:
                current_config = yaml.safe_load(f)

            # Find current prompt (first node)
            current_prompt = None
            for node in current_config.get("nodes", []):
                if "prompt" in node:
                    current_prompt = node["prompt"]
                    break

            return {
                "success": True,
                "dry_run": True,
                "current_prompt": current_prompt,
                "new_prompt": prompt,
                "variant": variant,
                "workflow_path": body.workflow_path,
            }

        else:
            # Apply the prompt
            backup_path = apply_prompt_to_workflow(
                body.workflow_path,
                prompt,
                backup=True,
            )

            return {
                "success": True,
                "backup_path": backup_path,
                "variant": variant,
                "workflow_path": body.workflow_path,
            }

    except FileNotFoundError as e:
        return Response(
            content=str(e),
            status_code=404
        )
    except Exception as e:
        logger.error(f"Failed to apply prompt: {e}")
        return Response(
            content=str(e),
            status_code=500
        )


# Export helper functions for templates
__all__ = [
    "router",
]
