# ADR-015: CLI Interface Design

**Status**: Implemented
**Date**: 2026-01-27
**Deciders**: User, Claude Code
**Related Tasks**: T-014 (CLI Interface)

---

## Context

The system needs a user-facing CLI for running and validating workflows. Design choices impact usability, learnability, and scripting integration.

### Requirements

1. **Run workflows** with inputs
2. **Validate configs** without execution
3. **Verbose output** for debugging
4. **Script-friendly** for automation
5. **Human-friendly** for interactive use
6. **Cross-platform** (Windows, Linux, macOS)

### Key Questions

1. **Command structure**: Subcommands vs flags?
2. **Input format**: Key-value pairs vs JSON file?
3. **Output format**: Pretty print vs JSON?
4. **Error handling**: Exit codes? Traceback control?
5. **Future extensibility**: Room for new commands?

---

## Decision

**Command structure**: `configurable-agents <command> <file> [options]`

### Commands

```bash
# Run workflow
configurable-agents run workflow.yaml --input topic="AI Safety" --input name="Alice"

# Validate config
configurable-agents validate workflow.yaml

# Verbose mode
configurable-agents run workflow.yaml --input topic="AI" --verbose
```

### Design Choices

1. **Subcommand Pattern**: `run`, `validate`, (future: `deploy`, `export`)
2. **Input Format**: `--input key=value` (repeatable)
3. **Output Format**: Pretty print with colors (human-friendly)
4. **Exit Codes**: 0 (success), 1 (error), 2 (validation failure)
5. **Traceback**: Hidden by default, shown with `--verbose`

---

## Rationale

### 1. Subcommand Pattern

**Why**:
- Clear, self-documenting: `run` vs `validate` vs `deploy`
- Room for growth: easy to add new commands
- Industry standard (git, docker, npm all use subcommands)

**Alternative rejected**: Flags like `--validate` mixed with operations
- **Why rejected**: Confusing (`run --validate`?), doesn't scale

### 2. `--input key=value` Format

**Why**:
- Shell-friendly: No quotes needed for simple values
- Quick for prototyping: `--input topic="AI"`
- Repeatable: Multiple `--input` flags
- Type inference: Strings by default (matches YAML)

**Examples**:
```bash
# Simple
configurable-agents run hello.yaml --input name="Alice"

# Multiple inputs
configurable-agents run workflow.yaml \
  --input topic="AI Safety" \
  --input depth="detailed"
```

**Alternative considered**: JSON file input
```bash
configurable-agents run workflow.yaml --inputs inputs.json
```
**Why rejected**: Extra file needed, slower for quick tests
**Future enhancement**: Support both (detect `.json` extension)

### 3. Pretty Print Output (Human-Friendly)

**Why**:
- Clear for humans: Formatted, colored output
- Shows key results prominently
- Hides internal details by default

**Example output**:
```
✓ Workflow completed successfully

Results:
  topic: "AI Safety"
  article: "In recent years, AI safety has..."
  word_count: 847

Execution time: 3.2s
```

**Alternative considered**: JSON output
```bash
configurable-agents run workflow.yaml --input topic="AI" --json
```
**Why rejected for default**: Hard to read, optimized for machines
**Future enhancement**: Add `--json` flag for scripting

### 4. Exit Codes

| Code | Meaning | Example |
|------|---------|---------|
| 0 | Success | Workflow completed |
| 1 | Runtime error | LLM API failure |
| 2 | Validation error | Invalid config |

**Why**:
- Script-friendly: `if configurable-agents validate config.yaml; then deploy; fi`
- Standard practice (POSIX convention)
- Distinguishes validation vs runtime errors

### 5. Traceback Control

**Default** (no traceback):
```
Error: Node 'research' failed: LLM API timeout
  Suggestion: Check GOOGLE_API_KEY and network connection
```

**Verbose** (full traceback):
```
Error: Node 'research' failed: LLM API timeout
  File "runtime/executor.py", line 127, in execute_node
    ...
  google.api.exceptions.Timeout: Request timed out
```

**Why**:
- Default: Clean, actionable errors for users
- Verbose: Full context for debugging
- Controlled with `--verbose` flag

---

## Implementation Details

**Status**: ✅ Implemented in v0.1
**Related Tasks**: T-014 (CLI Interface)
**Date Implemented**: 2026-01-27

### T-014: CLI Interface Implementation

**File**: `src/configurable_agents/cli.py` (280 lines)

**Framework**: Click (industry standard Python CLI framework)

