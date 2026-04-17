"""
Vitrine publique — Fëgg Jaay.

Pages accessibles sans connexion :
  /                          → landing page
  /boutique/<slug>/          → catalogue produits d'une boutique
  /boutique/<slug>/commander/ → passer une commande web
  /boutique/<slug>/commande/<ref>/ → confirmation de commande

Pages compte client (OTP WhatsApp) :
  /boutique/<slug>/compte/connexion/ → saisir son numéro → reçoit OTP
  /boutique/<slug>/compte/otp/       → saisir le code OTP
  /boutique/<slug>/compte/           → tableau de bord client (commandes)
  /boutique/<slug>/compte/deconnexion/ → se déconnecter
"""

import logging
import random
import string

from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_POST

from boutiques.models import Boutique, Categorie, Client, Commande, LigneCommande, OTPCode, Produit, ZoneLivraison

OTP_EXPIRY_MINUTES = 10

logger = logging.getLogger(__name__)


def landing(request):
    """Page d'accueil publique."""
    boutiques = Boutique.objects.filter(actif=True).order_by("nom")
    return render(request, "vitrine/landing.html", {"boutiques": boutiques})


def boutique(request, slug):
    """Vitrine publique d'une boutique : catalogue + formulaire de commande."""
    shop = get_object_or_404(Boutique, slug=slug, actif=True)

    # Filtre par catégorie + recherche
    cat_id = request.GET.get("cat", "")
    q = request.GET.get("q", "").strip()
    produits = Produit.objects.filter(boutique=shop, actif=True, stock__gt=0)
    if cat_id:
        produits = produits.filter(categorie_id=cat_id)
    if q:
        produits = produits.filter(nom__icontains=q)
    produits = produits.select_related("categorie").order_by("nom")

    categories = Categorie.objects.filter(boutique=shop, produits__actif=True, produits__stock__gt=0).distinct()
    zones = ZoneLivraison.objects.filter(boutique=shop, actif=True).order_by("frais", "nom")
    return render(request, "vitrine/boutique.html", {
        "boutique": shop,
        "produits": produits,
        "categories": categories,
        "cat_active": cat_id,
        "zones": zones,
        "q": q,
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
    zone_id = request.POST.get("zone_livraison", "").strip()

    if not telephone:
        return redirect("vitrine:boutique", slug=slug)

    # Récupérer la zone de livraison choisie
    zone = None
    frais_livraison = 0
    if zone_id:
        zone = ZoneLivraison.objects.filter(pk=zone_id, boutique=shop, actif=True).first()
        if zone:
            frais_livraison = zone.frais

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
                zone_livraison=zone,
                frais_livraison=frais_livraison,
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

            # Notifier le commerçant — nouvelle commande
            try:
                from whatsapp.sender import notifier_nouvelle_commande
                notifier_nouvelle_commande(shop, commande)
            except Exception:
                logger.warning("Notification commerçant impossible (commande %s).", commande.numero_ref)

            # Alertes stock bas pour les produits commandés
            try:
                from whatsapp.sender import notifier_alerte_stock
                for produit, _ in items:
                    p_refresh = Produit.objects.get(pk=produit.pk)
                    if p_refresh.stock <= p_refresh.stock_alerte:
                        notifier_alerte_stock(shop, p_refresh)
            except Exception:
                logger.warning("Alerte stock impossible après commande %s.", commande.numero_ref)

            logger.info("Commande web %s créée — client=%s", commande.numero_ref, telephone_stocke)

    except Exception:
        logger.exception("Erreur lors de la création de commande web.")
        return redirect("vitrine:boutique", slug=slug)

    return redirect("vitrine:confirmation", slug=slug, ref=commande.numero_ref)


# ─── Helpers compte client ────────────────────────────────────────────────────

def _session_key(boutique):
    """Clé de session pour stocker l'id du client connecté (par boutique)."""
    return f"client_id_{boutique.pk}"


def _otp_tel_key(boutique):
    """Clé de session temporaire : téléphone en cours de vérification OTP."""
    return f"otp_tel_{boutique.pk}"


def _get_client_connecte(request, boutique):
    """Retourne le Client connecté pour cette boutique, ou None."""
    client_id = request.session.get(_session_key(boutique))
    if not client_id:
        return None
    try:
        return Client.objects.get(pk=client_id, boutique=boutique)
    except Client.DoesNotExist:
        return None


def _generer_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


# ─── Vues compte client ───────────────────────────────────────────────────────

def connexion(request, slug):
    """Étape 1 : le client saisit son numéro WhatsApp → reçoit un OTP."""
    shop = get_object_or_404(Boutique, slug=slug, actif=True)

    # Déjà connecté → dashboard
    if _get_client_connecte(request, shop):
        return redirect("vitrine:compte", slug=slug)

    erreur = None

    if request.method == "POST":
        telephone_raw = request.POST.get("telephone", "").strip().replace(" ", "").replace("-", "")
        if not telephone_raw:
            erreur = "Veuillez entrer votre numéro WhatsApp."
        else:
            if not telephone_raw.startswith("+"):
                telephone_raw = "+" + telephone_raw
            telephone_stocke = telephone_raw.lstrip("+")

            client, _ = Client.objects.get_or_create(
                boutique=shop,
                telephone=telephone_stocke,
                defaults={"prenom": "", "langue_preferee": "fr"},
            )

            # Invalider les anciens OTP non utilisés de ce client
            OTPCode.objects.filter(client=client, utilise=False).update(utilise=True)

            code = _generer_otp()
            OTPCode.objects.create(
                client=client,
                code=code,
                expires_at=timezone.now() + timezone.timedelta(minutes=OTP_EXPIRY_MINUTES),
            )

            from django.conf import settings
            if settings.DEBUG:
                logger.info(">>> OTP DEV [%s] : %s <<<", telephone_stocke, code)
            try:
                from whatsapp.sender import envoyer_otp
                envoyer_otp(shop, telephone_stocke, code)
            except Exception:
                logger.warning("Impossible d'envoyer l'OTP à %s", telephone_stocke)

            # Stocker le téléphone en session pour la page OTP
            request.session[_otp_tel_key(shop)] = telephone_stocke
            return redirect("vitrine:otp", slug=slug)

    return render(request, "vitrine/compte/connexion.html", {
        "boutique": shop,
        "erreur": erreur,
    })


def verifier_otp(request, slug):
    """Étape 2 : le client saisit le code OTP reçu par WhatsApp."""
    shop = get_object_or_404(Boutique, slug=slug, actif=True)

    if _get_client_connecte(request, shop):
        return redirect("vitrine:compte", slug=slug)

    telephone = request.session.get(_otp_tel_key(shop))
    if not telephone:
        return redirect("vitrine:connexion", slug=slug)

    erreur = None

    if request.method == "POST":
        code_saisi = request.POST.get("code", "").strip()
        try:
            client = Client.objects.get(boutique=shop, telephone=telephone)
            otp = OTPCode.objects.filter(
                client=client,
                code=code_saisi,
                utilise=False,
            ).order_by("-created_at").first()

            if otp and otp.est_valide:
                otp.utilise = True
                otp.save(update_fields=["utilise"])
                request.session[_session_key(shop)] = client.pk
                del request.session[_otp_tel_key(shop)]
                return redirect("vitrine:compte", slug=slug)
            elif otp and not otp.est_valide:
                erreur = "Ce code a expiré. Recommencez."
            else:
                erreur = "Code incorrect. Vérifiez votre WhatsApp."
        except Client.DoesNotExist:
            erreur = "Numéro introuvable."

    return render(request, "vitrine/compte/otp.html", {
        "boutique": shop,
        "telephone": telephone,
        "erreur": erreur,
    })


def compte(request, slug):
    """Tableau de bord client : historique des commandes."""
    shop = get_object_or_404(Boutique, slug=slug, actif=True)
    client = _get_client_connecte(request, shop)
    if not client:
        return redirect("vitrine:connexion", slug=slug)

    commandes = (
        Commande.objects.filter(boutique=shop, client=client)
        .prefetch_related("lignes__produit")
        .order_by("-created_at")
    )
    return render(request, "vitrine/compte/dashboard.html", {
        "boutique": shop,
        "client": client,
        "commandes": commandes,
    })


@require_POST
def deconnexion(request, slug):
    """Déconnecte le client (supprime sa session pour cette boutique)."""
    shop = get_object_or_404(Boutique, slug=slug, actif=True)
    request.session.pop(_session_key(shop), None)
    request.session.pop(_otp_tel_key(shop), None)
    return redirect("vitrine:boutique", slug=slug)


# ─── Confirmation commande ────────────────────────────────────────────────────

@require_POST
def soumettre_paiement(request, slug, ref):
    """
    Le client soumet sa référence de transaction Wave/Orange Money depuis la web.
    Met à jour la commande et notifie le commerçant.
    """
    shop = get_object_or_404(Boutique, slug=slug, actif=True)
    commande = get_object_or_404(
        Commande,
        numero_ref=ref,
        boutique=shop,
        statut="attente_paiement",
    )

    mode = request.POST.get("mode_paiement", "").strip()
    reference = request.POST.get("reference_paiement", "").strip()

    if not reference:
        return redirect("vitrine:confirmation", slug=slug, ref=ref)

    commande.mode_paiement = mode
    commande.reference_paiement = reference
    commande.save(update_fields=["mode_paiement", "reference_paiement", "updated_at"])

    try:
        from whatsapp.sender import notifier_paiement_recu
        notifier_paiement_recu(shop, commande)
    except Exception:
        logger.warning("Notification paiement impossible (commande %s).", ref)

    logger.info("Référence paiement soumise — commande %s, mode %s", ref, mode)
    return redirect("vitrine:confirmation", slug=slug, ref=ref)


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
