# Quickstart Guide

**Welcome to Configurable Agents!** This guide will help you create and run your first AI workflow in under 5 minutes.

---

## Prerequisites

- **Python 3.10 or higher**
- **pip** (Python package manager)
- **Google Gemini API key** (free tier available at [ai.google.dev](https://ai.google.dev/))

---

## Step 1: Installation

```bash
# Clone the repository
git clone <repo-url>
cd configurable-agents

# Install the package
pip install -e .
```

**Verify installation:**
```bash
configurable-agents --help
```

You should see the CLI help text.

---

## Step 2: Set Up Your API Key

Configurable Agents uses Google Gemini as the LLM provider in v0.1.

1. **Get your API key** from [ai.google.dev](https://ai.google.dev/)
2. **Create a `.env` file** in the project root:

```bash
# Copy the example file
cp .env.example .env
```

3. **Edit `.env`** and add your key:

```bash
GOOGLE_API_KEY=your_api_key_here
```

**That's it!** The system will automatically load your API key from the `.env` file.

---

## Step 3: Your First Workflow

Let's create a simple "Hello World" workflow. Create a file called `hello.yaml`:

```yaml
schema_version: "1.0"

flow:
  name: hello_world
  description: "A simple greeting workflow"

state:
  fields:
    name:
      type: str
      required: true
      description: "Name to greet"
    greeting:
      type: str
      default: ""
      description: "Generated greeting"

nodes:
  - id: greet
    prompt: "Generate a friendly greeting for {state.name}"
    outputs: [greeting]
    output_schema:
      type: object
      fields:
        - name: greeting
          type: str
          description: "A friendly greeting message"

edges:
  - from: START
    to: greet
  - from: greet
    to: END
```

**What's happening here?**
- **state**: Defines the data fields (name is input, greeting is output)
- **nodes**: Defines the LLM task (generate a greeting)
- **edges**: Defines the flow (START → greet → END)

---

## Step 4: Validate Your Config

Before running, validate your configuration to catch errors early:

```bash
configurable-agents validate hello.yaml
```

You should see:
```
✓ Config validated successfully
```

---

## Step 5: Run Your Workflow

Execute the workflow with an input:

```bash
configurable-agents run hello.yaml --input name="Alice"
```

**Expected output:**
```
✓ Workflow completed successfully

Final State:
{
  "name": "Alice",
  "greeting": "Hello Alice! It's wonderful to meet you today. I hope you're having a great day!"
}
```

**Congratulations!** You've run your first AI workflow. 🎉

---

## Step 6: Try More Examples

Explore more complex examples in the `examples/` directory:

```bash
# Minimal example (same as above)
configurable-agents run examples/echo.yaml --input message="Hello!"

# Multi-step workflow with web search
configurable-agents run examples/article_writer.yaml --input topic="AI Safety"

# Nested state structures
configurable-agents run examples/nested_state.yaml \
  --input name="Alice" \
  --input 'interests=["AI", "music"]'

# Complete type system demo
configurable-agents run examples/type_enforcement.yaml --input topic="Python"
```

Each example has its own README in the `examples/` directory. Start with `echo.yaml` and work your way up!

---

## Understanding the Output

When you run a workflow, you'll see:

1. **Execution progress** (with verbose flag: `--verbose`)
2. **Final state** - All state fields after workflow completes
3. **Exit code** - 0 for success, 1 for errors

**Verbose mode** (useful for debugging):
```bash
configurable-agents run hello.yaml --input name="Bob" --verbose
```

This shows detailed execution logs including LLM calls, state updates, and timing.

---

## What's Next?

Now that you've run your first workflow, explore:

1. **[CONFIG_REFERENCE.md](CONFIG_REFERENCE.md)** - Complete config schema guide
2. **[examples/README.md](../examples/README.md)** - Learning path with 4 examples
3. **[SPEC.md](SPEC.md)** - Technical specification (advanced)
4. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions

---

## Common Commands

```bash
# Run a workflow
configurable-agents run workflow.yaml --input key="value"

# Validate without running
configurable-agents validate workflow.yaml

# Verbose output (for debugging)
configurable-agents run workflow.yaml --input key="value" --verbose

# Multiple inputs
configurable-agents run workflow.yaml \
  --input name="Alice" \
  --input count=5 \
  --input enabled=true
```

---

## Python API

You can also use Configurable Agents programmatically:

```python
from configurable_agents.runtime import run_workflow

# Run a workflow
result = run_workflow("hello.yaml", {"name": "Alice"})
print(result["greeting"])

# With verbose logging
result = run_workflow("hello.yaml", {"name": "Bob"}, verbose=True)
```

See [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) for the Python API reference.

---

## Need Help?

- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Config errors**: Check [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md)
- **Examples**: Browse [examples/](../examples/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/configurable-agents/issues)

---

**Happy building!** 🚀
