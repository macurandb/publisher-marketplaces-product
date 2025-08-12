"""
Webhook async tasks
"""

import logging

from celery import shared_task

from .models import WebhookEvent
from .services import WebhookService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_webhook_notification(self, webhook_event_id):
    """
    Send webhook notification with retry logic
    """
    try:
        logger.info(f"Processing webhook event {webhook_event_id}")
        webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
        webhook_service = WebhookService()

        result = webhook_service.send_notification(webhook_event)

        # Retry if failed and haven't exceeded max attempts
        if result.status == "failed" and result.attempts < result.max_attempts:
            logger.warning(
                f"Webhook {webhook_event_id} failed, retrying. Attempts: {result.attempts}/{result.max_attempts}"
            )
            raise self.retry(countdown=60 * result.attempts)  # Exponential backoff

        if result.status == "completed":
            logger.info(f"Webhook {webhook_event_id} sent successfully")
        else:
            logger.error(
                f"Webhook {webhook_event_id} failed after {result.attempts} attempts"
            )

        return f"Webhook {webhook_event_id} processed with status: {result.status}"

    except WebhookEvent.DoesNotExist:
        error_msg = f"Webhook event {webhook_event_id} not found"
        logger.error(error_msg)
        return error_msg
    except Exception as exc:
        logger.error(
            f"Error processing webhook {webhook_event_id}: {str(exc)}", exc_info=True
        )

        # Retry logic for transient errors
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying webhook {webhook_event_id}, attempt {self.request.retries + 1}"
            )
            raise self.retry(exc=exc, countdown=60)

        # If we've exhausted retries, mark the webhook as permanently failed
        try:
            webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
            webhook_event.status = "failed"
            webhook_event.response_body = f"Max retries exceeded: {str(exc)}"
            webhook_event.save()
            logger.error(
                f"Webhook {webhook_event_id} marked as permanently failed after {self.max_retries} retries"
            )
        except WebhookEvent.DoesNotExist:
            pass

        return f"Webhook {webhook_event_id} failed permanently: {str(exc)}"
