"""
Tests for webhook models
"""

from django.test import TestCase

from src.apps.webhooks.models import WebhookEvent


class WebhookEventModelTest(TestCase):

    def test_webhook_event_creation(self):
        """Test webhook event creation"""
        webhook_event = WebhookEvent.objects.create(
            event_type="product.enhanced",
            payload={"test": "data"},
            webhook_url="https://example.com/webhook",
        )

        self.assertEqual(str(webhook_event), "product.enhanced - pending")
        self.assertEqual(webhook_event.event_type, "product.enhanced")
        self.assertEqual(webhook_event.payload, {"test": "data"})
        self.assertEqual(webhook_event.status, "pending")
        self.assertEqual(webhook_event.attempts, 0)
        self.assertEqual(webhook_event.max_attempts, 3)

    def test_webhook_event_types(self):
        """Test webhook event types"""
        event_types = [choice[0] for choice in WebhookEvent.EVENT_TYPES]

        expected_types = [
            "product.enhanced",
            "product.enhancement_failed",
            "product.published",
            "product.publish_failed",
            "workflow.completed",
            "workflow.error",
            "canvas.workflow.started",
            "canvas.workflow.error",
            "marketplace.publish.retry",
            "webhook.max_retries_exceeded",
        ]

        for event_type in expected_types:
            self.assertIn(event_type, event_types)
