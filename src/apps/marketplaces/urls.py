"""
URLs for marketplaces
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MarketplaceViewSet, ProductListingViewSet

router = DefaultRouter()
router.register(r"marketplaces", MarketplaceViewSet)
router.register(r"listings", ProductListingViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
