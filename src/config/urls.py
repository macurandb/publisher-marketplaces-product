"""
URL Configuration for MultiMarket Hub
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/products/", include("src.apps.products.urls")),
    path("api/v1/marketplaces/", include("src.apps.marketplaces.urls")),
    path("api/v1/ai/", include("src.apps.ai_assistant.urls")),
    path("api/v1/webhooks/", include("src.apps.webhooks.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
