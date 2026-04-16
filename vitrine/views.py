"""
Vitrine publique — Fëgg Jaay.

Pages accessibles sans connexion :
  /                          → landing page
  /boutique/<slug>/          → catalogue produits d'une boutique
  /boutique/<slug>/commander/ → passer une commande web
  /boutique/<slug>/commande/<ref>/ → confirmation de commande
"""

import logging

from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from boutiques.models import Boutique, Client, Commande, LigneCommande, Produit

logger = logging.getLogger(__name__)


def landing(request):
    """Page d'accueil publique."""
    boutiques = Boutique.objects.filter(actif=True).order_by("nom")
    return render(request, "vitrine/landing.html", {"boutiques": boutiques})


def boutique(request, slug):
    """Vitrine publique d'une boutique : catalogue + formulaire de commande."""
    shop = get_object_or_404(Boutique, slug=slug, actif=True)
    produits = Produit.objects.filter(boutique=shop, actif=True, stock__gt=0).order_by("nom")
    return render(request, "vitrine/boutique.html", {
        "boutique": shop,
        "produits": produits,
    })


@require_http_methods(["POST"])
def passer_commande(request, slug):
    """
    Crée une commande depuis le formulaire web.
    Données POST attendues :
      - prenom : prénom du client
      - telephone : numéro WhatsApp du client
      - adresse : adresse de livraison
      - produit_<id> : quantité pour chaque produit (0 = pas commandé)
    """
    shop = get_object_or_404(Boutique, slug=slug, actif=True)

    prenom = request.POST.get("prenom", "").strip()
    telephone = request.POST.get("telephone", "").strip().replace(" ", "").replace("-", "")
    adresse = request.POST.get("adresse", "").strip()

    if not telephone:
        return redirect("vitrine:boutique", slug=slug)

    # Normaliser le numéro (ajouter + si absent)
    if not telephone.startswith("+"):
        telephone = "+" + telephone
    # Stocker sans le + pour cohérence avec le bot WhatsApp
    telephone_stocke = telephone.lstrip("+")

    # Récupérer les produits commandés
    items = []
    for produit in Produit.objects.filter(boutique=shop, actif=True, stock__gt=0):
        qte_str = request.POST.get(f"produit_{produit.pk}", "0")
        try:
            qte = int(qte_str)
        except ValueError:
            qte = 0
        if qte > 0:
            items.append((produit, qte))

    if not items:
        return redirect("vitrine:boutique", slug=slug)

    try:
        with transaction.atomic():
            client, _ = Client.objects.get_or_create(
                boutique=shop,
                telephone=telephone_stocke,
                defaults={"prenom": prenom, "langue_preferee": "fr"},
            )
            if prenom and not client.prenom:
                Client.objects.filter(pk=client.pk).update(prenom=prenom)

            commande = Commande.objects.create(
                boutique=shop,
                client=client,
                statut="attente_paiement",
                adresse_livraison=adresse,
            )

            for produit, quantite in items:
                # Recharger avec verrou pour gérer la concurrence
                p = Produit.objects.select_for_update().get(pk=produit.pk)
                quantite = min(quantite, p.stock)
                if quantite <= 0:
                    continue
                p.stock -= quantite
                p.save(update_fields=["stock"])
                LigneCommande.objects.create(
                    commande=commande,
                    produit=p,
                    quantite=quantite,
                    prix_unitaire=p.prix,
                )

            commande.recalculer_total()
            Client.objects.filter(pk=client.pk).update(
                total_commandes=client.total_commandes + 1
            )

            # Notifier le commerçant
            try:
                from whatsapp.sender import notifier_nouvelle_commande
                notifier_nouvelle_commande(shop, commande)
            except Exception:
                logger.warning("Notification commerçant impossible (commande %s).", commande.numero_ref)

            logger.info("Commande web %s créée — client=%s", commande.numero_ref, telephone_stocke)

    except Exception:
        logger.exception("Erreur lors de la création de commande web.")
        return redirect("vitrine:boutique", slug=slug)

    return redirect("vitrine:confirmation", slug=slug, ref=commande.numero_ref)


def confirmation(request, slug, ref):
    """Page de confirmation après commande."""
    shop = get_object_or_404(Boutique, slug=slug, actif=True)
    commande = get_object_or_404(
        Commande.objects.prefetch_related("lignes__produit"),
        numero_ref=ref,
        boutique=shop,
    )
    return render(request, "vitrine/confirmation.html", {
        "boutique": shop,
        "commande": commande,
    })
