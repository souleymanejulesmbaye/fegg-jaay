"""
Webhook WhatsApp pour Fëgg Jaay.

Endpoints :
  GET  /wa/webhook/  → vérification du webhook (Meta challenge)
  POST /wa/webhook/  → réception des messages entrants (Twilio sandbox)

En mode DEBUG, le traitement est synchrone (pas besoin de Celery).
En production, délègue à Celery.
"""

import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook(request):
    if request.method == "GET":
        return _verifier_webhook(request)
    return _recevoir_message(request)


# ─── Vérification initiale du webhook (Meta/Twilio) ──────────────────────────

def _verifier_webhook(request):
    """
    Meta envoie un GET avec hub.mode=subscribe, hub.verify_token et hub.challenge.
    Twilio ne fait pas de vérification GET — on répond juste 200.
    """
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    if mode == "subscribe" and token == settings.WA_WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook WhatsApp vérifié avec succès.")
        return HttpResponse(challenge, content_type="text/plain", status=200)

    # Twilio — simple ping GET
    return HttpResponse("OK", status=200)


# ─── Réception des messages entrants (Twilio) ────────────────────────────────

def _recevoir_message(request):
    """
    Extrait le message depuis le POST Twilio (form data) et le traite.
    En DEBUG : traitement synchrone direct.
    En production : délègue à Celery.
    """
    # Twilio envoie du form data, pas du JSON
    from_number = request.POST.get("From", "")   # ex: "whatsapp:+221771234567"
    to_number = request.POST.get("To", "")       # ex: "whatsapp:+14155238886"
    body = request.POST.get("Body", "")
    message_sid = request.POST.get("MessageSid", "")
    num_media = int(request.POST.get("NumMedia", 0))

    if not from_number:
        logger.warning("Webhook reçu sans champ 'From' — ignoré.")
        return HttpResponse("OK", status=200)

    # Nettoyer les numéros (enlever "whatsapp:")
    client_tel = from_number.replace("whatsapp:", "").replace("+", "")
    boutique_tel = to_number.replace("whatsapp:", "")

    # Déterminer le type de message
    if num_media > 0:
        media_type = request.POST.get("MediaContentType0", "")
        if "audio" in media_type:
            type_msg = "audio"
            contenu = request.POST.get("MediaUrl0", "")
        elif "image" in media_type:
            type_msg = "image"
            contenu = request.POST.get("MediaUrl0", "")
        else:
            type_msg = "document"
            contenu = request.POST.get("MediaUrl0", "")
    else:
        type_msg = "text"
        contenu = body

    logger.info(
        "Message Twilio reçu — from=%s to=%s body=%s...",
        from_number, to_number, body[:50],
    )

    msg_data = {
        "boutique_telephone_wa": boutique_tel,
        "client_telephone": client_tel,
        "wa_message_id": message_sid,
        "type_message": type_msg,
        "contenu": contenu,
        "timestamp": "",
    }

    _traiter_message_sync(msg_data)

    # Twilio attend toujours un 200 rapide
    return HttpResponse("OK", status=200)


# ─── Traitement synchrone (mode DEBUG) ───────────────────────────────────────

def _traiter_message_sync(msg_data: dict):
    """
    Version synchrone de traiter_message_entrant pour le développement local.
    Évite d'avoir besoin de Celery/Redis pour tester.
    """
    from boutiques.models import Boutique, Client, MessageLog
    from .bot_engine import traiter_message
    from .sender import envoyer_message_texte, envoyer_message_bienvenue

    boutique_tel = msg_data.get("boutique_telephone_wa", "")
    client_tel = msg_data.get("client_telephone", "")
    wa_message_id = msg_data.get("wa_message_id", "")
    type_msg = msg_data.get("type_message", "text")
    contenu = msg_data.get("contenu", "")

    try:
        boutique = Boutique.objects.get(telephone_wa=boutique_tel, actif=True)
    except Boutique.DoesNotExist:
        # Sandbox Twilio : le To est toujours +14155238886, pas le numéro de la boutique.
        # On prend la première boutique active (sandbox mono-tenant).
        boutique = Boutique.objects.filter(actif=True).first()
        if not boutique:
            logger.warning("Aucune boutique active trouvée pour '%s'.", boutique_tel)
            return
        logger.info("Sandbox : boutique '%s' sélectionnée par défaut.", boutique.nom)

    # Déduplication
    if wa_message_id and MessageLog.objects.filter(wa_message_id=wa_message_id).exists():
        logger.info("Message %s déjà traité — ignoré.", wa_message_id)
        return

    client, created = Client.objects.get_or_create(
        boutique=boutique,
        telephone=client_tel,
        defaults={"langue_preferee": "fr"},
    )

    MessageLog.objects.create(
        boutique=boutique,
        telephone_client=client_tel,
        direction="entrant",
        contenu=contenu,
        type_message=type_msg,
        wa_message_id=wa_message_id,
    )

    if created:
        envoyer_message_bienvenue(boutique, client_tel)
        return

    reponse = traiter_message(
        boutique=boutique,
        client=client,
        message=contenu,
        type_message=type_msg,
    )

    MessageLog.objects.create(
        boutique=boutique,
        telephone_client=client_tel,
        direction="sortant",
        contenu=reponse,
        type_message="text",
    )

    envoyer_message_texte(boutique, client_tel, reponse)
    logger.info("Réponse envoyée à %s : %s...", client_tel, reponse[:80])
