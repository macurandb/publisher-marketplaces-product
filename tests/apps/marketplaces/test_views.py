"""
Tests for marketplace views
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from src.apps.marketplaces.models import Marketplace


class MarketplaceViewSetTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        self.marketplace = Marketplace.objects.create(
            name="MercadoLibre",
            slug="mercadolibre",
            api_url="https://api.mercadolibre.com",
        )

    def test_list_marketplaces(self):
        """Test listing marketplaces"""
        url = reverse("marketplace-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle both paginated and non-paginated responses
        data = (
            response.data.get("results", response.data)
            if isinstance(response.data, dict)
            else response.data
        )
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "MercadoLibre")
