"""
Simple test to verify basic configuration
"""

import pytest
from django.test import TestCase


class SimpleTest(TestCase):
    """Simple test to verify Django is working"""

    def test_basic_configuration(self):
        """Test that Django is properly configured"""
        from django.conf import settings

        # Verify basic settings (DEBUG can be overridden by pytest-django)
        self.assertEqual(settings.SECRET_KEY, "test-secret-key-for-testing-only")

        # Verify apps are loaded
        self.assertIn("src.apps.core", settings.INSTALLED_APPS)
        self.assertIn("src.apps.products", settings.INSTALLED_APPS)
        self.assertIn("src.apps.marketplaces", settings.INSTALLED_APPS)
        self.assertIn("src.apps.ai_assistant", settings.INSTALLED_APPS)
        self.assertIn("src.apps.webhooks", settings.INSTALLED_APPS)

        # Verify Celery configuration
        self.assertTrue(settings.CELERY_TASK_ALWAYS_EAGER)
        self.assertTrue(settings.CELERY_TASK_EAGER_PROPAGATES)

    def test_database_configuration(self):
        """Test that database is configured for tests"""
        from django.conf import settings

        # Verify database configuration
        self.assertEqual(
            settings.DATABASES["default"]["ENGINE"], "django.db.backends.sqlite3"
        )
        # Accept both :memory: and Django's test database variations
        db_name = settings.DATABASES["default"]["NAME"]
        self.assertTrue(":memory:" in db_name or "memory" in db_name)

    def test_rest_framework_configuration(self):
        """Test that Django REST Framework is configured"""
        from django.conf import settings

        # Verify REST framework configuration
        self.assertIn("rest_framework", settings.INSTALLED_APPS)
        self.assertIn("DEFAULT_AUTHENTICATION_CLASSES", settings.REST_FRAMEWORK)
        self.assertIn("DEFAULT_PERMISSION_CLASSES", settings.REST_FRAMEWORK)
