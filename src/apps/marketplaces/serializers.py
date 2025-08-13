"""
Serializers for marketplaces
"""

from rest_framework import serializers

from .models import AsyncPublicationTask, Marketplace, ProductListing


class MarketplaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marketplace
        fields = ["id", "name", "slug", "api_url", "is_active"]


class ProductListingSerializer(serializers.ModelSerializer):
    marketplace_name = serializers.CharField(source="marketplace.name", read_only=True)
    product_title = serializers.CharField(source="product.title", read_only=True)

    class Meta:
        model = ProductListing
        fields = [
            "id",
            "product",
            "marketplace",
            "marketplace_name",
            "product_title",
            "external_id",
            "status",
            "last_sync",
        ]


class AsyncPublicationTaskSerializer(serializers.ModelSerializer):
    """Serializer for AsyncPublicationTask"""
    
    product_title = serializers.CharField(source="product.title", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    marketplace_name = serializers.CharField(source="marketplace.name", read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = AsyncPublicationTask
        fields = [
            'task_id', 'product', 'marketplace', 'status', 'current_step',
            'steps_completed', 'total_steps', 'progress_percentage',
            'enhancement_retries', 'publication_retries', 'webhook_retries',
            'enhancement_result', 'publication_result', 'webhook_result',
            'error_details', 'started_at', 'completed_at',
            'product_title', 'product_sku', 'marketplace_name'
        ]
        read_only_fields = [
            'task_id', 'steps_completed', 'progress_percentage',
            'enhancement_result', 'publication_result', 'webhook_result',
            'started_at', 'completed_at'
        ]