"""
Tests for webhook error handling and detailed error reporting
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from src.apps.marketplaces.models import (
    Marketplace,
    MarketplaceCredential,
    ProductListing,
)
from src.apps.marketplaces.tasks import publish_product_to_marketplace
from src.apps.products.models import Category, Product
from src.apps.products.tasks import (
    enhance_and_publish_workflow,
    enhanced_workflow_with_canvas,
)
from src.apps.webhooks.models import WebhookEvent
from src.apps.webhooks.tasks import send_webhook_notification


class WebhookErrorHandlingTest(TestCase):
    """
    Test comprehensive webhook error handling
    """

    def setUp(self):
        self.category = Category.objects.create(name="Electronics", slug="electronics")

        self.product = Product.objects.create(
            title="Test Product",
            description="Basic description",
            sku="TEST-001",
            price=Decimal("99.99"),
            category=self.category,
            ai_enhanced=False,
        )

        self.marketplace = Marketplace.objects.create(
            name="MercadoLibre",
            slug="mercadolibre",
            api_url="https://api.mercadolibre.com",
        )

        self.credential = MarketplaceCredential.objects.create(
            marketplace=self.marketplace, client_id="test_client_id"
        )

    @patch("src.apps.products.tasks.AIProductEnhancer")
    @patch("src.apps.webhooks.services.WebhookService")
    def test_ai_enhancement_failure_webhook_details(
        self, mock_webhook_service, mock_enhancer_class
    ):
        """
        Test that AI enhancement failure sends detailed webhook with error information
        """
        # Mock AI enhancer to fail
        mock_enhancer = MagicMock()
        mock_enhancer_class.return_value = mock_enhancer
        mock_enhancer.enhance_description.side_effect = Exception(
            "OpenAI API rate limit exceeded"
        )

        # Mock webhook service
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Execute workflow
        with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
            result = enhance_and_publish_workflow.delay(
                self.product.id, self.marketplace.id
            )

        # Verify workflow failed
        self.assertTrue(result.successful())
        self.assertIn("Workflow failed at AI enhancement", result.result)

        # Verify detailed error webhook was sent
        mock_webhook.send_webhook.assert_called_with(
            "product.enhancement_failed",
            {
                "event": "product.enhancement_failed",
                "product_id": self.product.id,
                "product_sku": self.product.sku,
                "error": "Error enhancing product 1: OpenAI API rate limit exceeded",
                "error_type": "ai_enhancement_failure",
                "marketplace_id": self.marketplace.id,
                "marketplace_name": self.marketplace.name,
                "timestamp": self.product.updated_at.isoformat(),
            },
        )

    @patch("src.apps.marketplaces.tasks.MarketplacePublisher")
    @patch("src.apps.webhooks.services.WebhookService")
    def test_marketplace_publish_failure_webhook_details(
        self, mock_webhook_service, mock_publisher_class
    ):
        """
        Test that marketplace publishing failure sends detailed webhook with error information
        """
        # Set product as AI enhanced
        self.product.ai_enhanced = True
        self.product.ai_description = "Enhanced description"
        self.product.save()

        # Create listing
        listing = ProductListing.objects.create(
            product=self.product, marketplace=self.marketplace, status="pending"
        )

        # Mock publisher to fail
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.publish_product.return_value = {
            "success": False,
            "error": "Marketplace API authentication failed",
            "error_code": "AUTH_FAILED",
            "response": {"status": 401, "message": "Invalid credentials"},
        }

        # Mock webhook service
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Execute task
        with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
            result = publish_product_to_marketplace.delay(listing.id)

        # Verify task completed but failed
        self.assertTrue(result.successful())
        self.assertIn("Error publishing product", result.result)

        # Verify detailed error webhook was sent
        mock_webhook.send_webhook.assert_called_with(
            "product.publish_failed",
            {
                "event": "product.publish_failed",
                "product_id": self.product.id,
                "product_sku": self.product.sku,
                "marketplace": self.marketplace.name,
                "marketplace_id": self.marketplace.id,
                "listing_id": listing.id,
                "error": "Marketplace API authentication failed",
                "error_details": {
                    "error_type": "marketplace_api_error",
                    "error_code": "AUTH_FAILED",
                    "error_message": "Marketplace API authentication failed",
                    "marketplace_response": {
                        "status": 401,
                        "message": "Invalid credentials",
                    },
                    "retry_count": 0,
                },
                "timestamp": listing.updated_at.isoformat(),
            },
        )

    @patch("src.apps.webhooks.services.WebhookService")
    def test_workflow_error_webhook_details(self, mock_webhook_service):
        """
        Test that workflow errors send detailed webhook with error information
        """
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Mock product.objects.get to raise exception
        with patch.object(Product.objects, "get") as mock_get:
            mock_get.side_effect = Exception("Database connection lost")

            # Execute workflow
            with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
                result = enhance_and_publish_workflow.delay(
                    self.product.id, self.marketplace.id
                )

        # Verify workflow failed
        self.assertTrue(result.successful())
        self.assertIn("Workflow error", result.result)

        # Verify detailed error webhook was sent
        mock_webhook.send_webhook.assert_called_with(
            "workflow.error",
            {
                "event": "workflow.error",
                "product_id": self.product.id,
                "marketplace_id": self.marketplace.id,
                "error": "Database connection lost",
                "error_type": "workflow_execution_error",
                "error_details": {
                    "error_class": "Exception",
                    "error_message": "Database connection lost",
                },
                "timestamp": self.product.updated_at.isoformat(),
            },
        )

    @patch("src.apps.webhooks.services.WebhookService")
    def test_canvas_workflow_error_webhook_details(self, mock_webhook_service):
        """
        Test that Canvas workflow errors send detailed webhook with error information
        """
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Mock chain to raise exception
        with patch("src.apps.products.tasks.chain") as mock_chain:
            mock_chain.side_effect = Exception("Redis connection failed")

            # Execute Canvas workflow
            with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
                result = enhanced_workflow_with_canvas.delay(
                    self.product.id, self.marketplace.id
                )

        # Verify workflow failed
        self.assertTrue(result.successful())
        self.assertIn("Canvas workflow startup error", result.result)

        # Verify detailed error webhook was sent
        mock_webhook.send_webhook.assert_called_with(
            "workflow.error",
            {
                "event": "workflow.error",
                "product_id": self.product.id,
                "marketplace_id": self.marketplace.id,
                "error": "Redis connection failed",
                "error_type": "canvas_workflow_startup_error",
                "error_details": {
                    "error_class": "Exception",
                    "error_message": "Redis connection failed",
                },
                "timestamp": self.product.updated_at.isoformat(),
            },
        )

    def test_webhook_event_types_coverage(self):
        """
        Test that all webhook event types are properly defined
        """
        event_types = [choice[0] for choice in WebhookEvent.EVENT_TYPES]

        # Verify all expected event types are present
        expected_events = [
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

        for event in expected_events:
            self.assertIn(
                event,
                event_types,
                f"Event type {event} not found in WebhookEvent.EVENT_TYPES",
            )


class WebhookRetryAndFailureTest(TestCase):
    """
    Test webhook retry mechanisms and failure handling
    """

    def setUp(self):
        self.webhook_event = WebhookEvent.objects.create(
            event_type="product.enhanced",
            payload={"test": "data"},
            webhook_url="https://test.example.com/webhook",
        )

    @patch("src.apps.webhooks.services.WebhookService")
    def test_webhook_retry_on_transient_failure(self, mock_webhook_service):
        """
        Test webhook retry on transient failures
        """
        mock_service = MagicMock()
        mock_webhook_service.return_value = mock_service

        # Mock webhook to fail initially, then succeed
        self.webhook_event.status = "failed"
        self.webhook_event.attempts = 1
        mock_service.send_notification.return_value = self.webhook_event

        # Execute webhook task
        with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
            result = send_webhook_notification.delay(self.webhook_event.id)

        # Verify task completed
        self.assertTrue(result.successful())

        # Verify webhook service was called
        mock_service.send_notification.assert_called_once_with(self.webhook_event)

    @patch("src.apps.webhooks.services.WebhookService")
    def test_webhook_max_retries_exceeded_handling(self, mock_webhook_service):
        """
        Test webhook handling when max retries are exceeded
        """
        mock_service = MagicMock()
        mock_webhook_service.return_value = mock_service

        # Mock webhook to always fail
        self.webhook_event.status = "failed"
        self.webhook_event.attempts = 3  # Max attempts reached
        mock_service.send_notification.return_value = self.webhook_event

        # Execute webhook task
        with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
            result = send_webhook_notification.delay(self.webhook_event.id)

        # Verify task completed but webhook failed permanently
        self.assertTrue(result.successful())
        self.assertIn("failed permanently", result.result)

        # Verify webhook was marked as permanently failed
        self.webhook_event.refresh_from_db()
        self.assertEqual(self.webhook_event.status, "failed")
        self.assertIn("Max retries exceeded", self.webhook_event.response_body)

    def test_webhook_event_creation_with_detailed_payload(self):
        """
        Test webhook event creation with detailed error payloads
        """
        # Test detailed error payload
        detailed_payload = {
            "event": "product.publish_failed",
            "product_id": 123,
            "product_sku": "TEST-123",
            "marketplace": "TestMarket",
            "error": "API rate limit exceeded",
            "error_details": {
                "error_type": "rate_limit_error",
                "error_code": "RATE_LIMIT_429",
                "retry_after": 60,
            },
            "timestamp": "2024-01-01T00:00:00Z",
        }

        webhook_event = WebhookEvent.objects.create(
            event_type="product.publish_failed",
            payload=detailed_payload,
            webhook_url="https://test.example.com/webhook",
        )

        # Verify event was created with detailed payload
        self.assertEqual(webhook_event.event_type, "product.publish_failed")
        self.assertEqual(
            webhook_event.payload["error_details"]["error_type"], "rate_limit_error"
        )
        self.assertEqual(
            webhook_event.payload["error_details"]["error_code"], "RATE_LIMIT_429"
        )
        self.assertEqual(webhook_event.payload["error_details"]["retry_after"], 60)
