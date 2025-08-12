"""
Factories for tests using factory_boy
"""

from decimal import Decimal

import factory
from django.contrib.auth.models import User

from src.apps.marketplaces.models import (
    Marketplace,
    MarketplaceCredential,
    ProductListing,
)
from src.apps.products.models import Category, Product, ProductImage
from src.apps.webhooks.models import WebhookEvent


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Faker("word")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower())


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    title = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("text", max_nb_chars=500)
    sku = factory.Sequence(lambda n: f"SKU-{n:04d}")
    price = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    stock = factory.Faker("random_int", min=0, max=100)
    category = factory.SubFactory(CategoryFactory)


class MarketplaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Marketplace

    name = factory.Faker("company")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    api_url = factory.Faker("url")
    is_active = True


class MarketplaceCredentialFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MarketplaceCredential

    marketplace = factory.SubFactory(MarketplaceFactory)
    client_id = factory.Faker("uuid4")
    client_secret = factory.Faker("uuid4")
    api_key = factory.Faker("uuid4")


class ProductListingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductListing

    product = factory.SubFactory(ProductFactory)
    marketplace = factory.SubFactory(MarketplaceFactory)
    external_id = factory.Faker("uuid4")
    status = "pending"


class WebhookEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WebhookEvent

    event_type = "product.enhanced"
    payload = factory.LazyFunction(lambda: {"test": "data"})
    webhook_url = "https://example.com/webhook"
    status = "pending"
