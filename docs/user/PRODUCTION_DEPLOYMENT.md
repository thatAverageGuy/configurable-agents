# Production Deployment

This guide covers patterns and best practices for deploying Configurable Agents in production environments.

## Table of Contents
- [Overview](#overview)
- [Deployment Architectures](#deployment-architectures)
- [Storage Backends](#storage-backends)
- [Scaling Strategies](#scaling-strategies)
- [Monitoring and Observability](#monitoring-and-observability)
- [High Availability](#high-availability)
- [Security in Production](#security-in-production)
- [Production Checklist](#production-checklist)
- [Troubleshooting](#troubleshooting)

## Overview

Production deployment requires consideration of:
- **Scalability**: Handling increased load
- **Reliability**: Ensuring consistent uptime
- **Security**: Protecting sensitive data
- **Observability**: Monitoring system health
- **Maintainability**: Updates and troubleshooting

## Deployment Architectures

### Single-Server Deployment

**Architecture:**

```
┌─────────────────────────────┐
│  Docker Container           │
│                             │
│  ┌───────────────────────┐ │
│  │  FastAPI Server       │ │
│  │  + Workflow Engine    │ │
│  └───────────────────────┘ │
│  ┌───────────────────────┐ │
│  │  MLFlow UI (Sidecar)  │ │
│  └───────────────────────┘ │
│  ┌───────────────────────┐ │
│  │  SQLite Database      │ │
│  └───────────────────────┘ │
└─────────────────────────────┘
```

**Use Case:**
- Small team (1-5 people)
- Single workflow
- < 100 executions/day
- Development/testing

**Setup:**

```bash
# Generate deployment artifacts
configurable-agents deploy generate \
  --config workflow.yaml \
  --output ./deploy

# Deploy with Docker
cd deploy
docker-compose up -d
```

**Pros:**
- Simple setup
- Low cost
- Easy to manage
- Fast deployment

**Cons:**
- Single point of failure
- Limited scalability
- Manual recovery
- No high availability

### Multi-Workflow Deployment

**Architecture:**

```
┌──────────────────────────────────────────────┐
│  Orchestrator Service                        │
│  (Discovers and coordinates agents)          │
└──────┬─────────────┬─────────────┬───────────┘
       │             │             │
┌──────▼──────┐ ┌────▼─────┐ ┌────▼──────┐
│  Agent 1    │ │  Agent 2 │ │  Agent 3  │
│  Workflow A │ │ Workflow │ │ Workflow │
│             │ │    B     │ │    C     │
└─────────────┘ └──────────┘ └───────────┘
       │             │             │
       └─────────────┴─────────────┘
                     │
            ┌────────▼────────┐
            │  Dashboard      │
            │  + MLFlow       │
            └─────────────────┘
```

**Use Case:**
- Small to medium team (5-20 people)
- Multiple workflows (3-10)
- 100-1000 executions/day
- Parallel execution needed

**Setup:**

```bash
# Start dashboard
configurable-agents dashboard --port 8000 &

# Deploy each agent
for workflow in workflows/*.yaml; do
  configurable-agents deploy generate \
    --config "$workflow" \
    --output "./deploy/$(basename $workflow .yaml)"
  docker-compose -f "./deploy/$(basename $workflow .yaml)/docker-compose.yml" up -d &
done
```

**Pros:**
- Parallel execution
- Workflow isolation
- Better resource utilization
- Agent discovery

**Cons:**
- More complex setup
- Multiple containers to manage
- Dashboard is single point of failure
- More infrastructure

### Kubernetes Deployment

**Architecture:**

```
┌────────────────────────────────────────┐
│  Kubernetes Cluster                    │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  Namespace: configurable-agents │ │
│  │                                  │ │
│  │  ┌────────────┐  ┌────────────┐ │ │
│  │  │  Agent Pods │  │  Dashboard│ │ │
│  │  │  (HPA: 3-10)│  │  (Stateful)│ │ │
│  │  └────────────┘  └────────────┘ │ │
│  │                                  │ │
│  │  ┌────────────┐  ┌────────────┐ │ │
│  │  │  MLFlow    │  │  Postgres  │ │ │
│  │  │  (Deployment)│ │  (StatefulSet)││ │
│  │  └────────────┘  └────────────┘ │ │
│  └──────────────────────────────────┘ │
└────────────────────────────────────────┘
```

**Use Case:**
- Enterprise scale
- High availability required
- 1000+ executions/day
- Multi-tenant
- Auto-scaling needed

**Setup:**

```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: configurable-agents
spec:
  replicas: 3
  selector:
    matchLabels:
      app: configurable-agents
  template:
    metadata:
      labels:
        app: configurable-agents
    spec:
      containers:
      - name: agent
        image: configurable-agents:latest
        resources:
          requests:
            cpu: 1000m
            memory: 1Gi
          limits:
            cpu: 4000m
            memory: 4Gi
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: google
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: configurable-agents-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: configurable-agents
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**Pros:**
- Auto-scaling
- High availability
- Self-healing
- Load balancing
- Rolling updates

**Cons:**
- Complex setup
- Higher operational cost
- Requires Kubernetes expertise
- More infrastructure

## Storage Backends

### SQLite (Default)

```yaml
# In .env
DATABASE_URL=sqlite:///./workflows.db
```

**Pros:**
- Zero configuration
- Embedded in workflow
- Sufficient for < 1000 executions/day
- No additional infrastructure

**Cons:**
- Single writer limitation
- No horizontal scaling
- Limited to single server
- No backup/replication

**When to Use:**
- Development
- Testing
- Small deployments
- Single-server production

### PostgreSQL (Recommended for Production)

```yaml
# In .env
DATABASE_URL=postgresql://user:pass@localhost:5432/workflows
```

**Pros:**
- Multi-writer support
- Horizontal scaling
- Better performance at scale
- Production-grade reliability
- Built-in replication
- Backup tools

**Setup:**

```bash
# Using Docker
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=workflows \
  -p 5432:5432 \
  -v postgres-data:/var/lib/postgresql/data \
  postgres:15

# Configure storage backend in workflow config
# config:
#   storage:
#     backend: "postgresql://user:pass@host:5432/workflows"
```

**When to Use:**
- Production deployments
- Multi-server setups
- High write throughput
- Need replication

### Redis (Future - Caching Layer)

```yaml
# In .env
REDIS_URL=redis://localhost:6379
```

**Use Cases:**
- Response caching
- Session storage
- Rate limiting
- Distributed locking

## Scaling Strategies

### Horizontal Scaling

**Docker Compose:**

```bash
docker-compose up -d --scale agent=3
```

**Kubernetes HPA:**

```bash
kubectl autoscale deployment configurable-agents \
  --min=3 --max=10 --cpu-percent=70
```

### Vertical Scaling

```yaml
resources:
  limits:
    cpu: 8000m      # 8 CPUs
    memory: 8Gi     # 8GB RAM
```

### Database Connection Pooling

```python
# In production configuration
database:
  url: postgresql://...
  pool_size: 20
  max_overflow: 40
  pool_timeout: 30
```

## Monitoring and Observability

### MLFlow Production Setup

```bash
# Deploy MLFlow with PostgreSQL backend
docker run -d \
  --name mlflow \
  -p 5000:5000 \
  -e BACKEND_STORE_URI=postgresql://... \
  -e DEFAULT_ARTIFACT_ROOT=s3://mlflow-artifacts \
  mlflow/mlflow \
  mlflow server \
    --backend-store-uri $BACKEND_STORE_URI \
    --default-artifact-root $DEFAULT_ARTIFACT_ROOT \
    --host 0.0.0.0
```

### Health Checks

```bash
# Health check endpoint
curl http://localhost:8000/health

# Response
{"status": "healthy", "database": "connected", "mlflow": "connected"}
```

### Metrics Collection

```yaml
observability:
  mlflow:
    enabled: true
    tracking_uri: "http://mlflow:5000"
  metrics:
    - name: workflow_duration
      type: histogram
    - name: llm_cost_usd
      type: gauge
    - name: error_rate
      type: gauge
```

### Logging

```bash
# Structured logging (JSON)
export LOG_FORMAT=json
export LOG_LEVEL=INFO

# Send to log aggregation
export LOG_DESTINATION=file:///var/log/agents.log
# OR
export LOG_DESTINATION=https://logs.example.com
```

## High Availability

### Load Balancing

```yaml
# nginx.conf
upstream agents {
    least_conn;
    server agent1:8000;
    server agent2:8000;
    server agent3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://agents;
        proxy_set_header Host $host;
    }
}
```

### Graceful Shutdown

```python
# Handle SIGTERM for container orchestration
import signal

def shutdown_handler(signum, frame):
    # Complete current workflow
    # Close database connections
    # Exit gracefully
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown_handler)
```

### Backup and Recovery

**Database Backups:**

```bash
# PostgreSQL backup
pg_dump -U user workflows > backup_$(date +%Y%m%d).sql

# Restore
psql -U user workflows < backup_20260204.sql
```

**Configuration Backups:**

```bash
# Backup all workflows
tar czf workflows_backup_$(date +%Y%m%d).tar.gz workflows/

# Backup MLFlow experiments
mlflow db upgrade --from-sqlite-migrations \
  mlflow.db mlflow_backup.db
```

## Security in Production

### Network Security

```bash
# Firewall rules
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 22/tcp    # SSH
ufw deny 8000/tcp   # Block direct access to internal ports
```

### TLS/SSL

```bash
# Let's Encrypt for HTTPS
certbot certonly --standalone -d agents.example.com

# Configure nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
}
```

### Secrets Management

```bash
# HashiCorp Vault integration
export VAULT_ADDR=https://vault.example.com
vault kv get -field=api_key secret/agents/openai

# AWS Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id configurable-agents/prod \
  --query SecretString --output text > .env
```

## Production Checklist

### Pre-Deployment

- [ ] Storage backend configured (PostgreSQL)
- [ ] MLFlow production deployment
- [ ] TLS/SSL certificates configured
- [ ] Secrets in secure vault
- [ ] Firewall rules configured
- [ ] Monitoring and alerting setup
- [ ] Backup procedures documented
- [ ] Health check endpoints configured
- [ ] Resource limits set
- [ ] Log aggregation configured
- [ ] Load balancer configured
- [ ] High availability setup

### Post-Deployment

- [ ] Verify all services healthy
- [ ] Test workflow execution
- [ ] Monitor metrics for 1 hour
- [ ] Load test with expected traffic
- [ ] Verify MLFlow tracking
- [ ] Test backup/restore
- [ ] Document incident response
- [ ] Train team on operations

### Ongoing Operations

- [ ] Daily health checks
- [ ] Weekly backup verification
- [ ] Monthly security updates
- [ ] Quarterly performance review
- [ ] Annual disaster recovery test
- [ ] Regular log reviews
- [ ] Capacity planning
- [ ] Cost optimization

## Troubleshooting

### Database Connection Issues

```bash
# Check database connectivity
psql $DATABASE_URL -c "SELECT 1"

# Check connection pool
curl http://localhost:8000/metrics | grep db_pool
```

### High Memory Usage

```bash
# Profile memory usage
python -m memory_profiler workflow.py

# Check for memory leaks
docker stats configurable-agents
```

### Slow Workflow Execution

```bash
# Enable profiling
export CONFIGURABLE_AGENTS_PROFILING=true

# View profile report
configurable-agents profile-report
```

### Pod Crashing (Kubernetes)

```bash
# Check pod status
kubectl get pods

# View pod logs
kubectl logs <pod-name>

# Describe pod
kubectl describe pod <pod-name>
```

## Related Documentation

- [Deployment Guide](DEPLOYMENT.md) - Docker deployment basics
- [Security Guide](SECURITY_GUIDE.md) - Security best practices
- [Observability Guide](OBSERVABILITY.md) - Monitoring setup
- [Performance Optimization](PERFORMANCE_OPTIMIZATION.md) - Tuning and optimization

---

**Level**: Advanced (⭐⭐⭐⭐⭐)
**Prerequisites**: Docker, Kubernetes, system administration
**Time Investment**: 16-40 hours for full production setup
**Importance**: CRITICAL for production success
