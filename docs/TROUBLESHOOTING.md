# Troubleshooting Guide

**Common issues and solutions**

This guide covers frequently encountered issues, error messages, and debugging techniques.

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Configuration Errors](#configuration-errors)
3. [Runtime Errors](#runtime-errors)
4. [API and Authentication](#api-and-authentication)
5. [Tool Errors](#tool-errors)
6. [Type Validation Issues](#type-validation-issues)
7. [Performance Issues](#performance-issues)
8. [Debugging Tips](#debugging-tips)

---

## Installation Issues

### "Command not found: configurable-agents"

**Problem:** CLI not in PATH after installation.

**Solution:**
```bash
# Reinstall in editable mode
pip install -e .

# Or use full path
python -m configurable_agents run workflow.yaml --input topic="AI"

# Or ensure pip bin directory is in PATH
export PATH="$HOME/.local/bin:$PATH"  # Linux/Mac
```

### Import errors after installation

**Problem:** `ModuleNotFoundError: No module named 'configurable_agents'`

**Solution:**
```bash
# Verify installation
pip list | grep configurable-agents

# Reinstall
pip uninstall configurable-agents
pip install -e .

# Check Python version (3.10+ required)
python --version
```

### Dependency conflicts

**Problem:** `pip` reports version conflicts.

**Solution:**
```bash
# Create fresh virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install fresh
pip install -e ".[dev]"
```

---

## Configuration Errors

### "Config file not found"

**Error:**
```
ConfigLoadError: Config file not found: workflow.yaml
```

**Solutions:**
1. **Check file path:**
   ```bash
   ls workflow.yaml  # Verify file exists
   ```

2. **Use absolute path:**
   ```bash
   configurable-agents run /full/path/to/workflow.yaml
   ```

3. **Check current directory:**
   ```bash
   pwd  # Make sure you're in the right directory
   ```

### "Invalid YAML syntax"

**Error:**
```
ConfigLoadError: Invalid YAML syntax at line 12
```

**Solutions:**
1. **Check indentation:** YAML requires consistent spaces (not tabs)
   ```yaml
   # Wrong (tabs)
   nodes:
   →- id: test

   # Right (spaces)
   nodes:
     - id: test
   ```

2. **Validate with online tool:** Use [yamllint.com](http://www.yamllint.com/)

3. **Check quotes:**
   ```yaml
   # Wrong (unmatched quotes)
   prompt: "Write about {state.topic}

   # Right
   prompt: "Write about {state.topic}"
   ```

### "Node 'X' not found in edges"

**Error:**
```
ValidationError: Edge references unknown node 'analyze'
```

**Solution:** Check node IDs match exactly:
```yaml
nodes:
  - id: research  # Must match edge reference

edges:
  - from: START
    to: research  # Must match node id
```

**Common mistakes:**
- Typos: `research` vs `reasearch`
- Case sensitivity: `Research` vs `research`
- Extra spaces: `research ` vs `research`

### "State field 'X' not found"

**Error:**
```
ValidationError: Node 'write' outputs to unknown state field 'article'
```

**Solution:** Define all fields in state:
```yaml
state:
  fields:
    article:  # Must be defined here
      type: str
      default: ""

nodes:
  - id: write
    outputs: [article]  # Must match state field name
```

### "Cannot have both 'required' and 'default'"

**Error:**
```
ValidationError: Field 'topic' cannot have both required=true and a default value
```

**Solution:** Choose one:
```yaml
# Option 1: Required input (no default)
topic:
  type: str
  required: true

# Option 2: Optional with default
topic:
  type: str
  default: "AI Safety"
```

---

## Runtime Errors

### "Missing required input: X"

**Error:**
```
StateInitializationError: Missing required input: topic
```

**Solution:** Provide all required inputs:
```bash
# Check which fields are required
configurable-agents validate workflow.yaml

# Provide required inputs
configurable-agents run workflow.yaml --input topic="AI Safety"
```

### "Workflow execution timeout"

**Error:**
```
WorkflowExecutionError: Node 'research' timed out after 60 seconds
```

**Solutions:**
1. **Increase timeout:**
   ```yaml
   config:
     execution:
       timeout_seconds: 120  # Increase from 60
   ```

2. **Simplify prompt:**
   - Shorter prompts execute faster
   - Break complex tasks into multiple nodes

3. **Check network connection:**
   - LLM API calls require internet
   - Test with: `curl https://generativelanguage.googleapis.com`

### "Graph build failed"

**Error:**
```
GraphBuildError: Invalid graph structure
```

**Solutions:**
1. **Verify START/END:**
   ```yaml
   edges:
     - from: START
       to: first_node
     # ... other edges ...
     - from: last_node
       to: END
   ```

2. **Check for disconnected nodes:**
   - Every node must be reachable from START
   - Every node must have path to END

3. **Validate flow is linear (v0.1):**
   - No cycles (loops)
   - No conditional branches
   - Each node: one input, one output edge

---

## API and Authentication

### "GOOGLE_API_KEY not set"

**Error:**
```
LLMConfigError: GOOGLE_API_KEY environment variable not set
```

**Solutions:**
1. **Create `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env and add your key
   ```

2. **Set environment variable:**
   ```bash
   # Linux/Mac
   export GOOGLE_API_KEY="your_key_here"

   # Windows (Command Prompt)
   set GOOGLE_API_KEY=your_key_here

   # Windows (PowerShell)
   $env:GOOGLE_API_KEY="your_key_here"
   ```

3. **Verify key is loaded:**
   ```bash
   echo $GOOGLE_API_KEY  # Linux/Mac
   echo %GOOGLE_API_KEY%  # Windows CMD
   ```

### "Invalid API key"

**Error:**
```
LLMAPIError: API request failed: 401 Unauthorized
```

**Solutions:**
1. **Check key validity:**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Generate new key if needed

2. **Check for extra spaces:**
   ```bash
   # Wrong (extra spaces)
   GOOGLE_API_KEY=" your_key "

   # Right
   GOOGLE_API_KEY="your_key"
   ```

3. **Test key directly:**
   ```python
   import os
   from google.generativeai import configure, GenerativeModel

   configure(api_key=os.getenv("GOOGLE_API_KEY"))
   model = GenerativeModel("gemini-1.5-flash")
   response = model.generate_content("Say hello")
   print(response.text)
   ```

### "Rate limit exceeded"

**Error:**
```
LLMAPIError: Rate limit exceeded. Retry after 60 seconds.
```

**Solutions:**
1. **Wait and retry:**
   - Free tier has limits (60 requests/minute)
   - System automatically retries with backoff

2. **Reduce frequency:**
   ```yaml
   config:
     execution:
       max_retries: 5  # More retries with backoff
   ```

3. **Upgrade to paid tier:**
   - Paid plans have higher rate limits
   - See [Google AI pricing](https://ai.google.dev/pricing)

---

## Tool Errors

### "SERPER_API_KEY not set"

**Error:**
```
ToolConfigError: SERPER_API_KEY environment variable not set
```

**Solutions:**
1. **Get API key:**
   - Visit [serper.dev](https://serper.dev/)
   - Sign up and get free API key

2. **Add to `.env`:**
   ```bash
   SERPER_API_KEY=your_serper_key_here
   ```

3. **Reload environment:**
   ```bash
   # Restart terminal or reload
   source .env  # If using direnv
   ```

### "Tool 'X' not found"

**Error:**
```
ToolNotFoundError: Tool 'google_search' not found. Available: ['serper_search']
```

**Solution:** Use correct tool name:
```yaml
nodes:
  - id: research
    tools: [serper_search]  # Correct name (not google_search)
```

**Available tools (v0.1):**
- `serper_search` - Web search (requires SERPER_API_KEY)

### "Tool execution failed"

**Error:**
```
NodeExecutionError: Tool 'serper_search' failed: Network error
```

**Solutions:**
1. **Check internet connection**
2. **Verify API key is valid**
3. **Check API status:** [serper.dev/status](https://serper.dev/status)
4. **Try with verbose mode:**
   ```bash
   configurable-agents run workflow.yaml --input topic="AI" --verbose
   ```

---

## Type Validation Issues

### "Output validation failed"

**Error:**
```
NodeExecutionError: Output validation failed: field 'word_count' expected int, got str
```

**Solutions:**
1. **Adjust temperature:** Lower temperature = more consistent types
   ```yaml
   config:
     llm:
       temperature: 0.0  # More deterministic
   ```

2. **Add type hints in descriptions:**
   ```yaml
   output_schema:
     type: object
     fields:
       - name: word_count
         type: int
         description: "Number of words (must be an integer number)"
   ```

3. **Increase retries:** System auto-retries on type mismatches
   ```yaml
   config:
     execution:
       max_retries: 5  # More attempts
   ```

### "Type mismatch in state"

**Error:**
```
ValidationError: Field 'score' expects float, config has int
```

**Solution:** Match types exactly:
```yaml
state:
  fields:
    score:
      type: float  # Must match
      default: 0.0  # Use float literal

# Or use int if appropriate
    count:
      type: int
      default: 0  # Integer literal
```

### "List type validation failed"

**Error:**
```
ValidationError: Field 'tags' expects list[str], got list
```

**Solution:** Specify element type:
```yaml
# Wrong
tags:
  type: list

# Right
tags:
  type: list[str]
  default: []
```

---

## Performance Issues

### "Workflow runs slowly"

**Causes and solutions:**

1. **Large prompts:**
   ```yaml
   # Before: Long prompt
   prompt: |
     {1000 lines of instructions}

   # After: Concise prompt
   prompt: "Write article about {state.topic}. Be concise."
   ```

2. **Too many retries:**
   ```yaml
   # Reduce retries if not needed
   config:
     execution:
       max_retries: 1  # Default: 3
   ```

3. **Wrong model:**
   ```yaml
   # Use flash for speed
   config:
     llm:
       model: "gemini-1.5-flash"  # Faster than pro
   ```

### "High API costs"

**Solutions:**
1. **Validate before running:**
   ```bash
   configurable-agents validate workflow.yaml  # Free, no API calls
   ```

2. **Use cheaper model:**
   ```yaml
   config:
     llm:
       model: "gemini-1.5-flash"  # Cheaper than pro
   ```

3. **Reduce retries:**
   ```yaml
   config:
     execution:
       max_retries: 1
   ```

4. **Shorter prompts:** Every token costs money

---

## Debugging Tips

### Enable verbose mode

**See detailed execution logs:**
```bash
configurable-agents run workflow.yaml --input topic="AI" --verbose
```

**Shows:**
- Node execution start/end
- LLM calls and responses
- State updates
- Timing information
- Full error tracebacks

### Validate before running

**Catch errors early (free):**
```bash
configurable-agents validate workflow.yaml
```

**Checks:**
- YAML syntax
- Schema structure
- Node references
- State field existence
- Type consistency
- Graph structure

### Test with minimal example

**Create test config:**
```yaml
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    message: {type: str, required: true}
    result: {type: str, default: ""}
nodes:
  - id: echo
    prompt: "Repeat: {state.message}"
    outputs: [result]
    output_schema:
      type: object
      fields:
        - name: result
          type: str
edges:
  - {from: START, to: echo}
  - {from: echo, to: END}
```

**Run:**
```bash
configurable-agents run test.yaml --input message="hello"
```

### Check example configs

**Compare against working examples:**
```bash
# These are tested and working
configurable-agents run examples/echo.yaml --input message="test"
configurable-agents run examples/nested_state.yaml --input name="Alice" --input 'interests=["AI"]'
```

### Use Python API for debugging

**More control:**
```python
from configurable_agents.runtime import run_workflow
from configurable_agents.config import validate_config, parse_config_file

# Validate first
config_dict = parse_config_file("workflow.yaml")
from configurable_agents.config import WorkflowConfig
config = WorkflowConfig(**config_dict)
validate_config(config)  # Raises ValidationError if invalid

# Run with try/except
try:
    result = run_workflow("workflow.yaml", {"topic": "AI"}, verbose=True)
    print(result)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
```

### Check logs

**Log file location:**
```bash
# Default: console output
# To file:
configurable-agents run workflow.yaml --input topic="AI" 2>&1 | tee output.log
```

### Inspect state at each step

**Use verbose mode** to see state after each node:
```bash
configurable-agents run workflow.yaml --input topic="AI" --verbose
```

Look for:
- Fields being updated correctly
- Unexpected None values
- Type conversions

---

## Common Patterns & Solutions

### Pattern: "It works sometimes, fails others"

**Likely cause:** Temperature too high (non-deterministic outputs)

**Solution:**
```yaml
config:
  llm:
    temperature: 0.0  # Fully deterministic
```

### Pattern: "First run works, subsequent fail"

**Likely cause:** State not resetting between runs

**Solution:**
- Each run starts fresh (no state persistence in v0.1)
- Check that required inputs are always provided
- Verify default values are correct

### Pattern: "Works in Python, fails in CLI"

**Likely cause:** Environment variables not loaded

**Solution:**
```bash
# Make sure .env is in current directory
ls .env

# Or set manually
export GOOGLE_API_KEY="your_key"
configurable-agents run workflow.yaml --input topic="AI"
```

---

## Getting Help

If you're still stuck:

1. **Check existing issues:** [GitHub Issues](https://github.com/thatAverageGuy/configurable-agents/issues)
2. **Search documentation:**
   - [QUICKSTART.md](QUICKSTART.md)
   - [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md)
   - [SPEC.md](SPEC.md)
3. **Open an issue:**
   - Include: config file, error message, verbose output
   - Minimal reproducible example helps!
4. **Ask in discussions:** [GitHub Discussions](https://github.com/thatAverageGuy/configurable-agents/discussions)

---

## Error Reference

Quick lookup of all error types:

| Error Type | Meaning | Common Fix |
|------------|---------|------------|
| `ConfigLoadError` | File not found or invalid YAML/JSON | Check file path and syntax |
| `ConfigValidationError` | Invalid config structure | Fix schema errors |
| `StateInitializationError` | Missing required input | Provide all required fields |
| `GraphBuildError` | Invalid graph structure | Check START/END and edges |
| `WorkflowExecutionError` | Node execution failed | Check verbose output |
| `NodeExecutionError` | Single node failed | Check prompt, tools, schema |
| `LLMConfigError` | LLM setup issue | Set API key |
| `LLMAPIError` | LLM API call failed | Check key, network, rate limits |
| `ToolConfigError` | Tool setup issue | Set tool API key |
| `ToolNotFoundError` | Unknown tool name | Use correct tool name |
| `TemplateResolutionError` | Variable not found in prompt | Check state field names |
| `ValidationError` | Pydantic validation failed | Fix type mismatches |

---

**Still having issues?** Open an issue with your config and error message!
