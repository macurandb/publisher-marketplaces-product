"""
Serializers for webhooks
"""

from rest_framework import serializers

from .models import WebhookEvent


class WebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEvent
        fields = [
            "id",
            "event_type",
            "payload",
            "webhook_url",
            "status",
            "response_status_code",
            "response_body",
            "attempts",
            "max_attempts",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
