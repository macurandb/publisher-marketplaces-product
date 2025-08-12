"""
Tests for product views
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from src.apps.products.models import Category, Product


class ProductViewSetTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        self.category = Category.objects.create(
            name="Test Category", slug="test-category"
        )

        self.product = Product.objects.create(
            title="Test Product",
            description="Test description",
            sku="TEST-001",
            price=Decimal("99.99"),
            stock=5,
            category=self.category,
        )

    def test_list_products(self):
        """Test listing products"""
        url = reverse("product-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle both paginated and non-paginated responses
        data = (
            response.data.get("results", response.data)
            if isinstance(response.data, dict)
            else response.data
        )
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Test Product")

    def test_create_product(self):
        """Test creating product"""
        url = reverse("product-list")
        data = {
            "title": "New Product",
            "description": "New description",
            "sku": "NEW-001",
            "price": "149.99",
            "stock": 10,
            "category": self.category.id,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)

        new_product = Product.objects.get(sku="NEW-001")
        self.assertEqual(new_product.title, "New Product")

    def test_enhance_with_ai_action(self):
        """Test AI enhancement action"""
        url = reverse("product-enhance-with-ai", kwargs={"pk": self.product.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task_id", response.data)
        self.assertIn("message", response.data)
