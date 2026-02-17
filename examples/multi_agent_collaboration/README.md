# Multi-Agent Collaboration Example

This example demonstrates coordinating multiple specialist agents working in parallel to accomplish complex tasks.

## Architecture

```
┌──────────────┐
│  Coordinator │
│   Agent      │
└──────┬───────┘
       │
       ├──────────────┬──────────────┐
       │              │              │
┌──────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐
│  Researcher │ │ Analyst  │ │  Writer    │
│   Agent     │ │  Agent   │ │   Agent    │
└─────────────┘ └──────────┘ └────────────┘
       │              │              │
       └──────────────┴──────────────┘
                      │
             ┌────────▼────────┐
             │   Deployments   │
             │   (Registry)    │
             └─────────────────┘
```

## Use Case

Complex research tasks requiring multiple specialist agents:
- Market analysis (competitive, financial, technical)
- Content creation (researcher, writer, editor)
- Data analysis (collector, analyst, reporter)
- Technical documentation (researcher, writer, reviewer)

## Features Demonstrated

- Deployment-based agent management
- Metadata-based agent filtering
- Parallel agent execution
- Multi-agent coordination

## Prerequisites

- Dashboard server running
- Multiple agent instances deployed

## Setup

### 1. Start Dashboard

```bash
configurable-agents dashboard --port 8000
```

### 2. Deploy Specialist Agents

```bash
# Researcher agent
configurable-agents deployments start \
  --name researcher \
  --port 8001 \
  --metadata '{"capability": "research", "specialty": "web_search"}'

# Analyst agent
configurable-agents deployments start \
  --name analyst \
  --port 8002 \
  --metadata '{"capability": "analysis", "specialty": "data_synthesis"}'

# Writer agent
configurable-agents deployments start \
  --name writer \
  --port 8003 \
  --metadata '{"capability": "writing", "specialty": "content_creation"}'
```

### 3. Run Collaborative Workflow

```bash
configurable-agents run multi_agent_collaboration.yaml
```

## Configuration

### Agent Discovery

Agents are discovered based on metadata via the deployments API:

```bash
# List all deployments
configurable-agents deployments list

# View deployment details
curl http://localhost:8000/api/deployments
```

### Parallel Execution

```yaml
execution:
  parallel_execution: true
  max_parallel_agents: 5
  timeout: 300
```

**Configuration Options:**
- `parallel_execution`: Enable/disable parallel execution
- `max_parallel_agents`: Maximum agents to run simultaneously
- `timeout`: Maximum time for entire workflow (seconds)

## Monitoring

### Dashboard

```bash
# Open dashboard
http://localhost:8000/deployments
```

**Dashboard Shows:**
- Active deployments
- Connected agents
- Agent health (heartbeat status)
- Execution metrics
- Agent metadata

## Production Considerations

### 1. Agent Health Monitoring

```yaml
# Heartbeat configuration
agent:
  heartbeat_ttl: 60  # seconds
  heartbeat_interval: 20  # seconds
```

**Features:**
- Automatic reconnection on heartbeat failure
- Graceful degradation when agents unavailable
- Health check endpoints

### 2. Error Handling

```yaml
execution:
  error_handling:
    retry_attempts: 3
    retry_delay: 5  # seconds
    fallback_to_single: true  # Run sequentially if parallel fails
```

**Error Scenarios:**
- Agent unavailable: Use alternative agent
- Agent timeout: Retry with extended timeout
- Agent failure: Log and continue with other agents
- All agents failed: Fail workflow gracefully

## Troubleshooting

### Agents Not Discoverable

```bash
# Check deployments
curl http://localhost:8000/api/deployments

# Verify agent metadata
curl http://localhost:8000/api/deployments/{deployment_id}
```

### Parallel Execution Issues

**Problem**: Agents not running in parallel

**Solutions:**
1. Check `max_parallel_agents` limit
2. Verify agent capacity (sufficient resources)
3. Review logs for errors
4. Ensure agents support concurrent execution

## Example Use Cases

### Market Analysis

```yaml
# Run market analysis with specialist teams
research_topic: "Competitive analysis of AI agent platforms"

specialist_agents:
  - technology_researcher
  - financial_analyst
  - market_analyst
  - product_strategist
```

### Content Creation Pipeline

```yaml
# Multi-stage content creation
specialist_agents:
  - topic_researcher
  - content_writer
  - content_editor
  - seo_specialist
```

### Data Analysis

```yaml
# Complex data analysis project
research_topic: "Customer churn prediction"

specialist_agents:
  - data_collector
  - data_analyst
  - ml_engineer
  - report_generator
```

## See Also

- [Production Deployment](../../docs/user/PRODUCTION_DEPLOYMENT.md)
- [Performance Optimization](../../docs/user/PERFORMANCE_OPTIMIZATION.md)

---

**Level**: Advanced
**Prerequisites**: Dashboard server, multiple agent instances
**Time Investment**: 1-2 hours to set up and test
**Complexity**: High - multi-agent coordination
