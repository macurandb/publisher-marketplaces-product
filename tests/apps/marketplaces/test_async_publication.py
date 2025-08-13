"""
Tests for async publication flow
"""

import uuid
from unittest.mock import Mock, patch

import pytest
from django.test import TestCase
from django.utils import timezone

from src.apps.marketplaces.models import AsyncPublicationTask, Marketplace
from src.apps.marketplaces.tasks import (
    create_async_publication_task,
    enhance_product_async,
    get_async_task_status,
    get_product_tasks_summary,
    publish_to_marketplace_async,
    send_external_webhook,
)
from src.apps.products.models import Category, Product


class AsyncPublicationTaskModelTest(TestCase):
    """Test AsyncPublicationTask model"""

    def setUp(self):
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            title="Test Product",
            description="Test description",
            price=99.99,
            sku="TEST-001",
            category=self.category,
        )
        self.marketplace = Marketplace.objects.create(
            name="Test Marketplace",
            slug="test-marketplace",
            api_url="https://api.test.com",
            webhook_url="https://webhook.test.com",
        )

    def test_create_async_task(self):
        """Test creating an async publication task"""
        task_id = str(uuid.uuid4())
        task = AsyncPublicationTask.objects.create(
            task_id=task_id,
            product=self.product,
            marketplace=self.marketplace,
        )

        self.assertEqual(task.task_id, task_id)
        self.assertEqual(task.status, AsyncPublicationTask.TaskStatus.PENDING)
        self.assertEqual(task.progress_percentage, 0)
        self.assertEqual(len(task.steps_completed), 0)

    def test_progress_calculation(self):
        """Test progress percentage calculation"""
        task_id = str(uuid.uuid4())
        task = AsyncPublicationTask.objects.create(
            task_id=task_id,
            product=self.product,
            marketplace=self.marketplace,
            total_steps=4,
        )

        # No steps completed
        self.assertEqual(task.progress_percentage, 0)

        # Add steps
        task.add_step_completed("enhancement")
        self.assertEqual(task.progress_percentage, 25)

        task.add_step_completed("publication")
        self.assertEqual(task.progress_percentage, 50)

        task.add_step_completed("webhook")
        self.assertEqual(task.progress_percentage, 75)

        task.add_step_completed("completed")
        self.assertEqual(task.progress_percentage, 100)

    def test_update_status(self):
        """Test status update functionality"""
        task_id = str(uuid.uuid4())
        task = AsyncPublicationTask.objects.create(
            task_id=task_id,
            product=self.product,
            marketplace=self.marketplace,
        )

        task.update_status(
            AsyncPublicationTask.TaskStatus.ENHANCING, "Starting AI enhancement"
        )

        task.refresh_from_db()
        self.assertEqual(task.status, AsyncPublicationTask.TaskStatus.ENHANCING)
        self.assertEqual(task.current_step, "Starting AI enhancement")


