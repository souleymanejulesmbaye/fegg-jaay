"""WSGI config pour Fëgg Jaay — utilisé par Gunicorn en production."""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fegg_jaay.settings")

application = get_wsgi_application()
