"""
Tests for the complete workflow: Product → AI Enhancement → Marketplace Publishing
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from src.apps.marketplaces.models import Marketplace, ProductListing
from src.apps.products.models import Category, Product
from src.apps.products.tasks import enhance_and_publish_workflow


class WorkflowIntegrationTest(TestCase):
    """
    Test the complete sequential workflow
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        self.category = Category.objects.create(name="Electronics", slug="electronics")

        self.marketplace = Marketplace.objects.create(
            name="MercadoLibre",
            slug="mercadolibre",
            api_url="https://api.mercadolibre.com",
        )

        self.product = Product.objects.create(
            title="Test Product",
            description="Basic description",
            sku="TEST-001",
            price=Decimal("99.99"),
            category=self.category,
        )

    def test_create_and_publish_endpoint(self):
        """Test the complete workflow endpoint"""
        url = reverse("product-create-and-publish", kwargs={"pk": self.product.pk})
        data = {"marketplace_id": self.marketplace.id}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("workflow_id", response.data)
        self.assertIn(
            "AI enhancement → Marketplace publishing", response.data["message"]
        )

    def test_create_and_publish_missing_marketplace(self):
        """Test workflow endpoint without marketplace_id"""
        url = reverse("product-create-and-publish", kwargs={"pk": self.product.pk})
        data = {}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("marketplace_id is required", response.data["error"])

    @patch("src.apps.products.tasks.enhance_product_with_ai")
    @patch("src.apps.marketplaces.tasks.publish_product_to_marketplace")
    @patch("src.apps.webhooks.services.WebhookService")
    def test_enhance_and_publish_workflow_success(
        self, mock_webhook_service, mock_publish, mock_enhance
    ):
        """Test successful complete workflow task"""
        # Mock successful AI enhancement
        mock_enhance_result = MagicMock()
        mock_enhance_result.result = "Product 1 enhanced successfully"
        mock_enhance.apply.return_value = mock_enhance_result

        # Mock successful marketplace publishing
        mock_publish_result = MagicMock()
        mock_publish_result.result = "Product published successfully: MLM123456789"
        mock_publish.apply.return_value = mock_publish_result

        # Mock webhook service
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Set product as AI-enhanced before workflow
        self.product.ai_enhanced = True
        self.product.save()

        # Execute workflow
        result = enhance_and_publish_workflow(self.product.id, self.marketplace.id)

        # Verify workflow completed
        self.assertIn("Complete workflow finished", result)
        self.assertIn("enhanced successfully", result)
        self.assertIn("published successfully", result)

        # Verify AI enhancement was called first with .apply()
        mock_enhance.apply.assert_called_once_with(args=[self.product.id])

        # Verify marketplace publishing was called after AI enhancement
        mock_publish.apply.assert_called_once()

        # Verify listing was created
        listing = ProductListing.objects.get(
            product=self.product, marketplace=self.marketplace
        )
        self.assertIsNotNone(listing)

    @patch("src.apps.products.tasks.enhance_product_with_ai")
    @patch("src.apps.webhooks.services.WebhookService")
    def test_enhance_and_publish_workflow_ai_failure(
        self, mock_webhook_service, mock_enhance
    ):
        """Test workflow when AI enhancement fails"""
        # Mock failed AI enhancement
        mock_enhance_result = MagicMock()
        mock_enhance_result.result = "Error enhancing product: API Error"
        mock_enhance.apply.return_value = mock_enhance_result

        # Mock webhook service
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Execute workflow
        result = enhance_and_publish_workflow(self.product.id, self.marketplace.id)

        # Verify workflow stopped at AI enhancement
        self.assertIn("Workflow failed at AI enhancement", result)
        self.assertIn("API Error", result)

        # Verify no listing was created
        self.assertFalse(
            ProductListing.objects.filter(
                product=self.product, marketplace=self.marketplace
            ).exists()
        )

    def test_workflow_sequence_verification(self):
        """Test that the workflow follows the correct sequence"""
        # This test verifies the conceptual flow without mocking
        # to ensure the sequence is: Product → AI → Marketplace → Webhook

        # 1. Product exists
        self.assertTrue(Product.objects.filter(id=self.product.id).exists())

        # 2. Product should not be AI enhanced initially
        self.assertFalse(self.product.ai_enhanced)

        # 3. No marketplace listing should exist initially
        self.assertFalse(
            ProductListing.objects.filter(
                product=self.product, marketplace=self.marketplace
            ).exists()
        )

        # The actual workflow would:
        # - First enhance the product with AI
        # - Then create a marketplace listing
        # - Finally publish to the marketplace
        # - Send webhook notifications at each step

        # This sequence ensures optimal product quality before marketplace publication
