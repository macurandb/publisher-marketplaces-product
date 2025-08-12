"""
Serializers for marketplaces
"""

from rest_framework import serializers

from .models import Marketplace, ProductListing


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