class AsyncPublicationTasksTest(TestCase):
    """Test async publication tasks"""

    def setUp(self):
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            title="Test Product",
            description="Test description",
            price=99.99,
            sku="TEST-001",
            category=self.category,
        )
        self.marketplace = Marketplace.objects.create(
            name="Test Marketplace",
            slug="test-marketplace",
            api_url="https://api.test.com",
            webhook_url="https://webhook.test.com",
        )

    @patch("src.apps.marketplaces.tasks.chain")
    def test_create_async_publication_task(self, mock_chain):
        """Test creating async publication task"""
        mock_chain_instance = Mock()
        mock_chain.return_value = mock_chain_instance

        result = create_async_publication_task(self.product.id, self.marketplace.id)

        self.assertIsNotNone(result["task_id"])
        self.assertEqual(result["status"], "processing")
        self.assertIn("task_id", result)

        # Verify task was created in database
        task = AsyncPublicationTask.objects.get(task_id=result["task_id"])
        self.assertEqual(task.product, self.product)
        self.assertEqual(task.marketplace, self.marketplace)
        self.assertEqual(task.status, AsyncPublicationTask.TaskStatus.PENDING)

        # Verify chain was called
        mock_chain.assert_called_once()
        mock_chain_instance.apply_async.assert_called_once()

    @patch("src.apps.ai_assistant.services.AIProductEnhancer")
    def test_enhance_product_async_success(self, mock_enhancer_class):
        """Test successful AI enhancement"""
        # Create task
        task_id = str(uuid.uuid4())
        task = AsyncPublicationTask.objects.create(
            task_id=task_id,
            product=self.product,
            marketplace=self.marketplace,
        )

        # Mock AI enhancer
        mock_enhancer = Mock()
        mock_enhancer.enhance_product.return_value = {
            "success": True,
            "enhanced_description": "Enhanced description",
            "keywords": ["test", "product"],
        }
        mock_enhancer_class.return_value = mock_enhancer

        # Run task
        result = enhance_product_async(task_id)

        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["task_id"], task_id)

        # Verify task was updated
        task.refresh_from_db()
        self.assertEqual(task.status, AsyncPublicationTask.TaskStatus.ENHANCED)
        self.assertIn("enhancement", task.steps_completed)
        self.assertEqual(task.enhancement_retries, 0)

    @patch("src.apps.ai_assistant.services.AIProductEnhancer")
    def test_enhance_product_async_failure_with_retries(self, mock_enhancer_class):
        """Test AI enhancement failure with retries"""
        # Create task
        task_id = str(uuid.uuid4())
        task = AsyncPublicationTask.objects.create(
            task_id=task_id,
            product=self.product,
            marketplace=self.marketplace,
        )

        # Mock AI enhancer to fail
        mock_enhancer = Mock()
        mock_enhancer.enhance_product.return_value = {
            "success": False,
            "error": "AI service unavailable",
        }
        mock_enhancer_class.return_value = mock_enhancer

        # Create mock task with retry capability
        mock_task = Mock()
        mock_task.request.retries = 0
        mock_task.retry = Mock(side_effect=Exception("Retry called"))

        # Run task and expect retry
        with self.assertRaises(Exception):
            enhance_product_async.bind(mock_task)(task_id)

        # Verify task was updated with retry info
        task.refresh_from_db()
        self.assertEqual(task.enhancement_retries, 1)
        self.assertIn("error", task.error_details)

    def test_get_async_task_status(self):
        """Test getting task status"""
        task_id = str(uuid.uuid4())
        task = AsyncPublicationTask.objects.create(
            task_id=task_id,
            product=self.product,
            marketplace=self.marketplace,
            status=AsyncPublicationTask.TaskStatus.ENHANCING,
            current_step="Processing AI enhancement",
        )
        task.add_step_completed("enhancement")

        result = get_async_task_status(task_id)

        self.assertEqual(result["task_id"], task_id)
        self.assertEqual(result["status"], AsyncPublicationTask.TaskStatus.ENHANCING)
        self.assertEqual(result["current_step"], "Processing AI enhancement")
        self.assertEqual(result["progress_percentage"], 25)
        self.assertIn("enhancement", result["steps_completed"])

    def test_get_async_task_status_not_found(self):
        """Test getting status for non-existent task"""
        task_id = str(uuid.uuid4())
        result = get_async_task_status(task_id)

        self.assertEqual(result["status"], "not_found")
        self.assertEqual(result["task_id"], task_id)
        self.assertIn("error", result)

    @patch("requests.post")
    def test_send_external_webhook_success(self, mock_post):
        """Test successful external webhook sending"""
        # Create completed task
        task_id = str(uuid.uuid4())
        task = AsyncPublicationTask.objects.create(
            task_id=task_id,
            product=self.product,
            marketplace=self.marketplace,
            status=AsyncPublicationTask.TaskStatus.PUBLISHED,
            enhancement_result={"success": True},
            publication_result={"success": True, "marketplace_id": "ML123"},
        )

        # Mock successful webhook response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        # Run webhook task
        publication_result = {"success": True}
        result = send_external_webhook(publication_result, task_id)

        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["task_id"], task_id)

        # Verify task was updated
        task.refresh_from_db()
        self.assertEqual(task.status, AsyncPublicationTask.TaskStatus.COMPLETED)
        self.assertIsNotNone(task.completed_at)
        self.assertIn("webhook", task.steps_completed)

        # Verify webhook was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], self.marketplace.webhook_url)
        self.assertIn("task_id", call_args[1]["json"])

    @patch("requests.post")
    def test_send_external_webhook_failure(self, mock_post):
        """Test external webhook failure"""
        # Create task
        task_id = str(uuid.uuid4())
        task = AsyncPublicationTask.objects.create(
            task_id=task_id,
            product=self.product,
            marketplace=self.marketplace,
        )

        # Mock failed webhook response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        # Create mock task with retry capability
        mock_task = Mock()
        mock_task.request.retries = 0
        mock_task.retry = Mock(side_effect=Exception("Retry called"))

        # Run webhook task and expect retry
        publication_result = {"success": True}
        with self.assertRaises(Exception):
            send_external_webhook.bind(mock_task)(publication_result, task_id)

        # Verify task was updated with retry info
        task.refresh_from_db()
        self.assertEqual(task.webhook_retries, 1)


