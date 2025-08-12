"""
Admin for products
"""

from django.contrib import admin

from .models import Category, Product, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent", "created_at"]
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ["parent", "created_at"]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "sku",
        "price",
        "stock",
        "category",
        "status",
        "ai_enhanced",
    ]
    list_filter = ["category", "status", "ai_enhanced", "created_at"]
    search_fields = ["title", "sku", "description"]
    inlines = [ProductImageInline]
    readonly_fields = ["ai_description", "ai_keywords", "created_at", "updated_at"]
