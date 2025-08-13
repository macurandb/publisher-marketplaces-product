"""
Views for marketplaces
"""

from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AsyncPublicationTask, Marketplace, ProductListing
from .serializers import MarketplaceSerializer, ProductListingSerializer
from .tasks import create_async_publication_task, get_async_task_status


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
        Publish a product to the marketplace (legacy method)
        """
        listing = self.get_object()

        # For now, redirect to the new async publication flow
        result = create_async_publication_task.delay(listing.product.id, listing.marketplace.id)
        
        if result.get('task_id'):
            return Response(
                {
                    "message": "Publishing started using new async flow",
                    "task_id": result['task_id'],
                    "status": result['status']
                },
                status=status.HTTP_202_ACCEPTED,
            )
        else:
            return Response(
                {"error": "Failed to start publication process"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    
    @action(detail=False, methods=["post"], url_path="async-publish")
    def async_publish(self, request):
        """
        Start async publication process: AI Enhancement -> Marketplace Publishing -> External Webhook
        
        Expected payload:
        {
            "product_id": 123,
            "marketplace_id": 456
        }
        """
        product_id = request.data.get('product_id')
        marketplace_id = request.data.get('marketplace_id')
        
        if not product_id or not marketplace_id:
            return Response(
                {
                    "error": "Both product_id and marketplace_id are required",
                    "required_fields": ["product_id", "marketplace_id"]
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate that product and marketplace exist
        try:
            from src.apps.products.models import Product
            product = Product.objects.get(id=product_id)
            marketplace = Marketplace.objects.get(id=marketplace_id)
        except Product.DoesNotExist:
            return Response(
                {"error": f"Product with id {product_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Marketplace.DoesNotExist:
            return Response(
                {"error": f"Marketplace with id {marketplace_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Start async publication process
        result = create_async_publication_task.delay(product_id, marketplace_id)
        
        if result.get('task_id'):
            return Response(
                {
                    "task_id": result['task_id'],
                    "status": result['status'],
                    "message": "Async publication process started",
                    "product_id": product_id,
                    "marketplace_id": marketplace_id,
                    "product_title": product.title,
                    "marketplace_name": marketplace.name
                },
                status=status.HTTP_202_ACCEPTED
            )
        else:
            return Response(
                {
                    "error": result.get('error', 'Failed to start publication process'),
                    "status": "failed"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=["get"], url_path="task-status/(?P<task_id>[^/.]+)")
    def task_status(self, request, task_id=None):
        """
        Get the status of an async publication task
        """
        if not task_id:
            return Response(
                {"error": "task_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get task status
        result = get_async_task_status.delay(task_id)
        task_info = result.get()
        
        if task_info.get('status') == 'not_found':
            return Response(
                {"error": "Task not found", "task_id": task_id},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(task_info, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=["get"], url_path="product-tasks/(?P<product_id>[^/.]+)")
    def product_tasks(self, request, product_id=None):
        """
        Get all async publication tasks for a specific product
        
        Query parameters:
        - status: Filter by task status (optional)
        - marketplace_id: Filter by marketplace (optional)
        - limit: Limit number of results (default: 50)
        - offset: Offset for pagination (default: 0)
        """
        if not product_id:
            return Response(
                {"error": "product_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate that product exists
        try:
            from src.apps.products.models import Product
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"error": f"Product with id {product_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get query parameters
        task_status_filter = request.query_params.get('status')
        marketplace_id = request.query_params.get('marketplace_id')
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        
        # Build queryset
        queryset = AsyncPublicationTask.objects.filter(product_id=product_id)
        
        # Apply filters
        if task_status_filter:
            queryset = queryset.filter(status=task_status_filter)
        
        if marketplace_id:
            try:
                marketplace = Marketplace.objects.get(id=marketplace_id)
                queryset = queryset.filter(marketplace=marketplace)
            except Marketplace.DoesNotExist:
                return Response(
                    {"error": f"Marketplace with id {marketplace_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Order by most recent first
        queryset = queryset.order_by('-started_at')
        
        # Get total count for pagination
        total_count = queryset.count()
        
        # Apply pagination
        tasks = queryset[offset:offset + limit]
        
        # Serialize tasks
        from .serializers import AsyncPublicationTaskSerializer
        serializer = AsyncPublicationTaskSerializer(tasks, many=True)
        
        # Prepare response
        response_data = {
            "product_id": product_id,
            "product_title": product.title,
            "product_sku": product.sku,
            "total_tasks": total_count,
            "showing": len(tasks),
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total_count,
            "tasks": serializer.data
        }
        
        # Add summary statistics
        if total_count > 0:
            status_counts = {}
            for task_status in AsyncPublicationTask.TaskStatus.values:
                count = AsyncPublicationTask.objects.filter(
                    product_id=product_id, 
                    status=task_status
                ).count()
                if count > 0:
                    status_counts[task_status] = count
            
            response_data["status_summary"] = status_counts
            
            # Add marketplace summary
            marketplace_counts = {}
            marketplace_tasks = AsyncPublicationTask.objects.filter(
                product_id=product_id
            ).values('marketplace__name').annotate(
                count=models.Count('id')
            )
            
            for item in marketplace_tasks:
                marketplace_counts[item['marketplace__name']] = item['count']
            
            response_data["marketplace_summary"] = marketplace_counts
        
        return Response(response_data, status=status.HTTP_200_OK)
