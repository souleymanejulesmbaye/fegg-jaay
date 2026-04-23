"""
Webhook WhatsApp pour Fëgg Jaay.

Endpoints :
  GET  /wa/webhook/  → vérification du webhook (Meta challenge)
  POST /wa/webhook/  → réception des messages entrants (Meta API ou Twilio sandbox)

Détection automatique du provider :
  - Meta API  : Content-Type application/json, champ "object" dans le body
  - Twilio    : form data avec champ "From"
"""

import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .routing_intelligent import detecter_boutique_dans_message
from .bot_intelligent_bilingue import traiter_message_intelligent
from .paiement_mobile import traiter_demande_paiement, confirmer_paiement_client

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook(request):
    if request.method == "GET":
        return _verifier_webhook(request)
    return _recevoir_message(request)


# ─── Vérification initiale du webhook (Meta) ─────────────────────────────────

def _verifier_webhook(request):
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    if mode == "subscribe" and token == getattr(settings, "WA_WEBHOOK_VERIFY_TOKEN", ""):
        logger.info("Webhook Meta vérifié avec succès.")
        return HttpResponse(challenge, content_type="text/plain", status=200)

    return HttpResponse("OK", status=200)


# ─── Réception des messages entrants ─────────────────────────────────────────

def _recevoir_message(request):
    content_type = request.content_type or ""

    if "application/json" in content_type:
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse("Bad Request", status=400)

        if payload.get("object") == "whatsapp_business_account":
            return _recevoir_meta(payload)

    # Twilio : form data
    return _recevoir_twilio(request)


# ─── Provider Meta ────────────────────────────────────────────────────────────

def _recevoir_meta(payload: dict):
    """Traite les messages entrants depuis Meta WhatsApp Business API."""
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                if not messages:
                    continue

                phone_number_id = value.get("metadata", {}).get("phone_number_id", "")
                msg = messages[0]
                from_number = msg.get("from", "")
                wa_message_id = msg.get("id", "")
                msg_type = msg.get("type", "text")

                if msg_type == "text":
                    contenu = msg.get("text", {}).get("body", "")
                elif msg_type == "audio":
                    contenu = msg.get("audio", {}).get("id", "")
                elif msg_type == "image":
                    contenu = msg.get("image", {}).get("id", "")
                else:
                    contenu = ""

                logger.info(
                    "Message Meta reçu — phone_number_id=%s from=%s body=%s...",
                    phone_number_id, from_number, contenu[:50],
                )

                msg_data = {
                    "provider": "meta",
                    "phone_number_id": phone_number_id,
                    "client_telephone": from_number,
                    "wa_message_id": wa_message_id,
                    "type_message": msg_type,
                    "contenu": contenu,
                }
                _traiter_message_sync(msg_data)

    except Exception as exc:
        logger.exception("Erreur traitement webhook Meta : %s", exc)

    return HttpResponse("OK", status=200)


# ─── Provider Twilio ──────────────────────────────────────────────────────────

def _recevoir_twilio(request):
    """Traite les messages entrants depuis Twilio WhatsApp Sandbox."""
    from_number = request.POST.get("From", "")
    to_number = request.POST.get("To", "")
    body = request.POST.get("Body", "")
    message_sid = request.POST.get("MessageSid", "")
    num_media = int(request.POST.get("NumMedia", 0))

    if not from_number:
        logger.warning("Webhook Twilio reçu sans champ 'From' — ignoré.")
        return HttpResponse("OK", status=200)

    client_tel = from_number.replace("whatsapp:", "").replace("+", "")
    boutique_tel = to_number.replace("whatsapp:", "")

    if num_media > 0:
        media_type = request.POST.get("MediaContentType0", "")
        type_msg = "audio" if "audio" in media_type else ("image" if "image" in media_type else "document")
        contenu = request.POST.get("MediaUrl0", "")
    else:
        type_msg = "text"
        contenu = body

    logger.info(
        "Message Twilio reçu — from=%s to=%s body=%s...",
        from_number, to_number, body[:50],
    )

    msg_data = {
        "provider": "twilio",
        "boutique_telephone_wa": boutique_tel,
        "client_telephone": client_tel,
        "wa_message_id": message_sid,
        "type_message": type_msg,
        "contenu": contenu,
    }
    _traiter_message_sync(msg_data)
    return HttpResponse("OK", status=200)


# ─── Traitement commun ────────────────────────────────────────────────────────

