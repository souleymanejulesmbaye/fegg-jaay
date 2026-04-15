"""Configuration Celery pour Fëgg Jaay."""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fegg_jaay.settings")

app = Celery("fegg_jaay")

# Lire la config depuis Django settings, namespace CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Découverte automatique des tâches dans toutes les apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
