"""
Sender WhatsApp — Fëgg Jaay.

Envoie des messages via l'API 360dialog (WhatsApp Business API).
Chaque boutique a son propre wa_token et wa_phone_id (multi-tenant).
"""

import logging
from typing import Optional

import httpx
from boutiques.models import Boutique

logger = logging.getLogger(__name__)

# URL de base de l'API 360dialog
BASE_URL = "https://waba.360dialog.io/v1"


def envoyer_message_texte(
    boutique: Boutique,
    telephone_destinataire: str,
    texte: str,
) -> bool:
    """
    Envoie un message texte WhatsApp depuis le numéro de la boutique.

    Args:
        boutique: instance Boutique (contient wa_token et wa_phone_id)
        telephone_destinataire: numéro avec indicatif, ex: "221771234567"
        texte: contenu du message

    Returns:
        True si l'envoi a réussi, False sinon
    """
    url = f"{BASE_URL}/messages"
    headers = {
        "D360-API-KEY": boutique.wa_token,
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": telephone_destinataire,
        "type": "text",
        "text": {"body": texte},
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info(
                "Message envoyé à %s depuis boutique %s",
                telephone_destinataire,
                boutique.nom,
            )
            return True

    except httpx.TimeoutException:
        logger.error(
            "Timeout lors de l'envoi à %s (boutique %s)",
            telephone_destinataire,
            boutique.nom,
        )
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Erreur HTTP %d lors de l'envoi à %s : %s",
            exc.response.status_code,
            telephone_destinataire,
            exc.response.text[:300],
        )
    except Exception as exc:
        logger.exception(
            "Erreur inattendue lors de l'envoi à %s : %s",
            telephone_destinataire,
            exc,
        )

    return False


def envoyer_notification_commercant(boutique: Boutique, message: str) -> bool:
    """
    Envoie une notification au propriétaire de la boutique via WhatsApp.
    Utilisé pour notifier les nouvelles ventes et les alertes stock.
    """
    return envoyer_message_texte(
        boutique=boutique,
        telephone_destinataire=boutique.proprietaire_tel,
        texte=message,
    )


def envoyer_message_bienvenue(boutique: Boutique, telephone: str) -> bool:
    """Envoie le message de bienvenue configuré par le commerçant."""
    return envoyer_message_texte(
        boutique=boutique,
        telephone_destinataire=telephone,
        texte=boutique.message_bienvenue,
    )


def notifier_nouvelle_commande(boutique: Boutique, commande) -> bool:
    """
    Notifie le commerçant d'une nouvelle commande passée via WhatsApp.
    """
    lignes = commande.lignes.select_related("produit").all()
    details = "\n".join(
        f"  • {l.quantite}x {l.produit.nom} — {l.sous_total_formate}"
        for l in lignes
    )
    message = (
        f"🛒 *Nouvelle commande !*\n\n"
        f"Réf : *{commande.numero_ref}*\n"
        f"Client : {commande.client.prenom or commande.client.telephone}\n"
        f"Produits :\n{details}\n"
        f"*Total : {commande.montant_formate}*\n\n"
        f"En attente de paiement. Vérifiez votre dashboard."
    )
    return envoyer_notification_commercant(boutique, message)


def notifier_alerte_stock(boutique: Boutique, produit) -> bool:
    """Alerte le commerçant quand le stock d'un produit passe sous le seuil."""
    message = (
        f"⚠️ *Alerte stock faible*\n\n"
        f"Produit : *{produit.nom}*\n"
        f"Stock actuel : *{produit.stock}* unité(s)\n"
        f"Seuil d'alerte : {produit.stock_alerte}\n\n"
        f"Pensez à réapprovisionner !"
    )
    return envoyer_notification_commercant(boutique, message)
