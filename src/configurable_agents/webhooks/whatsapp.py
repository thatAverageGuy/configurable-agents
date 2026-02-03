"""WhatsApp Business API webhook handler.

Provides webhook handler for WhatsApp Business API Cloud with:
- Meta webhook verification (hub.challenge response)
- Message and phone extraction from webhook payload
- Workflow command parsing for "/workflow_name input" format
- Async message sending via WhatsApp Cloud API
- Background workflow execution with result delivery

Environment variables required:
    WHATSAPP_PHONE_ID: Phone ID from WhatsApp Business App
    WHATSAPP_ACCESS_TOKEN: Access token for WhatsApp Cloud API
    WHATSAPP_VERIFY_TOKEN: User-defined token for webhook verification

Example:
    >>> handler = WhatsAppWebhookHandler(
    ...     phone_id="123456789",
    ...     access_token="your_token",
    ...     verify_token="your_verify_token"
    ... )
    >>> # Verify webhook
    >>> challenge = handler.verify_webhook("subscribe", "your_verify_token", "123456")
    >>> # Handle message
    >>> phone = handler.extract_phone(webhook_data)
    >>> message = handler.extract_message(webhook_data)
"""

import logging
from typing import Optional, Tuple

import httpx

from configurable_agents.runtime.executor import run_workflow_async

logger = logging.getLogger(__name__)


