---
phase: 03-interfaces-and-triggers
plan: 03B
type: execute
wave: 3
depends_on: [01, 02, 03]
files_modified:
  - src/configurable_agents/webhooks/whatsapp.py
  - src/configurable_agents/webhooks/telegram.py
  - src/configurable_agents/webhooks/router.py
  - tests/webhooks/test_whatsapp.py
  - tests/webhooks/test_telegram.py
  - tests/webhooks/test_router.py
autonomous: false
user_setup:
  - service: telegram
    why: "Telegram Bot API for triggering workflows via chat messages"
    env_vars:
      - name: TELEGRAM_BOT_TOKEN
        source: "BotFather on Telegram - create new bot and get token"
    dashboard_config:
      - task: "Create Telegram bot"
        location: "Open Telegram, search @BotFather, send /newbot, follow prompts"
  - service: whatsapp
    why: "WhatsApp Business API for triggering workflows via messages"
    env_vars:
      - name: WHATSAPP_PHONE_ID
        source: "Meta for Developers - create WhatsApp app, get phone ID"
      - name: WHATSAPP_ACCESS_TOKEN
        source: "Meta for Developers - generate access token for WhatsApp app"
      - name: WHATSAPP_VERIFY_TOKEN
        source: "User-defined secret for webhook verification"
    dashboard_config:
      - task: "Configure WhatsApp webhook"
        location: "Meta for Developers - WhatsApp > Configuration > Webhooks"

must_haves:
  truths:
    - "User can send a WhatsApp message that triggers a workflow execution and receive the result back in the same chat"
    - "User can send a Telegram message that triggers a workflow execution and receive the result back in the same chat"
    - "WhatsApp webhook verification endpoint returns challenge for Meta setup"
    - "Telegram bot handles /start command and workflow trigger messages"
  artifacts:
    - path: "src/configurable_agents/webhooks/whatsapp.py"
      provides: "WhatsApp webhook handler"
      exports: ["WhatsAppWebhookHandler", "extract_phone", "extract_message"]
    - path: "src/configurable_agents/webhooks/telegram.py"
      provides: "Telegram webhook handler via aiogram"
      exports: ["create_telegram_bot", "create_dispatcher", "handle_telegram_webhook"]
    - path: "src/configurable_agents/webhooks/router.py"
      provides: "FastAPI router with WhatsApp and Telegram endpoints"
      exports: ["router as webhooks_router"]
  key_links:
    - from: "src/configurable_agents/webhooks/router.py"
      to: "src/configurable_agents/runtime/executor.py"
      via: "run_workflow_async() for background workflow execution"
      pattern: "run_workflow_async"
    - from: "src/configurable_agents/webhooks/whatsapp.py"
      to: "https://graph.facebook.com"
      via: "WhatsApp Cloud API for sending messages"
      pattern: "https://graph.facebook.com"
    - from: "src/configurable_agents/webhooks/telegram.py"
      to: "https://api.telegram.org"
      via: "Telegram Bot API (aiogram) for sending messages"
      pattern: "aiogram|Bot.*token"
---

<objective>
Build WhatsApp Business API and Telegram Bot API webhook handlers on top of the generic webhook infrastructure, enabling users to trigger workflows by sending messages in their favorite chat apps.

Purpose: Extend the generic webhook system with platform-specific handlers for WhatsApp and Telegram. Users send "/workflow_name input" messages and receive workflow results back in the same chat.

Output: Webhook endpoints at /webhooks/whatsapp and /webhooks/telegram with platform-specific message handling
</objective>

<execution_context>
@C:\Users\ghost\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\ghost\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/03-interfaces-and-triggers/03-RESEARCH.md
@.planning/phases/03-interfaces-and-triggers/03-03-SUMMARY.md
@.planning/phases/02-agent-infrastructure/02-01A-SUMMARY.md

