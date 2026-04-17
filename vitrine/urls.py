"""URLs publiques — Fëgg Jaay."""

from django.urls import path
from . import views

app_name = "vitrine"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("boutique/<slug:slug>/", views.boutique, name="boutique"),
    path("boutique/<slug:slug>/commander/", views.passer_commande, name="commander"),
    path("boutique/<slug:slug>/commande/<str:ref>/", views.confirmation, name="confirmation"),
    path("boutique/<slug:slug>/commande/<str:ref>/payer/", views.soumettre_paiement, name="soumettre_paiement"),
    # Compte client
    path("boutique/<slug:slug>/compte/connexion/", views.connexion, name="connexion"),
    path("boutique/<slug:slug>/compte/otp/", views.verifier_otp, name="otp"),
    path("boutique/<slug:slug>/compte/", views.compte, name="compte"),
    path("boutique/<slug:slug>/compte/deconnexion/", views.deconnexion, name="deconnexion"),
]
