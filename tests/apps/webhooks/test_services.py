"""
Tests for webhook services
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from src.apps.webhooks.models import WebhookEvent
from src.apps.webhooks.services import WebhookService


class WebhookServiceTest(TestCase):

    @override_settings(WEBHOOK_URL="https://example.com/webhook")
    @override_settings(WEBHOOK_SECRET="test-secret")
    def setUp(self):
        self.webhook_service = WebhookService()
        self.test_payload = {
            "event": "product.enhanced",
            "product_id": 1,
            "timestamp": "2024-01-01T00:00:00Z",
        }

    def test_send_webhook_creates_event(self):
        """Test that send_webhook creates a WebhookEvent"""
        with patch("src.apps.webhooks.tasks.send_webhook_notification.delay"):
            webhook_event = self.webhook_service.send_webhook(
                "product.enhanced", self.test_payload
            )

        self.assertIsInstance(webhook_event, WebhookEvent)
        self.assertEqual(webhook_event.event_type, "product.enhanced")
        self.assertEqual(webhook_event.payload, self.test_payload)

    def test_generate_signature(self):
        """Test HMAC signature generation"""
        signature = self.webhook_service._generate_signature(self.test_payload)

        self.assertIsNotNone(signature)
        self.assertTrue(signature.startswith("sha256="))

    @patch("requests.post")
    def test_send_notification_success(self, mock_post):
        """Test successful webhook notification"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        webhook_event = WebhookEvent.objects.create(
            event_type="product.enhanced",
            payload=self.test_payload,
            webhook_url="https://example.com/webhook",
        )

        result = self.webhook_service.send_notification(webhook_event)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.response_status_code, 200)
        self.assertEqual(result.attempts, 1)

    @patch("requests.post")
    def test_send_notification_failure(self, mock_post):
        """Test failed webhook notification"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        webhook_event = WebhookEvent.objects.create(
            event_type="product.enhanced",
            payload=self.test_payload,
            webhook_url="https://example.com/webhook",
        )

        result = self.webhook_service.send_notification(webhook_event)

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.response_status_code, 500)
        self.assertEqual(result.attempts, 1)
