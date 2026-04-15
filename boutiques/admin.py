"""Interface d'administration Django pour les modèles boutiques."""

from django.contrib import admin
from django.utils.html import format_html
from .models import Boutique, Produit, Client, Commande, LigneCommande, MessageLog


class ProduitInline(admin.TabularInline):
    model = Produit
    extra = 1
    fields = ("nom", "prix", "stock", "stock_alerte", "actif")
    show_change_link = True


@admin.register(Boutique)
class BoutiqueAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone_wa", "ville", "plan", "actif", "abonnement_fin")
    list_filter = ("plan", "actif", "ville")
    search_fields = ("nom", "telephone_wa", "proprietaire_tel")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [ProduitInline]
    fieldsets = (
        ("Informations générales", {
            "fields": ("id", "nom", "ville", "plan", "actif", "abonnement_fin"),
        }),
        ("WhatsApp API (360dialog)", {
            "fields": ("telephone_wa", "wa_phone_id", "wa_token"),
            "classes": ("collapse",),
        }),
        ("Contact", {
            "fields": ("proprietaire_tel", "message_bienvenue"),
        }),
        ("Dates", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ("nom", "boutique", "prix_formate_admin", "stock", "stock_alerte", "actif")
    list_filter = ("actif", "boutique")
    search_fields = ("nom", "boutique__nom")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Prix")
    def prix_formate_admin(self, obj):
        return obj.prix_formate


class LigneCommandeInline(admin.TabularInline):
    model = LigneCommande
    extra = 0
    readonly_fields = ("sous_total_formate",)
    fields = ("produit", "quantite", "prix_unitaire", "sous_total_formate")

    @admin.display(description="Sous-total")
    def sous_total_formate(self, obj):
        return obj.sous_total_formate


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = (
        "numero_ref", "boutique", "client_nom", "montant_formate_admin",
        "statut_badge", "mode_paiement", "created_at",
    )
    list_filter = ("statut", "boutique", "mode_paiement")
    search_fields = ("numero_ref", "client__telephone", "client__prenom")
    readonly_fields = ("numero_ref", "created_at", "updated_at")
    inlines = [LigneCommandeInline]
    actions = ["marquer_payees", "marquer_livrees"]

    @admin.display(description="Client")
    def client_nom(self, obj):
        return str(obj.client)

    @admin.display(description="Montant")
    def montant_formate_admin(self, obj):
        return obj.montant_formate

    @admin.display(description="Statut")
    def statut_badge(self, obj):
        couleurs = {
            "attente_paiement": "orange",
            "payee": "blue",
            "en_preparation": "purple",
            "livree": "green",
            "annulee": "red",
        }
        couleur = couleurs.get(obj.statut, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            couleur,
            obj.get_statut_display(),
        )

    @admin.action(description="Marquer comme payées")
    def marquer_payees(self, request, queryset):
        queryset.update(statut="payee")

    @admin.action(description="Marquer comme livrées")
    def marquer_livrees(self, request, queryset):
        queryset.update(statut="livree")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("prenom", "telephone", "boutique", "langue_preferee", "total_commandes", "created_at")
    list_filter = ("langue_preferee", "boutique")
    search_fields = ("telephone", "prenom")
    readonly_fields = ("created_at", "updated_at", "total_commandes")


@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ("telephone_client", "boutique", "direction", "type_message", "apercu", "created_at")
    list_filter = ("direction", "type_message", "boutique")
    search_fields = ("telephone_client", "contenu")
    readonly_fields = ("created_at",)

    @admin.display(description="Aperçu")
    def apercu(self, obj):
        return obj.contenu[:60] + ("..." if len(obj.contenu) > 60 else "")
