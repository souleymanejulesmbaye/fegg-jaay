"""
Sender WhatsApp — Fëgg Jaay.

Envoie des messages via l'API Twilio (WhatsApp Sandbox pour les tests).
"""

import logging

import httpx
from django.conf import settings
from django.core.mail import send_mail

from boutiques.models import Boutique

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = getattr(settings, "TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = getattr(settings, "TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = getattr(settings, "TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

INFOBIP_API_KEY = getattr(settings, "INFOBIP_API_KEY", "")
INFOBIP_BASE_URL = getattr(settings, "INFOBIP_BASE_URL", "api.infobip.com")
INFOBIP_SENDER_NUMBER = getattr(settings, "INFOBIP_SENDER_NUMBER", "")


def _normaliser_telephone(telephone: str) -> str:
    """
    Formate le numéro pour Twilio : 'whatsapp:+221771234567'
    Accepte : '221771234567', '+221771234567', '771234567'
    """
    t = telephone.strip().replace(" ", "").replace("-", "")
    if t.startswith("whatsapp:"):
        return t
    if not t.startswith("+"):
        t = "+" + t
    return f"whatsapp:{t}"


def _get_meta_credentials(boutique: Boutique):
    """Retourne (phone_id, token) : boutique en priorité, sinon credentials plateforme."""
    if boutique.wa_phone_id and boutique.wa_token:
        return boutique.wa_phone_id, boutique.wa_token
    platform_token = getattr(settings, "WA_PLATFORM_TOKEN", "")
    platform_phone_id = getattr(settings, "WA_PLATFORM_PHONE_NUMBER_ID", "")
    if platform_token and platform_phone_id:
        return platform_phone_id, platform_token
    return None, None


def _est_infobip(boutique: Boutique) -> bool:
    if not INFOBIP_API_KEY or not INFOBIP_SENDER_NUMBER:
        return False
    tel = (boutique.telephone_wa or "").lstrip("+")
    sender = INFOBIP_SENDER_NUMBER.lstrip("+")
    return tel == sender


def envoyer_message_texte(
    boutique: Boutique,
    telephone_destinataire: str,
    texte: str,
) -> bool:
    """
    Envoie un message texte WhatsApp.
    Priorité : 1) Meta boutique  2) Infobip  3) Meta plateforme  4) Twilio sandbox
    """
    if boutique.wa_phone_id and boutique.wa_token:
        return _envoyer_meta_avec(boutique.wa_phone_id, boutique.wa_token, telephone_destinataire, texte, boutique.nom)

    if _est_infobip(boutique):
        return _envoyer_infobip(boutique, telephone_destinataire, texte)

    platform_token = getattr(settings, "WA_PLATFORM_TOKEN", "")
    platform_phone_id = getattr(settings, "WA_PLATFORM_PHONE_NUMBER_ID", "")
    if platform_token and platform_phone_id:
        return _envoyer_meta_avec(platform_phone_id, platform_token, telephone_destinataire, texte, boutique.nom)

    return _envoyer_twilio(boutique, telephone_destinataire, texte)


def _envoyer_meta_avec(phone_id: str, token: str, telephone_destinataire: str, texte: str, nom_boutique: str = "") -> bool:
    """Envoie via Meta WhatsApp Business API."""
    t = telephone_destinataire.strip().replace("+", "").replace(" ", "")
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": t,
        "type": "text",
        "text": {"body": texte},
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info("Meta: message envoyé à %s (boutique %s)", t, nom_boutique)
            return True
    except httpx.TimeoutException:
        logger.error("Meta: timeout envoi à %s (boutique %s)", t, nom_boutique)
    except httpx.HTTPStatusError as exc:
        logger.error("Meta: erreur HTTP %d à %s : %s", exc.response.status_code, t, exc.response.text[:300])
    except Exception as exc:
        logger.exception("Meta: erreur inattendue à %s : %s", t, exc)
    return False


def _envoyer_infobip(boutique: Boutique, telephone_destinataire: str, texte: str) -> bool:
    t = telephone_destinataire.strip().lstrip("+")
    url = f"https://{INFOBIP_BASE_URL}/whatsapp/1/message/text"
    headers = {
        "Authorization": f"App {INFOBIP_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "from": INFOBIP_SENDER_NUMBER.lstrip("+"),
        "to": t,
        "content": {"text": texte},
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info("Infobip: message envoyé à %s (boutique %s)", t, boutique.nom)
            return True
    except httpx.TimeoutException:
        logger.error("Infobip: timeout envoi à %s", t)
    except httpx.HTTPStatusError as exc:
        logger.error("Infobip: erreur HTTP %d à %s : %s", exc.response.status_code, t, exc.response.text[:300])
    except Exception as exc:
        logger.exception("Infobip: erreur inattendue à %s : %s", t, exc)
    return False


def _envoyer_twilio(boutique: Boutique, telephone_destinataire: str, texte: str) -> bool:
    """Envoie via Twilio WhatsApp Sandbox."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.warning("Twilio non configuré — message non envoyé à %s", telephone_destinataire)
        return False

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    destinataire = _normaliser_telephone(telephone_destinataire)

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                url,
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                data={
                    "From": TWILIO_WHATSAPP_FROM,
                    "To": destinataire,
                    "Body": texte,
                },
            )
            response.raise_for_status()
            logger.info("Twilio: message envoyé à %s (boutique %s)", telephone_destinataire, boutique.nom)
            return True
    except httpx.TimeoutException:
        logger.error("Twilio: timeout envoi à %s (boutique %s)", telephone_destinataire, boutique.nom)
    except httpx.HTTPStatusError as exc:
        logger.error("Twilio: erreur HTTP %d à %s : %s", exc.response.status_code, telephone_destinataire, exc.response.text[:300])
    except Exception as exc:
        logger.exception("Twilio: erreur inattendue à %s : %s", telephone_destinataire, exc)
    return False


def envoyer_notification_commercant(boutique: Boutique, message: str) -> bool:
    """
    Envoie une notification au propriétaire via WhatsApp, avec fallback email.
    """
    wa_ok = False
    if boutique.proprietaire_tel:
        wa_ok = envoyer_message_texte(
            boutique=boutique,
            telephone_destinataire=boutique.proprietaire_tel,
            texte=message,
        )

    if not wa_ok:
        _notifier_par_email(boutique, message)

    return wa_ok


def _notifier_par_email(boutique: Boutique, message: str) -> None:
    """Envoie la notification par email si WhatsApp échoue ou n'est pas configuré."""
    try:
        email_dest = boutique.proprietaire.email if boutique.proprietaire else ""
        if not email_dest or not settings.EMAIL_HOST_USER:
            logger.warning("Email non configuré — notification non envoyée pour %s.", boutique.nom)
            return
        sujet = f"[{boutique.nom}] Nouvelle notification Fëgg Jaay"
        send_mail(sujet, message, settings.DEFAULT_FROM_EMAIL, [email_dest], fail_silently=True)
        logger.info("Email notification envoyé à %s (boutique %s).", email_dest, boutique.nom)
    except Exception as exc:
        logger.error("Erreur envoi email notification : %s", exc)


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


def notifier_paiement_recu(boutique: Boutique, commande) -> bool:
    """
    Notifie le commerçant qu'un client a fourni une référence de paiement.
    Le commerçant doit vérifier et confirmer dans le dashboard.
    """
    mode_label = dict(commande.MODE_PAIEMENT_CHOICES).get(commande.mode_paiement, commande.mode_paiement)
    message = (
        f"💰 *Paiement reçu !*\n\n"
        f"Commande : *{commande.numero_ref}*\n"
        f"Client : {commande.client.prenom or commande.client.telephone}\n"
        f"Montant : *{commande.montant_formate}*\n"
        f"Mode : {mode_label}\n"
        f"Réf transaction : *{commande.reference_paiement}*\n\n"
        f"✅ Confirmez sur votre dashboard."
    )
    return envoyer_notification_commercant(boutique, message)


def envoyer_otp(boutique: Boutique, telephone: str, code: str) -> bool:
    """
    Envoie un code OTP à 6 chiffres au client via WhatsApp.
    Utilisé pour l'authentification sur la vitrine web.
    """
    message = (
        f"🔐 *Votre code de connexion {boutique.nom}*\n\n"
        f"Code : *{code}*\n\n"
        f"Ce code expire dans 10 minutes. Ne le partagez pas."
    )
    return envoyer_message_texte(boutique=boutique, telephone_destinataire=telephone, texte=message)


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

