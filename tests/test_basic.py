"""
Basic test that doesn't import Django models
"""

import pytest


def test_python_imports():
    """Test that Python can import basic modules"""
    import os
    import sys

    import django

    # Verify basic imports work
    assert os is not None
    assert sys is not None
    assert django is not None


def test_django_settings():
    """Test that Django settings can be loaded"""
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.config.settings.test")

    import django

    django.setup()

    from django.conf import settings

    # Debug: Print what settings are actually loaded
    print(f"DEBUG: {settings.DEBUG}")
    print(f"SECRET_KEY: {settings.SECRET_KEY}")
    print(f"SETTINGS_MODULE: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    print(f"INSTALLED_APPS: {settings.INSTALLED_APPS}")

    # Check if we can access the settings file directly
    import importlib

    try:
        test_settings = importlib.import_module("src.config.settings.test")
        print(
            f"Direct DEBUG from test settings: {getattr(test_settings, 'DEBUG', 'NOT_FOUND')}"
        )
        print(
            f"Direct SECRET_KEY from test settings: {getattr(test_settings, 'SECRET_KEY', 'NOT_FOUND')}"
        )
    except Exception as e:
        print(f"Error importing test settings directly: {e}")

    # Verify basic settings
    assert settings.DEBUG is True
    assert settings.SECRET_KEY == "test-secret-key-for-testing-only"

    # Verify apps are configured
    assert "src.apps.core" in settings.INSTALLED_APPS
    assert "src.apps.products" in settings.INSTALLED_APPS
    assert "src.apps.marketplaces" in settings.INSTALLED_APPS
    assert "src.apps.ai_assistant" in settings.INSTALLED_APPS
    assert "src.apps.webhooks" in settings.INSTALLED_APPS


def test_celery_configuration():
    """Test that Celery is configured for tests"""
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.config.settings.test")

    import django

    django.setup()

    from django.conf import settings

    # Verify Celery configuration
    assert settings.CELERY_TASK_ALWAYS_EAGER is True
    assert settings.CELERY_TASK_EAGER_PROPAGATES is True
    assert settings.CELERY_BROKER_URL == "memory://"
    assert settings.CELERY_RESULT_BACKEND == "cache+memory://"


def test_webhook_configuration():
    """Test that webhook configuration is set for tests"""
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.config.settings.test")

    import django

    django.setup()

    from django.conf import settings

    # Verify webhook configuration
    assert settings.WEBHOOK_URL == "https://test.example.com/webhook"
    assert settings.WEBHOOK_SECRET == "test-secret"
    assert settings.OPENAI_API_KEY == "test-api-key"
