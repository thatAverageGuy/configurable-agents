import docker
import os
import shutil
import tempfile
from pathlib import Path

def spawn_agent_container(yaml_content: str, agent_name: str, api_key: str):
    """
    Builds and spawns a persistent Docker container for the given agent config.
    """
    client = docker.from_env()
    
    # Clean name for Docker (lowercase, alphanumeric only)
    safe_name = "".join(c for c in agent_name.lower() if c.isalnum())
    image_tag = f"agent-{safe_name}:latest"
    container_name = f"running-{safe_name}"

    # Locate project root (assuming this file is in src/configurable_agents/)
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent.absolute()
    
    # Create a temporary directory for the build context
    with tempfile.TemporaryDirectory() as build_dir:
        build_path = Path(build_dir)
        print(f"Preparing build context in {build_path}...")

        # 1. Copy Source Code & Config Files
        # We need the 'src' folder and 'pyproject.toml' and uv.lock for install
        shutil.copytree(project_root / "src", build_path / "src")
        shutil.copy(project_root / "pyproject.toml", build_path / "pyproject.toml")
        shutil.copy(project_root / "uv.lock", build_path / "uv.lock")
        # 2. Write the Dynamic YAML Flow
        with open(build_path / "flow.yaml", "w", encoding='utf-8') as f:
            f.write(yaml_content)

        # 3. Copy Dockerfile Template
        template_path = project_root / "Dockerfile.template"
        if not template_path.exists():
            raise FileNotFoundError("Dockerfile.template not found in project root")
        shutil.copy(template_path, build_path / "Dockerfile")
        
        # 4. Build the Image
        print(f"Building Docker image: {image_tag}...")
        client.images.build(
            path=str(build_path),
            tag=image_tag,
            rm=True
        )

    # 5. Stop/Remove existing container if it exists
    try:
        old_container = client.containers.get(container_name)
        old_container.stop()
        old_container.remove()
        print(f"Removed existing container: {container_name}")
    except docker.errors.NotFound:
        pass

    # 6. Run the Container
    print(f"Starting container: {container_name}...")
    container = client.containers.run(
        image_tag,
        detach=True,
        ports={'8000/tcp': None},  # Let Docker assign a random host port
        environment={"GOOGLE_API_KEY": api_key},
        name=container_name
    )
    
    # 7. Get the assigned port
    container.reload()
    host_port = container.ports['8000/tcp'][0]['HostPort']
    
    endpoint_url = f"http://localhost:{host_port}"
    print(f"Agent spawned successfully at: {endpoint_url}")
    
    return endpoint_url