# Article Writer Workflow

**File**: `article_writer.yaml`
**Complexity**: ⭐⭐⭐ Intermediate (multi-step with tools)

## What It Does

A production-like workflow that:
1. **Researches** a topic using web search (Serper API)
2. **Writes** a comprehensive article based on research findings

Perfect for understanding:
- Multi-node sequential workflows
- Tool integration (web search)
- State flowing between nodes
- Structured outputs with multiple fields
- Global configuration (LLM settings, timeouts)

## Structure

- **1 input field**: `topic` (required)
- **4 state fields**: `topic`, `research`, `article`, `word_count`
- **2 nodes**: `research` (with tools) → `write`
- **1 tool**: `serper_search` (Google Search via Serper API)
- **Global config**: LLM model, temperature, timeout, retries

## Prerequisites

This example requires:
1. **Google API key** (for Gemini LLM)
2. **Serper API key** (for web search)

```bash
export GOOGLE_API_KEY="your-google-key"
export SERPER_API_KEY="your-serper-key"

# Get Serper key from: https://serper.dev (free tier: 2,500 searches)
```

## Usage

### CLI

```bash
configurable-agents run article_writer.yaml --input topic="AI Safety"
```

### Python

```python
from configurable_agents.runtime import run_workflow

result = run_workflow("examples/article_writer.yaml", {"topic": "AI Safety"})

print("Research:")
print(result["research"])
print("\nArticle:")
print(result["article"])
print(f"\nWord count: {result['word_count']}")
```

## How It Works

### Node 1: Research (`research`)
- **Input**: `{state.topic}`
- **Tool**: `serper_search` - searches Google for recent information
- **Output**: `research` field (summary of findings)
- **LLM Task**: Synthesize search results into 2-3 paragraph summary

### Node 2: Write (`write`)
- **Input**: `{state.topic}` and `{state.research}`
- **No tools**: Pure LLM text generation
- **Outputs**: `article` and `word_count` fields
- **LLM Task**: Write 300-400 word article with intro, body, conclusion

### State Flow

```
Initial: {topic: "AI Safety", research: "", article: "", word_count: 0}
         ↓
After research: {topic: "AI Safety", research: "...", article: "", word_count: 0}
         ↓
After write: {topic: "AI Safety", research: "...", article: "...", word_count: 350}
```

## Expected Output

```
Result:
  topic: AI Safety
  research: |
    AI Safety focuses on ensuring artificial intelligence systems are reliable,
    robust, and aligned with human values. Recent developments include...

  article: |
    # Understanding AI Safety

    As artificial intelligence becomes increasingly powerful, the field of AI
    safety has emerged as a critical area of research...

  word_count: 387
```

## Configuration Explained

```yaml
config:
  llm:
    model: "gemini-2.5-flash-lite"  # Fast, cost-effective model
    temperature: 0.7                 # Balance creativity/consistency
  execution:
    timeout: 120                     # 2 minutes max per node
    max_retries: 3                   # Retry on API failures
```

## What You'll Learn

- Multi-node workflows (sequential execution)
- Tool integration (web search API)
- State updates across nodes
- Multiple output fields from single node
- Global configuration for LLM and execution
- Structured outputs with complex schemas

## Troubleshooting

**Error: "SERPER_API_KEY not set"**
- Get free API key from https://serper.dev
- Set environment variable: `export SERPER_API_KEY=your-key`

**Error: "Timeout after 120 seconds"**
- Increase timeout in config: `timeout: 300`
- Or reduce scope in prompt

**Low quality output**
- Adjust temperature (higher = more creative)
- Try different model: `gemini-2.5-pro` (better quality, slower/pricier)
- Improve prompt specificity

## Next Steps

Once this works, try:
1. Modify prompts to change article style
2. Add a third node for editing/refinement
3. Change tools (future: add more tools)
4. Experiment with temperature/model settings
