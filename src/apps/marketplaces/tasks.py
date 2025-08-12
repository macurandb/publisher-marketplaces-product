"""
Async tasks for marketplaces
"""

import logging

from celery import shared_task

from src.apps.webhooks.services import WebhookService

from .models import ProductListing
from .services import MarketplacePublisher

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def publish_product_to_marketplace(self, listing_id):
    """
    Publish a product to a marketplace asynchronously
    """
    try:
        logger.info(f"Starting marketplace publishing for listing {listing_id}")
        listing = ProductListing.objects.get(id=listing_id)
        publisher = MarketplacePublisher(listing.marketplace)
        webhook_service = WebhookService()

        # Verify product is AI-enhanced before publishing
        if not listing.product.ai_enhanced:
            listing.status = "failed"
            listing.save()

            error_details = {
                "error_type": "ai_enhancement_required",
                "error_code": "AI_ENHANCEMENT_MISSING",
                "error_message": "Product must be AI-enhanced before marketplace publishing",
                "product_ai_status": listing.product.ai_enhanced,
                "product_ai_description_length": len(
                    listing.product.ai_description or ""
                ),
                "product_ai_keywords_length": len(listing.product.ai_keywords or ""),
            }

            # Send failure webhook with detailed error information
            webhook_payload = {
                "event": "product.publish_failed",
                "product_id": listing.product.id,
                "product_sku": listing.product.sku,
                "marketplace": listing.marketplace.name,
                "marketplace_id": listing.marketplace.id,
                "listing_id": listing.id,
                "error": error_details["error_message"],
                "error_details": error_details,
                "timestamp": listing.updated_at.isoformat(),
            }

            webhook_service.send_webhook("product.publish_failed", webhook_payload)
            logger.error(
                f"Publishing failed for listing {listing_id}: {error_details['error_message']}"
            )

            return f"Error: {error_details['error_message']}"

        # Update status to processing
        listing.status = "processing"
        listing.save()

        logger.info(
            f"Publishing product {listing.product.id} to marketplace {listing.marketplace.name}"
        )

        # Attempt to publish
        result = publisher.publish_product(listing.product)

        if result["success"]:
            listing.external_id = result["marketplace_id"]
            listing.status = "completed"
            listing.save()

            logger.info(
                f"Product {listing.product.id} published successfully to {listing.marketplace.name}"
            )

            # Send success webhook
            webhook_payload = {
                "event": "product.published",
                "product_id": listing.product.id,
                "product_sku": listing.product.sku,
                "marketplace": listing.marketplace.name,
                "marketplace_id": listing.marketplace.id,
                "listing_id": listing.id,
                "external_id": result["marketplace_id"],
                "publish_details": result.get("details", {}),
                "timestamp": listing.updated_at.isoformat(),
            }

            webhook_service.send_webhook("product.published", webhook_payload)

            return f"Product published successfully: {result['marketplace_id']}"
        else:
            listing.status = "failed"
            listing.save()

            error_details = {
                "error_type": "marketplace_api_error",
                "error_code": result.get("error_code", "UNKNOWN_ERROR"),
                "error_message": result["error"],
                "marketplace_response": result.get("response", {}),
                "retry_count": self.request.retries,
            }

            # Send failure webhook with detailed error information
            webhook_payload = {
                "event": "product.publish_failed",
                "product_id": listing.product.id,
                "product_sku": listing.product.sku,
                "marketplace": listing.marketplace.name,
                "marketplace_id": listing.marketplace.id,
                "listing_id": listing.id,
                "error": result["error"],
                "error_details": error_details,
                "timestamp": listing.updated_at.isoformat(),
            }

            webhook_service.send_webhook("product.publish_failed", webhook_payload)
            logger.error(
                f"Publishing failed for listing {listing_id}: {result['error']}"
            )

            # Retry logic for transient errors
            if self.request.retries < self.max_retries and self._is_retryable_error(
                result
            ):
                logger.info(
                    f"Retrying marketplace publishing for listing {listing_id}, attempt {self.request.retries + 1}"
                )
                raise self.retry(countdown=60 * (self.request.retries + 1))

            return f"Error publishing product: {result['error']}"

    except ProductListing.DoesNotExist:
        error_msg = f"Listing {listing_id} not found"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error publishing product: {str(e)}"
        logger.error(error_msg, exc_info=True)

        # Try to send error webhook if possible
        try:
            webhook_service = WebhookService()
            webhook_service.send_webhook(
                "product.publish_failed",
                {
                    "event": "product.publish_failed",
                    "listing_id": listing_id,
                    "error": error_msg,
                    "error_type": "unexpected_error",
                    "error_details": {
                        "error_class": type(e).__name__,
                        "error_message": str(e),
                        "retry_count": self.request.retries,
                    },
                    "timestamp": (
                        ProductListing.objects.get(id=listing_id).updated_at.isoformat()
                        if ProductListing.objects.filter(id=listing_id).exists()
                        else None
                    ),
                },
            )
        except Exception as webhook_error:
            logger.error(f"Failed to send error webhook: {webhook_error}")

        # Retry logic for transient errors
        if self.request.retries < self.max_retries and self._is_retryable_error(
            {"error": str(e)}
        ):
            logger.info(
                f"Retrying marketplace publishing for listing {listing_id}, attempt {self.request.retries + 1}"
            )
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

        return error_msg

    def _is_retryable_error(self, result):
        """
        Determine if an error is retryable
        """
        error = result.get("error", "").lower()
        retryable_errors = [
            "timeout",
            "connection",
            "network",
            "rate limit",
            "temporary",
            "service unavailable",
            "internal server error",
            "gateway timeout",
        ]

        return any(retryable in error for retryable in retryable_errors)
