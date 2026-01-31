"""
Docker deployment artifact generator.

Generates production-ready Docker containers with FastAPI servers for workflow deployment.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Any, Dict

from configurable_agents.config import WorkflowConfig, parse_config_file


class DeploymentArtifactGenerator:
    """Generates Docker deployment artifacts from workflow config"""

    def __init__(self, workflow_config: WorkflowConfig):
        """
        Initialize generator.

        Args:
            workflow_config: Parsed and validated workflow configuration
        """
        self.config = workflow_config
        self.templates_dir = Path(__file__).parent / "templates"

    def generate(
        self,
        output_dir: Path,
        api_port: int = 8000,
        mlflow_port: int = 5000,
        sync_timeout: int = 30,
        enable_mlflow: bool = True,
        container_name: str | None = None,
    ) -> Dict[str, Path]:
        """
        Generate all deployment artifacts.

        Args:
            output_dir: Directory to write generated files
            api_port: FastAPI server port (default: 8000)
            mlflow_port: MLFlow UI port (default: 5000, 0 to disable)
            sync_timeout: Sync/async threshold in seconds (default: 30)
            enable_mlflow: Include MLFlow UI in container (default: True)
            container_name: Container/image name (default: workflow name)

        Returns:
            Dict mapping artifact names to generated file paths

        Raises:
            FileNotFoundError: If template files are missing
            ValueError: If output_dir is not a directory
        """
        # Validate output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build template variables
        variables = self._build_template_variables(
            api_port=api_port,
            mlflow_port=mlflow_port,
            sync_timeout=sync_timeout,
            enable_mlflow=enable_mlflow,
            container_name=container_name or self.config.flow.name,
        )

        # Generate artifacts
        artifacts = {}

        # 1. Dockerfile
        artifacts["Dockerfile"] = self._generate_from_template(
            "Dockerfile.template", output_dir / "Dockerfile", variables
        )

        # 2. FastAPI server
        artifacts["server.py"] = self._generate_from_template(
            "server.py.template", output_dir / "server.py", variables
        )

        # 3. requirements.txt
        artifacts["requirements.txt"] = self._generate_from_template(
            "requirements.txt.template", output_dir / "requirements.txt", variables
        )

        # 4. docker-compose.yml
        artifacts["docker-compose.yml"] = self._generate_from_template(
            "docker-compose.yml.template", output_dir / "docker-compose.yml", variables
        )

        # 5. .env.example
        artifacts[".env.example"] = self._generate_from_template(
            ".env.example.template", output_dir / ".env.example", variables
        )

        # 6. README.md
        artifacts["README.md"] = self._generate_from_template(
            "README.md.template", output_dir / "README.md", variables
        )

        # 7. .dockerignore (static, no substitution)
        artifacts[".dockerignore"] = self._copy_static_file(
            ".dockerignore", output_dir / ".dockerignore"
        )

        # 8. workflow.yaml (copy original config)
        artifacts["workflow.yaml"] = self._copy_workflow_config(output_dir / "workflow.yaml")

        return artifacts

    def _build_template_variables(
        self,
        api_port: int,
        mlflow_port: int,
        sync_timeout: int,
        enable_mlflow: bool,
        container_name: str,
    ) -> Dict[str, Any]:
        """
        Build template variable dictionary.

        Args:
            api_port: FastAPI server port
            mlflow_port: MLFlow UI port
            sync_timeout: Sync/async threshold in seconds
            enable_mlflow: Include MLFlow UI
            container_name: Container/image name

        Returns:
            Dictionary of template variables for substitution
        """
        workflow_name = self.config.flow.name
        workflow_version = self.config.flow.version or "1.0.0"

        # CMD line for Dockerfile (with or without MLFlow)
        if enable_mlflow and mlflow_port > 0:
            cmd_line = (
                f"CMD mlflow ui --host 0.0.0.0 --port {mlflow_port} "
                f"--backend-store-uri file:///app/mlruns & python server.py"
            )
            mlflow_requirement = "mlflow>=2.9.0"
        else:
            cmd_line = "CMD python server.py"
            mlflow_requirement = "# mlflow disabled"

        # Build example input from state schema
        example_input = self._build_example_input()

        # Package version (read from pyproject.toml or default)
        package_version = self._get_package_version()

        return {
            "workflow_name": workflow_name,
            "workflow_version": workflow_version,
            "container_name": container_name,
            "api_port": str(api_port),
            "mlflow_port": str(mlflow_port),
            "sync_timeout": str(sync_timeout),
            "cmd_line": cmd_line,
            "mlflow_requirement": mlflow_requirement,
            "example_input": example_input,
            "package_version": package_version,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    def _build_example_input(self) -> str:
        """
        Build example JSON input from state schema.

        Returns:
            JSON string with example inputs
        """
        example = {}
        for field_name, field_def in self.config.state.fields.items():
            if field_def.required:
                # Generate example value based on type
                if field_def.type == "str":
                    example[field_name] = f"example_{field_name}"
                elif field_def.type == "int":
                    example[field_name] = 1
                elif field_def.type == "float":
                    example[field_name] = 1.0
                elif field_def.type == "bool":
                    example[field_name] = True
                elif field_def.type.startswith("list"):
                    example[field_name] = []
                elif field_def.type.startswith("dict"):
                    example[field_name] = {}
                else:
                    example[field_name] = None

        return json.dumps(example, indent=2)

    def _get_package_version(self) -> str:
        """
        Get configurable-agents package version.

        Returns:
            Version string (e.g., "0.1.0" or "0.1.0-dev")
        """
        try:
            # Try importing version from package
            from configurable_agents import __version__

            return __version__
        except (ImportError, AttributeError):
            # Fallback to reading pyproject.toml
            try:
                import tomli

                pyproject_path = Path(__file__).parents[3] / "pyproject.toml"
                with open(pyproject_path, "rb") as f:
                    pyproject = tomli.load(f)
                return pyproject["project"]["version"]
            except Exception:
                # Last resort: hardcoded fallback
                return "0.1.0-dev"

    def _generate_from_template(
        self, template_name: str, output_path: Path, variables: Dict[str, Any]
    ) -> Path:
        """
        Generate file from template with variable substitution.

        Args:
            template_name: Template filename (e.g., "Dockerfile.template")
            output_path: Output file path
            variables: Template variables for substitution

        Returns:
            Path to generated file

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        template_path = self.templates_dir / template_name

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        # Read template
        template_content = template_path.read_text(encoding="utf-8")

        # Substitute variables
        template = Template(template_content)
        try:
            generated_content = template.substitute(variables)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")

        # Write output
        output_path.write_text(generated_content, encoding="utf-8")

        return output_path

    def _copy_static_file(self, filename: str, output_path: Path) -> Path:
        """
        Copy static file (no template substitution).

        Args:
            filename: Source filename in templates directory
            output_path: Output file path

        Returns:
            Path to copied file

        Raises:
            FileNotFoundError: If source file doesn't exist
        """
        source_path = self.templates_dir / filename

        if not source_path.exists():
            raise FileNotFoundError(f"Static file not found: {source_path}")

        shutil.copy2(source_path, output_path)

        return output_path

    def _copy_workflow_config(self, output_path: Path) -> Path:
        """
        Copy workflow config to output directory.

        Args:
            output_path: Output file path

        Returns:
            Path to copied file
        """
        # Serialize config back to YAML
        import yaml

        config_dict = self.config.model_dump(mode="json", exclude_none=True)
        output_path.write_text(yaml.dump(config_dict, sort_keys=False), encoding="utf-8")

        return output_path


