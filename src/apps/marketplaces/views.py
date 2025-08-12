"""
Views for marketplaces
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Marketplace, ProductListing
from .serializers import MarketplaceSerializer, ProductListingSerializer
from .tasks import publish_product_to_marketplace


class MarketplaceViewSet(viewsets.ModelViewSet):
    queryset = Marketplace.objects.all()
    serializer_class = MarketplaceSerializer
    filterset_fields = ["is_active"]
    search_fields = ["name"]


class ProductListingViewSet(viewsets.ModelViewSet):
    queryset = ProductListing.objects.all()
    serializer_class = ProductListingSerializer
    filterset_fields = ["marketplace", "status"]

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """
        Publish a product to the marketplace
        """
        listing = self.get_object()

        # Execute async task
        task = publish_product_to_marketplace.delay(listing.id)

        return Response(
            {"message": "Publishing started", "task_id": task.id},
            status=status.HTTP_202_ACCEPTED,
        )
