"""
Views for webhook management
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import WebhookEvent
from .serializers import WebhookEventSerializer
from .tasks import send_webhook_notification


class WebhookEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for webhook events (read-only)
    """

    queryset = WebhookEvent.objects.all()
    serializer_class = WebhookEventSerializer
    filterset_fields = ["event_type", "status"]
    ordering = ["-created_at"]

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """
        Retry a failed webhook
        """
        webhook_event = self.get_object()

        if webhook_event.status != "failed":
            return Response(
                {"error": "Only failed webhooks can be retried"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if webhook_event.attempts >= webhook_event.max_attempts:
            return Response(
                {"error": "Maximum retry attempts exceeded"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reset status and queue for retry
        webhook_event.status = "pending"
        webhook_event.save()

        send_webhook_notification.delay(webhook_event.id)

        return Response(
            {"message": "Webhook queued for retry", "webhook_id": webhook_event.id}
        )