def generate_deployment_artifacts(
    config_path: str | Path,
    output_dir: str | Path,
    api_port: int = 8000,
    mlflow_port: int = 5000,
    sync_timeout: int = 30,
    enable_mlflow: bool = True,
    container_name: str | None = None,
) -> Dict[str, Path]:
    """
    Generate Docker deployment artifacts from workflow config.

    Convenience function that loads config and generates artifacts.

    Args:
        config_path: Path to workflow YAML/JSON config
        output_dir: Directory to write generated files
        api_port: FastAPI server port (default: 8000)
        mlflow_port: MLFlow UI port (default: 5000, 0 to disable)
        sync_timeout: Sync/async threshold in seconds (default: 30)
        enable_mlflow: Include MLFlow UI in container (default: True)
        container_name: Container/image name (default: workflow name)

    Returns:
        Dict mapping artifact names to generated file paths

    Raises:
        FileNotFoundError: If config file or templates are missing
        ValidationError: If workflow config is invalid

    Example:
        >>> artifacts = generate_deployment_artifacts(
        ...     "workflow.yaml",
        ...     "./deploy",
        ...     api_port=8000,
        ...     mlflow_port=5000
        ... )
        >>> print(artifacts)
        {
            'Dockerfile': PosixPath('deploy/Dockerfile'),
            'server.py': PosixPath('deploy/server.py'),
            ...
        }
    """
    # Load and validate workflow config
    config_dict = parse_config_file(str(config_path))
    workflow_config = WorkflowConfig(**config_dict)

    # Generate artifacts
    generator = DeploymentArtifactGenerator(workflow_config)
    artifacts = generator.generate(
        output_dir=Path(output_dir),
        api_port=api_port,
        mlflow_port=mlflow_port,
        sync_timeout=sync_timeout,
        enable_mlflow=enable_mlflow,
        container_name=container_name,
    )

    return artifacts
