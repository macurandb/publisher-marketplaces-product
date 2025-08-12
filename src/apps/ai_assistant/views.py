"""
Views for AI assistant
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import AIProductEnhancer


class EnhanceProductView(APIView):
    """
    View for enhancing products with AI
    """

    def post(self, request):
        title = request.data.get("title")
        description = request.data.get("description")
        category = request.data.get("category")

        if not all([title, description, category]):
            return Response(
                {"error": "title, description and category are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enhancer = AIProductEnhancer()

        enhanced_description = enhancer.enhance_description(
            title, description, category
        )
        keywords = enhancer.generate_keywords(title, enhanced_description, category)

        return Response(
            {"enhanced_description": enhanced_description, "keywords": keywords}
        )