def _traiter_message_sync(msg_data: dict):
    from boutiques.models import Boutique, Client, MessageLog
    from .bot_engine import traiter_message
    from .sender import envoyer_message_texte, envoyer_message_bienvenue

    provider = msg_data.get("provider", "twilio")
    client_tel = msg_data.get("client_telephone", "")
    wa_message_id = msg_data.get("wa_message_id", "")
    type_msg = msg_data.get("type_message", "text")
    contenu = msg_data.get("contenu", "")

    # ── Trouver la boutique ───────────────────────────────────────────────
    if provider == "meta":
        phone_number_id = msg_data.get("phone_number_id", "")
        try:
            boutique = Boutique.objects.get(wa_phone_id=phone_number_id, actif=True)
        except Boutique.DoesNotExist:
            logger.warning("Boutique introuvable pour phone_number_id='%s'.", phone_number_id)
            return
    else:
        # Twilio sandbox : To = +14155238886, pas le numéro de la boutique
        boutique_tel = msg_data.get("boutique_telephone_wa", "")
        try:
            boutique = Boutique.objects.get(telephone_wa=boutique_tel, actif=True)
        except Boutique.DoesNotExist:
            boutique = Boutique.objects.filter(actif=True).first()
            if not boutique:
                logger.warning("Aucune boutique active trouvée pour '%s'.", boutique_tel)
                return
            logger.info("Sandbox : boutique '%s' sélectionnée par défaut.", boutique.nom)

    # ── Déduplication ────────────────────────────────────────────────────
    if wa_message_id and MessageLog.objects.filter(wa_message_id=wa_message_id).exists():
        logger.info("Message %s déjà traité — ignoré.", wa_message_id)
        return

    # ── Routing commerçant — dashboard WhatsApp ──────────────────────────
    if boutique.proprietaire_tel:
        tel_norm = client_tel.lstrip("+")
        prop_norm = boutique.proprietaire_tel.lstrip("+")
        if tel_norm == prop_norm:
            from .dashboard_wa import traiter_message_commercant
            reponse = traiter_message_commercant(boutique, contenu)
            envoyer_message_texte(boutique, client_tel, reponse)
            logger.info("Dashboard commerçant — boutique=%s msg=%s...", boutique.nom, contenu[:40])
            return

    # ── Bot intelligent bilingue pour numéro 221767600283 (Twilio Sandbox) ───────
    if boutique.telephone_wa == "221767600283":
        # Bot intelligent bilingue - détection automatique et réponse intelligente
        boutique_ciblee, reponse_intelligente = traiter_message_intelligent(contenu)
        
        # Vérifier si c'est une demande de paiement
        if any(mot in contenu.lower() for mot in ['payer', 'paiement', 'wave', 'orange money', 'om']):
            logger.info(f"💳 Demande de paiement détectée: {contenu[:30]}...")
            
            # Créer/trouver le client
            langue = "wolof" if any(mot in contenu.lower() for mot in ["maa", "dama", "nga", "salam", "jang"]) else "fr"
            client, created = Client.objects.get_or_create(
                boutique=boutique,
                telephone=client_tel,
                defaults={"langue_preferee": langue},
            )
            
            # Traiter la demande de paiement
            instructions_paiement = traiter_demande_paiement(contenu, boutique, client_tel, 10000)  # Montant par défaut
            if instructions_paiement:
                envoyer_message_texte(boutique, client_tel, instructions_paiement)
                return
        
        # Vérifier si c'est une confirmation de paiement
        if any(mot in contenu.lower() for mot in ['paiement envoyé', 'envoyé', 'confirmé', 'bayi']):
            logger.info(f"✅ Confirmation de paiement détectée: {contenu[:30]}...")
            
            # Créer/trouver le client
            langue = "wolof" if any(mot in contenu.lower() for mot in ["maa", "dama", "nga", "salam", "jang"]) else "fr"
            client, created = Client.objects.get_or_create(
                boutique=boutique,
                telephone=client_tel,
                defaults={"langue_preferee": langue},
            )
            
            # Confirmer le paiement
            confirmation = confirmer_paiement_client(contenu, boutique, client_tel)
            if confirmation:
                envoyer_message_texte(boutique, client_tel, confirmation)
                return
        
        if boutique_ciblee and boutique_ciblee.id != boutique.id:
            # Router vers la boutique détectée avec réponse intelligente
            from .bot_engine import traiter_message_client
            logger.info(
                "🤖 Bot intelligent: %s → %s (message: %s...)",
                boutique.nom, boutique_ciblee.nom, contenu[:30]
            )
            
            # Créer/trouver le client pour la boutique cible
            langue = "wolof" if any(mot in contenu.lower() for mot in ["maa", "dama", "nga", "salam", "jang"]) else "fr"
            client, created = Client.objects.get_or_create(
                boutique=boutique_ciblee,
                telephone=client_tel,
                defaults={"langue_preferee": langue},
            )
            
            # Envoyer la réponse intelligente immédiatement
            if reponse_intelligente:
                envoyer_message_texte(boutique_ciblee, client_tel, reponse_intelligente)
            
            # Traiter le message avec la boutique cible pour plus de détails
            reponse_detaillee = traiter_message_client(boutique_ciblee, client, contenu, type_msg, wa_message_id)
            
            # Envoyer la réponse détaillée si différente de la réponse intelligente
            if reponse_detaillee and reponse_detaillee != reponse_intelligente:
                envoyer_message_texte(boutique_ciblee, client_tel, reponse_detaillee)
            return
        
        elif reponse_intelligente:
            # Envoyer la réponse intelligente même si aucune boutique spécifique détectée
            logger.info(
                "🤖 Bot intelligent: réponse générale pour %s (message: %s...)",
                client_tel, contenu[:30]
            )
            envoyer_message_texte(boutique, client_tel, reponse_intelligente)
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
