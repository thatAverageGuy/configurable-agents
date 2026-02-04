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
9. [v1.0 Specific Issues](#v10-specific-issues)

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

## v1.0 Specific Issues

### Multi-LLM Provider Errors

#### "Provider 'X' not configured"

**Error:**
```
LLMConfigError: Provider 'openai' not configured. Set OPENAI_API_KEY environment variable.
```

**Solution:**
```bash
# Add missing API key to .env
echo "OPENAI_API_KEY=your_key_here" >> .env

# Or set environment variable
export OPENAI_API_KEY="your_key_here"
```

**Supported providers in v1.0:**
- `google` - Requires `GOOGLE_API_KEY`
- `openai` - Requires `OPENAI_API_KEY`
- `anthropic` - Requires `ANTHROPIC_API_KEY`
- `ollama` - No API key required (local)

#### "Ollama connection failed"

**Error:**
```
LLMAPIError: Failed to connect to Ollama: Connection refused
```

**Solutions:**
1. **Start Ollama server:**
   ```bash
   ollama serve
   ```

2. **Verify Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

3. **Pull required model:**
   ```bash
   ollama pull llama2
   ```

4. **Check model name format:**
   ```yaml
   # Correct
   llm:
     provider: ollama
     model: "ollama_chat/llama2"  # ollama_chat prefix required

   # Wrong
   llm:
     provider: ollama
     model: "llama2"  # Missing prefix
   ```

#### "Model 'X' not found for provider 'Y'"

**Error:**
```
LLMConfigError: Model 'gpt-5' not found for provider 'openai'
```

**Solution:** Check available models per provider:

**Google Gemini:**
- gemini-1.5-flash
- gemini-1.5-pro
- gemini-1.0-pro

**OpenAI:**
- gpt-4
- gpt-4-turbo
- gpt-3.5-turbo

**Anthropic:**
- claude-3-opus-20240229
- claude-3-sonnet-20240229
- claude-3-haiku-20240307

**Ollama:**
- ollama_chat/llama2
- ollama_chat/mistral
- ollama_chat/neo

### Control Flow Issues

#### "Condition evaluation failed"

**Error:**
```
GraphBuildError: Invalid condition syntax: Missing closing brace
```

**Solution:** Check condition syntax:
```yaml
# Correct
condition: "{state.score} >= 90"

# Wrong (missing braces)
condition: "state.score >= 90"

# Wrong (unclosed brace)
condition: "{state.score >= 90"
```

**Supported operators:**
- Comparison: `==`, `!=`, `>`, `<`, `>=`, `<=`
- Logical: `and`, `or`, `not`
- Membership: `in`, `not in`

#### "Infinite loop detected"

**Error:**
```
WorkflowExecutionError: Maximum loop iterations exceeded for node 'refine'
```

**Solution:** Add loop iteration tracking:
```yaml
edges:
  - from: evaluate
    to: refine
    # Always include iteration limit
    condition: "{state.quality} < 8 and {state._loop_iteration_refine} < 5"

  - from: refine
    to: evaluate

  # Exit condition
  - from: evaluate
    to: END
    condition: "{state.quality} >= 8 or {state._loop_iteration_refine} >= 5"
```

**Loop iteration tracking:**
- System creates `_loop_iteration_{node_id}` automatically
- Starts at 0, increments each iteration
- Always include maximum iteration limit

#### "Parallel execution deadlock"

**Error:**
```
WorkflowExecutionError: Parallel execution timeout: nodes did not converge
```

**Solution:** Check parallel edge configuration:
```yaml
edges:
  # All parallel nodes must converge to same target
  - from: START
    to: [task1, task2, task3]

  # Correct: All converge to summarize
  - from: task1
    to: summarize
  - from: task2
    to: summarize
  - from: task3
    to: summarize
```

**Common mistakes:**
- Not all parallel nodes point to the same next node
- Conditional edges break parallel convergence
- Circular dependencies in parallel branches

### Sandbox Execution Failures

#### "Sandbox timeout exceeded"

**Error:**
```
SandboxTimeoutError: Code execution exceeded timeout of 10 seconds
```

**Solution:** Increase timeout or optimize code:
```yaml
nodes:
  - id: execute_code
    sandbox:
      enabled: true
      timeout_seconds: 30  # Increase from 10
      resource_preset: "high"
```

**Resource presets:**
- `low` - 5s timeout, 256MB memory
- `medium` - 10s timeout, 512MB memory
- `high` - 30s timeout, 1GB memory
- `max` - 60s timeout, 2GB memory

#### "Sandbox security violation"

**Error:**
```
SandboxSecurityError: Attempted to access blocked module: 'os'
```

**Solution:** RestrictedPython blocks dangerous modules. Use allowed operations:
```python
# Blocked
import os
os.system('rm -rf /')  # Security error

# Allowed
print("Safe output")
result = [1, 2, 3].sum()
```

**Allowed modules:**
- `math`, `datetime`, `json`, `re`
- Built-in functions: `print`, `len`, `range`, `sum`
- List/dict/set operations

**Blocked modules:**
- `os`, `sys`, `subprocess`, `eval`, `exec`
- File I/O (use `write_file` tool instead)
- Network operations (unless `network_enabled: true`)

#### "Sandbox memory limit exceeded"

**Error:**
```
SandboxMemoryError: Memory limit exceeded: 512MB
```

**Solution:** Increase resource preset:
```yaml
sandbox:
  enabled: true
  resource_preset: "max"  # 2GB memory
```

### Memory Backend Issues

#### "Memory backend connection failed"

**Error:**
```
MemoryBackendError: Failed to connect to memory backend: sqlite:///memory.db
```

**Solution:** Check memory configuration:
```yaml
config:
  memory:
    backend: sqlite
    connection_string: "sqlite:///memory.db"  # Check path is valid
```

**Verify database directory exists:**
```bash
# SQLite: Parent directory must exist
mkdir -p ./data

# Update config
config:
  memory:
    connection_string: "sqlite:///data/memory.db"
```

#### "Memory key not found"

**Error:**
```
MemoryKeyError: Memory key 'user:123' not found in namespace 'chat_history'
```

**Solution:** Handle missing memory gracefully:
```yaml
nodes:
  - id: load_memory
    memory:
      action: load
      namespace: "chat_history"
      key: "{state.user_id}"
      # Add default value if key not found
      default: ""  # Optional
    prompt: "Load conversation history"
    outputs: [history]
    output_schema:
      type: object
      fields:
        - name: history
          type: str
```

### Webhook Integration Problems

#### "WhatsApp webhook verification failed"

**Error:**
```
WebhookValidationError: HMAC verification failed for WhatsApp webhook
```

**Solution:** Check webhook secret configuration:
```bash
# .env
WEBHOOK_SECRET=your_secure_secret_here
WHATSAPP_VERIFY_TOKEN=your_verify_token
```

**Verify webhook URL:**
```bash
# Test webhook endpoint
curl "https://your-domain.com/webhooks/whatsapp?hub.verify_token=your_token"
```

#### "Telegram bot not responding"

**Error:**
```
TelegramAPIError: Bot was blocked by the user
```

**Solutions:**
1. **User must start bot first:**
   - Send `/start` to your bot in Telegram
   - Bot cannot message users who haven't initiated contact

2. **Check bot token:**
   ```bash
   # Verify token
   curl "https://api.telegram.org/bot{BOT_TOKEN}/getMe"
   ```

3. **Check webhook registration:**
   ```bash
   configurable-agents webhooks status --platform telegram
   ```

#### "Generic webhook timeout"

**Error:**
```
WebhookTimeoutError: Workflow execution timed out after 30 seconds
```

**Solution:** Webhooks run workflows asynchronously by default. Check job status:
```bash
# Webhook returns job_id
{
  "status": "async",
  "job_id": "abc-123-def-456",
  "message": "Poll /status/abc-123-def-456 for results"
}

# Poll for completion
curl http://localhost:8000/status/abc-123-def-456
```

### Registry Connection Issues

#### "Agent registry unreachable"

**Error:**
```
AgentRegistryError: Failed to connect to agent registry: http://localhost:8001
```

**Solutions:**
1. **Start registry server:**
   ```bash
   configurable-agents registry start
   ```

2. **Check registry URL:**
   ```bash
   # Verify registry is running
   curl http://localhost:8001/health
   ```

3. **Configure agent registry URL:**
   ```bash
   # .env
   AGENT_REGISTRY_URL=http://localhost:8001
   ```

#### "Agent heartbeat failed"

**Error:**
```
AgentHeartbeatError: Heartbeat failed: HTTP 5xx
```

**Solution:** Registry server may be overloaded. Agent will retry automatically. Check registry logs:
```bash
# View registry logs
configurable-agents registry logs
```

**Adjust heartbeat interval:**
```yaml
# Agent configuration
config:
  agent:
    registry_url: "http://localhost:8001"
    heartbeat_interval: 30  # Increase from 20s
    ttl: 90  # Increase from 60s
```

### MLFlow Optimization Issues

#### "A/B test insufficient data"

**Error:**
```
InsufficientDataError: Need at least 5 runs per variant for statistical significance
```

**Solution:** Increase number of runs:
```bash
configurable-agents optimization ab-test \
  --workflow workflow.yaml \
  --node my_node \
  --prompt-variants variant_a.yaml variant_b.yaml \
  --runs 20  # Increase from default 10
```

#### "Quality gate failed"

**Error:**
```
QualityGateError: Cost per run ($0.50) exceeds threshold ($0.30)
```

**Solution:** Adjust quality gate or optimize workflow:
```yaml
# config/quality_gates.yaml
gates:
  - name: cost_threshold
    metric: cost_per_run
    condition: "<= 0.50"  # Adjust threshold
    action: WARN  # or FAIL, BLOCK_DEPLOY

  - name: latency_threshold
    metric: p95_duration_seconds
    condition: "<= 10.0"
    action: FAIL
```

**Apply quality gates:**
```bash
configurable-agents optimization evaluate \
  --workflow workflow.yaml \
  --quality-gates config/quality_gates.yaml
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