class WhatsAppWebhookHandler:
    """
    WhatsApp Business API webhook handler.

    Handles incoming WhatsApp messages from Meta's webhook system,
    parses workflow commands, executes workflows asynchronously,
    and sends results back to WhatsApp.

    Attributes:
        phone_id: WhatsApp Business Phone Number ID
        access_token: Meta API access token for WhatsApp
        verify_token: User-defined token for webhook verification

    Example:
        >>> handler = WhatsAppWebhookHandler(
        ...     phone_id="123456789",
        ...     access_token="EAAxxxxxx",
        ...     verify_token="my_secret_token"
        ... )
        >>> # Verify webhook setup
        >>> handler.verify_webhook("subscribe", "my_secret_token", "challenge")
        'challenge'
    """

    def __init__(self, phone_id: str, access_token: str, verify_token: str):
        """
        Initialize WhatsApp webhook handler.

        Args:
            phone_id: WhatsApp Business Phone Number ID from Meta dashboard
            access_token: Long-lived access token for WhatsApp Cloud API
            verify_token: User-defined secret for webhook verification
        """
        self.phone_id = phone_id
        self.access_token = access_token
        self.verify_token = verify_token
        self.api_base = "https://graph.facebook.com/v18.0"

    def verify_webhook(
        self, mode: str, token: str, challenge: str
    ) -> Optional[int]:
        """
        Verify WhatsApp webhook registration with Meta.

        Meta sends a GET request with hub.mode, hub.verify_token,
        and hub.challenge when setting up the webhook. This method
        validates the request and returns the challenge if valid.

        Args:
            mode: Value of hub.mode query parameter (should be "subscribe")
            token: Value of hub.verify_token query parameter
            challenge: Value of hub.challenge query parameter

        Returns:
            The challenge value as int if verification succeeds, None otherwise

        Example:
            >>> handler.verify_webhook("subscribe", "my_token", "123456")
            123456
            >>> handler.verify_webhook("subscribe", "wrong_token", "123456")
            None
        """
        if mode == "subscribe" and token == self.verify_token:
            logger.debug("WhatsApp webhook verified successfully")
            return int(challenge) if challenge.isdigit() else challenge
        logger.warning(f"WhatsApp webhook verification failed: mode={mode}, token mismatch")
        return None

    def extract_phone(self, data: dict) -> Optional[str]:
        """
        Extract phone number from WhatsApp webhook payload.

        Parses the Meta webhook payload format to extract the sender's
        phone number from the message entry.

        Args:
            data: Webhook payload dict from Meta

        Returns:
            Phone number string or None if not found

        Example:
            >>> data = {
            ...     "entry": [{
            ...         "changes": [{
            ...             "value": {
            ...                 "messages": [{"from": "1234567890"}]
            ...             }
            ...         }]
            ...     }]
            ... }
            >>> handler.extract_phone(data)
            '1234567890'
        """
        try:
            entry = data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            if not messages:
                logger.debug("No messages in webhook payload")
                return None

            phone = messages[0].get("from")
            if phone:
                logger.debug(f"Extracted phone: {phone}")
                return phone

            logger.warning("No 'from' field in message payload")
            return None

        except (IndexError, KeyError, TypeError) as e:
            logger.error(f"Failed to extract phone from payload: {e}")
            return None

    def extract_message(self, data: dict) -> Optional[str]:
        """
        Extract message text from WhatsApp webhook payload.

        Parses the Meta webhook payload to extract the text body
        of the incoming message.

        Args:
            data: Webhook payload dict from Meta

        Returns:
            Message text string or None if not found

        Example:
            >>> data = {
            ...     "entry": [{
            ...         "changes": [{
            ...             "value": {
            ...                 "messages": [{
            ...                     "text": {"body": "/workflow_name input"}
            ...                 }]
            ...             }
            ...         }]
            ...     }]
            ... }
            >>> handler.extract_message(data)
            '/workflow_name input'
        """
        try:
            entry = data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            if not messages:
                logger.debug("No messages in webhook payload")
                return None

            text_body = messages[0].get("text", {}).get("body")
            if text_body:
                logger.debug(f"Extracted message: {text_body[:50]}...")
                return text_body

            logger.debug("No text body in message payload")
            return None

        except (IndexError, KeyError, TypeError) as e:
            logger.error(f"Failed to extract message from payload: {e}")
            return None

    @staticmethod
    def parse_workflow_command(message: str) -> Optional[Tuple[str, str]]:
        """
        Parse workflow command from message text.

        Expects format: "/workflow_name input_data"
        The leading slash is required for the workflow name.

        Args:
            message: Message text to parse

        Returns:
            Tuple of (workflow_name, workflow_input) or None if invalid

        Example:
            >>> WhatsAppWebhookHandler.parse_workflow_command("/article_writer AI Safety")
            ('article_writer', 'AI Safety')
            >>> WhatsAppWebhookHandler.parse_workflow_command("invalid format")
            None
        """
        message = message.strip()

        if not message.startswith("/"):
            logger.debug(f"Message does not start with slash: {message[:20]}")
            return None

        # Remove leading slash and split into workflow name and input
        parts = message[1:].split(maxsplit=1)

        if len(parts) < 2:
            logger.debug(f"Message has no input: {message[:20]}")
            return None

        workflow_name = parts[0].strip()
        workflow_input = parts[1].strip()

        logger.info(f"Parsed workflow command: {workflow_name} with input: {workflow_input[:50]}...")
        return (workflow_name, workflow_input)

    async def send_message(self, phone_number: str, text: str) -> None:
        """
        Send text message to WhatsApp phone number.

        Posts a message to the WhatsApp Cloud API using async httpx.

        Args:
            phone_number: Recipient phone number
            text: Message text to send

        Raises:
            httpx.HTTPStatusError: If API request fails
            httpx.RequestError: If network request fails

        Example:
            >>> await handler.send_message("1234567890", "Workflow complete!")
        """
        url = f"{self.api_base}/{self.phone_id}/messages"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": text},
        }

        logger.debug(f"Sending WhatsApp message to {phone_number}")

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        logger.info(f"WhatsApp message sent to {phone_number}")

    async def handle_message(
        self, phone: str, message: str, background_tasks_func
    ) -> str:
        """
        Handle incoming WhatsApp message and trigger workflow.

        Parses the workflow command from the message and queues
        a background task to execute the workflow.

        Args:
            phone: Sender's phone number
            message: Message text
            background_tasks_func: Function to add background task

        Returns:
            Acknowledgment message to send immediately

        Example:
            >>> async def bg_task():
            ...     await run_workflow_async("workflow.yaml", {"input": "data"})
            >>> ack = await handler.handle_message(
            ...     "1234567890",
            ...     "/article_writer AI Safety",
            ...     lambda fn: asyncio.create_task(fn())
            ... )
        """
        command = self.parse_workflow_command(message)

        if command is None:
            return "Usage: /workflow_name <input>"

        workflow_name, workflow_input = command

        # Queue background task for workflow execution
        async def execute_and_reply():
            """Execute workflow and send result back."""
            try:
                logger.info(f"Executing workflow: {workflow_name}")
                result = await run_workflow_async(
                    f"{workflow_name}.yaml", {"input": workflow_input}
                )

                # Format result as text
                if isinstance(result, dict):
                    result_text = str(result)
                else:
                    result_text = str(result)

                # Truncate if too long for WhatsApp (4096 char limit)
                # Account for "Result:\n" prefix in the limit
                prefix = "Result:\n"
                max_length = 4096
                max_result_length = max_length - len(prefix)
                if len(result_text) > max_result_length:
                    result_text = result_text[: max_result_length - 3] + "..."

                await self.send_message(phone, f"{prefix}{result_text}")
                logger.info(f"Workflow {workflow_name} completed, result sent to {phone}")

            except Exception as e:
                logger.error(f"Workflow execution failed: {e}")
                await self.send_message(phone, f"Error: {str(e)}")

        # Add background task
        background_tasks_func(execute_and_reply)

        return f"Executing workflow: {workflow_name}"
