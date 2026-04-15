"""
Planification des tâches Celery Beat pour Fëgg Jaay.

À importer dans settings.py si vous préférez une config statique
(alternative à la gestion via l'admin Django / django-celery-beat).

Usage dans settings.py :
    from fegg_jaay.celery_beat_schedule import CELERY_BEAT_SCHEDULE
"""

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Rapport quotidien à 20h00 (Africa/Dakar)
    "rapport-quotidien-20h": {
        "task": "whatsapp.envoyer_rapport_quotidien",
        "schedule": crontab(hour=20, minute=0),
    },
    # Vérification des alertes stock toutes les heures
    "verifier-alertes-stock": {
        "task": "whatsapp.verifier_alertes_stock",
        "schedule": crontab(minute=0),  # toutes les heures
    },
    # Relance des commandes en attente toutes les 2 heures
    "relancer-commandes-attente": {
        "task": "whatsapp.relancer_commandes",
        "schedule": crontab(minute=0, hour="*/2"),
    },
}
