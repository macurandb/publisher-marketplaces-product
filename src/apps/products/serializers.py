"""
Serializers for products
"""

from rest_framework import serializers

from .models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary"]


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "description",
            "short_description",
            "sku",
            "price",
            "cost",
            "stock",
            "weight",
            "dimensions",
            "category",
            "category_name",
            "status",
            "ai_enhanced",
            "ai_description",
            "ai_keywords",
            "images",
            "created_at",
            "updated_at",
        ]


class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "title",
            "description",
            "short_description",
            "sku",
            "price",
            "cost",
            "stock",
            "weight",
            "dimensions",
            "category",
        ]
