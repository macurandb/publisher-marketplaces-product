"""
Tests for Celery async workflow to verify proper sequential execution
"""

import json
from decimal import Decimal
from unittest.mock import MagicMock, call, patch

from celery import current_app
from celery.result import AsyncResult
from django.test import TestCase, TransactionTestCase, override_settings

from src.apps.marketplaces.models import (
    Marketplace,
    MarketplaceCredential,
    ProductListing,
)
from src.apps.marketplaces.tasks import publish_product_to_marketplace
from src.apps.products.models import Category, Product
from src.apps.products.tasks import (
    enhance_and_publish_workflow,
    enhance_product_with_ai,
    enhanced_workflow_with_canvas,
    send_workflow_completion_webhook,
)
from src.apps.webhooks.models import WebhookEvent
from src.apps.webhooks.tasks import send_webhook_notification


class CeleryAsyncWorkflowTest(TransactionTestCase):
    """
    Test Celery async workflow with proper task execution verification
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

    def test_task_registration_in_celery(self):
        """
        Test that all tasks are properly registered with Celery
        """
        # Get registered tasks
        registered_tasks = list(current_app.tasks.keys())

        # Expected task names (full module paths)
        expected_tasks = [
            "src.apps.products.tasks.enhance_product_with_ai",
            "src.apps.products.tasks.enhance_and_publish_workflow",
            "src.apps.products.tasks.enhanced_workflow_with_canvas",
            "src.apps.products.tasks.send_workflow_completion_webhook",
            "src.apps.marketplaces.tasks.publish_product_to_marketplace",
            "src.apps.webhooks.tasks.send_webhook_notification",
        ]

        for task_name in expected_tasks:
            self.assertIn(
                task_name,
                registered_tasks,
                f"Task {task_name} not registered. Available tasks: {registered_tasks}",
            )

    @patch("src.apps.products.tasks.Product.objects.get")
    @patch("src.apps.products.tasks.AIProductEnhancer")
    @patch("src.apps.products.tasks.WebhookService")
    def test_ai_enhancement_task_async_execution(
        self, mock_webhook_service, mock_enhancer_class, mock_product_get
    ):
        """
        Test AI enhancement task executes asynchronously and properly
        """
        # Mock product from database
        mock_product = MagicMock()
        mock_product.id = self.product.id
        mock_product.title = self.product.title
        mock_product.description = self.product.description
        mock_product.category.name = self.category.name
        mock_product.sku = self.product.sku
        mock_product.updated_at.isoformat.return_value = "2024-01-01T00:00:00Z"
        mock_product_get.return_value = mock_product

        # Mock AI enhancer
        mock_enhancer = MagicMock()
        mock_enhancer_class.return_value = mock_enhancer
        mock_enhancer.enhance_description.return_value = "Enhanced description with AI"
        mock_enhancer.generate_keywords.return_value = ["ai", "enhanced", "product"]

        # Mock webhook service
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Execute task directly (not async) to avoid broker issues
        from src.apps.products.tasks import enhance_product_with_ai

        result = enhance_product_with_ai(self.product.id)

        # Verify task completed successfully
        self.assertIn("enhanced successfully", result)

        # Verify product was retrieved from database
        mock_product_get.assert_called_once_with(id=self.product.id)

        # Verify AI enhancer was called
        mock_enhancer.enhance_description.assert_called_once_with(
            title=self.product.title,
            description=self.product.description,
            category=self.category.name,
        )
        mock_enhancer.generate_keywords.assert_called_once()

        # Verify product was updated
        self.assertTrue(mock_product.save.called)

        # Verify webhook was sent
        mock_webhook.send_webhook.assert_called_once_with(
            "product.enhanced",
            {
                "event": "product.enhanced",
                "product_id": self.product.id,
                "product_sku": self.product.sku,
                "enhanced_description": "Enhanced description with AI",
                "keywords": ["ai", "enhanced", "product"],
                "timestamp": "2024-01-01T00:00:00Z",
            },
        )

    @patch("src.apps.marketplaces.tasks.ProductListing.objects.get")
    @patch("src.apps.marketplaces.tasks.MarketplacePublisher")
    @patch("src.apps.marketplaces.tasks.WebhookService")
    def test_marketplace_publish_task_async_execution(
        self, mock_webhook_service, mock_publisher_class, mock_listing_get
    ):
        """
        Test marketplace publishing task executes asynchronously
        """
        # Mock listing from database
        mock_listing = MagicMock()
        mock_listing.id = 1
        mock_listing.product = self.product
        mock_listing.marketplace = self.marketplace
        mock_listing.product.ai_enhanced = True
        mock_listing.product.ai_description = "Enhanced description"
        mock_listing.updated_at.isoformat.return_value = "2024-01-01T00:00:00Z"
        mock_listing_get.return_value = mock_listing

        # Mock publisher
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.publish_product.return_value = {
            "success": True,
            "marketplace_id": "MLM123456789",
        }

        # Mock webhook service
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Execute task directly
        from src.apps.marketplaces.tasks import publish_product_to_marketplace

        result = publish_product_to_marketplace(1)

        # Verify task completed successfully
        self.assertIn("published successfully", result)

        # Verify listing was retrieved from database
        mock_listing_get.assert_called_once_with(id=1)

        # Verify listing was updated
        self.assertEqual(mock_listing.external_id, "MLM123456789")
        self.assertEqual(mock_listing.status, "completed")
        self.assertTrue(mock_listing.save.called)

        # Verify webhook was sent
        mock_webhook.send_webhook.assert_called_once()
        call_args = mock_webhook.send_webhook.call_args
        self.assertEqual(call_args[0][0], "product.published")
        self.assertEqual(call_args[0][1]["event"], "product.published")

    @patch("src.apps.marketplaces.tasks.ProductListing.objects.get")
    @patch("src.apps.marketplaces.tasks.WebhookService")
    def test_marketplace_publish_fails_without_ai_enhancement(
        self, mock_webhook_service, mock_listing_get
    ):
        """
        Test that marketplace publishing fails if product is not AI-enhanced
        """
        # Mock listing with non-enhanced product
        mock_listing = MagicMock()
        mock_listing.id = 1
        mock_listing.product = self.product
        mock_listing.marketplace = self.marketplace
        mock_listing.product.ai_enhanced = False  # Not AI enhanced
        mock_listing.updated_at.isoformat.return_value = "2024-01-01T00:00:00Z"
        mock_listing_get.return_value = mock_listing

        # Mock webhook service
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Execute task directly
        from src.apps.marketplaces.tasks import publish_product_to_marketplace

        result = publish_product_to_marketplace(1)

        # Verify task completed but failed
        self.assertIn("must be AI-enhanced", result)

        # Verify listing status was updated to failed
        self.assertEqual(mock_listing.status, "failed")
        self.assertTrue(mock_listing.save.called)

    @patch("src.apps.products.tasks.enhance_product_with_ai")
    @patch("src.apps.marketplaces.tasks.publish_product_to_marketplace")
    @patch("src.apps.webhooks.services.WebhookService")
    def test_complete_workflow_sequential_execution(
        self, mock_webhook_service, mock_publish_task, mock_enhance_task
    ):
        """
        Test complete workflow executes tasks in correct sequence
        """
        # Mock successful AI enhancement
        mock_enhance_result = MagicMock()
        mock_enhance_result.result = "Product 1 enhanced successfully"
        mock_enhance_task.apply.return_value = mock_enhance_result

        # Mock successful marketplace publishing
        mock_publish_result = MagicMock()
        mock_publish_result.result = "Product published successfully: MLM123456789"
        mock_publish_task.apply.return_value = mock_publish_result

        # Mock webhook service
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Mock product refresh to show it's enhanced
        with patch.object(Product, "refresh_from_db") as mock_refresh:
            self.product.ai_enhanced = True
            mock_refresh.return_value = None

            # Execute complete workflow
            with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
                result = enhance_and_publish_workflow.delay(
                    self.product.id, self.marketplace.id
                )

        # Verify workflow completed
        self.assertTrue(result.successful())
        self.assertIn("Complete workflow finished", result.result)

        # Verify tasks were called in correct order with synchronous execution
        mock_enhance_task.apply.assert_called_once_with(args=[self.product.id])
        mock_publish_task.apply.assert_called_once()

        # Verify workflow completion webhook was sent
        webhook_calls = mock_webhook.send_webhook.call_args_list
        workflow_completion_call = None
        for call in webhook_calls:
            if call[0][0] == "workflow.completed":
                workflow_completion_call = call
                break

        self.assertIsNotNone(
            workflow_completion_call, "Workflow completion webhook not sent"
        )
        self.assertEqual(workflow_completion_call[0][1]["event"], "workflow.completed")
        self.assertEqual(workflow_completion_call[0][1]["product_id"], self.product.id)

    @patch("src.apps.products.tasks.enhance_product_with_ai")
    @patch("src.apps.webhooks.services.WebhookService")
    def test_workflow_stops_on_ai_enhancement_failure(
        self, mock_webhook_service, mock_enhance_task
    ):
        """
        Test that workflow stops if AI enhancement fails
        """
        # Mock failed AI enhancement
        mock_enhance_result = MagicMock()
        mock_enhance_result.result = "Error enhancing product: API timeout"
        mock_enhance_task.apply.return_value = mock_enhance_result

        # Mock webhook service
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Execute workflow
        with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
            result = enhance_and_publish_workflow.delay(
                self.product.id, self.marketplace.id
            )

        # Verify workflow failed at enhancement step
        self.assertTrue(result.successful())
        self.assertIn("Workflow failed at AI enhancement", result.result)

        # Verify failure webhook was sent with detailed error information
        mock_webhook.send_webhook.assert_called_with(
            "product.enhancement_failed",
            {
                "event": "product.enhancement_failed",
                "product_id": self.product.id,
                "product_sku": self.product.sku,
                "error": "Error enhancing product: API timeout",
                "error_type": "ai_enhancement_failure",
                "marketplace_id": self.marketplace.id,
                "marketplace_name": self.marketplace.name,
                "timestamp": self.product.updated_at.isoformat(),
            },
        )

        # Verify no listing was created (workflow stopped)
        self.assertFalse(
            ProductListing.objects.filter(
                product=self.product, marketplace=self.marketplace
            ).exists()
        )

    @patch("src.apps.webhooks.tasks.WebhookEvent.objects.get")
    @patch("src.apps.webhooks.tasks.WebhookService.send_notification")
    def test_webhook_task_async_execution(
        self, mock_send_notification, mock_webhook_get
    ):
        """
        Test webhook task executes asynchronously
        """
        # Mock webhook event
        mock_webhook_event = MagicMock()
        mock_webhook_event.id = 1
        mock_webhook_event.payload = {"test": "data"}  # JSON serializable payload
        mock_webhook_get.return_value = mock_webhook_event

        # Mock successful webhook delivery result
        mock_result = MagicMock()
        mock_result.status = "completed"
        mock_result.attempts = 1
        mock_result.max_attempts = 3
        mock_send_notification.return_value = mock_result

        # Execute webhook task directly
        from src.apps.webhooks.tasks import send_webhook_notification

        result = send_webhook_notification(1)

        # Verify task completed
        self.assertIn("completed", result)

        # Verify webhook event was retrieved
        mock_webhook_get.assert_called_once_with(id=1)

        # Verify webhook service was called
        mock_send_notification.assert_called_once_with(mock_webhook_event)

    def test_task_retry_configuration(self):
        """
        Test that tasks have proper retry configuration
        """
        # Test webhook task retry configuration
        webhook_task = current_app.tasks.get(
            "src.apps.webhooks.tasks.send_webhook_notification"
        )

        if webhook_task:
            # Verify retry configuration
            self.assertTrue(hasattr(webhook_task, "max_retries"))
            self.assertEqual(webhook_task.max_retries, 3)

    @patch("src.apps.products.tasks.enhance_product_with_ai")
    @patch("src.apps.marketplaces.tasks.publish_product_to_marketplace")
    def test_workflow_task_execution_order_verification(
        self, mock_publish_task, mock_enhance_task
    ):
        """
        Test that workflow tasks are executed in the correct order
        """
        execution_order = []

        def track_enhance(*args, **kwargs):
            execution_order.append("enhance")
            result = MagicMock()
            result.result = "Product enhanced successfully"
            return result

        def track_publish(*args, **kwargs):
            execution_order.append("publish")
            result = MagicMock()
            result.result = "Product published successfully"
            return result

        mock_enhance_task.apply.side_effect = track_enhance
        mock_publish_task.apply.side_effect = track_publish

        # Mock product as enhanced after enhancement
        with patch.object(Product, "refresh_from_db"):
            self.product.ai_enhanced = True

            # Execute workflow
            with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
                result = enhance_and_publish_workflow.delay(
                    self.product.id, self.marketplace.id
                )

        # Verify execution order
        self.assertEqual(execution_order, ["enhance", "publish"])
        self.assertTrue(result.successful())

        # Verify both tasks were called
        mock_enhance_task.apply.assert_called_once()
        mock_publish_task.apply.assert_called_once()


class CeleryCanvasWorkflowTest(TransactionTestCase):
    """
    Test Celery Canvas workflow functionality
    """

    def setUp(self):
        self.category = Category.objects.create(name="Test", slug="test")
        self.marketplace = Marketplace.objects.create(
            name="Test Marketplace", slug="test", api_url="https://api.test.com"
        )
        MarketplaceCredential.objects.create(
            marketplace=self.marketplace, client_id="test"
        )
        self.product = Product.objects.create(
            title="Test Product",
            description="Test",
            sku="TEST-001",
            price=Decimal("99.99"),
            category=self.category,
        )

    @patch("src.apps.products.tasks.enhance_product_with_ai")
    @patch("src.apps.marketplaces.tasks.publish_product_to_marketplace")
    @patch("src.apps.products.tasks.send_workflow_completion_webhook")
    def test_canvas_workflow_creation(
        self, mock_completion_webhook, mock_publish, mock_enhance
    ):
        """
        Test that Canvas workflow creates proper task chain
        """
        # Mock task signatures
        mock_enhance_sig = MagicMock()
        mock_publish_sig = MagicMock()
        mock_completion_sig = MagicMock()

        mock_enhance.s.return_value = mock_enhance_sig
        mock_publish.s.return_value = mock_publish_sig
        mock_completion_webhook.s.return_value = mock_completion_sig

        # Mock chain result
        mock_chain = MagicMock()
        mock_chain.apply_async.return_value = MagicMock(id="canvas-task-123")

        with patch("src.apps.products.tasks.chain", return_value=mock_chain):
            with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
                result = enhanced_workflow_with_canvas.delay(
                    self.product.id, self.marketplace.id
                )

        # Verify Canvas workflow started successfully
        self.assertTrue(result.successful())
        self.assertIn("Canvas workflow started successfully", result.result)
        self.assertIn("canvas-task-123", result.result)

        # Verify task signatures were created
        mock_enhance.s.assert_called_once_with(self.product.id)
        mock_publish.s.assert_called_once_with(self.marketplace.id)
        mock_completion_webhook.s.assert_called_once_with(
            self.product.id, self.marketplace.id
        )

    @patch("src.apps.webhooks.services.WebhookService")
    def test_canvas_workflow_error_handling(self, mock_webhook_service):
        """
        Test Canvas workflow error handling and webhook notifications
        """
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Mock chain to raise exception
        with patch("src.apps.products.tasks.chain") as mock_chain:
            mock_chain.side_effect = Exception("Canvas creation failed")

            with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
                result = enhanced_workflow_with_canvas.delay(
                    self.product.id, self.marketplace.id
                )

        # Verify error was handled
        self.assertTrue(result.successful())
        self.assertIn("Canvas workflow startup error", result.result)

        # Verify error webhook was sent
        mock_webhook.send_webhook.assert_called_once_with(
            "workflow.error",
            {
                "event": "workflow.error",
                "product_id": self.product.id,
                "marketplace_id": self.marketplace.id,
                "error": "Canvas creation failed",
                "error_type": "canvas_workflow_startup_error",
                "error_details": {
                    "error_class": "Exception",
                    "error_message": "Canvas creation failed",
                },
                "timestamp": self.product.updated_at.isoformat(),
            },
        )


class WorkflowCompletionWebhookTest(TransactionTestCase):
    """
    Test workflow completion webhook functionality
    """

    def setUp(self):
        self.category = Category.objects.create(name="Test", slug="test")
        self.marketplace = Marketplace.objects.create(
            name="Test Marketplace", slug="test", api_url="https://api.test.com"
        )
        MarketplaceCredential.objects.create(
            marketplace=self.marketplace, client_id="test"
        )
        self.product = Product.objects.create(
            title="Test Product",
            description="Test",
            sku="TEST-001",
            price=Decimal("99.99"),
            category=self.category,
        )
        self.listing = ProductListing.objects.create(
            product=self.product,
            marketplace=self.marketplace,
            status="completed",
            external_id="EXT-123",
        )

    @patch("src.apps.webhooks.services.WebhookService")
    def test_workflow_completion_webhook_success(self, mock_webhook_service):
        """
        Test successful workflow completion webhook
        """
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
            result = send_workflow_completion_webhook.delay(
                self.product.id, self.marketplace.id
            )

        # Verify task completed successfully
        self.assertTrue(result.successful())
        self.assertIn("Completion webhook sent", result.result)

        # Verify webhook was sent with correct data
        mock_webhook.send_webhook.assert_called_once_with(
            "workflow.completed",
            {
                "event": "workflow.completed",
                "product_id": self.product.id,
                "product_sku": self.product.sku,
                "marketplace": self.marketplace.name,
                "listing_id": self.listing.id,
                "status": "completed",
                "timestamp": self.listing.updated_at.isoformat(),
            },
        )

    def test_workflow_completion_webhook_missing_data(self):
        """
        Test workflow completion webhook with missing data
        """
        # Test with non-existent product
        with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
            result = send_workflow_completion_webhook.delay(99999, self.marketplace.id)

        # Verify task handled error gracefully
        self.assertTrue(result.successful())
        self.assertIn("Failed to send completion webhook", result.result)


class CeleryTaskChainTest(TransactionTestCase):
    """
    Test Celery task chaining and dependencies
    """

    def setUp(self):
        self.category = Category.objects.create(name="Test", slug="test")
        self.marketplace = Marketplace.objects.create(
            name="Test Marketplace", slug="test", api_url="https://api.test.com"
        )
        MarketplaceCredential.objects.create(
            marketplace=self.marketplace, client_id="test"
        )

    def test_task_signature_creation(self):
        """
        Test that task signatures can be created properly
        """
        product = Product.objects.create(
            title="Test Product",
            description="Test",
            sku="TEST-001",
            price=Decimal("99.99"),
            category=self.category,
        )

        # Create task signatures
        enhance_sig = enhance_product_with_ai.s(product.id)
        workflow_sig = enhance_and_publish_workflow.s(product.id, self.marketplace.id)
        canvas_sig = enhanced_workflow_with_canvas.s(product.id, self.marketplace.id)

        # Verify signatures are created
        self.assertIsNotNone(enhance_sig)
        self.assertIsNotNone(workflow_sig)
        self.assertIsNotNone(canvas_sig)
        self.assertEqual(
            enhance_sig.task, "src.apps.products.tasks.enhance_product_with_ai"
        )
        self.assertEqual(
            workflow_sig.task, "src.apps.products.tasks.enhance_and_publish_workflow"
        )
        self.assertEqual(
            canvas_sig.task, "src.apps.products.tasks.enhanced_workflow_with_canvas"
        )

    @patch("src.apps.products.tasks.enhance_product_with_ai")
    @patch("src.apps.marketplaces.tasks.publish_product_to_marketplace")
    def test_synchronous_task_execution_in_workflow(self, mock_publish, mock_enhance):
        """
        Test that tasks within workflow are executed synchronously using .apply()
        """
        product = Product.objects.create(
            title="Test Product",
            description="Test",
            sku="TEST-001",
            price=Decimal("99.99"),
            category=self.category,
        )

        # Mock task results
        enhance_result = MagicMock()
        enhance_result.result = "Product enhanced successfully"
        mock_enhance.apply.return_value = enhance_result

        publish_result = MagicMock()
        publish_result.result = "Product published successfully"
        mock_publish.apply.return_value = publish_result

        # Mock product refresh
        with patch.object(Product, "refresh_from_db"):
            product.ai_enhanced = True

            # Execute workflow
            with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
                result = enhance_and_publish_workflow.delay(
                    product.id, self.marketplace.id
                )

        # Verify synchronous execution (.apply() was used, not .delay())
        mock_enhance.apply.assert_called_once_with(args=[product.id])
        mock_publish.apply.assert_called_once()

        # Verify .delay() was NOT used (which would be asynchronous)
        mock_enhance.delay.assert_not_called()
        mock_publish.delay.assert_not_called()

        self.assertTrue(result.successful())


class ErrorHandlingAndRetryTest(TransactionTestCase):
    """
    Test error handling and retry mechanisms
    """

    def setUp(self):
        self.category = Category.objects.create(name="Test", slug="test")
        self.marketplace = Marketplace.objects.create(
            name="Test Marketplace", slug="test", api_url="https://api.test.com"
        )
        MarketplaceCredential.objects.create(
            marketplace=self.marketplace, client_id="test"
        )
        self.product = Product.objects.create(
            title="Test Product",
            description="Test",
            sku="TEST-001",
            price=Decimal("99.99"),
            category=self.category,
        )

    @patch("src.apps.products.tasks.AIProductEnhancer")
    @patch("src.apps.products.tasks.WebhookService")
    def test_ai_enhancement_retry_logic(
        self, mock_webhook_service, mock_enhancer_class
    ):
        """
        Test AI enhancement retry logic for transient errors
        """
        # Mock AI enhancer to fail initially
        mock_enhancer = MagicMock()
        mock_enhancer_class.return_value = mock_enhancer
        mock_enhancer.enhance_description.side_effect = [
            Exception("Temporary API error"),  # First call fails
            "Enhanced description",  # Second call succeeds
        ]
        mock_enhancer.generate_keywords.return_value = ["test", "keywords"]

        # Mock webhook service
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Execute task with retry
        with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
            result = enhance_product_with_ai.delay(self.product.id)

        # Verify task completed (retry succeeded)
        self.assertTrue(result.successful())

        # Verify retry was attempted
        self.assertEqual(mock_enhancer.enhance_description.call_count, 2)

    @patch("src.apps.marketplaces.tasks.MarketplacePublisher")
    @patch("src.apps.marketplaces.tasks.WebhookService")
    def test_marketplace_publish_retry_logic(
        self, mock_webhook_service, mock_publisher_class
    ):
        """
        Test marketplace publishing retry logic
        """
        # Set product as AI enhanced
        self.product.ai_enhanced = True
        self.product.save()

        # Create listing
        listing = ProductListing.objects.create(
            product=self.product, marketplace=self.marketplace, status="pending"
        )

        # Mock publisher to fail initially
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.publish_product.side_effect = [
            {"success": False, "error": "Rate limit exceeded"},  # First call fails
            {"success": True, "marketplace_id": "EXT-123"},  # Second call succeeds
        ]

        # Mock webhook service
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Execute task with retry
        with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
            result = publish_product_to_marketplace.delay(listing.id)

        # Verify task completed (retry succeeded)
        self.assertTrue(result.successful())
        self.assertIn("published successfully", result.result)

        # Verify retry was attempted
        self.assertEqual(mock_publisher.publish_product.call_count, 2)

    def test_webhook_max_retries_exceeded(self):
        """
        Test webhook max retries exceeded scenario
        """
        # Create webhook event
        webhook_event = WebhookEvent.objects.create(
            event_type="product.enhanced",
            payload={"test": "data"},
            webhook_url="https://test.example.com/webhook",
        )

        # Mock webhook service to always fail
        with patch("src.apps.webhooks.tasks.WebhookService") as mock_webhook_service:
            mock_service = MagicMock()
            mock_webhook_service.return_value = mock_service

            # Mock webhook to always fail
            webhook_event.status = "failed"
            webhook_event.attempts = 3  # Max attempts reached
            mock_service.send_notification.return_value = webhook_event

            # Execute webhook task
            with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
                result = send_webhook_notification.delay(webhook_event.id)

        # Verify task completed but webhook failed permanently
        self.assertTrue(result.successful())
        self.assertIn("failed permanently", result.result)
