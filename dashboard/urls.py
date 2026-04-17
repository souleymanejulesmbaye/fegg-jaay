"""URLs du dashboard commerçant — Fëgg Jaay."""

from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    # Auth
    path("inscription/", views.inscription, name="inscription"),
    path("login/", views.vue_login, name="login"),
    path("logout/", views.vue_logout, name="logout"),

    # Accueil / stats
    path("", views.accueil, name="accueil"),

    # Produits
    path("produits/", views.liste_produits, name="liste_produits"),
    path("produits/nouveau/", views.creer_produit, name="creer_produit"),
    path("produits/<int:produit_id>/modifier/", views.modifier_produit, name="modifier_produit"),
    path("produits/<int:produit_id>/supprimer/", views.supprimer_produit, name="supprimer_produit"),

    # Commandes
    path("commandes/", views.liste_commandes, name="liste_commandes"),
    path("commandes/<int:commande_id>/", views.detail_commande, name="detail_commande"),
    path("commandes/<int:commande_id>/statut/", views.changer_statut_commande, name="changer_statut"),

    # Clients
    path("clients/", views.liste_clients, name="liste_clients"),
    path("clients/<int:client_id>/", views.conversation_client, name="conversation_client"),

    # Export
    path("commandes/export/", views.exporter_commandes_csv, name="exporter_commandes"),

    # Configuration boutique
    path("config/", views.config_boutique, name="config_boutique"),

    # Catégories
    path("produits/categories/", views.gestion_categories, name="gestion_categories"),

    # Livraisons
    path("livraisons/zones/", views.zones_livraison, name="zones_livraison"),

    # Test bot
    path("test-bot/", views.test_bot, name="test_bot"),
    path("test-bot/reset/", views.reset_test_bot, name="reset_test_bot"),

    # API interne JSON
    path("api/stats/", views.api_stats, name="api_stats"),

    # Super-Admin
    path("superadmin/", views.superadmin_accueil, name="superadmin_accueil"),
    path("superadmin/boutique/<uuid:boutique_id>/", views.superadmin_boutique, name="superadmin_boutique"),
    path("superadmin/boutique/<uuid:boutique_id>/toggle/", views.superadmin_toggle_boutique, name="superadmin_toggle"),
    path("superadmin/boutique/<uuid:boutique_id>/plan/", views.superadmin_changer_plan, name="superadmin_plan"),
]
