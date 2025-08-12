"""
Tests for product models
"""

from decimal import Decimal

from django.test import TestCase

from src.apps.products.models import Category, Product


class CategoryModelTest(TestCase):

    def test_category_creation(self):
        """Test category creation"""
        category = Category.objects.create(name="Electronics", slug="electronics")

        self.assertEqual(str(category), "Electronics")
        self.assertEqual(category.slug, "electronics")

    def test_category_with_parent(self):
        """Test category with parent"""
        parent = Category.objects.create(name="Electronics", slug="electronics")

        child = Category.objects.create(
            name="Smartphones", slug="smartphones", parent=parent
        )

        self.assertEqual(child.parent, parent)


class ProductModelTest(TestCase):

    def setUp(self):
        self.category = Category.objects.create(name="Electronics", slug="electronics")

    def test_product_creation(self):
        """Test product creation"""
        product = Product.objects.create(
            title="iPhone 15",
            description="Latest iPhone",
            sku="IPH15-001",
            price=Decimal("999.99"),
            stock=10,
            category=self.category,
        )

        self.assertEqual(str(product), "iPhone 15")
        self.assertEqual(product.sku, "IPH15-001")
        self.assertEqual(product.price, Decimal("999.99"))
        self.assertFalse(product.ai_enhanced)

    def test_product_ai_enhancement(self):
        """Test product AI enhancement fields"""
        product = Product.objects.create(
            title="iPhone 15",
            description="Latest iPhone",
            sku="IPH15-001",
            price=Decimal("999.99"),
            stock=10,
            category=self.category,
            ai_enhanced=True,
            ai_description="Enhanced description with AI",
            ai_keywords="iphone, smartphone, apple",
        )

        self.assertTrue(product.ai_enhanced)
        self.assertEqual(product.ai_description, "Enhanced description with AI")
        self.assertEqual(product.ai_keywords, "iphone, smartphone, apple")
