# ADR-024: Webhook Integration Pattern

**Status**: Accepted
**Date**: 2026-02-04
**Deciders**: thatAverageGuy, Claude Code

---

## Context

The system needs to trigger workflows from external messaging platforms (WhatsApp, Telegram) and any generic system that can send HTTP webhooks.

### Requirements

- **INT-01**: User can trigger workflows from WhatsApp messages (webhook integration)
- **INT-02**: User can trigger workflows from Telegram messages (bot integration)
- **INT-03**: User can trigger workflows from any external system via generic webhook API

### Constraints

- Must be secure (prevent unauthorized webhook triggers)
- Must be idempotent (duplicate webhooks should not re-run workflows)
- Must handle platform-specific formats (WhatsApp vs Telegram vs generic)
- Must support async execution (webhooks shouldn't block)

---

## Decision

**Use FastAPI for webhook endpoints with HMAC signature verification, idempotency tracking via database, and platform-specific handlers for WhatsApp/Telegram. Generic webhook endpoint for universal integration.**

---

## Rationale

### Why HMAC Signature Verification?

1. **Security**: Prevents unauthorized webhook triggers
2. **Standard**: Used by GitHub, Stripe, Twilio, Meta
3. **Simple**: Shared secret, hash comparison
4. **Optional**: Can disable for internal/testing (configurable)

### Why Idempotency Tracking?

1. **Duplicate Delivery**: Webhooks may be retried (network issues, server restart)
2. **Exactly-Once**: Prevent running same workflow twice
3. **Database**: `INSERT OR IGNORE` pattern (unique constraint on webhook_id)
4. **Standard**: Used by Stripe, GitHub Actions

### Why Platform-Specific Handlers?

1. **Format Differences**: WhatsApp vs Telegram have different message formats
2. **Validation**: Each platform has specific verification requirements
3. **Lazy Loading**: Only load handler when platform env vars configured
4. **Extensible**: Easy to add new platforms (Slack, Discord, etc.)

### Why Generic Webhook?

1. **Universal Integration**: Any system that can send HTTP POST
2. **Simple**: Just workflow_name + inputs in JSON
3. **Flexibility**: Users define trigger conditions in workflow config
4. **Fallback**: For platforms without specific handler

---

## Implementation

### Generic Webhook Endpoint

```python
@app.post("/webhooks/generic")
async def generic_webhook(
    request: Request,
    workflow_name: str,
    inputs: dict,
    webhook_id: Optional[str] = None,
    signature: Optional[str] = Header(None)
):
    """Universal webhook endpoint"""

    # Verify HMAC signature if secret configured
    if WEBHOOK_SECRET:
        verify_signature(signature, await request.body(), WEBHOOK_SECRET)

    # Check idempotency (prevent duplicates)
    if webhook_id and _webhook_exists(webhook_id):
        return {"status": "already_processed"}

    # Run workflow asynchronously
    run_workflow_async(workflow_name, inputs)

    # Track webhook
    if webhook_id:
        _track_webhook(webhook_id, workflow_name, inputs)

    return {"status": "triggered", "workflow_name": workflow_name}
```

### HMAC Signature Verification

```python
import hmac
import hashlib

def verify_signature(signature: str, body: bytes, secret: str) -> bool:
    """Verify HMAC signature"""
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected, signature)
```

### Idempotency Tracking

```python
class WebhookExecution(Base):
    """Track webhook executions for idempotency"""
    __tablename__ = "webhook_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    webhook_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    workflow_name: Mapped[str] = mapped_column(String(255))
    inputs: Mapped[JSON] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

def _track_webhook(webhook_id: str, workflow_name: str, inputs: dict):
    """Track webhook execution (INSERT OR IGNORE)"""
    with Session(session_factory) as session:
        execution = WebhookExecution(
            webhook_id=webhook_id,
            workflow_name=workflow_name,
            inputs=inputs
        )
        session.add(execution)
        try:
            session.commit()
        except IntegrityError:
            pass  # Already exists (idempotent)
```

### WhatsApp Handler

```python
@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    """WhatsApp Business API webhook"""

    # Verify webhook (Meta requirement)
    if request.method == "GET":
        mode = request.query["hub.mode"]
        challenge = request.query["hub.challenge"]
        token = request.query["hub.verify_token"]
        if token == WHATSAPP_VERIFY_TOKEN:
            return Response(content=challenge, status_code=200)

    # Process message
    body = await request.json()
    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    phone_number = message["from"]
    text = message["text"]["body"]

    # Trigger workflow
    run_workflow_async(
        workflow_name="whatsapp_handler",
        inputs={"phone": phone_number, "message": text}
    )

    return {"status": "ok"}
```

### Telegram Handler (aiogram 3.x)

```python
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

# Initialize bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command"""
    run_workflow_async(
        workflow_name="telegram_welcome",
        inputs={"user_id": message.from_user.id, "message": message.text}
    )

async def start_telegram_bot():
    """Start Telegram bot polling"""
    await dp.start_polling(bot)
```

### Async Workflow Execution

```python
def run_workflow_async(workflow_name: str, inputs: dict):
    """Run workflow in background task"""
    async def _run():
        # Load and execute workflow
        result = run_workflow(workflow_name, inputs)

    # Spawn background task
    asyncio.create_task(_run())
```

---

## Configuration

### Global Webhook Config

```yaml
config:
  webhooks:
    enabled: true
    secret: "webhook_secret_key"  # HMAC signing
    max_retries: 3
    timeout: 30
```

### Platform-Specific Config

```yaml
config:
  webhooks:
    platforms:
      whatsapp:
        enabled: true
        phone_id: "123456789"
        access_token: "whatsapp_token"
        verify_token: "verify_token"
        webhook_url: "https://myserver.com/webhooks/whatsapp"
      telegram:
        enabled: true
        bot_token: "telegram_bot_token"
```

---

## Security

### HMAC Signature Verification

```python
# Client sends header
X-Webhook-Signature: sha256=<hash>

# Server verifies
signature = request.headers["X-Webhook-Signature"]
expected = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()

if not hmac.compare_digest(expected, signature):
    raise HTTPException(status_code=401, detail="Invalid signature")
```

### Meta Webhook Verification (WhatsApp)

```python
@app.get("/webhooks/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str,
    hub_challenge: str,
    hub_verify_token: str
):
    """Meta webhook verification (GET request)"""
    if hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        return Response(content=hub_challenge, status_code=200)
    else:
        raise HTTPException(status_code=403)
```

### Idempotency

```python
# Client sends unique ID
POST /webhooks/generic
X-Webhook-Id: abc123

# Server tracks ID
INSERT OR IGNORE INTO webhook_executions (webhook_id, ...)
```

---

## Message Chunking

### WhatsApp (4096 char limit)

```python
def chunk_message(message: str, max_length: int = 4096) -> List[str]:
    """Split message into chunks"""
    chunks = []
    while message:
        chunks.append(message[:max_length])
        message = message[max_length:]
    return chunks
```

### Telegram (4096 char limit)

```python
async def send_telegram_message(chat_id: int, text: str):
    """Send message with chunking"""
    MAX_LENGTH = 4096
    for chunk in chunk_message(text, MAX_LENGTH):
        await bot.send_message(chat_id, chunk)
```

---

## Alternatives Considered

### Alternative 1: No Signature Verification

**Pros**:
- Simpler integration
- No shared secret management

**Cons**:
- **Security Risk**: Anyone can trigger workflows
- **Unauthorized Execution**: Bad actors can spam webhooks

**Why rejected**: Security is non-negotiable. Webhooks must be authenticated.

### Alternative 2: Query String Params (Shared Secret)

**Pros**:
- Simpler than HMAC
- Works with basic auth

**Cons**:
- **Security Risk**: Secret in URL (logged, cached)
- **No Integrity**: Can't verify request body wasn't tampered

**Why rejected**: HMAC is standard (GitHub, Stripe, Twilio use it).

### Alternative 3: JWT Tokens

**Pros**:
- Standard (OAuth 2.0)
- Claims/expiration built-in

**Cons**:
- Overkill for webhooks
- Token management overhead
- Not designed for webhook verification

**Why rejected**: HMAC is simpler and purpose-built for webhooks.

---

## Consequences

### Positive Consequences

1. **Secure**: HMAC verification prevents unauthorized triggers
2. **Idempotent**: Duplicate webhooks don't re-run workflows
3. **Universal**: Generic endpoint works with any HTTP client
4. **Platform-Specific**: WhatsApp/Telegram handlers provide best UX
5. **Async**: Webhooks return immediately, workflows run in background

### Negative Consequences

1. **Secret Management**: Must distribute shared secret to webhook senders
2. **Setup Complexity**: WhatsApp requires Meta developer account
3. **Polling**: Telegram bot uses polling (can upgrade to webhooks later)
4. **No Retry**: Failed webhooks aren't retried (can add later)

### Risks

#### Risk 1: Secret Leaked

**Likelihood**: Medium
**Impact**: High
**Mitigation**: Rotate secrets regularly. Use environment variables. Alert on failures.

#### Risk 2: Clock Skew (HMAC)

**Likelihood**: Low (webhooks are fast)
**Impact**: Low
**Mitigation**: HMAC is time-insensitive (no timestamp in signature).

#### Risk 3: Idempotency Collision

**Likelihood**: Low (UUIDs)
**Impact**: Low
**Mitigation**: Unique constraint on webhook_id. Use UUID v4.

---

## Related Decisions

- [ADR-020](ADR-020-agent-registry.md): Agent registry (webhook storage backend)
- [ADR-021](ADR-021-htmx-dashboard.md): Dashboard (webhook status display)

---

## Implementation Status

**Status**: ✅ Complete (v1.0)

**Files**:
- `src/configurable_agents/webhooks/server.py` - FastAPI webhook endpoints
- `src/configurable_agents/webhooks/platforms/whatsapp.py` - WhatsApp handler
- `src/configurable_agents/webhooks/platforms/telegram.py` - Telegram handler (aiogram 3.x)
- `src/configurable_agents/webhooks/models.py` - WebhookExecution ORM

**Features**:
- Generic webhook endpoint (HMAC verification optional)
- WhatsApp Business API integration (Meta verification + message handling)
- Telegram Bot API integration (aiogram 3.x async patterns)
- Idempotency tracking (webhook_id unique constraint)
- Async workflow execution (background tasks)
- Message chunking (4096 char limits)

**Testing**: 17 tests covering signature verification, idempotency, and platform handlers

---

## Superseded By

None (current)
