"""
Models for product management
"""

from django.db import models

from src.apps.core.models import StatusChoices, TimeStampedModel


class Category(TimeStampedModel):
    """
    Product categories
    """

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    """
    Main product model
    """

    title = models.CharField(max_length=200)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True)
    sku = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dimensions = models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE
    )

    # AI enhancement fields
    ai_enhanced = models.BooleanField(default=False)
    ai_description = models.TextField(blank=True)
    ai_keywords = models.TextField(blank=True)

    def __str__(self):
        return self.title


class ProductImage(TimeStampedModel):
    """
    Product images
    """

    product = models.ForeignKey(
        Product, related_name="images", on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.product.title}"
