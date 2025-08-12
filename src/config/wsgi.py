"""
WSGI config for multimarket_hub project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.config.settings.local")

application = get_wsgi_application()
