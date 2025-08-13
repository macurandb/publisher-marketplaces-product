"""
Async tasks for marketplaces
"""

import logging
import uuid
from django.db import models
from django.utils import timezone

from celery import chain, shared_task

from src.apps.webhooks.services import WebhookService

from .models import AsyncPublicationTask, ProductListing
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
            if self.request.retries < self.max_retries and _is_retryable_error(
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
        if self.request.retries < self.max_retries and _is_retryable_error(
            {"error": str(e)}
        ):
            logger.info(
                f"Retrying marketplace publishing for listing {listing_id}, attempt {self.request.retries + 1}"
            )
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

        return error_msg


def _is_retryable_error(result):
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


# ============================================================================
# NEW ASYNC PUBLICATION FLOW
# ============================================================================

@shared_task
def create_async_publication_task(product_id, marketplace_id):
    """
    Create and start the async publication process
    Returns task_id for tracking
    """
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Create tracking record
        async_task = AsyncPublicationTask.objects.create(
            task_id=task_id,
            product_id=product_id,
            marketplace_id=marketplace_id,
            status=AsyncPublicationTask.TaskStatus.PENDING,
            current_step="Initializing publication process"
        )
        
        logger.info(f"Created async publication task {task_id} for product {product_id} to marketplace {marketplace_id}")
        
        # Start the async chain
        publication_chain = chain(
            enhance_product_async.s(task_id),
            publish_to_marketplace_async.s(task_id),
            send_external_webhook.s(task_id)
        )
        
        # Execute the chain
        publication_chain.apply_async()
        
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "Publication process started"
        }
        
    except Exception as e:
        logger.error(f"Failed to create async publication task: {str(e)}", exc_info=True)
        return {
            "task_id": None,
            "status": "failed",
            "error": str(e)
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enhance_product_async(self, task_id):
    """
    Step 1: Enhance product with AI
    """
    try:
        async_task = AsyncPublicationTask.objects.get(task_id=task_id)
        async_task.update_status(
            AsyncPublicationTask.TaskStatus.ENHANCING,
            "Enhancing product with AI"
        )
        
        logger.info(f"Starting AI enhancement for task {task_id}")
        
        # Import here to avoid circular imports
        from src.apps.ai_assistant.services import AIProductEnhancer
        
        # Enhance the product
        enhancer = AIProductEnhancer()
        result = enhancer.enhance_product(async_task.product)
        
        if result.get('success', False):
            # Update task with success
            async_task.enhancement_result = result
            async_task.update_status(
                AsyncPublicationTask.TaskStatus.ENHANCED,
                "Product enhanced successfully"
            )
            async_task.add_step_completed("enhancement")
            
            logger.info(f"AI enhancement completed for task {task_id}")
            return {"success": True, "task_id": task_id}
            
        else:
            # Handle enhancement failure
            async_task.enhancement_retries += 1
            async_task.error_details = {
                "step": "enhancement",
                "error": result.get('error', 'Unknown enhancement error'),
                "retries": async_task.enhancement_retries
            }
            async_task.save()
            
            # Retry if we haven't exceeded max retries
            if async_task.enhancement_retries < 3:
                logger.warning(f"AI enhancement failed for task {task_id}, retrying (attempt {async_task.enhancement_retries})")
                raise self.retry(countdown=60 * async_task.enhancement_retries)
            else:
                # Max retries exceeded, fail the task
                async_task.update_status(
                    AsyncPublicationTask.TaskStatus.FAILED,
                    "AI enhancement failed after 3 retries"
                )
                logger.error(f"AI enhancement failed permanently for task {task_id}")
                
                # Send failure webhook
                send_external_webhook.delay(task_id, failed_step="enhancement")
                return {"success": False, "task_id": task_id, "error": "Enhancement failed"}
                
    except AsyncPublicationTask.DoesNotExist:
        logger.error(f"Async task {task_id} not found")
        return {"success": False, "error": "Task not found"}
    except Exception as e:
        logger.error(f"Unexpected error in AI enhancement for task {task_id}: {str(e)}", exc_info=True)
        
        # Update retry count and error details
        try:
            async_task = AsyncPublicationTask.objects.get(task_id=task_id)
            async_task.enhancement_retries += 1
            async_task.error_details = {
                "step": "enhancement",
                "error": str(e),
                "retries": async_task.enhancement_retries
            }
            async_task.save()
            
            if async_task.enhancement_retries < 3:
                raise self.retry(exc=e, countdown=60 * async_task.enhancement_retries)
            else:
                async_task.update_status(AsyncPublicationTask.TaskStatus.FAILED, "Enhancement failed")
                send_external_webhook.delay(task_id, failed_step="enhancement")
        except:
            pass
            
        return {"success": False, "task_id": task_id, "error": str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def publish_to_marketplace_async(self, enhancement_result, task_id):
    """
    Step 2: Publish product to marketplace
    """
    try:
        async_task = AsyncPublicationTask.objects.get(task_id=task_id)
        
        # Check if enhancement was successful
        if not enhancement_result.get('success', False):
            logger.error(f"Cannot publish task {task_id} - enhancement failed")
            return {"success": False, "task_id": task_id, "error": "Enhancement failed"}
        
        async_task.update_status(
            AsyncPublicationTask.TaskStatus.PUBLISHING,
            "Publishing to marketplace"
        )
        
        logger.info(f"Starting marketplace publication for task {task_id}")
        
        # Get or create product listing
        listing, created = ProductListing.objects.get_or_create(
            product=async_task.product,
            marketplace=async_task.marketplace,
            defaults={'status': 'pending'}
        )
        
        # Publish using the marketplace publisher
        publisher = MarketplacePublisher(async_task.marketplace)
        result = publisher.publish_product(async_task.product)
        
        if result.get('success', False):
            # Update listing and task
            listing.external_id = result.get('marketplace_id', '')
            listing.status = 'completed'
            listing.save()
            
            async_task.publication_result = result
            async_task.update_status(
                AsyncPublicationTask.TaskStatus.PUBLISHED,
                "Published to marketplace successfully"
            )
            async_task.add_step_completed("publication")
            
            logger.info(f"Marketplace publication completed for task {task_id}")
            return {"success": True, "task_id": task_id, "result": result}
            
        else:
            # Handle publication failure
            async_task.publication_retries += 1
            async_task.error_details = {
                "step": "publication",
                "error": result.get('error', 'Unknown publication error'),
                "marketplace_response": result.get('response', {}),
                "retries": async_task.publication_retries
            }
            async_task.save()
            
            # Retry if we haven't exceeded max retries
            if async_task.publication_retries < 3:
                logger.warning(f"Marketplace publication failed for task {task_id}, retrying (attempt {async_task.publication_retries})")
                raise self.retry(countdown=60 * async_task.publication_retries)
            else:
                # Max retries exceeded, fail the task
                async_task.update_status(
                    AsyncPublicationTask.TaskStatus.FAILED,
                    "Marketplace publication failed after 3 retries"
                )
                logger.error(f"Marketplace publication failed permanently for task {task_id}")
                
                # Send failure webhook
                send_external_webhook.delay(task_id, failed_step="publication")
                return {"success": False, "task_id": task_id, "error": "Publication failed"}
                
    except AsyncPublicationTask.DoesNotExist:
        logger.error(f"Async task {task_id} not found")
        return {"success": False, "error": "Task not found"}
    except Exception as e:
        logger.error(f"Unexpected error in marketplace publication for task {task_id}: {str(e)}", exc_info=True)
        
        # Update retry count and error details
        try:
            async_task = AsyncPublicationTask.objects.get(task_id=task_id)
            async_task.publication_retries += 1
            async_task.error_details = {
                "step": "publication",
                "error": str(e),
                "retries": async_task.publication_retries
            }
            async_task.save()
            
            if async_task.publication_retries < 3:
                raise self.retry(exc=e, countdown=60 * async_task.publication_retries)
            else:
                async_task.update_status(AsyncPublicationTask.TaskStatus.FAILED, "Publication failed")
                send_external_webhook.delay(task_id, failed_step="publication")
        except:
            pass
            
        return {"success": False, "task_id": task_id, "error": str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_external_webhook(self, publication_result, task_id, failed_step=None):
    """
    Step 3: Send webhook to external system
    """
    import requests
    from django.conf import settings
    
    try:
        async_task = AsyncPublicationTask.objects.get(task_id=task_id)
        
        # Determine webhook URL (marketplace-specific or global)
        webhook_url = async_task.marketplace.webhook_url
        if not webhook_url:
            webhook_url = getattr(settings, 'GLOBAL_WEBHOOK_URL', None)
        
        if not webhook_url:
            logger.warning(f"No webhook URL configured for task {task_id}")
            async_task.update_status(
                AsyncPublicationTask.TaskStatus.COMPLETED,
                "Completed (no webhook configured)"
            )
            async_task.completed_at = timezone.now()
            async_task.save()
            return {"success": True, "message": "No webhook configured"}
        
        # Prepare webhook payload
        if failed_step:
            # Failure webhook
            webhook_payload = {
                "task_id": task_id,
                "product_id": async_task.product.id,
                "status": "failed",
                "failed_step": failed_step,
                "error_details": async_task.error_details,
                "retries": {
                    "enhancement_retries": async_task.enhancement_retries,
                    "publication_retries": async_task.publication_retries,
                    "webhook_retries": async_task.webhook_retries
                },
                "timestamp": timezone.now().isoformat()
            }
        else:
            # Success webhook
            webhook_payload = {
                "task_id": task_id,
                "product_id": async_task.product.id,
                "status": "completed",
                "enhancement_result": async_task.enhancement_result,
                "publication_result": async_task.publication_result,
                "retries": {
                    "enhancement_retries": async_task.enhancement_retries,
                    "publication_retries": async_task.publication_retries,
                    "webhook_retries": async_task.webhook_retries
                },
                "timestamp": timezone.now().isoformat()
            }
        
        # Send webhook
        logger.info(f"Sending external webhook for task {task_id} to {webhook_url}")
        
        response = requests.post(
            webhook_url,
            json=webhook_payload,
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            # Webhook sent successfully
            async_task.webhook_result = {
                "status_code": response.status_code,
                "response": response.text[:1000]  # Limit response size
            }
            async_task.update_status(
                AsyncPublicationTask.TaskStatus.WEBHOOK_SENT,
                "External webhook sent successfully"
            )
            async_task.add_step_completed("webhook")
            
            # Mark as completed
            async_task.update_status(
                AsyncPublicationTask.TaskStatus.COMPLETED,
                "Process completed successfully"
            )
            async_task.completed_at = timezone.now()
            async_task.save()
            
            logger.info(f"External webhook sent successfully for task {task_id}")
            return {"success": True, "task_id": task_id}
            
        else:
            # Webhook failed
            async_task.webhook_retries += 1
            async_task.webhook_result = {
                "status_code": response.status_code,
                "response": response.text[:1000],
                "retries": async_task.webhook_retries
            }
            async_task.save()
            
            # Retry if we haven't exceeded max retries
            if async_task.webhook_retries < 3:
                logger.warning(f"External webhook failed for task {task_id}, retrying (attempt {async_task.webhook_retries})")
                raise self.retry(countdown=60 * async_task.webhook_retries)
            else:
                # Max retries exceeded, but don't fail the whole task
                logger.error(f"External webhook failed permanently for task {task_id}")
                async_task.update_status(
                    AsyncPublicationTask.TaskStatus.COMPLETED,
                    "Completed (webhook failed after 3 retries)"
                )
                async_task.completed_at = timezone.now()
                async_task.save()
                return {"success": False, "task_id": task_id, "error": "Webhook failed"}
                
    except AsyncPublicationTask.DoesNotExist:
        logger.error(f"Async task {task_id} not found")
        return {"success": False, "error": "Task not found"}
    except Exception as e:
        logger.error(f"Unexpected error sending webhook for task {task_id}: {str(e)}", exc_info=True)
        
        # Update retry count
        try:
            async_task = AsyncPublicationTask.objects.get(task_id=task_id)
            async_task.webhook_retries += 1
            async_task.webhook_result = {
                "error": str(e),
                "retries": async_task.webhook_retries
            }
            async_task.save()
            
            if async_task.webhook_retries < 3:
                raise self.retry(exc=e, countdown=60 * async_task.webhook_retries)
            else:
                async_task.update_status(
                    AsyncPublicationTask.TaskStatus.COMPLETED,
                    "Completed (webhook failed)"
                )
                async_task.completed_at = timezone.now()
                async_task.save()
        except:
            pass
            
        return {"success": False, "task_id": task_id, "error": str(e)}


@shared_task
def get_async_task_status(task_id):
    """
    Get the status of an async publication task
    """
    try:
        async_task = AsyncPublicationTask.objects.get(task_id=task_id)
        return {
            "task_id": task_id,
            "status": async_task.status,
            "current_step": async_task.current_step,
            "progress_percentage": async_task.progress_percentage,
            "steps_completed": async_task.steps_completed,
            "retries": {
                "enhancement_retries": async_task.enhancement_retries,
                "publication_retries": async_task.publication_retries,
                "webhook_retries": async_task.webhook_retries
            },
            "started_at": async_task.started_at.isoformat(),
            "completed_at": async_task.completed_at.isoformat() if async_task.completed_at else None,
            "error_details": async_task.error_details if async_task.status == AsyncPublicationTask.TaskStatus.FAILED else None
        }
    except AsyncPublicationTask.DoesNotExist:
        return {
            "task_id": task_id,
            "status": "not_found",
            "error": "Task not found"
        }


@shared_task
def get_product_tasks_summary(product_id, status_filter=None, marketplace_id=None):
    """
    Get summary of all async publication tasks for a product
    """
    try:
        from src.apps.products.models import Product
        
        # Validate product exists
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return {
                "error": "Product not found",
                "product_id": product_id
            }
        
        # Build queryset
        queryset = AsyncPublicationTask.objects.filter(product_id=product_id)
        
        # Apply filters
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if marketplace_id:
            queryset = queryset.filter(marketplace_id=marketplace_id)
        
        # Get tasks
        tasks = queryset.order_by('-started_at')
        
        # Build response
        task_list = []
        for task in tasks:
            task_data = {
                "task_id": task.task_id,
                "status": task.status,
                "current_step": task.current_step,
                "progress_percentage": task.progress_percentage,
                "marketplace_name": task.marketplace.name,
                "marketplace_id": task.marketplace.id,
                "steps_completed": task.steps_completed,
                "retries": {
                    "enhancement_retries": task.enhancement_retries,
                    "publication_retries": task.publication_retries,
                    "webhook_retries": task.webhook_retries
                },
                "started_at": task.started_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "error_details": task.error_details if task.status == AsyncPublicationTask.TaskStatus.FAILED else None
            }
            task_list.append(task_data)
        
        # Generate summary statistics
        total_tasks = queryset.count()
        status_counts = {}
        
        for task_status in AsyncPublicationTask.TaskStatus.values:
            count = queryset.filter(status=task_status).count()
            if count > 0:
                status_counts[task_status] = count
        
        # Marketplace summary
        marketplace_counts = {}
        marketplace_tasks = queryset.values('marketplace__name').annotate(
            count=models.Count('id')
        )
        
        for item in marketplace_tasks:
            marketplace_counts[item['marketplace__name']] = item['count']
        
        return {
            "product_id": product_id,
            "product_title": product.title,
            "product_sku": product.sku,
            "total_tasks": total_tasks,
            "status_summary": status_counts,
            "marketplace_summary": marketplace_counts,
            "tasks": task_list
        }
        
    except Exception as e:
        logger.error(f"Error getting product tasks summary for product {product_id}: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "product_id": product_id
        }