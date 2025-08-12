"""
Pytest configuration for MultiMarket Hub
"""
import os
import pytest
import django
from django.conf import settings

# Set Django settings for tests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.config.settings.test')

# Configure Celery for tests
os.environ['CELERY_TASK_ALWAYS_EAGER'] = 'True'
os.environ['CELERY_TASK_EAGER_PROPAGATES'] = 'True'
os.environ['CELERY_BROKER_URL'] = 'memory://'
os.environ['CELERY_RESULT_BACKEND'] = 'cache+memory://'

# Setup Django
django.setup()

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Setup Django database for tests"""
    with django_db_blocker.unblock():
        pass

@pytest.fixture
def api_client():
    """API client for tests"""
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def user():
    """Test user"""
    from django.contrib.auth.models import User
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def authenticated_client(api_client, user):
    """Authenticated API client"""
    api_client.force_authenticate(user=user)
    return api_client