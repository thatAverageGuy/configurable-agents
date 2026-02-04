#!/bin/bash

# Test webhook script for webhook integration example

WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:8000/webhooks/generic}"

PAYLOAD='{
  "workflow_name": "slack_notification",
  "inputs": {
    "event_type": "test",
    "message": "Test webhook from shell script",
    "slack_channel": "#general"
  }
}'

echo "=================================="
echo "Webhook Integration Test"
echo "=================================="
echo ""
echo "Sending webhook to: $WEBHOOK_URL"
echo ""
echo "Payload:"
echo "$PAYLOAD" | python -m json.tool
echo ""
echo "=================================="
echo "Response:"
echo "=================================="

curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  -w "\nHTTP Status: %{http_code}\n"

echo ""
echo "=================================="
echo "Check MLFlow UI for execution results:"
echo "http://localhost:5000"
echo "=================================="
