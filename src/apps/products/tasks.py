"""
Async tasks for products
"""

import logging

from celery import chain, group, shared_task
from django.conf import settings

from src.apps.ai_assistant.services import AIProductEnhancer
from src.apps.webhooks.services import WebhookService

from .models import Product

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enhance_product_with_ai(self, product_id):
    """
    Enhance a product using AI asynchronously
    """
    try:
        logger.info(f"Starting AI enhancement for product {product_id}")
        product = Product.objects.get(id=product_id)
        enhancer = AIProductEnhancer()
        webhook_service = WebhookService()

        # Generate enhanced description
        enhanced_description = enhancer.enhance_description(
            title=product.title,
            description=product.description,
            category=product.category.name,
        )

        # Generate keywords
        keywords = enhancer.generate_keywords(
            title=product.title,
            description=enhanced_description,
            category=product.category.name,
        )

        # Update product
        product.ai_description = enhanced_description
        product.ai_keywords = ", ".join(keywords)
        product.ai_enhanced = True
        product.save()

        logger.info(f"Product {product_id} enhanced successfully with AI")

        # Send webhook notification
        webhook_payload = {
            "event": "product.enhanced",
            "product_id": product.id,
            "product_sku": product.sku,
            "enhanced_description": enhanced_description,
            "keywords": keywords,
            "timestamp": product.updated_at.isoformat(),
        }

        webhook_service.send_webhook("product.enhanced", webhook_payload)

        return f"Product {product.id} enhanced successfully"

    except Product.DoesNotExist:
        error_msg = f"Product {product_id} not found"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error enhancing product {product_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)

        # Retry logic for transient errors
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying AI enhancement for product {product_id}, attempt {self.request.retries + 1}"
            )
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

        return error_msg


@shared_task
def enhance_and_publish_workflow(product_id, marketplace_id):
    """
    Complete workflow: Enhance product with AI, then publish to marketplace
    This task ensures the sequential flow: AI Enhancement → Marketplace Publishing → Webhooks
    """
    try:
        from src.apps.marketplaces.models import Marketplace, ProductListing
        from src.apps.marketplaces.tasks import publish_product_to_marketplace
        from src.apps.webhooks.services import WebhookService

        logger.info(
            f"Starting complete workflow for product {product_id} on marketplace {marketplace_id}"
        )

        product = Product.objects.get(id=product_id)
        marketplace = Marketplace.objects.get(id=marketplace_id)
        webhook_service = WebhookService()

        # Step 1: Enhance product with AI (call synchronously to ensure completion)
        enhancement_result = enhance_product_with_ai.apply(args=[product_id]).result

        if "enhanced successfully" not in enhancement_result:
            # Send failure webhook with detailed error information
            webhook_service.send_webhook(
                "product.enhancement_failed",
                {
                    "event": "product.enhancement_failed",
                    "product_id": product_id,
                    "product_sku": product.sku,
                    "error": enhancement_result,
                    "error_type": "ai_enhancement_failure",
                    "marketplace_id": marketplace_id,
                    "marketplace_name": marketplace.name,
                    "timestamp": product.updated_at.isoformat(),
                },
            )
            logger.error(f"Workflow failed at AI enhancement: {enhancement_result}")
            return f"Workflow failed at AI enhancement: {enhancement_result}"

        # Verify product was actually enhanced
        product.refresh_from_db()
        if not product.ai_enhanced:
            error_msg = "Product was not properly enhanced with AI"
            webhook_service.send_webhook(
                "product.enhancement_failed",
                {
                    "event": "product.enhancement_failed",
                    "product_id": product_id,
                    "product_sku": product.sku,
                    "error": error_msg,
                    "error_type": "ai_enhancement_verification_failure",
                    "marketplace_id": marketplace_id,
                    "marketplace_name": marketplace.name,
                    "timestamp": product.updated_at.isoformat(),
                },
            )
            logger.error(f"Workflow failed: {error_msg}")
            return f"Workflow failed: {error_msg}"

        # Step 2: Create marketplace listing if it doesn't exist
        listing, created = ProductListing.objects.get_or_create(
            product=product, marketplace=marketplace, defaults={"status": "pending"}
        )

        # Step 3: Publish to marketplace (call synchronously to ensure completion)
        publish_result = publish_product_to_marketplace.apply(args=[listing.id]).result

        # Step 4: Send workflow completion webhook
        webhook_service.send_webhook(
            "workflow.completed",
            {
                "event": "workflow.completed",
                "product_id": product_id,
                "product_sku": product.sku,
                "marketplace": marketplace.name,
                "listing_id": listing.id,
                "enhancement_result": enhancement_result,
                "publish_result": publish_result,
                "timestamp": listing.updated_at.isoformat(),
            },
        )

        logger.info(f"Complete workflow finished successfully for product {product_id}")
        return f"Complete workflow finished. Enhancement: {enhancement_result}. Publishing: {publish_result}"

    except Exception as e:
        # Send error webhook with detailed error information
        try:
            webhook_service = WebhookService()
            webhook_service.send_webhook(
                "workflow.error",
                {
                    "event": "workflow.error",
                    "product_id": product_id,
                    "marketplace_id": marketplace_id,
                    "error": str(e),
                    "error_type": "workflow_execution_error",
                    "error_details": {
                        "error_class": type(e).__name__,
                        "error_message": str(e),
                    },
                    "timestamp": Product.objects.get(
                        id=product_id
                    ).updated_at.isoformat(),
                },
            )
        except Exception as webhook_error:
            logger.error(f"Failed to send error webhook: {webhook_error}")

        logger.error(
            f"Workflow error for product {product_id}: {str(e)}", exc_info=True
        )
        return f"Workflow error: {str(e)}"


