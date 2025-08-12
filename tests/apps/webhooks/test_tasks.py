"""
Tests for webhook tasks
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from src.apps.webhooks.models import WebhookEvent
from src.apps.webhooks.tasks import send_webhook_notification


class WebhookTasksTest(TestCase):

    @override_settings(WEBHOOK_URL="https://example.com/webhook")
    @override_settings(WEBHOOK_SECRET="test-secret")
    def setUp(self):
        self.test_payload = {
            "event": "product.enhanced",
            "product_id": 1,
            "timestamp": "2024-01-01T00:00:00Z",
        }

    @patch("src.apps.webhooks.tasks.WebhookService")
    def test_send_webhook_notification_success(self, mock_webhook_service):
        """Test successful webhook notification task"""
        webhook_event = WebhookEvent.objects.create(
            event_type="product.enhanced",
            payload=self.test_payload,
            webhook_url="https://example.com/webhook",
        )

        # Mock webhook service
        mock_service = MagicMock()
        mock_webhook_service.return_value = mock_service

        # Mock successful result
        webhook_event.status = "completed"
        webhook_event.attempts = 1
        mock_service.send_notification.return_value = webhook_event

        result = send_webhook_notification(webhook_event.id)

        self.assertIn("completed", result)
        mock_service.send_notification.assert_called_once_with(webhook_event)

    def test_send_webhook_notification_not_found(self):
        """Test webhook notification task with non-existent event"""
        result = send_webhook_notification(99999)  # Non-existent ID

        self.assertIn("not found", result)
