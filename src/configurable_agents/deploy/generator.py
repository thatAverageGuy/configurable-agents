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
        enable_registry: bool = False,
        registry_url: str | None = None,
        agent_id: str | None = None,
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
            enable_registry: Enable agent registry integration (default: False)
            registry_url: URL of agent registry server (required if enable_registry=True)
            agent_id: Agent ID for registry (default: workflow name)

        Returns:
            Dict mapping artifact names to generated file paths

        Raises:
            FileNotFoundError: If template files are missing
            ValueError: If output_dir is not a directory or registry enabled but URL missing
        """
        # Validate registry parameters
        if enable_registry and not registry_url:
            raise ValueError("registry_url is required when enable_registry=True")

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
            enable_registry=enable_registry,
            registry_url=registry_url or "",
            agent_id=agent_id or self.config.flow.name,
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

        # 9. Copy source code for local installation
        artifacts["src/"] = self._copy_source_code(output_dir)

        # 10. Copy pyproject.toml for package installation
        artifacts["pyproject.toml"] = self._copy_pyproject_toml(output_dir / "pyproject.toml")

        return artifacts

    def _build_template_variables(
        self,
        api_port: int,
        mlflow_port: int,
        sync_timeout: int,
        enable_mlflow: bool,
        container_name: str,
        enable_registry: bool = False,
        registry_url: str = "",
        agent_id: str = "",
    ) -> Dict[str, Any]:
        """
        Build template variable dictionary.

        Args:
            api_port: FastAPI server port
            mlflow_port: MLFlow UI port
            sync_timeout: Sync/async threshold in seconds
            enable_mlflow: Include MLFlow UI
            container_name: Container/image name
            enable_registry: Enable agent registry integration
            registry_url: Agent registry server URL
            agent_id: Agent ID for registry

        Returns:
            Dictionary of template variables for substitution
        """
        workflow_name = self.config.flow.name
        workflow_version = self.config.flow.version or "1.0.0"

        # CMD line for Dockerfile (with or without MLFlow)
        # Note: MLFlow always runs on port 5000 INSIDE container
        # The mlflow_port parameter is only for HOST-side port mapping
        if enable_mlflow and mlflow_port > 0:
            cmd_line = (
                "CMD mlflow ui --host 0.0.0.0 --port 5000 "
                "--backend-store-uri sqlite:///app/mlflow.db & python server.py"
            )
            mlflow_requirement = "mlflow>=3.9.0"
        else:
            cmd_line = "CMD python server.py"
            mlflow_requirement = "# mlflow disabled"

        # Build example input from state schema
        example_input = self._build_example_input()

        # Package version (read from pyproject.toml or default)
        package_version = self._get_package_version()

        # Registry-related template variables
        # Generate code blocks that are either populated or empty based on enable_registry
        if enable_registry:
            registry_import = "from configurable_agents.registry import AgentRegistryClient"
            heartbeat_interval = 20  # Default: TTL (60) / 3
            registry_client_init = f"""# Agent registry client
registry_client = AgentRegistryClient(
    registry_url="{registry_url}",
    agent_id="{agent_id}",
    ttl_seconds=60,
    heartbeat_interval={heartbeat_interval},
)"""
            registry_startup_handler = """@app.on_event("startup")
async def registry_startup():
    '''Register with agent registry and start heartbeat loop.'''
    try:
        await registry_client.register()
        await registry_client.start_heartbeat_loop()
        print(f"Registered agent '{agent_id}' with registry at {registry_url}")
    except Exception as e:
        print(f"Warning: Failed to register with agent registry: {e}")"""
            registry_shutdown_handler = """@app.on_event("shutdown")
async def registry_shutdown():
    '''Deregister from agent registry on shutdown.'''
    try:
        await registry_client.deregister()
        print(f"Deregistered agent '{agent_id}' from registry")
    except Exception as e:
        print(f"Warning: Failed to deregister from agent registry: {e}")"""
            health_check_endpoints = """

