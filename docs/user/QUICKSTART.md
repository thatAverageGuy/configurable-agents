# Quickstart Guide

**Welcome to Configurable Agents v1.0!** This guide will help you create and run your first AI workflow in under 5 minutes.

**What's New in v1.0:**
- Multi-LLM support (OpenAI, Anthropic, Ollama, Google Gemini)
- Conditional routing and loop execution
- Parallel node execution
- Code execution sandbox
- Persistent memory across runs
- Pre-built tool ecosystem (15+ tools)
- MLFlow observability and cost tracking
- Chat UI for config generation
- Dashboard for execution monitoring
- WhatsApp and Telegram integrations

---

## Prerequisites

- **Python 3.10 or higher**
- **pip** (Python package manager)
- **API key** for at least one LLM provider:
  - Google Gemini (free tier available at [ai.google.dev](https://ai.google.dev/))
  - OpenAI (requires paid account)
  - Anthropic (requires paid account)
  - Ollama (free, local - [ollama.com](https://ollama.com/))

---

## Step 1: Installation

```bash
# Clone the repository
git clone https://github.com/thatAverageGuy/configurable-agents.git
cd configurable-agents

# Install the package
pip install -e .
```

**Verify installation:**
```bash
configurable-agents --help
```

You should see the CLI help text with all available commands.

---

## Step 2: Set Up Your API Key

Configurable Agents v1.0 supports multiple LLM providers. Choose one or more:

### Option A: Google Gemini (Recommended for Beginners)

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

### Option B: OpenAI

```bash
OPENAI_API_KEY=your_openai_key_here
```

### Option C: Anthropic

```bash
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### Option D: Ollama (Free, Local)

1. Install Ollama: https://ollama.com/
2. Pull a model: `ollama pull llama2`
3. No API key needed!

**That's it!** The system will automatically load your API keys from the `.env` file.

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

## Step 6: Try v1.0 Features

### Multi-LLM Setup

Configure different providers per node:

```yaml
# multi_llm.yaml
schema_version: "1.0"

flow:
  name: multi_provider_demo
  description: "Uses multiple LLM providers"

state:
  fields:
    topic:
      type: str
      required: true
    research:
      type: str
      default: ""
    summary:
      type: str
      default: ""

nodes:
  - id: research
    llm:
      provider: openai
      model: "gpt-4"
    prompt: "Research {state.topic} and provide detailed findings"
    outputs: [research]
    output_schema:
      type: object
      fields:
        - name: research
          type: str

  - id: summarize
    llm:
      provider: anthropic
      model: "claude-3-sonnet-20240229"
    prompt: "Summarize this research:\n{state.research}"
    outputs: [summary]
    output_schema:
      type: object
      fields:
        - name: summary
          type: str

edges:
  - from: START
    to: research
  - from: research
    to: summarize
  - from: summarize
    to: END
```

**Run it:**
```bash
configurable-agents run multi_llm.yaml --input topic="Quantum Computing"
```

### Conditional Routing

Route workflows based on LLM outputs:

```yaml
# conditional.yaml
schema_version: "1.0"

flow:
  name: sentiment_router
  description: "Routes based on sentiment analysis"

state:
  fields:
    text:
      type: str
      required: true
    sentiment:
      type: str
      default: ""
    response:
      type: str
      default: ""

nodes:
  - id: analyze
    prompt: |
      Analyze the sentiment of this text: "{state.text}"
      Return ONLY one word: positive, negative, or neutral
    outputs: [sentiment]
    output_schema:
      type: object
      fields:
        - name: sentiment
          type: str

  - id: positive_response
    prompt: "Write a thank you message for positive feedback"
    outputs: [response]
    output_schema:
      type: object
      fields:
        - name: response
          type: str

  - id: negative_response
    prompt: "Write an apology message for negative feedback"
    outputs: [response]
    output_schema:
      type: object
      fields:
        - name: response
          type: str

  - id: neutral_response
    prompt: "Write a neutral acknowledgment message"
    outputs: [response]
    output_schema:
      type: object
      fields:
        - name: response
          type: str

edges:
  - from: START
    to: analyze

  # Conditional routing based on sentiment
  - from: analyze
    to: positive_response
    condition: "{state.sentiment} == 'positive'"

  - from: analyze
    to: negative_response
    condition: "{state.sentiment} == 'negative'"

  - from: analyze
    to: neutral_response
    condition: "{state.sentiment} == 'neutral'"

  # All paths converge to END
  - from: positive_response
    to: END
  - from: negative_response
    to: END
  - from: neutral_response
    to: END
```

**Run it:**
```bash
configurable-agents run conditional.yaml --input text="I love this product!"
```

### Loop Execution

Retry nodes with iteration tracking:

```yaml
# loop.yaml
schema_version: "1.0"

flow:
  name: refinement_loop
  description: "Iteratively refines output until quality threshold"

state:
  fields:
    topic:
      type: str
      required: true
    draft:
      type: str
      default: ""
    quality_score:
      type: int
      default: 0
    iteration:
      type: int
      default: 0

nodes:
  - id: draft
    prompt: "Write a brief paragraph about {state.topic}"
    outputs: [draft]
    output_schema:
      type: object
      fields:
        - name: draft
          type: str

  - id: evaluate
    prompt: |
      Rate the quality of this draft from 1-10:
      {state.draft}

      Return ONLY a number.
    outputs: [quality_score]
    output_schema:
      type: object
      fields:
        - name: quality_score
          type: int

  - id: refine
    prompt: |
      Improve this draft (iteration {state._loop_iteration_refine}):
      {state.draft}

      Make it more detailed and engaging.
    outputs: [draft]
    output_schema:
      type: object
      fields:
        - name: draft
          type: str

edges:
  - from: START
    to: draft

  - from: draft
    to: evaluate

  # Loop back to refine if quality < 7, max 3 iterations
  - from: evaluate
    to: refine
    condition: "{state.quality_score} < 7 and {state._loop_iteration_refine} < 3"

  - from: refine
    to: evaluate

  # Exit to END when quality >= 7 or max iterations reached
  - from: evaluate
    to: END
    condition: "{state.quality_score} >= 7 or {state._loop_iteration_refine} >= 3"
```

**Run it:**
```bash
configurable-agents run loop.yaml --input topic="Machine Learning"
```

### Parallel Execution

Run multiple nodes concurrently:

```yaml
# parallel.yaml
schema_version: "1.0"

flow:
  name: parallel_research
  description: "Researches multiple aspects in parallel"

state:
  fields:
    topic:
      type: str
      required: true
    technical_analysis:
      type: str
      default: ""
    business_analysis:
      type: str
      default: ""
    ethical_analysis:
      type: str
      default: ""
    summary:
      type: str
      default: ""

nodes:
  # These three nodes run in parallel
  - id: technical
    prompt: "Analyze technical aspects of {state.topic}"
    outputs: [technical_analysis]
    output_schema:
      type: object
      fields:
        - name: technical_analysis
          type: str

  - id: business
    prompt: "Analyze business implications of {state.topic}"
    outputs: [business_analysis]
    output_schema:
      type: object
      fields:
        - name: business_analysis
          type: str

  - id: ethical
    prompt: "Analyze ethical considerations of {state.topic}"
    outputs: [ethical_analysis]
    output_schema:
      type: object
      fields:
        - name: ethical_analysis
          type: str

  # Runs after all parallel nodes complete
  - id: summarize
    prompt: |
      Synthesize these analyses:
      Technical: {state.technical_analysis}
      Business: {state.business_analysis}
      Ethical: {state.ethical_analysis}

      Provide a comprehensive summary.
    outputs: [summary]
    output_schema:
      type: object
      fields:
        - name: summary
          type: str

edges:
  - from: START
    to: [technical, business, ethical]  # Parallel execution

  # All three must complete before summarize
  - from: technical
    to: summarize
  - from: business
    to: summarize
  - from: ethical
    to: summarize

  - from: summarize
    to: END
```

**Run it:**
```bash
configurable-agents run parallel.yaml --input topic="AI in Healthcare"
```

### Sandbox Code Execution

Run agent-generated Python code safely:

```yaml
# sandbox.yaml
schema_version: "1.0"

flow:
  name: code_executor
  description: "Executes Python code in sandboxed environment"

state:
  fields:
    task:
      type: str
      required: true
    code:
      type: str
      default: ""
    result:
      type: str
      default: ""

nodes:
  - id: generate_code
    prompt: |
      Write Python code to: {state.task}

      Return ONLY the code, no explanations.
      Use print() to output results.
    outputs: [code]
    output_schema:
      type: object
      fields:
        - name: code
          type: str

  - id: execute
    sandbox:
      enabled: true
      timeout_seconds: 10
      resource_preset: "medium"  # CPU: 1.0, Memory: 512MB
    inputs:
      user_code: "{state.code}"
    prompt: "Execute the provided code"
    outputs: [result]
    output_schema:
      type: object
      fields:
        - name: result
          type: str
          description: "Output from code execution"

edges:
  - from: START
    to: generate_code
  - from: generate_code
    to: execute
  - from: execute
    to: END
```

**Run it:**
```bash
configurable-agents run sandbox.yaml --input task="Calculate fibonacci numbers up to 100"
```

### Persistent Memory

Use memory that persists across workflow runs:

```yaml
# memory.yaml
schema_version: "1.0"

flow:
  name: memory_demo
  description: "Demonstrates persistent memory"

state:
  fields:
    user_id:
      type: str
      required: true
    message:
      type: str
      required: true
    context:
      type: str
      default: ""

nodes:
  - id: load_memory
    memory:
      action: load
      namespace: "chat_history"
      key: "{state.user_id}"
    prompt: "Load previous conversation history for user {state.user_id}"
    outputs: [context]
    output_schema:
      type: object
      fields:
        - name: context
          type: str
          description: "Previous conversation context"

  - id: respond
    prompt: |
      Previous context:
      {state.context}

      New message: {state.message}

      Respond helpfully.
    outputs: [response]
    output_schema:
      type: object
      fields:
        - name: response
          type: str

  - id: save_memory
    memory:
      action: save
      namespace: "chat_history"
      key: "{state.user_id}"
      value: "User: {state.message}\nAssistant: {state.response}"
    prompt: "Save conversation to memory"
    outputs: []
    output_schema:
      type: object
      fields: []

edges:
  - from: START
    to: load_memory
  - from: load_memory
    to: respond
  - from: respond
    to: save_memory
  - from: save_memory
    to: END
```

**Run it multiple times:**
```bash
# First run
configurable-agents run memory.yaml --input user_id="alice" --input message="My name is Alice"

# Second run (remembers context)
configurable-agents run memory.yaml --input user_id="alice" --input message="What's my name?"
```

### Using Pre-Built Tools

Use tools like web search, file operations, and more:

```yaml
# tools.yaml
schema_version: "1.0"

flow:
  name: research_with_tools
  description: "Uses web search tool"

state:
  fields:
    query:
      type: str
      required: true
    search_results:
      type: str
      default: ""
    answer:
      type: str
      default: ""

nodes:
  - id: search
    tools: [serper_search]  # Web search tool
    prompt: "Search for: {state.query}"
    outputs: [search_results]
    output_schema:
      type: object
      fields:
        - name: search_results
          type: str

  - id: answer
    prompt: |
      Based on these search results:
      {state.search_results}

      Answer the question: {state.query}
    outputs: [answer]
    output_schema:
      type: object
      fields:
        - name: answer
          type: str

edges:
  - from: START
    to: search
  - from: search
    to: answer
  - from: answer
    to: END
```

**Available tools in v1.0:**
- `serper_search` - Web search (requires SERPER_API_KEY)
- `write_file` - Write to local files
- `read_file` - Read local files
- `python_repl` - Execute Python code
- `shell` - Run shell commands
- `sql_query` - Execute SQL queries
- And more... (see [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md))

---

## Step 7: Explore User Interfaces

### Chat UI (Generate Configs by Talking)

Generate workflow configs through conversation:

```bash
# Start the chat UI
configurable-agents chat
```

Open http://localhost:7860 in your browser.

**Example conversation:**
```
You: I want a workflow that analyzes sentiment and routes to different responses

AI: I'll create a sentiment analysis workflow for you. Here's what I'm building:
[Generates YAML config in real-time]

You: Can you add a node for neutral sentiment too?

AI: [Updates config to include neutral branch]
```

### Dashboard

Monitor and manage executions and deployments:

```bash
# Start the dashboard
configurable-agents dashboard
```

Open http://localhost:8000 in your browser.

**Features:**
- View all executions with status tracking
- Real-time logs and metrics
- Start/stop/restart executions
- Deployment management (register, monitor, health checks)
- MLFlow integration (view traces)

---

## Step 8: Webhook Integrations

### WhatsApp Integration

Trigger workflows from WhatsApp messages:

1. **Set up environment variables:**
```bash
# .env
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_VERIFY_TOKEN=your_verify_token
```

2. **Configure webhook:**
```bash
configurable-agents webhooks register --platform whatsapp --workflow my_workflow.yaml
```

3. **Send WhatsApp message:**
```
Send "your trigger text" to your WhatsApp Business number
```

### Telegram Integration

Trigger workflows from Telegram messages:

1. **Set up environment variables:**
```bash
# .env
TELEGRAM_BOT_TOKEN=your_bot_token
```

2. **Configure webhook:**
```bash
configurable-agents webhooks register --platform telegram --workflow my_workflow.yaml
```

3. **Send Telegram message:**
```
/start in your bot to trigger the workflow
```

---

## Step 9: Observability

### Enable MLFlow Tracking

Track costs, tokens, and performance:

```yaml
# workflow.yaml
config:
  observability:
    mlflow:
      enabled: true
      tracking_uri: "sqlite:///mlflow.db"
```

After running workflows, view traces:
```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
# Open http://localhost:5000
```

### Cost Reporting

View costs across all providers:

```bash
# Cost report with Rich tables
configurable-agents cost-report

# Profile report with bottleneck analysis
configurable-agents profile-report

# Observability system status
configurable-agents observability-status
```

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

This shows detailed execution logs including LLM calls, state updates, timing, and routing decisions.

---

## What's Next?

Now that you've run your first workflow, explore:

1. **[CONFIG_REFERENCE.md](CONFIG_REFERENCE.md)** - Complete config schema guide
2. **[OBSERVABILITY.md](OBSERVABILITY.md)** - MLFlow tracking and cost reporting
3. **[DEPLOYMENT.md](DEPLOYMENT.md)** - Docker deployment and production setup
4. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
5. **[examples/](../examples/)** - Learning path with examples

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

# Chat UI (generate configs)
configurable-agents chat

# Dashboard
configurable-agents dashboard

# Deployments
configurable-agents deployments list

# Observability
configurable-agents cost-report
configurable-agents profile-report
configurable-agents observability-status

# Webhooks
configurable-agents webhooks register --platform whatsapp --workflow my_workflow.yaml

# Docker deployment
configurable-agents deploy workflow.yaml
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

# With profiling enabled
import os
os.environ["CONFIGURABLE_AGENTS_PROFILING"] = "true"
result = run_workflow("workflow.yaml", inputs)
```

See [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) for the Python API reference.

---

## Need Help?

- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Config errors**: Check [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md)
- **Examples**: Browse [examples/](../examples/)
- **Issues**: [GitHub Issues](https://github.com/thatAverageGuy/configurable-agents/issues)

---

**Happy building!** 🚀