@src/configurable_agents/runtime/executor.py
@src/configurable_agents/config/schema.py
@src/configurable_agents/webhooks/base.py
@src/configurable_agents/storage/base.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create WhatsApp webhook handler</name>
  <files>src/configurable_agents/webhooks/whatsapp.py, tests/webhooks/test_whatsapp.py</files>
  <action>
    Create WhatsApp Business API webhook handler:

    1. **Create whatsapp.py:**
       - WhatsAppWebhookHandler class
       - __init__(phone_id: str, access_token: str, verify_token: str)
       - verify_webhook(mode: str, token: str, challenge: str) -> Optional[int]: Meta webhook verification (returns challenge on success, None on failure)

       extract_phone(data: dict) -> Optional[str]:
         * Parse Meta webhook payload format: entry[0].changes[0].value.messages[0].from
         * Return None if no message in payload

       extract_message(data: dict) -> Optional[str]:
         * Extract text body from message payload
         * Return None if no text content

       async def send_message(phone_number: str, text: str) -> None:
         * POST to https://graph.facebook.com/v18.0/{phone_id}/messages
         * Headers: Authorization: Bearer {access_token}
         * Body: {"messaging_product": "whatsapp", "to": phone_number, "type": "text", "text": {"body": text}}
         * Use httpx.AsyncClient for async HTTP (matching patterns from 02-01A-SUMMARY)

       parse_workflow_command(message: str) -> Optional[Tuple[str, str]]:
         * Parse "/workflow_name input" format
         * Return (workflow_name, workflow_input) or None if format invalid

       async def handle_message(phone: str, message: str, background_tasks: BackgroundTasks) -> str:
         * Parse workflow command from message
         * Add background task to execute workflow via run_workflow_async()
         * Return acknowledgment message

    2. **Create tests/webhooks/test_whatsapp.py:**
       - test_verify_webhook: Test Meta verification with valid/invalid tokens
       - test_extract_phone: Test phone extraction from webhook payload
       - test_extract_message: Test message extraction from payload
       - test_parse_workflow_command: Test command parsing
       - test_send_message_mock: Test async message sending with mock httpx
       - test_handle_message: Test full message handling flow

       Use pytest with pytest.mark.asyncio
       Mock httpx.AsyncClient for HTTP tests
       Use existing async test patterns

    Reference research: .planning/phases/03-interfaces-and-triggers/03-RESEARCH.md lines 576-680
    Use httpx for async HTTP (matching 02-01A patterns)
  </action>
  <verify>
    pytest tests/webhooks/test_whatsapp.py -v
    # All tests pass
  </verify>
  <done>
    WhatsAppWebhookHandler with Meta verification endpoint
    Message and phone extraction from webhook payload
    Workflow command parsing for "/workflow_name input" format
    Async send_message() using httpx.AsyncClient
    All WhatsApp tests passing
  </done>
</task>