```python
import click
from configurable_agents.runtime import run_workflow, validate_workflow

@click.group()
def cli():
    """Configurable Agents CLI"""
    pass

@cli.command()
@click.argument('config_path', type=click.Path(exists=True))
@click.option('--input', '-i', multiple=True, help='Input key=value pairs')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def run(config_path, input, verbose):
    """Run a workflow from config file"""
    try:
        # Parse inputs
        inputs = {}
        for pair in input:
            key, value = pair.split('=', 1)
            inputs[key] = value

        # Execute workflow
        result = run_workflow(config_path, inputs)

        # Pretty print results
        click.secho("✓ Workflow completed successfully", fg='green')
        click.echo("\nResults:")
        for key, value in result.items():
            click.echo(f"  {key}: {repr(value)}")

    except Exception as e:
        if verbose:
            raise  # Show full traceback
        else:
            click.secho(f"Error: {e}", fg='red')
            sys.exit(1)

@cli.command()
@click.argument('config_path', type=click.Path(exists=True))
def validate(config_path):
    """Validate a workflow config"""
    try:
        validate_workflow(config_path)
        click.secho("✓ Config is valid", fg='green')
    except ValidationError as e:
        click.secho(f"✗ Validation failed:", fg='red')
        click.echo(f"  {e.message}")
        if e.suggestion:
            click.secho(f"  Suggestion: {e.suggestion}", fg='yellow')
        sys.exit(2)
```

**Entry Point** (`pyproject.toml`):
```toml
[project.scripts]
configurable-agents = "configurable_agents.cli:cli"
```

**Features Implemented**:
- `run` command with input parsing
- `validate` command with helpful errors
- `--verbose` flag for debugging
- Colored output (green success, red errors, yellow suggestions)
- Exit codes (0, 1, 2)
- Cross-platform compatibility (Click handles Windows/Unix)

**Test Coverage**: 15 CLI tests (command execution, input parsing, error handling)

---

## Alternatives Considered

### Alternative 1: YAML Input File

```bash
configurable-agents run workflow.yaml --inputs inputs.yaml
```

**Pros**:
- Complex inputs (nested objects)
- Reusable input files
- Version controlled

**Cons**:
- Extra file needed
- Slower for quick tests
- Overkill for simple cases

**Why rejected**: Too heavyweight for common case (1-3 simple inputs)

**Future enhancement**: Support both formats (detect `.yaml`/`.json`)

---

### Alternative 2: Positional Arguments

```bash
configurable-agents run workflow.yaml "AI Safety" "Alice"
```

**Pros**:
- Shortest syntax
- No `--input` noise

**Cons**:
- Order-dependent (fragile)
- No field names (unclear which is which)
- Doesn't scale to many inputs

**Why rejected**: Too implicit, error-prone

---

### Alternative 3: JSON Output by Default

```bash
configurable-agents run workflow.yaml --input topic="AI"
# Output: {"topic": "AI Safety", "article": "..."}
```

**Pros**:
- Machine-parseable
- Script-friendly
- Complete data

**Cons**:
- Hard for humans to read
- Noisy for interactive use
- Most users are humans, not scripts

**Why rejected**: Optimize for human readability first

**Future enhancement**: Add `--json` flag for scripting

---

## Consequences

### Positive Consequences

1. **Easy to Learn**: Familiar subcommand pattern
2. **Quick Prototyping**: `--input key=value` is fast
3. **Human-Friendly**: Pretty output, clear errors
4. **Script-Friendly**: Exit codes, optional JSON output (future)
5. **Extensible**: Easy to add new commands (`deploy`, `export`)

### Negative Consequences

1. **Complex Inputs Limited**: Can't pass nested objects easily
   - **Mitigation**: Add YAML input file support in v0.2

2. **Click Dependency**: Adds framework dependency
   - **Mitigation**: Click is lightweight, industry standard

3. **No Interactive Mode**: Can't modify inputs mid-run
   - **Mitigation**: Out of scope for v0.1, consider REPL for v0.3

---

## Future Enhancements (v0.2+)

1. **JSON/YAML Input Files**:
   ```bash
   configurable-agents run workflow.yaml --inputs inputs.yaml
   ```

2. **JSON Output Flag**:
   ```bash
   configurable-agents run workflow.yaml --input topic="AI" --json
   ```

3. **Deploy Command** (T-024):
   ```bash
   configurable-agents deploy workflow.yaml --env-file .env
   ```

4. **Watch Mode** (v0.3):
   ```bash
   configurable-agents run workflow.yaml --input topic="AI" --watch
   # Re-runs on config file changes
   ```

5. **Interactive REPL** (v0.3):
   ```bash
   configurable-agents shell workflow.yaml
   >>> run(topic="AI Safety")
   >>> result.article
   ```

---

## References

- Click documentation: https://click.palletsprojects.com/
- CLI design patterns: https://clig.dev/
- T-014 implementation: `src/configurable_agents/cli.py`

---

## Related Decisions

- **ADR-003**: Config-driven architecture (configs as primary interface)
- **ADR-004**: Parse-time validation (validates before execution)
- **Future ADR**: Streamlit UI (auxiliary interface)
- **ADR-012**: Docker deployment (future `deploy` command)
