"""
Tests for async publication API endpoints
"""

import uuid
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from src.apps.marketplaces.models import AsyncPublicationTask, Marketplace
from src.apps.products.models import Category, Product


class AsyncPublicationAPITest(TestCase):
    """Test async publication API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            title="API Test Product",
            description="Test description",
            price=299.99,
            sku="API-001",
            category=self.category,
        )
        self.marketplace = Marketplace.objects.create(
            name="API Test Marketplace",
            slug="api-test-marketplace",
            api_url="https://api.apitest.com",
            webhook_url="https://webhook.apitest.com",
        )

    @patch("src.apps.marketplaces.tasks.create_async_publication_task.delay")
    def test_async_publish_endpoint_success(self, mock_task):
        """Test successful async publish endpoint"""
        task_id = str(uuid.uuid4())
        mock_task.return_value = {
            "task_id": task_id,
            "status": "processing",
            "message": "Publication process started",
        }

        url = reverse("productlisting-async-publish")
        data = {
            "product_id": self.product.id,
            "marketplace_id": self.marketplace.id,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task_id", response.data)
        self.assertEqual(response.data["status"], "processing")
        self.assertEqual(response.data["product_id"], self.product.id)
        self.assertEqual(response.data["marketplace_id"], self.marketplace.id)

        # Verify task was called
        mock_task.assert_called_once_with(self.product.id, self.marketplace.id)

    def test_async_publish_endpoint_missing_data(self):
        """Test async publish endpoint with missing data"""
        url = reverse("productlisting-async-publish")
        data = {"product_id": self.product.id}  # Missing marketplace_id

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("required_fields", response.data)

    def test_async_publish_endpoint_invalid_product(self):
        """Test async publish endpoint with invalid product"""
        url = reverse("productlisting-async-publish")
        data = {
            "product_id": 99999,  # Non-existent product
            "marketplace_id": self.marketplace.id,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)

    def test_async_publish_endpoint_invalid_marketplace(self):
        """Test async publish endpoint with invalid marketplace"""
        url = reverse("productlisting-async-publish")
        data = {
            "product_id": self.product.id,
            "marketplace_id": 99999,  # Non-existent marketplace
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)

    @patch("src.apps.marketplaces.tasks.get_async_task_status.delay")
    def test_task_status_endpoint_success(self, mock_status_task):
        """Test successful task status endpoint"""
        task_id = str(uuid.uuid4())
        
        # Create actual task for realistic test
        task = AsyncPublicationTask.objects.create(
            task_id=task_id,
            product=self.product,
            marketplace=self.marketplace,
            status=AsyncPublicationTask.TaskStatus.ENHANCING,
            current_step="Processing AI enhancement",
        )
        task.add_step_completed("enhancement")

        mock_status_result = Mock()
        mock_status_result.get.return_value = {
            "task_id": task_id,
            "status": "enhancing",
            "current_step": "Processing AI enhancement",
            "progress_percentage": 25,
            "steps_completed": ["enhancement"],
            "retries": {
                "enhancement_retries": 0,
                "publication_retries": 0,
                "webhook_retries": 0,
            },
            "started_at": task.started_at.isoformat(),
            "completed_at": None,
        }
        mock_status_task.return_value = mock_status_result

        url = reverse("productlisting-task-status", kwargs={"task_id": task_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["task_id"], task_id)
        self.assertEqual(response.data["status"], "enhancing")
        self.assertEqual(response.data["progress_percentage"], 25)

    @patch("src.apps.marketplaces.tasks.get_async_task_status.delay")
    def test_task_status_endpoint_not_found(self, mock_status_task):
        """Test task status endpoint with non-existent task"""
        task_id = str(uuid.uuid4())

        mock_status_result = Mock()
        mock_status_result.get.return_value = {
            "task_id": task_id,
            "status": "not_found",
            "error": "Task not found",
        }
        mock_status_task.return_value = mock_status_result

        url = reverse("productlisting-task-status", kwargs={"task_id": task_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)


class ProductTasksAPITest(TestCase):
    """Test product tasks API endpoint"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            title="Product Tasks Test",
            description="Test description",
            price=199.99,
            sku="PTT-001",
            category=self.category,
        )
        self.marketplace1 = Marketplace.objects.create(
            name="Marketplace 1",
            slug="marketplace-1",
            api_url="https://api.mp1.com",
            webhook_url="https://webhook.mp1.com",
        )
        self.marketplace2 = Marketplace.objects.create(
            name="Marketplace 2",
            slug="marketplace-2",
            api_url="https://api.mp2.com",
            webhook_url="https://webhook.mp2.com",
        )

    def test_product_tasks_endpoint_success(self):
        """Test successful product tasks endpoint"""
        # Create some test tasks
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
        )
        
        task3 = AsyncPublicationTask.objects.create(
            task_id=str(uuid.uuid4()),
            product=self.product,
            marketplace=self.marketplace1,
            status=AsyncPublicationTask.TaskStatus.FAILED,
            current_step="Failed during publication",
            error_details={"error": "Test error"}
        )

        url = reverse("productlisting-product-tasks", kwargs={"product_id": self.product.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["product_id"], str(self.product.id))
        self.assertEqual(response.data["product_title"], self.product.title)
        self.assertEqual(response.data["total_tasks"], 3)
        self.assertEqual(len(response.data["tasks"]), 3)
        
        # Check status summary
        self.assertIn("status_summary", response.data)
        self.assertEqual(response.data["status_summary"]["completed"], 1)
        self.assertEqual(response.data["status_summary"]["enhancing"], 1)
        self.assertEqual(response.data["status_summary"]["failed"], 1)
        
        # Check marketplace summary
        self.assertIn("marketplace_summary", response.data)
        self.assertEqual(response.data["marketplace_summary"]["Marketplace 1"], 2)
        self.assertEqual(response.data["marketplace_summary"]["Marketplace 2"], 1)

    def test_product_tasks_endpoint_with_status_filter(self):
        """Test product tasks endpoint with status filter"""
        # Create tasks with different statuses
        AsyncPublicationTask.objects.create(
            task_id=str(uuid.uuid4()),
            product=self.product,
            marketplace=self.marketplace1,
            status=AsyncPublicationTask.TaskStatus.COMPLETED,
        )
        AsyncPublicationTask.objects.create(
            task_id=str(uuid.uuid4()),
            product=self.product,
            marketplace=self.marketplace1,
            status=AsyncPublicationTask.TaskStatus.FAILED,
        )
        AsyncPublicationTask.objects.create(
            task_id=str(uuid.uuid4()),
            product=self.product,
            marketplace=self.marketplace2,
            status=AsyncPublicationTask.TaskStatus.ENHANCING,
        )

        # Filter by completed status
        url = reverse("productlisting-product-tasks", kwargs={"product_id": self.product.id})
        response = self.client.get(url, {"status": "completed"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_tasks"], 1)
        self.assertEqual(len(response.data["tasks"]), 1)
        self.assertEqual(response.data["tasks"][0]["status"], "completed")

    def test_product_tasks_endpoint_with_marketplace_filter(self):
        """Test product tasks endpoint with marketplace filter"""
        # Create tasks for different marketplaces
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

        # Filter by marketplace 1
        url = reverse("productlisting-product-tasks", kwargs={"product_id": self.product.id})
        response = self.client.get(url, {"marketplace_id": self.marketplace1.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_tasks"], 1)
        self.assertEqual(len(response.data["tasks"]), 1)
        self.assertEqual(response.data["tasks"][0]["marketplace_name"], "Marketplace 1")

    def test_product_tasks_endpoint_with_pagination(self):
        """Test product tasks endpoint with pagination"""
        # Create multiple tasks
        for i in range(10):
            AsyncPublicationTask.objects.create(
                task_id=str(uuid.uuid4()),
                product=self.product,
                marketplace=self.marketplace1,
                status=AsyncPublicationTask.TaskStatus.COMPLETED,
            )

        # Test first page
        url = reverse("productlisting-product-tasks", kwargs={"product_id": self.product.id})
        response = self.client.get(url, {"limit": 5, "offset": 0})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_tasks"], 10)
        self.assertEqual(response.data["showing"], 5)
        self.assertEqual(response.data["offset"], 0)
        self.assertEqual(response.data["limit"], 5)
        self.assertTrue(response.data["has_more"])

        # Test second page
        response = self.client.get(url, {"limit": 5, "offset": 5})
        self.assertEqual(response.data["showing"], 5)
        self.assertEqual(response.data["offset"], 5)
        self.assertFalse(response.data["has_more"])

    def test_product_tasks_endpoint_product_not_found(self):
        """Test product tasks endpoint with non-existent product"""
        url = reverse("productlisting-product-tasks", kwargs={"product_id": 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("Product with id 99999 not found", response.data["error"])

    def test_product_tasks_endpoint_marketplace_filter_not_found(self):
        """Test product tasks endpoint with non-existent marketplace filter"""
        url = reverse("productlisting-product-tasks", kwargs={"product_id": self.product.id})
        response = self.client.get(url, {"marketplace_id": 99999})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("Marketplace with id 99999 not found", response.data["error"])

    def test_product_tasks_endpoint_empty_results(self):
        """Test product tasks endpoint with no tasks"""
        url = reverse("productlisting-product-tasks", kwargs={"product_id": self.product.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_tasks"], 0)
        self.assertEqual(len(response.data["tasks"]), 0)
        self.assertNotIn("status_summary", response.data)
        self.assertNotIn("marketplace_summary", response.data)

    def test_product_tasks_endpoint_task_details(self):
        """Test that task details are properly serialized"""
        task = AsyncPublicationTask.objects.create(
            task_id=str(uuid.uuid4()),
            product=self.product,
            marketplace=self.marketplace1,
            status=AsyncPublicationTask.TaskStatus.PUBLISHING,
            current_step="Publishing to marketplace",
            enhancement_retries=1,
            publication_retries=0,
            webhook_retries=0,
        )
        task.add_step_completed("enhancement")

        url = reverse("productlisting-product-tasks", kwargs={"product_id": self.product.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task_data = response.data["tasks"][0]
        
        self.assertEqual(task_data["task_id"], task.task_id)
        self.assertEqual(task_data["status"], "publishing")
        self.assertEqual(task_data["current_step"], "Publishing to marketplace")
        self.assertEqual(task_data["marketplace_name"], "Marketplace 1")
        self.assertEqual(task_data["enhancement_retries"], 1)
        self.assertEqual(task_data["publication_retries"], 0)
        self.assertEqual(task_data["webhook_retries"], 0)
        self.assertIn("enhancement", task_data["steps_completed"])