<task type="auto">
  <name>Task 2: Create Telegram webhook handler with aiogram</name>
  <files>src/configurable_agents/webhooks/telegram.py, tests/webhooks/test_telegram.py</files>
  <action>
    Create Telegram Bot API webhook handler using aiogram 3.x:

    1. **Create telegram.py:**
       - from aiogram import Bot, Dispatcher, types
       - from aiogram.filters import Command

       create_telegram_bot(token: str) -> Bot:
         * Factory function creating aiogram 3.x Bot instance
         * Returns configured Bot for webhook handling

       create_dispatcher() -> Dispatcher:
         * Factory function creating aiogram 3.x Dispatcher
         * Returns empty dispatcher for handler registration

       register_workflow_handlers(dispatcher: Dispatcher, run_workflow_func: Callable):
         * Register message handlers using aiogram 3.x decorators
         * @dp.message(Command("start")): Send welcome message with usage instructions
         * @dp.message(): Handle workflow trigger messages
           * Parse "/workflow_name input" format
           * Send "typing" action via bot.send_chat_action()
           * Call run_workflow_func in background
           * Send result back (split if >4096 chars per Telegram limit)
         * Use aiogram 3.x async patterns with modern Python 3.10+ syntax

       async def handle_telegram_webhook(request: Request, bot: Bot, dispatcher: Dispatcher) -> dict:
         * Parse Update from request.body()
         * Feed to dispatcher via await dp.feed_webhook_update(bot, update)
         * Return {"status": "ok"}

       async def send_telegram_message(bot: Bot, chat_id: int, text: str) -> None:
         * Split text into chunks of 4096 chars (Telegram message limit)
         * Send each chunk via await bot.send_message()

    2. **Create tests/webhooks/test_telegram.py:**
       - test_create_bot: Test Bot creation factory
       - test_create_dispatcher: Test Dispatcher creation
       - test_register_workflow_handlers: Test handler registration
       - test_send_telegram_message_chunking: Test message splitting for >4096 chars
       - test_handle_telegram_webhook: Test webhook handler with mock update

       Use pytest with pytest.mark.asyncio
       Mock aiogram Bot for message sending tests
       Mock Update objects for webhook tests

    Reference research: .planning/phases/03-interfaces-and-triggers/03-RESEARCH.md lines 683-763
    Use aiogram 3.x patterns with async/await (not legacy aiogram 2.x callbacks)
  </action>
  <verify>
    pytest tests/webhooks/test_telegram.py -v
    # All tests pass
  </verify>
  <done>
    Telegram Bot and Dispatcher factory functions using aiogram 3.x
    Workflow handler registration with @dp.message decorators
    Command handler for /start sending usage instructions
    Message handler for workflow triggers with typing action
    Message chunking for >4096 char results (Telegram limit)
    Webhook handler function for FastAPI integration
    All Telegram tests passing
  </done>
</task>

