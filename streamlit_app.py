# streamlit_app.py
import streamlit as st
import yaml
import json
import subprocess
import tempfile
import time
import socket
from pathlib import Path
from dotenv import load_dotenv
from configurable_agents.runtime import run_workflow_from_config
from configurable_agents.config.schema import WorkflowConfig
from configurable_agents.deploy.generator import generate_deployment_artifacts
from configurable_agents.runtime.executor import validate_workflow

# Load environment variables from .env
load_dotenv()

st.set_page_config(page_title="Workflow Executor", layout="wide")
st.title("🔧 Workflow Executor")

# Initialize session state
if 'workflow_yaml' not in st.session_state:
    st.session_state.workflow_yaml = ""
if 'last_deployment' not in st.session_state:
    st.session_state.last_deployment = None
if 'deploy_settings' not in st.session_state:
    st.session_state.deploy_settings = {
        'container_name': 'workflow-container',
        'api_port': 8000,
        'mlflow_port': 5000,
        'enable_mlflow': True,
        'output_dir': './deploy',
        'sync_timeout': 30
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_port_in_use(port: int) -> bool:
    """Check if TCP port is already in use on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def validate_workflow_config(yaml_text: str) -> tuple[bool, str, WorkflowConfig | None]:
    """
    Validate workflow YAML configuration.

    Returns:
        Tuple of (success, error_message, config_object)
    """
    if not yaml_text.strip():
        return False, "Please provide a workflow YAML configuration", None

    try:
        # Parse YAML
        config_dict = yaml.safe_load(yaml_text)

        # Convert to WorkflowConfig
        config = WorkflowConfig(**config_dict)

        # Additional validation using runtime validator
        # Save to temp file for validation
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_text)
            temp_path = f.name

        try:
            validate_workflow(temp_path)
        finally:
            Path(temp_path).unlink()

        return True, "", config

    except yaml.YAMLError as e:
        return False, f"Invalid YAML syntax: {str(e)}", None
    except Exception as e:
        return False, f"Config validation failed: {str(e)}", None


def validate_env_file_content(content: str) -> tuple[bool, str]:
    """
    Validate environment file content.

    Returns:
        Tuple of (success, error_message)
    """
    if not content.strip():
        return True, ""  # Empty is valid

    for line_num, line in enumerate(content.split('\n'), 1):
        line = line.strip()
        if line and not line.startswith('#') and '=' not in line:
            return False, f"Line {line_num} may be malformed: {line}"

    return True, ""


def sanitize_container_name(name: str) -> str:
    """Sanitize container name to Docker-compatible format."""
    return "".join(
        c if c.isalnum() or c in ("-", "_") else "-"
        for c in name.lower()
    )


def check_docker_available() -> tuple[bool, str]:
    """
    Check if Docker is installed and running.

    Returns:
        Tuple of (available, error_message)
    """
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return False, "Docker daemon is not running. Please start Docker Desktop."
        return True, ""
    except FileNotFoundError:
        return False, "Docker is not installed. Install from: https://docs.docker.com/get-docker/"
    except subprocess.TimeoutExpired:
        return False, "Docker command timed out. Please check if Docker is responding."


def build_docker_image(output_dir: Path, container_name: str) -> tuple[bool, str, float]:
    """
    Build Docker image.

    Returns:
        Tuple of (success, error_message, build_time_seconds)
    """
    build_start = time.time()
    try:
        result = subprocess.run(
            ["docker", "build", "-t", f"{container_name}:latest", str(output_dir)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes
        )

        build_time = time.time() - build_start

        if result.returncode != 0:
            return False, f"Docker build failed:\n{result.stderr}", build_time

        return True, "", build_time

    except subprocess.TimeoutExpired:
        return False, "Docker build timed out after 5 minutes", time.time() - build_start
    except Exception as e:
        return False, f"Build failed: {str(e)}", time.time() - build_start


def run_docker_container(
    container_name: str,
    api_port: int,
    mlflow_port: int,
    env_file_path: Path | None,
    enable_mlflow: bool
) -> tuple[bool, str, str]:
    """
    Run Docker container.

    Returns:
        Tuple of (success, error_message, container_id)
    """
    # Build port arguments
    port_args = ["-p", f"{api_port}:8000"]
    if enable_mlflow and mlflow_port > 0:
        port_args.extend(["-p", f"{mlflow_port}:5000"])

    # Build env file arguments
    env_file_args = []
    if env_file_path and env_file_path.exists():
        env_file_args = ["--env-file", str(env_file_path)]

    # Build docker run command
    docker_run_cmd = [
        "docker", "run", "-d",
        "--name", container_name,
        *port_args,
        *env_file_args,
        f"{container_name}:latest"
    ]

    try:
        result = subprocess.run(
            docker_run_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            stderr = result.stderr.lower()
            if "conflict" in stderr or "already in use" in stderr:
                return False, f"Container '{container_name}' already exists. Remove it with: docker rm -f {container_name}", ""
            else:
                return False, f"Failed to start container:\n{result.stderr}", ""

        container_id = result.stdout.strip()[:12]
        return True, "", container_id

    except subprocess.TimeoutExpired:
        return False, "Container start timed out", ""
    except Exception as e:
        return False, f"Failed to start container: {str(e)}", ""


# ============================================================================
# TABBED INTERFACE
# ============================================================================

tab1, tab2 = st.tabs(["▶️ Run Workflow", "🐳 Deploy to Docker"])

# ============================================================================
# TAB 1: RUN WORKFLOW (Existing Functionality)
# ============================================================================

with tab1:
    # YAML input
    yaml_text = st.text_area(
        "Workflow YAML Configuration:",
        height=300,
        placeholder="Paste your workflow YAML here...",
        key="run_yaml_input"
    )

    # Store in session state for reuse in Deploy tab
    if yaml_text:
        st.session_state.workflow_yaml = yaml_text

    # Inputs
    st.subheader("Inputs")
    inputs_text = st.text_area(
        "Provide inputs (one per line: key=value):",
        height=100,
        placeholder="topic=AI Safety\ncount=5\nenabled=true"
    )

    # Run button
    if st.button("▶️ Run Workflow", type="primary"):
        if not yaml_text.strip():
            st.error("❌ Please provide a workflow YAML configuration")
        else:
            try:
                # Parse YAML to dict
                config_dict = yaml.safe_load(yaml_text)

                # Convert to WorkflowConfig
                config = WorkflowConfig(**config_dict)

                # Parse inputs (same logic as CLI)
                inputs = {}
                if inputs_text.strip():
                    for line in inputs_text.strip().split('\n'):
                        line = line.strip()
                        if not line or '=' not in line:
                            continue
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()

                        # Try JSON parsing for types
                        try:
                            inputs[key] = json.loads(value)
                        except (json.JSONDecodeError, ValueError):
                            inputs[key] = value

                # Execute workflow
                with st.spinner("⚙️ Executing workflow..."):
                    result = run_workflow_from_config(config, inputs)

                # Show success
                st.success("✅ Workflow completed successfully!")
                st.json(result)

            except yaml.YAMLError as e:
                st.error(f"❌ Invalid YAML syntax:\n{str(e)}")
            except Exception as e:
                st.error(f"❌ Execution failed:")
                st.code(str(e), language="text")

    # Instructions
    with st.expander("ℹ️ Instructions"):
        st.markdown("""
        1. Paste your workflow YAML configuration above
        2. Add required inputs (one per line: `key=value`)
        3. Click "Run Workflow"

        **Input parsing:**
        - Strings: `topic=AI Safety`
        - Numbers: `count=5`
        - Booleans: `enabled=true`
        - Lists: `tags=["ai","safety"]`
        - Objects: `config={"key":"value"}`
        """)


# ============================================================================
# TAB 2: DEPLOY TO DOCKER (New Functionality)
# ============================================================================

with tab2:
    st.markdown("### Deploy Workflow as Docker Container")
    st.info("💡 This will package your workflow into a production-ready Docker container with FastAPI endpoints.")

    # Section A: Workflow Configuration
    st.subheader("📝 Workflow Configuration")

    # Pre-populate from Run tab if available
    default_yaml = st.session_state.workflow_yaml if st.session_state.workflow_yaml else ""

    deploy_yaml_text = st.text_area(
        "Workflow YAML Configuration:",
        height=250,
        placeholder="Paste your workflow YAML here...",
        value=default_yaml,
        key="deploy_yaml_input"
    )

    # Section B: Deployment Settings
    st.subheader("⚙️ Deployment Settings")

    col1, col2 = st.columns(2)

    with col1:
        container_name = st.text_input(
            "Container Name",
            value=st.session_state.deploy_settings['container_name'],
            help="Lowercase alphanumeric with dashes/underscores only"
        )
        container_name = sanitize_container_name(container_name)
        st.caption(f"Sanitized name: `{container_name}`")

        api_port = st.number_input(
            "API Port",
            min_value=1024,
            max_value=65535,
            value=st.session_state.deploy_settings['api_port'],
            help="Port for FastAPI endpoints"
        )

        mlflow_port = st.number_input(
            "MLFlow Port",
            min_value=1024,
            max_value=65535,
            value=st.session_state.deploy_settings['mlflow_port'],
            help="Port for MLFlow UI"
        )

    with col2:
        enable_mlflow = st.toggle(
            "Enable MLFlow",
            value=st.session_state.deploy_settings['enable_mlflow'],
            help="Enable MLFlow for experiment tracking"
        )

        output_dir = st.text_input(
            "Output Directory",
            value=st.session_state.deploy_settings['output_dir'],
            help="Directory to store deployment artifacts"
        )

        sync_timeout = st.number_input(
            "Sync Timeout (seconds)",
            min_value=10,
            max_value=300,
            value=st.session_state.deploy_settings['sync_timeout'],
            help="Timeout for workflow execution"
        )

    # Section C: Environment Variables (Optional)
    st.subheader("🔐 Environment Variables (Optional)")

    env_option = st.radio(
        "How would you like to provide environment variables?",
        ["Skip (configure later)", "Upload .env file", "Paste key=value pairs"],
        horizontal=True
    )

    env_file_content = None

    if env_option == "Upload .env file":
        uploaded_file = st.file_uploader(
            "Upload .env file",
            type=['env', 'txt'],
            help="Upload a .env file with KEY=VALUE pairs"
        )
        if uploaded_file:
            env_file_content = uploaded_file.read().decode('utf-8')
            st.code(env_file_content, language="bash")

    elif env_option == "Paste key=value pairs":
        env_file_content = st.text_area(
            "Environment Variables (one per line: KEY=VALUE)",
            height=150,
            placeholder="OPENAI_API_KEY=sk-...\nANTHROPIC_API_KEY=sk-ant-...\nDEBUG=false"
        )

    # Section D: Actions
    st.subheader("🚀 Actions")

    col1, col2 = st.columns(2)

    with col1:
        deploy_button = st.button("🐳 Build & Deploy", type="primary", use_container_width=True)

    with col2:
        generate_button = st.button("📦 Generate Artifacts Only", use_container_width=True)

    # Section E: Deployment Progress
    if deploy_button or generate_button:
        # Validate workflow config
        st.markdown("---")
        st.subheader("📊 Deployment Progress")

        progress_bar = st.progress(0)
        status_text = st.empty()

        # Step 1: Validate workflow config
        status_text.text("⏳ Step 1/7: Validating workflow config...")
        progress_bar.progress(1/7)

        success, error_msg, config = validate_workflow_config(deploy_yaml_text)
        if not success:
            st.error(f"❌ {error_msg}")
            st.info("💡 Fix the YAML configuration and try again.")
            st.stop()

        status_text.text("✅ Step 1/7: Workflow config validated")
        progress_bar.progress(2/7)

        # Step 2: Check Docker availability
        status_text.text("⏳ Step 2/7: Checking Docker availability...")

        docker_available, docker_error = check_docker_available()
        if not docker_available:
            st.error(f"❌ {docker_error}")
            st.stop()

        status_text.text("✅ Step 2/7: Docker is available")
        progress_bar.progress(3/7)

        # Step 3: Check port availability (skip if generate-only)
        if deploy_button:
            status_text.text("⏳ Step 3/7: Checking port availability...")

            if is_port_in_use(api_port):
                st.error(f"❌ Port {api_port} is already in use")
                st.info(f"💡 Choose a different API port or stop the service using port {api_port}")
                st.stop()

            if enable_mlflow and is_port_in_use(mlflow_port):
                st.error(f"❌ Port {mlflow_port} is already in use")
                st.info(f"💡 Choose a different MLFlow port or disable MLFlow")
                st.stop()

            status_text.text("✅ Step 3/7: Ports are available")
        else:
            status_text.text("⏭️ Step 3/7: Skipped (generate-only mode)")

        progress_bar.progress(4/7)

        # Step 4: Validate env file (if provided)
        env_file_path = None
        if env_file_content:
            env_valid, env_error = validate_env_file_content(env_file_content)
            if not env_valid:
                st.error(f"❌ Environment file validation failed: {env_error}")
                st.info("💡 Fix the environment file format and try again.")
                st.stop()

        # Step 5: Generate deployment artifacts
        status_text.text("⏳ Step 4/7: Generating deployment artifacts...")

        try:
            # Save workflow YAML to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(deploy_yaml_text)
                temp_config_path = f.name

            # Generate artifacts
            output_path = Path(output_dir)
            mlflow_port_value = 0 if not enable_mlflow else mlflow_port

            artifacts = generate_deployment_artifacts(
                config_path=temp_config_path,
                output_dir=output_path,
                api_port=api_port,
                mlflow_port=mlflow_port_value,
                sync_timeout=sync_timeout,
                enable_mlflow=enable_mlflow,
                container_name=container_name,
            )

            # Clean up temp file
            Path(temp_config_path).unlink()

            # Save env file if provided
            if env_file_content:
                env_file_path = output_path / ".env"
                env_file_path.write_text(env_file_content)

            status_text.text(f"✅ Step 4/7: Generated {len(artifacts)} deployment artifacts")
            progress_bar.progress(5/7)

            # Show generated files
            with st.expander("📁 Generated Files"):
                for artifact_name, artifact_path in artifacts.items():
                    st.text(f"  {artifact_name}: {artifact_path}")
                if env_file_path:
                    st.text(f"  .env: {env_file_path}")

        except Exception as e:
            st.error(f"❌ Failed to generate artifacts: {str(e)}")
            st.stop()

        # Exit early if generate-only
        if generate_button:
            status_text.text("✅ Artifacts generated successfully!")
            progress_bar.progress(1.0)

            st.success(f"✅ Deployment artifacts generated in: `{output_dir}`")
            st.info(f"💡 To build manually, run:\n```bash\ndocker build -t {container_name}:latest {output_dir}\n```")
            st.stop()

        # Step 6: Build Docker image
        status_text.text("⏳ Step 5/7: Building Docker image...")

        with st.spinner(f"Building image '{container_name}:latest' (this may take 1-2 minutes)..."):
            build_success, build_error, build_time = build_docker_image(output_path, container_name)

        if not build_success:
            st.error(f"❌ {build_error}")
            st.info("💡 Check the Dockerfile and dependencies, then try again.")
            st.stop()

        status_text.text(f"✅ Step 5/7: Image built successfully in {build_time:.1f}s")
        progress_bar.progress(6/7)

        # Step 7: Run container
        status_text.text("⏳ Step 6/7: Starting container...")

        run_success, run_error, container_id = run_docker_container(
            container_name=container_name,
            api_port=api_port,
            mlflow_port=mlflow_port,
            env_file_path=env_file_path,
            enable_mlflow=enable_mlflow
        )

        if not run_success:
            st.error(f"❌ {run_error}")
            st.stop()

        status_text.text(f"✅ Step 6/7: Container started (ID: {container_id})")
        progress_bar.progress(7/7)

        # Step 8: Complete
        status_text.text("✅ Step 7/7: Deployment complete!")
        progress_bar.progress(1.0)

        # Store deployment info in session state
        st.session_state.last_deployment = {
            'container_name': container_name,
            'container_id': container_id,
            'api_port': api_port,
            'mlflow_port': mlflow_port if enable_mlflow else None,
            'enable_mlflow': enable_mlflow
        }

        # Section F: Results Display
        st.markdown("---")
        st.success("🎉 Deployment successful!")

        # Endpoints table
        st.subheader("🌐 Endpoints")

        endpoints_data = {
            "Service": ["API", "Interactive Docs", "Health Check"],
            "URL": [
                f"http://localhost:{api_port}/execute",
                f"http://localhost:{api_port}/docs",
                f"http://localhost:{api_port}/health"
            ]
        }

        if enable_mlflow:
            endpoints_data["Service"].append("MLFlow UI")
            endpoints_data["URL"].append(f"http://localhost:{mlflow_port}")

        st.table(endpoints_data)

        # Example curl commands
        st.subheader("📝 Example Usage")

        curl_example = f"""curl -X POST http://localhost:{api_port}/execute \\
  -H 'Content-Type: application/json' \\
  -d '{{}}'"""

        st.code(curl_example, language="bash")

        # Container management panel
        st.subheader("🔧 Container Management")

        mgmt_col1, mgmt_col2, mgmt_col3 = st.columns(3)

        with mgmt_col1:
            if st.button("📋 View Logs", use_container_width=True):
                try:
                    result = subprocess.run(
                        ["docker", "logs", container_name, "--tail", "50"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    st.code(result.stdout, language="text")
                except Exception as e:
                    st.error(f"Failed to retrieve logs: {str(e)}")

        with mgmt_col2:
            if st.button("⏸️ Stop Container", use_container_width=True):
                try:
                    subprocess.run(
                        ["docker", "stop", container_name],
                        capture_output=True,
                        timeout=30
                    )
                    st.success(f"Container '{container_name}' stopped")
                    st.session_state.last_deployment = None
                except Exception as e:
                    st.error(f"Failed to stop container: {str(e)}")

        with mgmt_col3:
            if st.button("🗑️ Remove Container", use_container_width=True):
                try:
                    subprocess.run(
                        ["docker", "rm", "-f", container_name],
                        capture_output=True,
                        timeout=30
                    )
                    st.success(f"Container '{container_name}' removed")
                    st.session_state.last_deployment = None
                except Exception as e:
                    st.error(f"Failed to remove container: {str(e)}")

        st.markdown("---")
        st.caption("💡 **Tip:** The container runs independently. You can close this Streamlit app and the container will keep running.")

    # Show last deployment info if available
    elif st.session_state.last_deployment:
        st.markdown("---")
        st.info("ℹ️ Previous Deployment Information")

        last = st.session_state.last_deployment
        st.markdown(f"""
        **Container:** `{last['container_name']}` (ID: `{last['container_id']}`)
        **API Endpoint:** http://localhost:{last['api_port']}/execute
        **Documentation:** http://localhost:{last['api_port']}/docs
        """)

        if last['enable_mlflow']:
            st.markdown(f"**MLFlow UI:** http://localhost:{last['mlflow_port']}")

        st.caption("💡 Use the management buttons above after deploying to control the container.")
