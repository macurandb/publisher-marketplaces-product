"""
Models for marketplace integrations
"""

from django.db import models

from src.apps.core.models import StatusChoices, TimeStampedModel


class Marketplace(TimeStampedModel):
    """
    Marketplace configuration
    """

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    api_url = models.URLField()
    is_active = models.BooleanField(default=True)
    
    # Webhook configuration
    webhook_url = models.URLField(blank=True, help_text="Marketplace-specific webhook URL")

    def __str__(self):
        return self.name


class MarketplaceCredential(TimeStampedModel):
    """
    Credentials for each marketplace
    """

    marketplace = models.OneToOneField(Marketplace, on_delete=models.CASCADE)
    client_id = models.CharField(max_length=200, blank=True)
    client_secret = models.CharField(max_length=200, blank=True)
    api_key = models.CharField(max_length=200, blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)

    def __str__(self):
        return f"Credentials for {self.marketplace.name}"


class ProductListing(TimeStampedModel):
    """
    Product listings on marketplaces
    """

    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    marketplace = models.ForeignKey(Marketplace, on_delete=models.CASCADE)
    external_id = models.CharField(
        max_length=100, blank=True, help_text="ID from the marketplace"
    )
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    last_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["product", "marketplace"]

    def __str__(self):
        return f"{self.product.title} on {self.marketplace.name}"


class AsyncPublicationTask(TimeStampedModel):
    """
    Model to track async publication process
    """
    
    class TaskStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ENHANCING = 'enhancing', 'Enhancing with AI'
        ENHANCED = 'enhanced', 'Enhanced'
        PUBLISHING = 'publishing', 'Publishing to Marketplace'
        PUBLISHED = 'published', 'Published'
        WEBHOOK_SENT = 'webhook_sent', 'Webhook Sent'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
    
    # Task identification
    task_id = models.CharField(max_length=255, unique=True)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    marketplace = models.ForeignKey(Marketplace, on_delete=models.CASCADE)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.PENDING)
    current_step = models.CharField(max_length=100, blank=True)
    
    # Progress tracking
    steps_completed = models.JSONField(default=list)
    total_steps = models.IntegerField(default=4)  # enhance, publish, webhook, complete
    
    # Retry tracking
    enhancement_retries = models.IntegerField(default=0)
    publication_retries = models.IntegerField(default=0)
    webhook_retries = models.IntegerField(default=0)
    
    # Results and errors
    enhancement_result = models.JSONField(default=dict, blank=True)
    publication_result = models.JSONField(default=dict, blank=True)
    webhook_result = models.JSONField(default=dict, blank=True)
    error_details = models.JSONField(default=dict, blank=True)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Task {self.task_id} - {self.product.title} to {self.marketplace.name}"
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage"""
        if self.total_steps == 0:
            return 0
        return (len(self.steps_completed) / self.total_steps) * 100
    
    def add_step_completed(self, step_name):
        """Add a completed step"""
        if step_name not in self.steps_completed:
            self.steps_completed.append(step_name)
            self.save(update_fields=['steps_completed'])
    
    def update_status(self, status, current_step=None):
        """Update task status and current step"""
        self.status = status
        if current_step:
            self.current_step = current_step
        self.save(update_fields=['status', 'current_step'])
