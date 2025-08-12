"""
Tests for core models
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from src.apps.core.models import StatusChoices
from src.apps.products.models import Category, Product


class StatusChoicesTest(TestCase):

    def test_status_choices_values(self):
        """Test status choices values"""
        expected_choices = [
            ("active", "Active"),
            ("inactive", "Inactive"),
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ]

        self.assertEqual(list(StatusChoices.choices), expected_choices)

    def test_status_choices_usage(self):
        """Test status choices can be used in models"""
        category = Category.objects.create(name="Test Category", slug="test-category")

        product = Product.objects.create(
            title="Test Product",
            description="Test description",
            sku="TEST-001",
            price=Decimal("99.99"),
            category=category,
            status=StatusChoices.ACTIVE,
        )

        self.assertEqual(product.status, "active")


class TimeStampedModelTest(TestCase):

    def test_timestamps_auto_created(self):
        """Test that timestamps are automatically created"""
        category = Category.objects.create(name="Test Category", slug="test-category")

        # Check that timestamps were set
        self.assertIsNotNone(category.created_at)
        self.assertIsNotNone(category.updated_at)

        # Check that created_at and updated_at are close to now
        now = timezone.now()
        self.assertLess((now - category.created_at).total_seconds(), 1)
        self.assertLess((now - category.updated_at).total_seconds(), 1)

    def test_updated_at_changes_on_save(self):
        """Test that updated_at changes when model is saved"""
        category = Category.objects.create(name="Test Category", slug="test-category")

        original_updated_at = category.updated_at

        # Wait a bit and save again
        import time

        time.sleep(0.01)

        category.name = "Updated Category"
        category.save()

        # updated_at should have changed
        self.assertGreater(category.updated_at, original_updated_at)

    def test_created_at_does_not_change_on_save(self):
        """Test that created_at does not change when model is saved"""
        category = Category.objects.create(name="Test Category", slug="test-category")

        original_created_at = category.created_at

        # Wait a bit and save again
        import time

        time.sleep(0.01)

        category.name = "Updated Category"
        category.save()

        # created_at should not have changed
        self.assertEqual(category.created_at, original_created_at)
