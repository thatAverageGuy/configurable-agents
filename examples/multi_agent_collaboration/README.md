# Multi-Agent Collaboration Example

This example demonstrates orchestrating multiple specialist agents working in parallel to accomplish complex tasks.

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
             │  Orchestrator   │
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

- Agent registration and discovery
- Metadata-based agent filtering
- Parallel agent execution
- Orchestrator pattern
- Multi-agent coordination

## Prerequisites

- Agent registry running
- Multiple agent instances registered
- Dashboard server running

## Setup

### 1. Start Agent Registry

```bash
configurable-agents registry --port 8000
```

### 2. Register Specialist Agents

```bash
# Researcher agent
configurable-agents agent start \
  --name researcher \
  --port 8001 \
  --metadata '{"capability": "research", "specialty": "web_search"}'

# Analyst agent
configurable-agents agent start \
  --name analyst \
  --port 8002 \
  --metadata '{"capability": "analysis", "specialty": "data_synthesis"}'

# Writer agent
configurable-agents agent start \
  --name writer \
  --port 8003 \
  --metadata '{"capability": "writing", "specialty": "content_creation"}'
```

### 3. Run Orchestrated Workflow

```bash
configurable-agents run multi_agent_collaboration.yaml \
  --orchestrator-url http://localhost:8000
```

## Configuration

### Orchestrator Discovery

Agents are discovered based on metadata:

```python
# orchestrator_config.py
from configurable_agents.orchestrator import AgentRegistryOrchestratorClient

client = AgentRegistryOrchestratorClient(
    registry_url="http://localhost:8000"
)

# Find agents by capability
agents = client.discover_agents(
    metadata_filter={"capability": "research"}
)

# Find specific specialist
analyst = client.discover_agents(
    metadata_filter={"specialty": "data_synthesis"}
)

# Find all available agents
all_agents = client.discover_agents()
```

### Parallel Execution

```yaml
orchestration:
  parallel_execution: true
  max_parallel_agents: 5
  timeout: 300
```

**Configuration Options:**
- `parallel_execution`: Enable/disable parallel execution
- `max_parallel_agents`: Maximum agents to run simultaneously
- `timeout`: Maximum time for entire workflow (seconds)

## Monitoring

### Orchestrator Dashboard

```bash
# Open dashboard
http://localhost:8000/orchestrator
```

**Dashboard Shows:**
- Active orchestrators
- Connected agents
- Agent health (heartbeat status)
- Execution metrics
- Agent metadata

### MLFlow Tracking

Each agent execution tracked separately:
- `agent_name` tag
- `agent_id` tag
- `specialty` tag
- Agent-specific metrics

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

### 2. Load Balancing

```python
# Multiple agents per specialty
for i in range(3):
    agent.start(
        metadata={"capability": "research", "instance": i}
    )

# Round-robin assignment
orchestrator.set_load_balancing_strategy("round_robin")
```

**Strategies:**
- Round-robin: Distribute evenly
- Least connections: Route to least busy agent
- Random: Random selection
- Custom: User-defined logic

### 3. Error Handling

```yaml
orchestration:
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
# Check registry
curl http://localhost:8000/api/agents

# Verify agent metadata
curl http://localhost:8000/api/agents/{agent_id}

# Check heartbeat status
curl http://localhost:8000/api/agents/active
```

### Parallel Execution Issues

**Problem**: Agents not running in parallel

**Solutions:**
1. Check `max_parallel_agents` limit
2. Verify agent capacity (sufficient resources)
3. Review orchestrator logs for errors
4. Ensure agents support concurrent execution

**Check Capacity:**
```bash
# View agent capacity
curl http://localhost:8000/orchestrator/capacity
```

### Orchestration Timeout

**Problem**: Workflow exceeds timeout

**Solutions:**
1. Increase timeout in workflow config
2. Optimize agent performance
3. Break into smaller workflows
4. Use more powerful agent instances

## Advanced Usage

### Custom Orchestration Logic

```python
from configurable_agents.orchestrator import OrchestratorService

class CustomOrchestrator(OrchestratorService):
    def select_agents(self, task):
        # Custom agent selection logic
        if task.difficulty == "high":
            return self.get_agents_by_capability("expert")
        else:
            return self.get_agents_by_capability("standard")

    def route_work(self, work_items):
        # Custom work distribution
        return self.distribute_by_workload(work_items)
```

### Dynamic Agent Scaling

```python
# Auto-scale based on queue depth
queue_depth = orchestrator.get_queue_depth()

if queue_depth > 10:
    # Add more agents
    orchestrator.scale_agents(count=queue_depth // 5)
elif queue_depth < 2:
    # Remove excess agents
    orchestrator.scale_agents(count=2)
```

### Multi-Stage Workflows

```yaml
# Stage 1: Research
stage1_research:
  agents: [researcher_1, researcher_2]

# Stage 2: Analysis (runs after research completes)
stage2_analysis:
  agents: [analyst]
  depends_on: [stage1_research]

# Stage 3: Writing (runs after analysis completes)
stage3_writing:
  agents: [writer]
  depends_on: [stage2_analysis]
```

## See Also

- [Orchestrator Documentation](../../docs/ORCHESTRATOR.md)
- [Agent Registration Guide](../../docs/AGENT_REGISTRATION.md)
- [Production Deployment](../../docs/PRODUCTION_DEPLOYMENT.md)

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

---

**Level**: Advanced (⭐⭐⭐⭐⭐)
**Prerequisites**: Agent registry, multiple agent instances
**Time Investment**: 1-2 hours to set up and test
**Complexity**: High - orchestration and multi-agent coordination