<task type="checkpoint:human-verify">
  <name>Task 3: Wire platform handlers into router and add CLI with manual verification</name>
  <files>src/configurable_agents/webhooks/router.py, tests/webhooks/test_router.py</files>
  <action>
    Update router.py to include WhatsApp and Telegram endpoints, add CLI:

    1. **Update router.py:**
       - Import WhatsAppWebhookHandler from .whatsapp
       - Import create_telegram_bot, create_dispatcher, register_workflow_handlers from .telegram

       **WhatsApp endpoints:**
       - GET /whatsapp: Webhook verification (calls WhatsAppWebhookHandler.verify_webhook())
       - POST /whatsapp: Handle incoming message
         * Extract phone and message from payload
         * Parse workflow command
         * Queue background task via BackgroundTasks
         * Execute workflow via run_workflow_async()
         * Send result back via WhatsAppWebhookHandler.send_message()

       **Telegram endpoints:**
       - POST /telegram: Handle Update via aiogram
         * Parse Update from request body
         * Feed to dispatcher via feed_webhook_update()
         * Return {"status": "ok"}

       Helper functions:
       - _get_whatsapp_config() -> dict: Load WHATSAPP_* env vars (PHONE_ID, ACCESS_TOKEN, VERIFY_TOKEN)
       - _get_telegram_token() -> str: Load TELEGRAM_BOT_TOKEN env var
       - Initialize WhatsApp handler on module load if env vars present
       - Initialize Telegram bot and dispatcher on module load if token present

    2. **Update/create tests/webhooks/test_router.py:**
       - test_whatsapp_verification: Test GET /webhooks/whatsapp endpoint
       - test_whatsapp_message: Test POST /webhooks/whatsapp with mock handler
       - test_telegram_webhook: Test POST /webhooks/telegram with mock dispatcher
       - test_generic_webhook_still_works: Verify generic endpoint unchanged

       Use TestClient from fastapi.testclient
       Mock WhatsApp handler and Telegram components

    3. **Add CLI command for webhook server:**
       - Add @click.command() for "configurable-agents webhooks" CLI
       - Options: --host (default: 0.0.0.0), --port (default: 7862)
       - Create storage backend and FastAPI app
       - Include webhooks router
       - Launch with uvicorn.run(app, host=host, port=port)

    Reference research: .planning/phases/03-interfaces-and-triggers/03-RESEARCH.md lines 1347-1475
    Use existing CLI patterns from Phase 2 (02-01C-SUMMARY)
  </action>
  <verify>
    pytest tests/webhooks/test_router.py -v
    # All tests pass

    # Test CLI
    configurable-agents webhooks --help
    # Shows help with --host, --port options

    # Test server launch
    configurable-agents webhooks --port 7862 &
    curl -X POST http://localhost:7862/webhooks/generic -H "Content-Type: application/json" -d '{"workflow_name":"test","inputs":{}}'
    # Returns response (200 if valid, 400/403 if invalid)
  </verify>
  <done>
    WhatsApp endpoints (GET/POST /webhooks/whatsapp) working
    Telegram endpoint (POST /webhooks/telegram) working
    Generic webhook endpoint still functional
    Background tasks execute workflows async
    Results sent back to WhatsApp/Telegram after completion
    CLI command "configurable-agents webhooks" working
    Server launches on port 7862
    All router tests passing
  </done>
  <what-built>WhatsApp and Telegram webhook integrations with full message handling and workflow result delivery</what-built>
  <how-to-verify>
    1. Automated tests: `pytest tests/webhooks/ -v`
    2. Generic webhook test: `curl -X POST http://localhost:7862/webhooks/generic -H "Content-Type: application/json" -d '{"workflow_name":"test","inputs":{"topic":"AI"}}'`
    3. Telegram setup (user action required):
       - Open Telegram, search @BotFather
       - Send /newbot, follow prompts to create bot
       - Copy BOT_TOKEN
       - Set TELEGRAM_BOT_TOKEN environment variable
       - Use webhook or ngrok to expose localhost:7862
       - Set webhook URL for your bot
       - Send "/workflow_name input" to your bot
       - Verify workflow executes and result returned
    4. WhatsApp setup (optional, user action required):
       - Create WhatsApp app in Meta for Developers
       - Get PHONE_ID, ACCESS_TOKEN, set VERIFY_TOKEN
       - Set env vars: WHATSAPP_PHONE_ID, WHATSAPP_ACCESS_TOKEN, WHATSAPP_VERIFY_TOKEN
       - Configure webhook URL in Meta dashboard
       - Send message to WhatsApp number
       - Verify workflow executes
  </how-to-verify>
  <resume-signal>Type "approved" if platform webhooks are working, or describe issues to fix</resume-signal>
</task>

</tasks>

<verification>
After completing all tasks, verify:

1. **All webhook tests pass:**
   ```bash
   pytest tests/webhooks/ -v
   ```

2. **Import verification:**
   ```bash
   python -c "from configurable_agents.webhooks import router; from configurable_agents.webhooks.whatsapp import WhatsAppWebhookHandler; from configurable_agents.webhooks.telegram import create_telegram_bot; print('OK')"
   ```

3. **CLI verification:**
   ```bash
   configurable-agents webhooks --help
   ```

4. **Manual verification (checkpoint):**
   See Task 3 checkpoint for detailed manual verification steps including Telegram bot setup and WhatsApp configuration.
</verification>

<success_criteria>
1. Webhook server launches via CLI on port 7862
2. GET /webhooks/whatsapp returns challenge for Meta verification
3. POST /webhooks/whatsapp accepts messages and triggers workflows
4. POST /webhooks/telegram accepts updates and triggers workflows
5. POST /webhooks/generic still triggers workflows (plan 03-03A functionality preserved)
6. Idempotency tracking prevents duplicate executions across all endpoints
7. Results sent back to WhatsApp after workflow completion
8. Results sent back to Telegram after workflow completion
9. Error messages sent back on workflow failure
10. All tests passing
</success_criteria>

<output>
After completion, create `.planning/phases/03-interfaces-and-triggers/03-03B-SUMMARY.md`
</output>
