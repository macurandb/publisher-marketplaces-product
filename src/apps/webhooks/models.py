"""
Webhook models for external notifications
"""

from django.db import models

from src.apps.core.models import StatusChoices, TimeStampedModel


class WebhookEvent(TimeStampedModel):
    """
    Webhook event log
    """

    EVENT_TYPES = [
        ("product.enhanced", "Product Enhanced"),
        ("product.enhancement_failed", "Product Enhancement Failed"),
        ("product.published", "Product Published"),
        ("product.publish_failed", "Product Publish Failed"),
        ("workflow.completed", "Workflow Completed"),
        ("workflow.error", "Workflow Error"),
        ("canvas.workflow.started", "Canvas Workflow Started"),
        ("canvas.workflow.error", "Canvas Workflow Error"),
        ("marketplace.publish.retry", "Marketplace Publish Retry"),
        ("webhook.max_retries_exceeded", "Webhook Max Retries Exceeded"),
    ]

    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    payload = models.JSONField()
    webhook_url = models.URLField()
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    response_status_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)

    def __str__(self):
        return f"{self.event_type} - {self.status}"