@app.get("/health/live")
async def health_live():
    '''Liveness probe - agent is running.'''
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready():
    '''Readiness probe - agent is ready to accept requests.'''
    return {"status": "ready"}"""
        else:
            registry_import = ""
            registry_client_init = "# Agent registry disabled"
            registry_startup_handler = ""
            registry_shutdown_handler = ""
            health_check_endpoints = ""

        # VF-003: Conditional MLflow fragments for templates
        if enable_mlflow and mlflow_port > 0:
            compose_mlflow_port = f'      - "{mlflow_port}:5000"'
            compose_mlflow_volume = "      - ./mlflow.db:/app/mlflow.db"
            compose_mlflow_comment = "      # Persist MLFlow data across container restarts"
            dockerfile_expose = "EXPOSE 8000 5000"
            dockerfile_mlflow_dir_comment = "# Create data directory for MLflow SQLite DB"
            dockerfile_cmd_comment = "# Start server (MLFlow UI in background if enabled, FastAPI in foreground)"
        else:
            compose_mlflow_port = ""
            compose_mlflow_volume = ""
            compose_mlflow_comment = ""
            dockerfile_expose = "EXPOSE 8000"
            dockerfile_mlflow_dir_comment = "# Create data directory"
            dockerfile_cmd_comment = "# Start server"

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
            # MLflow conditional fragments
            "compose_mlflow_port": compose_mlflow_port,
            "compose_mlflow_volume": compose_mlflow_volume,
            "compose_mlflow_comment": compose_mlflow_comment,
            "dockerfile_expose": dockerfile_expose,
            "dockerfile_mlflow_dir_comment": dockerfile_mlflow_dir_comment,
            "dockerfile_cmd_comment": dockerfile_cmd_comment,
            # Registry variables
            "registry_enabled": str(enable_registry).lower(),
            "registry_import": registry_import,
            "registry_client_init": registry_client_init,
            "registry_startup_handler": registry_startup_handler,
            "registry_shutdown_handler": registry_shutdown_handler,
            "health_check_endpoints": health_check_endpoints,
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

    def _copy_source_code(self, output_dir: Path) -> Path:
        """
        Copy configurable-agents source code to output directory.

        Args:
            output_dir: Output directory

        Returns:
            Path to copied src directory
        """
        # Find project root (where pyproject.toml is)
        project_root = Path(__file__).parents[3]
        src_dir = project_root / "src"

        if not src_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {src_dir}")

        # Copy entire src/ directory
        dest_src_dir = output_dir / "src"
        if dest_src_dir.exists():
            shutil.rmtree(dest_src_dir)

        shutil.copytree(src_dir, dest_src_dir)

        return dest_src_dir

    def _copy_pyproject_toml(self, output_path: Path) -> Path:
        """
        Copy pyproject.toml to output directory, stripping invalid script entries.

        The main pyproject.toml may contain non-PEP-517 script entries (e.g.
        "docs:build") that are shell commands rather than Python entry points.
        These break ``pip install`` in Docker where strict validation is enforced.
        This method removes any script entry whose value is not a valid
        Python entry point reference (must contain a colon-separated module path).

        Args:
            output_path: Output file path

        Returns:
            Path to copied file
        """
        # Find project root (where pyproject.toml is)
        project_root = Path(__file__).parents[3]
        pyproject_path = project_root / "pyproject.toml"

        if not pyproject_path.exists():
            raise FileNotFoundError(f"pyproject.toml not found: {pyproject_path}")

        # Read, sanitize invalid script entries, then write
        content = pyproject_path.read_text(encoding="utf-8")

        # Remove script lines whose values aren't Python entry points.
        # Valid entry point: "name = \"module.path:func\""
        # Invalid: "docs:build = \"sphinx-build ...\""
        sanitized_lines = []
        in_scripts = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped == "[project.scripts]":
                in_scripts = True
                sanitized_lines.append(line)
                continue
            if in_scripts:
                if stripped.startswith("["):
                    # Entered a new section
                    in_scripts = False
                    sanitized_lines.append(line)
                    continue
                if "=" in stripped and not stripped.startswith("#"):
                    # Check if the value looks like a Python entry point (module:attr)
                    _, _, value = stripped.partition("=")
                    value = value.strip().strip('"').strip("'")
                    # A valid entry point contains a module path with a colon
                    # e.g. "configurable_agents.cli:main"
                    # Invalid ones look like shell commands: "sphinx-build ..."
                    if ":" in value and " " not in value:
                        sanitized_lines.append(line)
                    # else: skip invalid entry
                    continue
            sanitized_lines.append(line)

        output_path.write_text("\n".join(sanitized_lines) + "\n", encoding="utf-8")

        return output_path


def generate_deployment_artifacts(
    config_path: str | Path,
    output_dir: str | Path,
    api_port: int = 8000,
    mlflow_port: int = 5000,
    sync_timeout: int = 30,
    enable_mlflow: bool = True,
    container_name: str | None = None,
    enable_registry: bool = False,
    registry_url: str | None = None,
    agent_id: str | None = None,
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
        enable_registry: Enable agent registry integration (default: False)
        registry_url: URL of agent registry server (required if enable_registry=True)
        agent_id: Agent ID for registry (default: workflow name)

    Returns:
        Dict mapping artifact names to generated file paths

    Raises:
        FileNotFoundError: If config file or templates are missing
        ValidationError: If workflow config is invalid
        ValueError: If registry enabled but URL missing

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
        enable_registry=enable_registry,
        registry_url=registry_url,
        agent_id=agent_id,
    )

    return artifacts
