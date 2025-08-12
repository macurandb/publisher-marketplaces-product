# Import Celery so Django recognizes it
# Only import if not in test environment
import os

if os.environ.get("DJANGO_SETTINGS_MODULE") != "src.config.settings.test":
    from .celery import app as celery_app

    __all__ = ("celery_app",)
else:
    __all__ = ()