@pytest.mark.integration
class AsyncPublicationIntegrationTest(TestCase):
    """Integration tests for the complete async publication flow"""

    def setUp(self):
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            title="Integration Test Product",
            description="Test description",
            price=199.99,
            sku="INT-001",
            category=self.category,
        )
        self.marketplace = Marketplace.objects.create(
            name="Integration Marketplace",
            slug="integration-marketplace",
            api_url="https://api.integration.com",
            webhook_url="https://webhook.integration.com",
        )

    @patch("src.apps.ai_assistant.services.AIProductEnhancer")
    @patch("src.apps.marketplaces.services.MarketplacePublisher")
    @patch("requests.post")
    def test_complete_async_flow_success(
        self, mock_webhook_post, mock_publisher_class, mock_enhancer_class
    ):
        """Test complete successful async publication flow"""
        # Mock AI enhancer
        mock_enhancer = Mock()
        mock_enhancer.enhance_product.return_value = {
            "success": True,
            "enhanced_description": "AI enhanced description",
            "keywords": ["integration", "test"],
        }
        mock_enhancer_class.return_value = mock_enhancer

        # Mock marketplace publisher
        mock_publisher = Mock()
        mock_publisher.publish_product.return_value = {
            "success": True,
            "marketplace_id": "INT123456",
            "details": {"listing_url": "https://marketplace.com/INT123456"},
        }
        mock_publisher_class.return_value = mock_publisher

        # Mock webhook response
        mock_webhook_response = Mock()
        mock_webhook_response.status_code = 200
        mock_webhook_response.text = "Success"
        mock_webhook_post.return_value = mock_webhook_response

        # Start async publication
        result = create_async_publication_task(self.product.id, self.marketplace.id)
        task_id = result["task_id"]

        # Simulate the chain execution manually
        # Step 1: AI Enhancement
        enhance_result = enhance_product_async(task_id)
        self.assertTrue(enhance_result["success"])

        # Step 2: Marketplace Publication
        publish_result = publish_to_marketplace_async(enhance_result, task_id)
        self.assertTrue(publish_result["success"])

        # Step 3: External Webhook
        webhook_result = send_external_webhook(publish_result, task_id)
        self.assertTrue(webhook_result["success"])

        # Verify final task state
        task = AsyncPublicationTask.objects.get(task_id=task_id)
        self.assertEqual(task.status, AsyncPublicationTask.TaskStatus.COMPLETED)
        self.assertEqual(task.progress_percentage, 100)
        self.assertEqual(len(task.steps_completed), 3)
        self.assertIsNotNone(task.completed_at)

        # Verify all services were called
        mock_enhancer.enhance_product.assert_called_once_with(self.product)
        mock_publisher.publish_product.assert_called_once_with(self.product)
        mock_webhook_post.assert_called_once()


