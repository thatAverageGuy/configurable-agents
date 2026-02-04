# Webhook Integration Example

This example shows how to trigger workflows from external webhooks, enabling event-driven automation.

## Use Case

Automatically process events from external services (GitHub, Stripe, custom systems) and send notifications or take actions.

## Features Demonstrated

- Webhook triggering with generic endpoint
- Event processing and logging
- Notification formatting
- MLFlow tracking for webhook events

## Prerequisites

- Configurable Agents running with webhooks enabled
- Ngrok or public IP for webhook delivery (for testing)
- Dashboard server running

## Setup

### 1. Start the Dashboard with Webhooks

```bash
configurable-agents dashboard --port 8000
```

### 2. Register the Workflow

```bash
curl -X POST http://localhost:8000/api/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "slack_notification",
    "config_path": "webhook_integration.yaml"
  }'
```

### 3. Test with Webhook

```bash
./test_webhook.sh
```

### 4. Verify Execution

Check MLFlow UI: http://localhost:5000

## Webhook Payload

Send POST request to `http://localhost:8000/webhooks/generic`:

```json
{
  "workflow_name": "slack_notification",
  "inputs": {
    "event_type": "deployment",
    "message": "New version deployed to production",
    "slack_channel": "#alerts"
  }
}
```

## Testing

### Manual Testing

```bash
WEBHOOK_URL="http://localhost:8000/webhooks/generic"
PAYLOAD='{
  "workflow_name": "slack_notification",
  "inputs": {
    "event_type": "test",
    "message": "Test webhook from curl",
    "slack_channel": "#general"
  }
}'

curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
```

### Using Test Script

```bash
./test_webhook.sh
```

### Expected Output

The workflow will:
1. Log the event (node: log_event)
2. Format a Slack notification (node: format_notification)
3. Return the final notification text

## Production Deployment

### 1. Configure Webhook Secret

Generate and configure webhook secret:

```bash
# Generate secret
openssl rand -hex 32 > /etc/webhook-secret
export WEBHOOK_SECRET=$(cat /etc/webhook-secret)
```

### 2. Use HTTPS Endpoints

Always use HTTPS in production:

```bash
# Let's Encrypt
certbot certonly --standalone -d webhooks.example.com
```

### 3. Implement Signature Verification

Add HMAC signature to your webhook sender:

```python
import hmac
import hashlib
import json
import requests

def send_webhook(url, payload, secret):
    """Send webhook with HMAC signature."""
    payload_str = json.dumps(payload)
    signature = hmac.new(
        secret.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()

    requests.post(
        url,
        data=payload_str,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature
        }
    )
```

### 4. Set Up Retry Logic

Implement retry logic for failed webhooks:

```python
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retries)
session.mount('http://', adapter)
session.mount('https://', adapter)
```

## Troubleshooting

### Webhook Not Triggering

1. Check workflow is registered:
```bash
curl http://localhost:8000/api/workflows
```

2. Verify webhook endpoint is accessible:
```bash
curl http://localhost:8000/webhooks/generic
```

3. Check logs for errors:
```bash
configurable-agents logs --follow
```

### Signature Verification Failed

1. Verify secret is set:
```bash
echo $WEBHOOK_SECRET
```

2. Check signature generation matches format

3. Ensure payload is JSON-encoded correctly

### Workflow Not Executing

1. Check MLFlow for execution records
2. Verify workflow configuration is valid
3. Review dashboard logs for errors

## Advanced Usage

### Custom Webhook Endpoints

Create custom endpoints for specific services:

```python
# In your FastAPI app
@app.post("/webhooks/github")
async def github_webhook(request: Request):
    payload = await request.json()
    # Map GitHub events to workflow inputs
    return await trigger_workflow(payload)

@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.json()
    # Map Stripe events to workflow inputs
    return await trigger_workflow(payload)
```

### Webhook Chaining

Chain multiple workflows:

```yaml
# first_workflow.yaml
nodes:
  - name: trigger_next
    llm:
      provider: google
      model: gemini-1.5-flash
    prompt: |
      Complete processing and trigger next workflow
```

Then trigger second workflow via webhook:

```python
requests.post(WEBHOOK_URL, json={
  "workflow_name": "second_workflow",
  "inputs": {"data": result}
})
```

## See Also

- [Webhooks Documentation](../../docs/WEBHOOKS.md)
- [Security Guide](../../docs/SECURITY_GUIDE.md) - Webhook security
- [Examples README](../README.md) - More examples

## Example Webhook Sources

### GitHub

```yaml
# GitHub webhook payload
{
  "ref": "refs/heads/main",
  "repository": {
    "name": "configurable-agents"
  },
  "head_commit": {
    "message": "Add new feature"
  }
}
```

### Stripe

```yaml
# Stripe webhook payload
{
  "type": "charge.succeeded",
  "data": {
    "object": {
      "amount": 2000,
      "currency": "usd"
    }
  }
}
```

### Custom Systems

```yaml
# Custom webhook payload
{
  "event": "user_action",
  "user_id": "12345",
  "action": "completed_task",
  "timestamp": "2026-02-04T12:00:00Z"
}
```

---

**Level**: Advanced (⭐⭐⭐⭐)
**Prerequisites**: Running dashboard, basic HTTP knowledge
**Time Investment**: 30-60 minutes to set up and test
