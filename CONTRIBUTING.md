# Contributing to Configurable Agents

Thank you for your interest in contributing to Configurable Agents! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Quick Start](#quick-start)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Commit Message Conventions](#commit-message-conventions)
- [Getting Help](#getting-help)

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Git
- A GitHub account

### Setup (15 minutes)

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/configurable-agents.git
cd configurable-agents

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate the virtual environment
# On Unix/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# 4. Install in development mode
pip install -e ".[dev]"

# 5. Verify setup
pytest tests/ -v
black --check src/
ruff check src/
mypy src/
```

If all commands pass, you're ready to contribute!

## Development Workflow

### 1. Fork and Clone

Fork the repository on GitHub and clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/configurable-agents.git
cd configurable-agents
```

### 2. Create a Feature Branch

Create a new branch for your contribution:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions or changes

### 3. Make Changes

Make your changes following the [Code Standards](#code-standards) below.

### 4. Test Your Changes

Run tests and code quality checks:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/runtime/test_executor.py -v

# Run with coverage
pytest tests/ --cov=configurable_agents --cov-report=html

# Format code
black src/ tests/

# Check formatting
black --check src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

### 5. Commit Your Changes

Follow the [Commit Message Conventions](#commit-message-conventions):

```bash
git add .
git commit -m "feat(runtime): add support for parallel execution"
```

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub following the [Pull Request Process](#pull-request-process).

## Code Standards

### Python Version

- **Minimum**: Python 3.10
- **Tested**: Python 3.10, 3.11, 3.12

### Type Hints

Type hints are **required** for all public functions and methods:

```python
from typing import Optional
from pathlib import Path

def run_workflow(
    config_path: str | Path,
    timeout: Optional[int] = None,
) -> dict:
    """Execute a workflow from a configuration file.

    Args:
        config_path: Path to YAML or JSON configuration file.
        timeout: Maximum execution time in seconds.

    Returns:
        Dictionary containing workflow results.
    """
    ...
```

### Code Formatting

We use **Black** for code formatting:

```bash
# Format code
black src/ tests/

# Check formatting
black --check src/ tests/
```

**Configuration**:
- Line length: 100 characters
- Target versions: Python 3.10, 3.11, 3.12

### Linting

We use **Ruff** for linting:

```bash
# Lint code
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/
```

**Enabled rules**:
- `E` - pycodestyle errors
- `W` - pycodestyle warnings
- `F` - pyflakes
- `I` - isort (import sorting)
- `B` - flake8-bugbear
- `C4` - flake8-comprehensions

### Type Checking

We use **MyPy** for static type checking:

```bash
# Type check
mypy src/
```

**Configuration**:
- Python version: 3.10
- Strict mode: Enabled
- `disallow_untyped_defs`: Enabled

### Docstrings

Use **Google style** docstrings:

```python
def validate_workflow(config_path: str | Path) -> bool:
    """Validate a workflow configuration without execution.

    This function loads and validates the workflow configuration,
    checking for schema compliance, reference integrity, and
    configuration best practices.

    Args:
        config_path: Path to YAML or JSON configuration file.

    Returns:
        True if configuration is valid, False otherwise.

    Raises:
        ConfigLoadError: If configuration file cannot be parsed.
        ConfigValidationError: If configuration fails validation.

    Examples:
        Validate a simple workflow:

        >>> from configurable_agents.runtime import validate_workflow
        >>> is_valid = validate_workflow("examples/simple.yaml")
        >>> if is_valid:
        ...     print("Configuration is valid!")
    """
```

## Testing Requirements

### Test Structure

Tests are organized by module:

```
tests/
├── config/              # Configuration tests
├── core/                # Core functionality tests
├── runtime/             # Runtime execution tests
├── llm/                 # LLM provider tests
├── tools/               # Tool tests
├── integration/         # End-to-end tests
└── conftest.py          # Shared fixtures
```

### Writing Tests

**Unit Tests**:
- Test individual functions and classes
- Use mocks for external dependencies
- Fast execution (< 1 second per test)

```python
import pytest
from configurable_agents.config import parse_config_file

def test_parse_valid_config():
    """Test parsing a valid configuration file."""
    config = parse_config_file("examples/echo.yaml")
    assert config.name == "echo"
    assert len(config.nodes) == 1
```

**Integration Tests**:
- Test multiple components working together
- May require API keys (use `@pytest.mark.integration`)
- Slower execution

```python
import pytest
from configurable_agents.runtime import run_workflow

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="Requires GOOGLE_API_KEY"
)
def test_run_workflow_with_llm():
    """Test running a workflow with LLM execution."""
    result = run_workflow("examples/simple_workflow.yaml")
    assert result["final_output"] is not None
```

### Test Coverage

**Target coverage**: 80%+ for new code

```bash
# Run tests with coverage
pytest tests/ --cov=configurable_agents --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Test Execution

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/ -v -m "not integration"

# Run integration tests only
pytest tests/ -v -m integration

# Run specific test file
pytest tests/runtime/test_executor.py -v

# Run specific test
pytest tests/runtime/test_executor.py::test_run_workflow -v

# Run with coverage
pytest tests/ --cov=configurable_agents --cov-report=html

# Skip slow tests
pytest tests/ -v -m "not slow"
```

## Pull Request Process

### Creating a Pull Request

1. **Update your branch**: `git pull upstream main`
2. **Push changes**: `git push origin feature/your-feature-name`
3. **Create PR** on GitHub with:
   - Clear title following commit conventions
   - Description using the PR template
   - Link to related issues

### Pull Request Template

```markdown
## Description
Brief description of changes (1-2 sentences)

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated (if applicable)
- [ ] All tests passing locally
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines (Black, Ruff, MyPy)
- [ ] Self-review completed
- [ ] Documentation updated (if applicable)
- [ ] No new warnings generated
- [ ] Added tests for changes
- [ ] All tests passing
```

### Review Criteria

Pull requests are reviewed based on:
- **Code quality**: Follows style guidelines, well-documented
- **Testing**: Adequate test coverage, tests pass
- **Functionality**: Works as intended, no regressions
- **Documentation**: Updated for user-facing changes
- **Breaking changes**: Clearly documented and justified

### Approval Requirements

- At least one maintainer approval required
- All CI checks must pass
- No unresolved review comments

## Commit Message Conventions

Follow the **Conventional Commits** specification:

```
type(scope): description

[optional body]

[optional footer]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or changes
- `refactor`: Code refactoring (no functional changes)
- `chore`: Maintenance tasks
- `perf`: Performance improvements
- `style`: Code style changes (formatting, etc.)

### Scopes

Common scopes:
- `runtime`: Runtime execution
- `config`: Configuration and validation
- `core`: Core functionality
- `llm`: LLM providers
- `tools`: Tool system
- `observability`: MLFlow and monitoring
- `ui`: User interface components
- `docs`: Documentation

### Examples

```
feat(runtime): add support for parallel node execution

Implement parallel execution for independent nodes using
LangGraph's Send API. This improves performance for workflows
with multiple independent nodes.

Closes #123

fix(config): handle missing required fields in validation

Add proper error messages when required fields are missing
from workflow configuration. Previously would raise generic
ValidationError.

Fixes #145

docs(api): add API reference documentation

Add Sphinx-based API documentation for all public modules.
Includes runtime, config, core, llm, and tools modules.

refactor(tools): simplify tool registration interface

Simplify the tool registration API by removing redundant
factory functions. This is a breaking change for custom tools.

BREAKING CHANGE: Tool registration API changed from
`register_tool_factory(name, factory)` to `register_tool(name, tool)`.
Custom tools will need to update their registration code.

test(core): add tests for state builder

Add comprehensive unit tests for StateBuilder class,
covering edge cases and error conditions.
```

## Getting Help

### Questions?

- **Discord**: [Join our Discord community](https://discord.gg/)
- **GitHub Issues**: [Open an issue](https://github.com/yourusername/configurable-agents/issues)
- **Discussions**: [Start a discussion](https://github.com/yourusername/configurable-agents/discussions)

### Reporting Issues

Use the issue templates when reporting bugs or requesting features:

1. **Bug Reports**: Use the "Bug report" template
2. **Feature Requests**: Use the "Feature request" template
3. **Documentation**: Use the "Documentation" template

### Development Chat

For real-time discussion:
- Join our [Discord server](https://discord.gg/)
- Look for the `#contributing` channel

### Architecture Decision Records

For significant changes, create an Architecture Decision Record (ADR):

```bash
# Create new ADR
cd docs/adr
cp 0000-template.md 0000-your-decision.md

# Follow the template structure
# Submit PR for review
```

## Additional Resources

- [Documentation](docs/)
- [Architecture](docs/ARCHITECTURE.md)
- [Configuration Reference](docs/CONFIG_REFERENCE.md)
- [Examples](examples/)

Thanks for contributing to Configurable Agents! 🚀
