# ADR-013: Environment Variable Handling for Deployments

**Status**: Accepted
**Date**: 2026-01-30
**Deciders**: Product team
**Related**: ADR-012 (Docker Deployment)

---

## Context

Docker deployments require API keys for LLM providers (Google, OpenAI) and tools (Serper). These secrets must be:
1. **Secure**: Never baked into images (leak risk, Git commits)
2. **Flexible**: Support CLI users and Streamlit UI users
3. **Simple**: Minimal setup friction
4. **Documented**: Clear security best practices

We support two interfaces:
- **CLI**: Technical users deploying from terminal
- **Streamlit UI**: Non-technical users deploying from web interface

Each interface has different UX constraints and security considerations.

---

## Decision

**Dual interface for environment variables: File-based for CLI, Upload/Paste for Streamlit UI.**

### CLI Interface: File-Based

**Default behavior** (auto-detect `.env`):
```bash
# Looks for .env in current directory
configurable-agents deploy workflow.yaml
```

**Custom file path**:
```bash
configurable-agents deploy workflow.yaml --env-file /path/to/production.env
```

**Skip env file** (manual configuration):
```bash
configurable-agents deploy workflow.yaml --no-env-file
# User must configure via: docker run -e KEY=value ...
```

**File format** (standard `.env`):
```bash
# .env
GOOGLE_API_KEY=AIzaSyC3x...
SERPER_API_KEY=abc123...
OPENAI_API_KEY=sk-proj-...  # Future
```

**Validation**:
```python
# Check file exists (if --env-file specified)
if not env_file.exists():
    error(f"Env file not found: {env_file}")
    exit(1)

# Validate format (basic check)
with open(env_file) as f:
    lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    invalid = [l for l in lines if "=" not in l]
    if invalid:
        warning(f"Invalid lines in {env_file}: {invalid}")
```

### Streamlit UI: Upload or Paste

**Radio button selection**:
```python
env_method = st.radio(
    "How do you want to provide API keys?",
    [
        "Upload .env file",
        "Paste variables",
        "Skip (configure later)"
    ],
    help="API keys needed for LLM providers and tools"
)
```

**Option 1: Upload .env file**:
```python
if env_method == "Upload .env file":
    uploaded_file = st.file_uploader(
        "Upload .env file",
        type=["env", "txt"],
        help="File with KEY=value pairs, one per line"
    )

    if uploaded_file:
        env_content = uploaded_file.read().decode("utf-8")
        st.success(f"✓ Loaded {len(env_content.splitlines())} variables")

        # Preview with masked values (security)
        with st.expander("Preview (values hidden)"):
            preview = "\n".join([
                line.split("=")[0] + "=***" if "=" in line else line
                for line in env_content.splitlines()
            ])
            st.code(preview)

        # Save to temp file for deploy command
        temp_env_path = Path("/tmp/workflow_temp.env")
        temp_env_path.write_text(env_content)
```

**Option 2: Paste variables**:
```python
elif env_method == "Paste variables":
    env_content = st.text_area(
        "Paste environment variables",
        placeholder="GOOGLE_API_KEY=your_key_here\nSERPER_API_KEY=your_key_here",
        height=150,
        help="One per line: KEY=value"
    )

    if env_content:
        var_count = len([l for l in env_content.splitlines() if l.strip() and "=" in l])
        st.success(f"✓ {var_count} variables provided")

        # Validate format
        invalid_lines = [
            l for l in env_content.splitlines()
            if l.strip() and not l.startswith("#") and "=" not in l
        ]
        if invalid_lines:
            st.error(f"❌ Invalid format (missing '='): {invalid_lines}")

        # Save to temp file
        temp_env_path = Path("/tmp/workflow_temp.env")
        temp_env_path.write_text(env_content)
```

**Option 3: Skip**:
```python
else:  # Skip (configure later)
    st.warning("⚠️ Container will start without API keys. Configure via:")
    st.code("docker run -e GOOGLE_API_KEY=xxx -e SERPER_API_KEY=yyy ...")
```

### Security Measures

**1. Never bake into image**:
```dockerfile
# ❌ BAD - Secret in image layer
ENV GOOGLE_API_KEY=AIzaSyC3x...

# ✅ GOOD - Injected at runtime
# (no ENV in Dockerfile for secrets)
```

