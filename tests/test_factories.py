"""
Tests para factories
"""

from django.test import TestCase

from tests.factories import (
    CategoryFactory,
    MarketplaceFactory,
    ProductFactory,
    ProductListingFactory,
    UserFactory,
)


class FactoriesTest(TestCase):

    def test_user_factory(self):
        """Test UserFactory"""
        user = UserFactory()

        self.assertTrue(user.username)
        self.assertTrue(user.email)
        self.assertIn("@example.com", user.email)

    def test_category_factory(self):
        """Test CategoryFactory"""
        category = CategoryFactory()

        self.assertTrue(category.name)
        self.assertTrue(category.slug)
        self.assertEqual(category.slug, category.name.lower())

    def test_product_factory(self):
        """Test ProductFactory"""
        product = ProductFactory()

        self.assertTrue(product.title)
        self.assertTrue(product.description)
        self.assertTrue(product.sku)
        self.assertGreater(product.price, 0)
        self.assertIsNotNone(product.category)

    def test_marketplace_factory(self):
        """Test MarketplaceFactory"""
        marketplace = MarketplaceFactory()

        self.assertTrue(marketplace.name)
        self.assertTrue(marketplace.slug)
        self.assertTrue(marketplace.api_url)
        self.assertTrue(marketplace.is_active)

    def test_product_listing_factory(self):
        """Test ProductListingFactory"""
        listing = ProductListingFactory()

        self.assertIsNotNone(listing.product)
        self.assertIsNotNone(listing.marketplace)
        self.assertEqual(listing.status, "pending")