class ProductTasksSummaryTest(TestCase):
    """Test get_product_tasks_summary Celery task"""

    def setUp(self):
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            title="Task Summary Test Product",
            description="Test description",
            price=399.99,
            sku="TST-001",
            category=self.category,
        )
        self.marketplace1 = Marketplace.objects.create(
            name="Summary Marketplace 1",
            slug="summary-marketplace-1",
            api_url="https://api.summary1.com",
        )
        self.marketplace2 = Marketplace.objects.create(
            name="Summary Marketplace 2",
            slug="summary-marketplace-2",
            api_url="https://api.summary2.com",
        )

    def test_get_product_tasks_summary_success(self):
        """Test successful product tasks summary"""
        # Create test tasks
        task1 = AsyncPublicationTask.objects.create(
            task_id=str(uuid.uuid4()),
            product=self.product,
            marketplace=self.marketplace1,
            status=AsyncPublicationTask.TaskStatus.COMPLETED,
            current_step="Completed successfully",
        )
        task1.add_step_completed("enhancement")
        task1.add_step_completed("publication")
        task1.add_step_completed("webhook")
        
        task2 = AsyncPublicationTask.objects.create(
            task_id=str(uuid.uuid4()),
            product=self.product,
            marketplace=self.marketplace2,
            status=AsyncPublicationTask.TaskStatus.ENHANCING,
            current_step="Processing AI enhancement",
            enhancement_retries=1,
        )
        
        task3 = AsyncPublicationTask.objects.create(
            task_id=str(uuid.uuid4()),
            product=self.product,
            marketplace=self.marketplace1,
            status=AsyncPublicationTask.TaskStatus.FAILED,
            current_step="Failed during publication",
            error_details={"error": "Test error", "step": "publication"}
        )

        # Call the task
        result = get_product_tasks_summary(self.product.id)

        # Verify result structure
        self.assertNotIn("error", result)
        self.assertEqual(result["product_id"], self.product.id)
        self.assertEqual(result["product_title"], self.product.title)
        self.assertEqual(result["product_sku"], self.product.sku)
        self.assertEqual(result["total_tasks"], 3)
        
        # Verify status summary
        self.assertEqual(result["status_summary"]["completed"], 1)
        self.assertEqual(result["status_summary"]["enhancing"], 1)
        self.assertEqual(result["status_summary"]["failed"], 1)
        
        # Verify marketplace summary
        self.assertEqual(result["marketplace_summary"]["Summary Marketplace 1"], 2)
        self.assertEqual(result["marketplace_summary"]["Summary Marketplace 2"], 1)
        
        # Verify tasks list
        self.assertEqual(len(result["tasks"]), 3)
        
        # Check completed task details
        completed_task = next(t for t in result["tasks"] if t["status"] == "completed")
        self.assertEqual(completed_task["task_id"], task1.task_id)
        self.assertEqual(completed_task["progress_percentage"], 75.0)  # 3 out of 4 steps
        self.assertEqual(len(completed_task["steps_completed"]), 3)
        
        # Check enhancing task details
        enhancing_task = next(t for t in result["tasks"] if t["status"] == "enhancing")
        self.assertEqual(enhancing_task["task_id"], task2.task_id)
        self.assertEqual(enhancing_task["retries"]["enhancement_retries"], 1)
        
        # Check failed task details
        failed_task = next(t for t in result["tasks"] if t["status"] == "failed")
        self.assertEqual(failed_task["task_id"], task3.task_id)
        self.assertIsNotNone(failed_task["error_details"])

    def test_get_product_tasks_summary_with_filters(self):
        """Test product tasks summary with filters"""
        # Create tasks with different statuses and marketplaces
        AsyncPublicationTask.objects.create(
            task_id=str(uuid.uuid4()),
            product=self.product,
            marketplace=self.marketplace1,
            status=AsyncPublicationTask.TaskStatus.COMPLETED,
        )
        AsyncPublicationTask.objects.create(
            task_id=str(uuid.uuid4()),
            product=self.product,
            marketplace=self.marketplace2,
            status=AsyncPublicationTask.TaskStatus.ENHANCING,
        )
        AsyncPublicationTask.objects.create(
            task_id=str(uuid.uuid4()),
            product=self.product,
            marketplace=self.marketplace1,
            status=AsyncPublicationTask.TaskStatus.FAILED,
        )

        # Test status filter
        result = get_product_tasks_summary(self.product.id, status_filter="completed")
        self.assertEqual(result["total_tasks"], 1)
        self.assertEqual(len(result["tasks"]), 1)
        self.assertEqual(result["tasks"][0]["status"], "completed")

        # Test marketplace filter
        result = get_product_tasks_summary(self.product.id, marketplace_id=self.marketplace1.id)
        self.assertEqual(result["total_tasks"], 2)
        self.assertEqual(len(result["tasks"]), 2)
        for task in result["tasks"]:
            self.assertEqual(task["marketplace_name"], "Summary Marketplace 1")

    def test_get_product_tasks_summary_product_not_found(self):
        """Test product tasks summary with non-existent product"""
        result = get_product_tasks_summary(99999)
        
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Product not found")
        self.assertEqual(result["product_id"], 99999)

    def test_get_product_tasks_summary_empty_results(self):
        """Test product tasks summary with no tasks"""
        result = get_product_tasks_summary(self.product.id)
        
        self.assertNotIn("error", result)
        self.assertEqual(result["total_tasks"], 0)
        self.assertEqual(len(result["tasks"]), 0)
        self.assertEqual(result["status_summary"], {})
        self.assertEqual(result["marketplace_summary"], {})