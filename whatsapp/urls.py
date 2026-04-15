"""URLs de l'app WhatsApp — Fëgg Jaay."""

from django.urls import path
from . import views

app_name = "whatsapp"

urlpatterns = [
    # Webhook Meta/360dialog (GET = vérification, POST = messages entrants)
    path("webhook/", views.webhook, name="webhook"),
]
