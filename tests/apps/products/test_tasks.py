"""
Tests for product tasks
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from src.apps.products.models import Category, Product
from src.apps.products.tasks import enhance_product_with_ai


class ProductTasksTest(TestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name="Test Category", slug="test-category"
        )

        self.product = Product.objects.create(
            title="Test Product",
            description="Basic description",
            sku="TEST-001",
            price=Decimal("99.99"),
            stock=5,
            category=self.category,
        )

    @patch("src.apps.products.tasks.AIProductEnhancer")
    @patch("src.apps.products.tasks.WebhookService")
    def test_enhance_product_with_ai_success(
        self, mock_webhook_service, mock_enhancer_class
    ):
        """Test successful product enhancement with AI"""
        # Mock the enhancer
        mock_enhancer = MagicMock()
        mock_enhancer_class.return_value = mock_enhancer

        mock_enhancer.enhance_description.return_value = "Enhanced description with AI"
        mock_enhancer.generate_keywords.return_value = [
            "keyword1",
            "keyword2",
            "keyword3",
        ]

        # Mock webhook service
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Execute task
        result = enhance_product_with_ai(self.product.id)

        # Verify result
        self.assertIn("enhanced successfully", result)

        # Verify product was updated
        self.product.refresh_from_db()
        self.assertTrue(self.product.ai_enhanced)
        self.assertEqual(self.product.ai_description, "Enhanced description with AI")
        self.assertEqual(self.product.ai_keywords, "keyword1, keyword2, keyword3")

        # Verify webhook was called
        mock_webhook.send_webhook.assert_called_once()

    def test_enhance_product_with_ai_product_not_found(self):
        """Test when product doesn't exist"""
        result = enhance_product_with_ai(99999)  # Non-existent ID

        self.assertIn("not found", result)