**2. Pass at runtime**:
```bash
# Via --env-file
docker run --env-file .env my-workflow

# Via -e flags
docker run -e GOOGLE_API_KEY=xxx -e SERPER_API_KEY=yyy my-workflow
```

**3. Never commit to Git**:
```gitignore
# .gitignore (documented in generated README.md)
.env
.env.*
*.env
!.env.example  # Template OK (no secrets)
```

**4. Streamlit temp file cleanup**:
```python
# Clean up temp files after deploy
try:
    # Deploy command runs here
    subprocess.run(["configurable-agents", "deploy", ...])
finally:
    # Always clean up
    if temp_env_path.exists():
        temp_env_path.unlink()
```

**5. Value masking in UI**:
```python
# Preview with masked values
preview = "\n".join([
    line.split("=")[0] + "=***" if "=" in line else line
    for line in env_content.splitlines()
])
st.code(preview)  # Shows: GOOGLE_API_KEY=***
```

---

## Rationale

### Why File-Based for CLI?

**Pros**:
- ✅ Standard pattern (`.env` files ubiquitous in dev)
- ✅ Works with existing tools (docker-compose, dotenv libraries)
- ✅ Easy to manage (one file, version control friendly with `.gitignore`)
- ✅ No interactive input (scriptable, CI/CD friendly)

**Cons**:
- ❌ Users must create `.env` file manually (friction)
  - *Mitigation*: Generate `.env.example` template

### Why Upload/Paste for Streamlit?

**Pros**:
- ✅ No file system access needed (works in browser)
- ✅ Non-technical users can paste from password manager
- ✅ Visual feedback (preview with masking)
- ✅ Temporary (no persistent files on server)

**Cons**:
- ❌ Temp files created (cleanup required)
  - *Mitigation*: Always clean up in `finally` block
- ❌ Risk of logging secrets (Streamlit logs)
  - *Mitigation*: Never log env var values

### Why Not Interactive Prompts?

**Alternative**: CLI prompts for API keys interactively.

```bash
configurable-agents deploy workflow.yaml
Enter GOOGLE_API_KEY: [hidden input]
Enter SERPER_API_KEY: [hidden input]
```

**Rejected because**:
- ❌ Doesn't work in CI/CD (non-interactive environments)
- ❌ Can't script deployments
- ❌ Annoying for repeated deployments
- ❌ Can't version control (harder to reproduce)

### Why Not Secrets Management (Vault, AWS Secrets Manager)?

**Alternative**: Integrate with HashiCorp Vault, AWS Secrets Manager, etc.

**Deferred to v0.2+ because**:
- Adds complexity (auth, setup, dependencies)
- Not all users have Vault/AWS (barrier to entry)
- v0.1 targets local development (production secrets in v0.2+)

**Enterprise path documented**:
```yaml
# Future (v0.2+)
config:
  secrets:
    provider: aws_secrets_manager  # or vault, gcp_secret_manager
    secret_id: "prod/configurable-agents/api-keys"
```

---

## Alternatives Considered

### 1. Bake Secrets into Image (Build-Time)

**Approach**: `docker build --build-arg GOOGLE_API_KEY=xxx`

**Pros**:
- Simple (no runtime injection)

**Cons**:
- ❌ **INSECURE**: Secrets in image layers (forever)
- ❌ Can't rotate keys without rebuild
- ❌ Leaks if image pushed to registry
- ❌ Anti-pattern (Docker best practices)

**Rejected**: Security risk unacceptable.

### 2. Environment Variables from Host (No File)

**Approach**: Deploy command reads from host environment.

```bash
export GOOGLE_API_KEY=xxx
export SERPER_API_KEY=yyy
configurable-agents deploy workflow.yaml  # Reads from host env
```

**Pros**:
- No file management

**Cons**:
- ❌ Pollutes host environment (global variables)
- ❌ Hard to manage multiple deployments (different keys)
- ❌ Not explicit (hidden dependency on host env)

**Rejected**: File-based is more explicit and manageable.

### 3. Prompt Once, Store in ~/.config

**Approach**: First deploy prompts for keys, stores in `~/.config/configurable-agents/secrets`.

**Pros**:
- Only enter keys once

**Cons**:
- ❌ Security risk (keys on disk, unencrypted)
- ❌ Can't have per-project keys (all workflows share)
- ❌ Rotation requires manual file edit

**Rejected**: File-based `.env` per project is safer and more flexible.

