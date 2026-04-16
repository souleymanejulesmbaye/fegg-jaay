"""URLs publiques — Fëgg Jaay."""

from django.urls import path
from . import views

app_name = "vitrine"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("boutique/<slug:slug>/", views.boutique, name="boutique"),
    path("boutique/<slug:slug>/commander/", views.passer_commande, name="commander"),
    path("boutique/<slug:slug>/commande/<str:ref>/", views.confirmation, name="confirmation"),
]