@shared_task
def enhanced_workflow_with_canvas(product_id, marketplace_id):
    """
    Enhanced workflow using Celery Canvas for better dependency management
    This approach provides more robust task chaining and error handling
    """
    try:
        from src.apps.marketplaces.tasks import publish_product_to_marketplace
        from src.apps.webhooks.services import WebhookService

        logger.info(
            f"Starting Canvas-based workflow for product {product_id} on marketplace {marketplace_id}"
        )

        # Create task chain with proper error handling
        workflow_chain = chain(
            enhance_product_with_ai.s(product_id),
            publish_product_to_marketplace.s(marketplace_id),
            send_workflow_completion_webhook.s(product_id, marketplace_id),
        )

        # Execute the chain asynchronously
        result = workflow_chain.apply_async()

        logger.info(f"Canvas workflow started with task ID: {result.id}")
        return f"Canvas workflow started successfully with task ID: {result.id}"

    except Exception as e:
        logger.error(f"Failed to start Canvas workflow: {str(e)}", exc_info=True)

        # Send error webhook
        try:
            webhook_service = WebhookService()
            webhook_service.send_webhook(
                "workflow.error",
                {
                    "event": "workflow.error",
                    "product_id": product_id,
                    "marketplace_id": marketplace_id,
                    "error": str(e),
                    "error_type": "canvas_workflow_startup_error",
                    "error_details": {
                        "error_class": type(e).__name__,
                        "error_message": str(e),
                    },
                    "timestamp": Product.objects.get(
                        id=product_id
                    ).updated_at.isoformat(),
                },
            )
        except Exception as webhook_error:
            logger.error(f"Failed to send error webhook: {webhook_error}")

        return f"Canvas workflow startup error: {str(e)}"


@shared_task
def send_workflow_completion_webhook(product_id, marketplace_id):
    """
    Send completion webhook after successful workflow execution
    This task is designed to be chained with other tasks
    """
    try:
        from src.apps.marketplaces.models import Marketplace, ProductListing
        from src.apps.webhooks.services import WebhookService

        product = Product.objects.get(id=product_id)
        marketplace = Marketplace.objects.get(id=marketplace_id)
        listing = ProductListing.objects.get(product=product, marketplace=marketplace)

        webhook_service = WebhookService()

        # Send completion webhook
        webhook_service.send_webhook(
            "workflow.completed",
            {
                "event": "workflow.completed",
                "product_id": product_id,
                "product_sku": product.sku,
                "marketplace": marketplace.name,
                "listing_id": listing.id,
                "status": "completed",
                "timestamp": listing.updated_at.isoformat(),
            },
        )

        logger.info(f"Workflow completion webhook sent for product {product_id}")
        return f"Completion webhook sent for product {product_id}"

    except Exception as e:
        logger.error(f"Failed to send completion webhook: {str(e)}", exc_info=True)
        return f"Failed to send completion webhook: {str(e)}"
