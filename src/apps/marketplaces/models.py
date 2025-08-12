"""
Models for marketplace integrations
"""

from django.db import models

from src.apps.core.models import StatusChoices, TimeStampedModel


class Marketplace(TimeStampedModel):
    """
    Marketplace configuration
    """

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    api_url = models.URLField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class MarketplaceCredential(TimeStampedModel):
    """
    Credentials for each marketplace
    """

    marketplace = models.OneToOneField(Marketplace, on_delete=models.CASCADE)
    client_id = models.CharField(max_length=200, blank=True)
    client_secret = models.CharField(max_length=200, blank=True)
    api_key = models.CharField(max_length=200, blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)

    def __str__(self):
        return f"Credentials for {self.marketplace.name}"


class ProductListing(TimeStampedModel):
    """
    Product listings on marketplaces
    """

    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    marketplace = models.ForeignKey(Marketplace, on_delete=models.CASCADE)
    external_id = models.CharField(
        max_length=100, blank=True, help_text="ID from the marketplace"
    )
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    last_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["product", "marketplace"]

    def __str__(self):
        return f"{self.product.title} on {self.marketplace.name}"
