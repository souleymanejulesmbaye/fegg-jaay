"""
Tâches Celery pour Fëgg Jaay.

Tâches :
  - traiter_message_entrant   → traitement IA d'un message WhatsApp reçu
  - envoyer_rapport_quotidien → rapport 20h pour tous les commerçants actifs
  - verifier_alertes_stock    → alerte commerçant si stock < seuil
  - relancer_commandes        → relance les commandes en attente de paiement > 2h
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─── Traitement d'un message entrant ─────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="whatsapp.traiter_message_entrant",
)
def traiter_message_entrant(self, msg_data: dict):
    """
    Tâche principale : traite un message WhatsApp reçu.

    msg_data keys:
        boutique_telephone_wa, client_telephone, wa_message_id,
        type_message, contenu, timestamp
    """
    from boutiques.models import Boutique, Client, MessageLog
    from .bot_engine import traiter_message
    from .sender import envoyer_message_texte, notifier_nouvelle_commande, notifier_alerte_stock

    boutique_tel = msg_data.get("boutique_telephone_wa", "")
    client_tel = msg_data.get("client_telephone", "")
    wa_message_id = msg_data.get("wa_message_id", "")
    type_msg = msg_data.get("type_message", "texte")
    contenu = msg_data.get("contenu", "")

    try:
        # 1. Récupérer la boutique par son numéro WhatsApp
        boutique = Boutique.objects.get(telephone_wa=boutique_tel, actif=True)
    except Boutique.DoesNotExist:
        logger.warning("Boutique introuvable pour le numéro %s", boutique_tel)
        return

    # 2. Vérifier la déduplication (même message_id déjà traité ?)
    if wa_message_id and MessageLog.objects.filter(wa_message_id=wa_message_id).exists():
        logger.info("Message %s déjà traité — ignoré.", wa_message_id)
        return

    try:
        # 3. Récupérer ou créer le client
        client, created = Client.objects.get_or_create(
            boutique=boutique,
            telephone=client_tel,
            defaults={"langue_preferee": "fr"},
        )

        # 4. Logger le message entrant
        MessageLog.objects.create(
            boutique=boutique,
            telephone_client=client_tel,
            direction="entrant",
            contenu=contenu,
            type_message=type_msg,
            wa_message_id=wa_message_id,
        )

        # 5. Message bienvenue pour les nouveaux clients
        if created:
            from .sender import envoyer_message_bienvenue
            envoyer_message_bienvenue(boutique, client_tel)
            return

        # 6. Transcription audio si nécessaire
        texte_traite = contenu
        if type_msg == "audio" and contenu:
            texte_traite = _transcrire_audio(contenu, boutique) or "(message vocal non transcrit)"

        # 7. Appel au moteur IA
        reponse = traiter_message(
            boutique=boutique,
            client=client,
            message=texte_traite,
            type_message=type_msg,
        )

        # 8. Logger la réponse sortante (toujours, même si l'envoi échoue)
        MessageLog.objects.create(
            boutique=boutique,
            telephone_client=client_tel,
            direction="sortant",
            contenu=reponse,
            type_message="texte",
        )

        # 9. Envoyer la réponse au client via WhatsApp
        envoye = envoyer_message_texte(boutique, client_tel, reponse)
        if not envoye:
            logger.warning(
                "Envoi WhatsApp échoué (boutique=%s, client=%s) — wa_token configuré ?",
                boutique.nom, client_tel,
            )

        # 10. Vérifier alertes stock après chaque commande
        _verifier_et_alerter_stock(boutique)

    except Exception as exc:
        logger.exception(
            "Erreur dans traiter_message_entrant (boutique=%s, client=%s) : %s",
            boutique_tel,
            client_tel,
            exc,
        )
        # Retry automatique (max 3 fois)
        raise self.retry(exc=exc)


# ─── Rapport quotidien 20h ────────────────────────────────────────────────────

@shared_task(name="whatsapp.envoyer_rapport_quotidien")
def envoyer_rapport_quotidien():
    """
    Envoie un rapport de ventes du jour à chaque commerçant actif.
    Planifié via Celery Beat à 20h Africa/Dakar.
    """
    from boutiques.models import Boutique, Commande
    from .sender import envoyer_notification_commercant

    maintenant = timezone.now()
    debut_journee = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)

    boutiques = Boutique.objects.filter(actif=True)
    logger.info("Envoi du rapport quotidien pour %d boutiques.", boutiques.count())

    for boutique in boutiques:
        commandes_jour = Commande.objects.filter(
            boutique=boutique,
            created_at__gte=debut_journee,
        )

        nb_commandes = commandes_jour.count()
        nb_payees = commandes_jour.filter(statut__in=["payee", "en_preparation", "livree"]).count()
        chiffre_affaires = sum(
            c.montant_total
            for c in commandes_jour.filter(statut__in=["payee", "en_preparation", "livree"])
        )

        if nb_commandes == 0:
            message = (
                f"📊 *Rapport du {maintenant:%d/%m/%Y}*\n\n"
                f"Pas de commandes aujourd'hui. Bonne soirée !"
            )
        else:
            ca_formate = f"{chiffre_affaires:,} FCFA".replace(",", " ")
            message = (
                f"📊 *Rapport du {maintenant:%d/%m/%Y}*\n\n"
                f"Commandes reçues : *{nb_commandes}*\n"
                f"Commandes payées : *{nb_payees}*\n"
                f"Chiffre d'affaires : *{ca_formate}*\n\n"
                f"Consultez votre dashboard pour les détails."
            )

        envoyer_notification_commercant(boutique, message)
        logger.info("Rapport envoyé à %s.", boutique.nom)


# ─── Vérification alertes stock ────────────────────────────────────────────────

@shared_task(name="whatsapp.verifier_alertes_stock")
def verifier_alertes_stock():
    """
    Vérifie le stock de tous les produits actifs.
    Notifie le commerçant si un produit est sous le seuil d'alerte.
    Planifié via Celery Beat toutes les heures.
    """
    from boutiques.models import Boutique, Produit
    from .sender import notifier_alerte_stock

    boutiques = Boutique.objects.filter(actif=True)
    for boutique in boutiques:
        _verifier_et_alerter_stock(boutique)


def _verifier_et_alerter_stock(boutique):
    """Helper : vérifie et alerte pour une boutique spécifique."""
    from boutiques.models import Produit
    from .sender import notifier_alerte_stock

    for produit in Produit.objects.filter(boutique=boutique, actif=True):
        if produit.stock <= produit.stock_alerte:
            notifier_alerte_stock(boutique, produit)
            logger.info(
                "Alerte stock envoyée : %s (%d unités) — boutique %s",
                produit.nom,
                produit.stock,
                boutique.nom,
            )


# ─── Relance commandes en attente ─────────────────────────────────────────────

@shared_task(name="whatsapp.relancer_commandes")
def relancer_commandes():
    """
    Relance les clients dont la commande est en attente de paiement
    depuis plus de 2 heures.
    Planifié via Celery Beat toutes les 2 heures.
    """
    from boutiques.models import Commande
    from .sender import envoyer_message_texte

    seuil = timezone.now() - timedelta(hours=2)
    commandes = Commande.objects.filter(
        statut="attente_paiement",
        created_at__lt=seuil,
        created_at__gte=timezone.now() - timedelta(hours=24),  # pas plus de 24h
    ).select_related("boutique", "client")

    logger.info("%d commande(s) à relancer.", commandes.count())

    for commande in commandes:
        client = commande.client
        langue = client.langue_preferee

        if langue == "wo":
            message = (
                f"Waaw, commande *{commande.numero_ref}* bi tax-taxal yoor ⏳\n"
                f"Total : *{commande.montant_formate}*\n"
                f"Jox ñu xaalis bi bu kanam."
            )
        else:
            message = (
                f"Rappel : votre commande *{commande.numero_ref}* "
                f"est toujours en attente de paiement ⏳\n"
                f"Total : *{commande.montant_formate}*\n"
                f"Envoyez votre preuve de paiement pour confirmer."
            )

        envoyer_message_texte(commande.boutique, client.telephone, message)
        logger.info("Relance envoyée pour commande %s.", commande.numero_ref)


# ─── Transcription audio (Whisper) ────────────────────────────────────────────

def _transcrire_audio(media_id: str, boutique) -> str | None:
    """
    Télécharge le fichier audio depuis WhatsApp et le transcrit via OpenAI Whisper.
    Retourne le texte transcrit ou None en cas d'échec.
    """
    import httpx
    from django.conf import settings

    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY non configuré — transcription audio désactivée.")
        return None

    try:
        # 1. Récupérer l'URL du fichier média depuis 360dialog
        url_media_info = f"https://waba.360dialog.io/v1/media/{media_id}"
        headers = {"D360-API-KEY": boutique.wa_token}

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url_media_info, headers=headers)
            resp.raise_for_status()
            media_url = resp.json().get("url", "")

            if not media_url:
                return None

            # 2. Télécharger le fichier audio
            audio_resp = client.get(media_url, headers=headers)
            audio_resp.raise_for_status()
            audio_bytes = audio_resp.content

        # 3. Transcrire via OpenAI Whisper
        from openai import OpenAI
        openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.ogg", audio_bytes, "audio/ogg"),
        )
        logger.info("Transcription audio réussie : %s...", transcript.text[:50])
        return transcript.text

    except Exception as exc:
        logger.error("Erreur transcription audio (media_id=%s) : %s", media_id, exc)
        return None
