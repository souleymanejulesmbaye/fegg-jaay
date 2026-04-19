"""
Dashboard WhatsApp pour les commerçants Fëgg Jaay.

Commandes disponibles (envoyées par le commerçant via WhatsApp) :
  stats          → ventes du jour
  commandes      → liste des commandes en attente
  confirmer REF  → marquer une commande comme payée
  stock          → produits avec stock bas ou nul
  aide / menu    → liste des commandes
"""

import logging

from django.db.models import F, Sum
from django.utils import timezone

from boutiques.models import Boutique, Commande, Produit

logger = logging.getLogger(__name__)


def traiter_message_commercant(boutique: Boutique, message: str) -> str:
    """Traite un message WhatsApp envoyé par le commerçant."""
    msg = message.strip()
    msg_lower = msg.lower()

    if msg_lower in ("stats", "résumé", "resume", "bilan", "chiffres"):
        return _stats(boutique)

    if msg_lower in ("commandes", "orders", "pending", "en attente"):
        return _commandes_en_attente(boutique)

    if msg_lower in ("stock", "stocks", "inventaire"):
        return _stock_bas(boutique)

    if msg_lower.startswith("confirmer ") or msg_lower.startswith("confirm "):
        ref = msg.split(" ", 1)[1].strip().upper()
        return _confirmer_commande(boutique, ref)

    if msg_lower.startswith("livrer ") or msg_lower.startswith("livree "):
        ref = msg.split(" ", 1)[1].strip().upper()
        return _marquer_livree(boutique, ref)

    # aide / menu / anything else
    return _menu()


# ─── Commandes ────────────────────────────────────────────────────────────────

def _stats(boutique: Boutique) -> str:
    aujourd_hui = timezone.now().date()
    qs = Commande.objects.filter(boutique=boutique, created_at__date=aujourd_hui)
    total = qs.filter(statut__in=("payee", "en_preparation", "livree")).aggregate(
        s=Sum("montant_total")
    )["s"] or 0
    nb_total = qs.count()
    nb_attente = qs.filter(statut="attente_paiement").count()
    nb_payee = qs.filter(statut="payee").count()
    nb_livree = qs.filter(statut="livree").count()

    return (
        f"📊 *Stats du jour — {boutique.nom}*\n\n"
        f"Commandes reçues : *{nb_total}*\n"
        f"  ⏳ En attente : {nb_attente}\n"
        f"  ✅ Payées : {nb_payee}\n"
        f"  🚚 Livrées : {nb_livree}\n\n"
        f"💰 *Chiffre confirmé : {total:,} FCFA*"
    )


def _commandes_en_attente(boutique: Boutique) -> str:
    commandes = (
        Commande.objects
        .filter(boutique=boutique, statut="attente_paiement")
        .select_related("client")
        .order_by("-created_at")[:8]
    )
    if not commandes:
        return "✅ Aucune commande en attente de paiement."

    lignes = []
    for c in commandes:
        client_label = c.client.prenom or c.client.telephone
        ref_pay = f" — réf: {c.reference_paiement}" if c.reference_paiement else ""
        lignes.append(f"• *{c.numero_ref}* — {client_label} — {c.montant_formate}{ref_pay}")

    return (
        f"🛒 *Commandes en attente ({len(commandes)})*\n\n"
        + "\n".join(lignes)
        + "\n\nPour confirmer le paiement : *confirmer CMD-XXXX*"
    )


def _confirmer_commande(boutique: Boutique, ref: str) -> str:
    try:
        commande = Commande.objects.select_related("client").get(
            boutique=boutique,
            numero_ref=ref,
            statut="attente_paiement",
        )
    except Commande.DoesNotExist:
        return (
            f"❌ Commande *{ref}* introuvable ou déjà traitée.\n"
            f"Vérifiez la référence avec *commandes*."
        )

    commande.statut = "payee"
    commande.save(update_fields=["statut", "updated_at"])
    client_label = commande.client.prenom or commande.client.telephone
    logger.info("Commande %s marquée payée par le commerçant (WA dashboard).", ref)

    return (
        f"✅ *{ref}* confirmée !\n"
        f"Client : {client_label}\n"
        f"Montant : {commande.montant_formate}\n\n"
        f"Pour marquer livrée : *livrer {ref}*"
    )


def _marquer_livree(boutique: Boutique, ref: str) -> str:
    try:
        commande = Commande.objects.select_related("client").get(
            boutique=boutique,
            numero_ref=ref,
            statut__in=("payee", "en_preparation"),
        )
    except Commande.DoesNotExist:
        return f"❌ Commande *{ref}* introuvable ou déjà livrée/annulée."

    commande.statut = "livree"
    commande.save(update_fields=["statut", "updated_at"])
    client_label = commande.client.prenom or commande.client.telephone
    logger.info("Commande %s marquée livrée par le commerçant (WA dashboard).", ref)

    return f"🚚 *{ref}* marquée livrée !\nClient : {client_label}"


def _stock_bas(boutique: Boutique) -> str:
    produits = (
        Produit.objects
        .filter(boutique=boutique, actif=True, stock__lte=F("stock_alerte"))
        .order_by("stock")[:10]
    )
    if not produits:
        return "✅ Tous les stocks sont au-dessus du seuil d'alerte."

    lignes = [
        f"• *{p.nom}* : {p.stock} unité(s) (seuil : {p.stock_alerte})"
        for p in produits
    ]
    return (
        f"⚠️ *Stocks bas — {boutique.nom}*\n\n"
        + "\n".join(lignes)
        + "\n\nMettez à jour le stock sur votre dashboard web."
    )


def _menu() -> str:
    return (
        "📱 *Dashboard WhatsApp — Fëgg Jaay*\n\n"
        "Commandes disponibles :\n"
        "• *stats* — ventes et chiffres du jour\n"
        "• *commandes* — commandes en attente\n"
        "• *confirmer CMD-XXXX* — valider un paiement\n"
        "• *livrer CMD-XXXX* — marquer une commande livrée\n"
        "• *stock* — produits en stock bas\n\n"
        "Tapez une commande pour commencer."
    )
