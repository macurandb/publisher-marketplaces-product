"""
Webhook services for external notifications
"""

import hashlib
import hmac
import json

import requests
from django.conf import settings

from .models import WebhookEvent


class WebhookService:
    """
    Service for sending webhook notifications
    """

    def __init__(self):
        self.webhook_url = settings.WEBHOOK_URL
        self.webhook_secret = settings.WEBHOOK_SECRET

    def send_webhook(self, event_type, payload):
        """
        Send webhook notification asynchronously
        """
        if not self.webhook_url:
            return None

        webhook_event = WebhookEvent.objects.create(
            event_type=event_type, payload=payload, webhook_url=self.webhook_url
        )

        # Import here to avoid circular imports
        from .tasks import send_webhook_notification

        send_webhook_notification.delay(webhook_event.id)

        return webhook_event

    def _generate_signature(self, payload):
        """
        Generate HMAC signature for webhook security
        """
        if not self.webhook_secret:
            return None

        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = hmac.new(
            self.webhook_secret.encode("utf-8"), payload_bytes, hashlib.sha256
        ).hexdigest()

        return f"sha256={signature}"

    def send_notification(self, webhook_event):
        """
        Send actual HTTP request to webhook URL
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MultiMarket-Hub/1.0",
        }

        signature = self._generate_signature(webhook_event.payload)
        if signature:
            headers["X-Hub-Signature-256"] = signature

        try:
            response = requests.post(
                webhook_event.webhook_url,
                json=webhook_event.payload,
                headers=headers,
                timeout=30,
            )

            webhook_event.response_status_code = response.status_code
            webhook_event.response_body = response.text[:1000]  # Limit response body
            webhook_event.attempts += 1

            if response.status_code == 200:
                webhook_event.status = "completed"
            else:
                webhook_event.status = "failed"

        except requests.exceptions.RequestException as e:
            webhook_event.response_body = str(e)[:1000]
            webhook_event.attempts += 1
            webhook_event.status = "failed"

        webhook_event.save()
        return webhook_event
