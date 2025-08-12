"""
Tests for marketplace tasks
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from src.apps.marketplaces.models import (
    Marketplace,
    MarketplaceCredential,
    ProductListing,
)
from src.apps.marketplaces.tasks import publish_product_to_marketplace
from src.apps.products.models import Category, Product


class MarketplaceTasksTest(TestCase):

    def setUp(self):
        self.category = Category.objects.create(name="Electronics", slug="electronics")

        self.product = Product.objects.create(
            title="Test Product",
            description="Test description",
            sku="TEST-001",
            price=Decimal("99.99"),
            category=self.category,
        )

        self.marketplace = Marketplace.objects.create(
            name="MercadoLibre",
            slug="mercadolibre",
            api_url="https://api.mercadolibre.com",
        )

        self.credential = MarketplaceCredential.objects.create(
            marketplace=self.marketplace, client_id="test_client_id"
        )

        self.listing = ProductListing.objects.create(
            product=self.product, marketplace=self.marketplace
        )

    @patch("src.apps.marketplaces.tasks.MarketplacePublisher")
    @patch("src.apps.marketplaces.tasks.WebhookService")
    def test_publish_product_success(self, mock_webhook_service, mock_publisher_class):
        """Test successful product publishing"""
        # Set product as AI-enhanced
        self.product.ai_enhanced = True
        self.product.ai_description = "Enhanced description"
        self.product.save()

        # Mock the publisher
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.publish_product.return_value = {
            "success": True,
            "marketplace_id": "MLM123456789",
        }

        # Mock webhook service
        mock_webhook = MagicMock()
        mock_webhook_service.return_value = mock_webhook

        # Execute task
        result = publish_product_to_marketplace(self.listing.id)

        # Verify result
        self.assertIn("published successfully", result)
        self.assertIn("MLM123456789", result)

        # Verify listing was updated
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.external_id, "MLM123456789")
        self.assertEqual(self.listing.status, "completed")

        # Verify webhook was called
        mock_webhook.send_webhook.assert_called_once()

    def test_publish_product_listing_not_found(self):
        """Test when listing doesn't exist"""
        result = publish_product_to_marketplace(99999)  # Non-existent ID

        self.assertIn("not found", result)
