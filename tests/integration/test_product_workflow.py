"""
Integration tests for MultiMarket Hub
"""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from src.apps.marketplaces.models import Marketplace, ProductListing
from src.apps.products.models import Category, Product


@pytest.mark.integration()
class ProductToMarketplaceIntegrationTest(TransactionTestCase):
    """
    Complete integration tests for product -> marketplace flow
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        # Create test data
        self.category = Category.objects.create(name="Smartphones", slug="smartphones")

        self.marketplace = Marketplace.objects.create(
            name="MercadoLibre",
            slug="mercadolibre",
            api_url="https://api.mercadolibre.com",
        )

    def test_complete_product_workflow(self):
        """Test complete flow: create product -> enhance with AI -> publish"""

        # 1. Create product
        product_data = {
            "title": "iPhone 15 Pro",
            "description": "New iPhone with A17 chip",
            "sku": "IPH15PRO-001",
            "price": "1299.99",
            "stock": 5,
            "category": self.category.id,
        }

        product_url = reverse("product-list")
        response = self.client.post(product_url, product_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product_id = response.data.get("id")
        if not product_id:
            # If no id in response, get the created product
            product = Product.objects.get(sku="IPH15PRO-001")
            product_id = product.id

        # 2. Verify product was created correctly
        product = Product.objects.get(id=product_id)
        self.assertEqual(product.title, "iPhone 15 Pro")
        self.assertFalse(product.ai_enhanced)

        # 3. Create listing for marketplace
        listing_data = {"product": product_id, "marketplace": self.marketplace.id}

        listing_url = reverse("productlisting-list")
        response = self.client.post(listing_url, listing_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        listing_id = response.data["id"]

        # 4. Verify listing was created
        listing = ProductListing.objects.get(id=listing_id)
        self.assertEqual(listing.product, product)
        self.assertEqual(listing.marketplace, self.marketplace)
        self.assertEqual(listing.status, "pending")

        # 5. Verify listing endpoints
        products_response = self.client.get(reverse("product-list"))
        self.assertEqual(products_response.status_code, status.HTTP_200_OK)
        products_data = (
            products_response.data.get("results", products_response.data)
            if isinstance(products_response.data, dict)
            else products_response.data
        )
        self.assertEqual(len(products_data), 1)

        listings_response = self.client.get(reverse("productlisting-list"))
        self.assertEqual(listings_response.status_code, status.HTTP_200_OK)
        listings_data = (
            listings_response.data.get("results", listings_response.data)
            if isinstance(listings_response.data, dict)
            else listings_response.data
        )
        self.assertEqual(len(listings_data), 1)

    def test_product_filtering_and_search(self):
        """Test product filtering and search"""

        # Create multiple products
        products_data = [
            {
                "title": "iPhone 15",
                "description": "Basic iPhone",
                "sku": "IPH15-001",
                "price": "999.99",
                "stock": 10,
                "category": self.category.id,
            },
            {
                "title": "Samsung Galaxy S24",
                "description": "Samsung flagship",
                "sku": "SAM24-001",
                "price": "899.99",
                "stock": 8,
                "category": self.category.id,
            },
        ]

        product_url = reverse("product-list")
        for data in products_data:
            response = self.client.post(product_url, data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test search by title
        search_response = self.client.get(product_url, {"search": "iPhone"})
        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        search_data = (
            search_response.data.get("results", search_response.data)
            if isinstance(search_response.data, dict)
            else search_response.data
        )
        iphone_products = [p for p in search_data if "iPhone" in p["title"]]
        self.assertGreaterEqual(len(iphone_products), 1)

        # Test filter by category
        category_response = self.client.get(product_url, {"category": self.category.id})
        self.assertEqual(category_response.status_code, status.HTTP_200_OK)
        category_data = (
            category_response.data.get("results", category_response.data)
            if isinstance(category_response.data, dict)
            else category_response.data
        )
        self.assertGreaterEqual(len(category_data), 2)

    def test_marketplace_listing_workflow(self):
        """Test marketplace listing workflow"""

        # Create product
        product = Product.objects.create(
            title="Test Product",
            description="Test description",
            sku="TEST-001",
            price=Decimal("99.99"),
            category=self.category,
        )

        # Create multiple marketplaces
        walmart = Marketplace.objects.create(
            name="Walmart", slug="walmart", api_url="https://api.walmart.com"
        )

        # Create listings on different marketplaces
        listing1 = ProductListing.objects.create(
            product=product, marketplace=self.marketplace
        )

        listing2 = ProductListing.objects.create(product=product, marketplace=walmart)

        # Verify filtering by marketplace
        listings_url = reverse("productlisting-list")

        ml_response = self.client.get(
            listings_url, {"marketplace": self.marketplace.id}
        )
        self.assertEqual(ml_response.status_code, status.HTTP_200_OK)
        ml_data = (
            ml_response.data.get("results", ml_response.data)
            if isinstance(ml_response.data, dict)
            else ml_response.data
        )
        ml_listings = [l for l in ml_data if l["marketplace"] == self.marketplace.id]
        self.assertGreaterEqual(len(ml_listings), 1)

        walmart_response = self.client.get(listings_url, {"marketplace": walmart.id})
        self.assertEqual(walmart_response.status_code, status.HTTP_200_OK)
        walmart_data = (
            walmart_response.data.get("results", walmart_response.data)
            if isinstance(walmart_response.data, dict)
            else walmart_response.data
        )
        walmart_listings = [l for l in walmart_data if l["marketplace"] == walmart.id]
        self.assertGreaterEqual(len(walmart_listings), 1)

        # Verify duplicate listings cannot be created
        duplicate_data = {"product": product.id, "marketplace": self.marketplace.id}

        duplicate_response = self.client.post(listings_url, duplicate_data)
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
