"""
Webhook WhatsApp pour Fëgg Jaay.

Endpoints :
  GET  /wa/webhook/  → vérification du webhook (Meta challenge)
  POST /wa/webhook/  → réception des messages entrants

Le POST valide la signature HMAC-SHA256, puis délègue le traitement
à Celery pour rester sous les 15 secondes exigées par Meta.
"""

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .tasks import traiter_message_entrant

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook(request):
    if request.method == "GET":
        return _verifier_webhook(request)
    return _recevoir_message(request)


# ─── Vérification initiale du webhook (Meta) ──────────────────────────────────

def _verifier_webhook(request):
    """
    Meta envoie un GET avec hub.mode=subscribe, hub.verify_token et hub.challenge.
    On répond avec hub.challenge si le token correspond.
    """
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    if mode == "subscribe" and token == settings.WA_WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook WhatsApp vérifié avec succès.")
        return HttpResponse(challenge, content_type="text/plain", status=200)

    logger.warning("Échec vérification webhook : token invalide.")
    return HttpResponse("Token invalide", status=403)


# ─── Réception des messages entrants ─────────────────────────────────────────

def _recevoir_message(request):
    """
    Valide la signature HMAC-SHA256, extrait le message et délègue à Celery.
    Retourne toujours 200 rapidement pour éviter les relances Meta.
    """
    # 1. Validation signature
    if not _signature_valide(request):
        logger.warning("Signature HMAC invalide — message rejeté.")
        return HttpResponse("Signature invalide", status=403)

    # 2. Parsing JSON
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error("Payload JSON invalide reçu sur le webhook.")
        return HttpResponse("JSON invalide", status=400)

    logger.debug("Payload webhook reçu : %s", json.dumps(payload)[:500])

    # 3. Extraire les messages de la structure Meta
    try:
        messages = _extraire_messages(payload)
    except Exception as exc:
        logger.error("Erreur lors de l'extraction des messages : %s", exc)
        return JsonResponse({"status": "ok"}, status=200)

    # 4. Déléguer chaque message à Celery (async, non bloquant)
    for msg_data in messages:
        traiter_message_entrant.delay(msg_data)
        logger.info(
            "Message traité — boutique_tel=%s client=%s",
            msg_data.get("boutique_telephone_wa"),
            msg_data.get("client_telephone"),
        )

    return JsonResponse({"status": "ok"}, status=200)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _signature_valide(request) -> bool:
    """
    Vérifie la signature X-Hub-Signature-256 envoyée par Meta.
    En développement (DEBUG=True et pas de secret configuré), on laisse passer.
    """
    # En développement, on bypasse la vérification de signature
    if settings.DEBUG:
        logger.debug("Mode DEBUG — vérification signature HMAC ignorée.")
        return True

    app_secret = settings.WA_APP_SECRET
    if not app_secret:
        return False

    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header.startswith("sha256="):
        return False

    signature_recue = signature_header[7:]  # retire "sha256="
    signature_calculee = hmac.new(
        app_secret.encode("utf-8"),
        msg=request.body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature_calculee, signature_recue)


def _extraire_messages(payload: dict) -> list[dict]:
    """
    Extrait les messages utiles de la structure de payload Meta/360dialog.

    Retourne une liste de dicts avec les champs nécessaires à Celery :
    {
        "boutique_telephone_wa": str,   # le numéro WhatsApp de la boutique
        "client_telephone": str,        # le numéro du client
        "wa_message_id": str,
        "type_message": str,            # text / audio / image / document
        "contenu": str,                 # texte ou media_id
        "timestamp": str,
    }
    """
    messages_extraits = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # Numéro de téléphone de la boutique (metadata)
            boutique_tel = value.get("metadata", {}).get("display_phone_number", "")

            for msg in value.get("messages", []):
                type_msg = msg.get("type", "text")

                # Extraction du contenu selon le type
                contenu = ""
                if type_msg == "text":
                    contenu = msg.get("text", {}).get("body", "")
                elif type_msg == "audio":
                    contenu = msg.get("audio", {}).get("id", "")  # media_id
                elif type_msg == "image":
                    contenu = msg.get("image", {}).get("id", "")
                elif type_msg == "document":
                    contenu = msg.get("document", {}).get("id", "")

                messages_extraits.append({
                    "boutique_telephone_wa": boutique_tel,
                    "client_telephone": msg.get("from", ""),
                    "wa_message_id": msg.get("id", ""),
                    "type_message": type_msg,
                    "contenu": contenu,
                    "timestamp": msg.get("timestamp", ""),
                })

    return messages_extraits
