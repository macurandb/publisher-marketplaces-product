"""
Views for products
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Product
from .serializers import CategorySerializer, ProductCreateSerializer, ProductSerializer
from .tasks import enhance_product_with_ai, enhanced_workflow_with_canvas


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filterset_fields = ["parent"]
    search_fields = ["name"]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["category", "status", "ai_enhanced"]
    search_fields = ["title", "description", "sku"]
    ordering_fields = ["created_at", "price", "stock"]

    def get_serializer_class(self):
        if self.action == "create":
            return ProductCreateSerializer
        return ProductSerializer

    @action(detail=True, methods=["post"])
    def enhance_with_ai(self, request, pk=None):
        """
        Enhance product using AI
        """
        product = self.get_object()

        # Execute async task
        task = enhance_product_with_ai.delay(product.id)

        return Response(
            {"message": "AI enhancement process started", "task_id": task.id},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"])
    def create_and_publish(self, request, pk=None):
        """
        Complete workflow: Enhance with AI then publish to marketplace
        """
        product = self.get_object()
        marketplace_id = request.data.get("marketplace_id")

        if not marketplace_id:
            return Response(
                {"error": "marketplace_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Import here to avoid circular imports
        from .tasks import enhance_and_publish_workflow

        # Execute complete workflow
        task = enhance_and_publish_workflow.delay(product.id, marketplace_id)

        return Response(
            {
                "message": "Complete workflow started: AI enhancement → Marketplace publishing",
                "workflow_id": task.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"])
    def enhanced_workflow_canvas(self, request, pk=None):
        """
        Enhanced workflow using Celery Canvas for better dependency management
        """
        product = self.get_object()
        marketplace_id = request.data.get("marketplace_id")

        if not marketplace_id:
            return Response(
                {"error": "marketplace_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Execute enhanced workflow with Canvas
        task = enhanced_workflow_with_canvas.delay(product.id, marketplace_id)

        return Response(
            {
                "message": "Enhanced Canvas workflow started with improved dependency management",
                "canvas_workflow_id": task.id,
                "workflow_type": "celery_canvas",
            },
            status=status.HTTP_202_ACCEPTED,
        )
