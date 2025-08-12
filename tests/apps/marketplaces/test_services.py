"""
Tests for marketplace services
"""

from decimal import Decimal

from django.test import TestCase

from src.apps.marketplaces.models import Marketplace, MarketplaceCredential
from src.apps.marketplaces.services import MarketplacePublisher
from src.apps.products.models import Category, Product


class MarketplacePublisherTest(TestCase):

    def setUp(self):
        self.category = Category.objects.create(name="Electronics", slug="electronics")

        self.product = Product.objects.create(
            title="iPhone 15",
            description="Latest iPhone model",
            sku="IPH15-001",
            price=Decimal("999.99"),
            category=self.category,
            ai_description="Enhanced description for iPhone 15",
        )

        self.marketplace = Marketplace.objects.create(
            name="MercadoLibre",
            slug="mercadolibre",
            api_url="https://api.mercadolibre.com",
        )

        self.credential = MarketplaceCredential.objects.create(
            marketplace=self.marketplace,
            client_id="test_client_id",
            client_secret="test_client_secret",
        )

    def test_publish_to_mercadolibre(self):
        """Test publishing to MercadoLibre"""
        publisher = MarketplacePublisher(self.marketplace)
        result = publisher.publish_product(self.product)

        self.assertTrue(result["success"])
        self.assertIn("marketplace_id", result)
        self.assertEqual(result["marketplace_id"], f"MLM{self.product.id}")

    def test_publish_unsupported_marketplace(self):
        """Test publishing to unsupported marketplace"""
        unsupported = Marketplace.objects.create(
            name="Unsupported",
            slug="unsupported",
            api_url="https://api.unsupported.com",
        )

        MarketplaceCredential.objects.create(
            marketplace=unsupported, api_key="test_key"
        )

        publisher = MarketplacePublisher(unsupported)
        result = publisher.publish_product(self.product)

        self.assertFalse(result["success"])
        self.assertIn("Unsupported marketplace", result["error"])
