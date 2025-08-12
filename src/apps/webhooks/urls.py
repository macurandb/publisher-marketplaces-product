"""
URLs for webhooks
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import WebhookEventViewSet

router = DefaultRouter()
router.register(r"events", WebhookEventViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