### 4. Required --env-file Flag (No Auto-Detect)

**Approach**: Make `--env-file` required (no default `.env` lookup).

```bash
configurable-agents deploy workflow.yaml --env-file .env  # Required
```

**Pros**:
- Explicit (no magic)

**Cons**:
- ❌ Extra friction (users must type flag every time)
- ❌ Default `.env` is standard convention

**Rejected**: Auto-detect `.env` follows conventions (less friction).

---

## Security Best Practices (Documented)

### For Users

**Generated README.md includes**:

```markdown
## Security Best Practices

### ⚠️ Never Commit Secrets to Git

Add to `.gitignore`:
```gitignore
.env
.env.*
*.env
```

### ✅ Use .env.example for Templates

Commit a template (no real keys):
```bash
# .env.example
GOOGLE_API_KEY=your_key_here
SERPER_API_KEY=your_key_here
```

Team members copy and fill in:
```bash
cp .env.example .env
# Edit .env with real keys
```

### 🔒 Rotate Keys Regularly

Update `.env` and restart container:
```bash
docker stop my-workflow
docker rm my-workflow
configurable-agents deploy workflow.yaml  # Uses updated .env
```

### 🏢 Production Secrets Management

For production deployments, use:
- **AWS Secrets Manager**: Centralized, audited, rotated
- **HashiCorp Vault**: Self-hosted, enterprise-grade
- **GCP Secret Manager**: Google Cloud native

Example (v0.2+):
```bash
# Fetch from AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id prod/api-keys | \
  jq -r '.SecretString' > .env

# Deploy with fetched secrets
configurable-agents deploy workflow.yaml
```

### 🔍 Audit Container Logs

Container logs may expose env var values in error messages.

**Avoid**:
```python
print(f"Error: API key {os.getenv('GOOGLE_API_KEY')} is invalid")
```

**Instead**:
```python
print("Error: GOOGLE_API_KEY is invalid")
```

### 🚫 Don't Share .env Files

Send `.env.example` to team, not `.env`.
Use password manager for secure sharing if needed.
```

---

## Implementation Details

### CLI Validation Logic

```python
# src/configurable_agents/cli.py (deploy command)

def validate_env_file(env_file: Path, required: bool = False) -> Optional[Path]:
    """
    Validate env file exists and has correct format.

    Args:
        env_file: Path to .env file
        required: If True, fail if file doesn't exist

    Returns:
        Path to env file if valid, None if optional and missing

    Raises:
        click.ClickException if validation fails
    """
    if not env_file.exists():
        if required:
            raise click.ClickException(f"Env file not found: {env_file}")
        else:
            return None  # Optional

    # Validate format
    try:
        with open(env_file) as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
            invalid = [l for l in lines if "=" not in l]

            if invalid:
                click.echo(
                    f"⚠️  Warning: Invalid lines in {env_file} (missing '='):\n"
                    f"    {invalid}",
                    err=True
                )

        return env_file

    except Exception as e:
        raise click.ClickException(f"Failed to read env file: {e}")


@click.command()
@click.argument("workflow_path", type=click.Path(exists=True))
@click.option("--env-file", default=".env", help="Environment variables file")
@click.option("--no-env-file", is_flag=True, help="Skip env file")
def deploy(workflow_path, env_file, no_env_file, ...):
    """Deploy workflow as Docker container"""

    # Handle env file
    env_file_path = None

    if no_env_file:
        click.echo("⚠️  Skipping env file (configure via docker run -e)")
    else:
        env_file_path = validate_env_file(
            Path(env_file),
            required=(env_file != ".env")  # .env is optional, custom path is required
        )

        if env_file_path:
            click.echo(f"✓ Using env file: {env_file_path}")
        else:
            click.echo("ℹ️  No .env file found (optional)")

    # ... proceed with deployment ...
```

### Streamlit Temp File Management

```python
# streamlit_app.py

import tempfile
from pathlib import Path

def deploy_workflow(config_text, env_content, port, name, ...):
    """Deploy workflow with cleanup"""
    temp_config = None
    temp_env = None

    try:
        # Save config to temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False
        ) as f:
            f.write(config_text)
            temp_config = Path(f.name)

        # Save env vars to temp file (if provided)
        if env_content:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.env',
                delete=False
            ) as f:
                f.write(env_content)
                temp_env = Path(f.name)

        # Build deploy command
        cmd = ["configurable-agents", "deploy", str(temp_config)]

        if temp_env:
            cmd.extend(["--env-file", str(temp_env)])
        else:
            cmd.append("--no-env-file")

        # Execute deployment
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180
        )

        return result

    finally:
        # Always clean up temp files
        if temp_config and temp_config.exists():
            temp_config.unlink()
        if temp_env and temp_env.exists():
            temp_env.unlink()
```

### Generated .env.example

```bash
# .env.example
# Copy to .env and fill in your API keys

# Google Gemini API Key (required)
# Get yours at: https://makersuite.google.com/app/apikey
GOOGLE_API_KEY=your_google_api_key_here

# Serper Search API Key (required if using serper_search tool)
# Get yours at: https://serper.dev/
SERPER_API_KEY=your_serper_api_key_here

# OpenAI API Key (future, v0.2+)
# OPENAI_API_KEY=your_openai_api_key_here

# Anthropic API Key (future, v0.2+)
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

---

## Consequences

### Positive

1. **Secure by default**: Secrets never baked into images
2. **Flexible**: Supports CLI and UI workflows
3. **Standard conventions**: `.env` files are industry standard
4. **Scriptable**: File-based approach works in CI/CD
5. **User-friendly**: Streamlit upload/paste for non-technical users
6. **Documented**: Clear security best practices in README

### Negative

1. **File management**: Users must create/manage `.env` files
   - *Mitigation*: Generate `.env.example` template
2. **Temp files in Streamlit**: Risk if cleanup fails
   - *Mitigation*: Use `finally` block for cleanup
3. **No rotation automation**: Users must manually update `.env`
   - *Future*: Integrate secrets managers in v0.2+

### Neutral

1. **No interactive prompts**: Good for automation, but some users prefer prompts
2. **Optional .env**: May confuse users if deploy succeeds without keys (fails at runtime)
   - *Mitigation*: Warning message when no env file detected

---

## Future Enhancements (v0.2+)

1. **Secrets Managers Integration**:
   ```bash
   configurable-agents deploy workflow.yaml --secrets aws-secrets-manager
   ```

2. **Encrypted .env Files**:
   ```bash
   # Encrypt with password
   configurable-agents secrets encrypt .env > .env.encrypted

   # Deploy with decryption
   configurable-agents deploy workflow.yaml --encrypted-env .env.encrypted
   ```

3. **Per-Workflow Key Overrides**:
   ```yaml
   # workflow.yaml
   config:
     secrets:
       GOOGLE_API_KEY: "${WORKFLOW_GOOGLE_KEY}"  # Override default
   ```

4. **Key Validation at Deploy Time**:
   ```bash
   # Test API keys before building image
   configurable-agents deploy workflow.yaml --validate-keys
   ```

---

## References

- Docker Secrets: https://docs.docker.com/engine/swarm/secrets/
- 12-Factor App (Config): https://12factor.net/config
- OWASP Secrets Management: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html
- AWS Secrets Manager: https://aws.amazon.com/secrets-manager/
- HashiCorp Vault: https://www.vaultproject.io/

---

## Supersedes

None (first secrets management decision)

---

## Implementation Planning

**Status**: ⏳ Planned for v0.1 (not yet implemented)
**Related Tasks**: T-024 (CLI Deploy Command & Streamlit Integration)
**Target Date**: February 2026
**Estimated Effort**: Included in T-024 (2 days)

### Implementation Details

**CLI Interface** (part of T-024):
- `--env-file` flag for deploy command
- Auto-detect `.env` if exists
- Inject into container via `docker run --env-file`
- Never bake into image layers

**Streamlit UI** (part of T-024):
- File upload widget for .env files
- Textarea for pasting key=value pairs
- Preview with masked values
- Same security: runtime injection only

### Current State

**Completed**:
- ✅ Dual interface approach decided (this ADR)
- ✅ Security strategy defined (runtime injection, never baked)
- ✅ Integration with deployment flow designed

**Not Started**:
- ⏳ CLI --env-file implementation
- ⏳ Streamlit upload/paste UI
- ⏳ Runtime injection logic

**Next Steps**: Implemented as part of T-024 (after T-022, T-023)

---

## Related Decisions

- **ADR-012**: Docker deployment architecture (env var injection)
- **Future ADR**: Secrets management integration (v0.2)
