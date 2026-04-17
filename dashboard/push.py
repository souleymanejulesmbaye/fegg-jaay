"""Utilitaire Web Push — envoie des notifications aux commerçants abonnés."""

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def envoyer_push_nouvelle_commande(boutique, commande):
    """Notifie tous les abonnements push actifs de la boutique d'une nouvelle commande."""
    from boutiques.models import PushSubscription

    subscriptions = PushSubscription.objects.filter(boutique=boutique)
    if not subscriptions.exists():
        return

    vapid_private = getattr(settings, "VAPID_PRIVATE_KEY", "")
    vapid_claims_email = getattr(settings, "VAPID_CLAIMS_EMAIL", "admin@feggjaay.com")
    vapid_public = getattr(settings, "VAPID_PUBLIC_KEY", "")

    if not vapid_private:
        logger.warning("VAPID_PRIVATE_KEY non configuré — push ignoré.")
        return

    payload = json.dumps({
        "title": f"🛒 Nouvelle commande — {boutique.nom}",
        "body": f"{commande.numero_ref} · {commande.montant_formate}",
        "url": f"/dashboard/commandes/{commande.pk}/",
        "tag": f"commande-{commande.pk}",
    })

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.warning("pywebpush non installé — push ignoré.")
        return

    stale_endpoints = []

    for sub in subscriptions:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh,
                "auth": sub.auth,
            },
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=vapid_private,
                vapid_claims={
                    "sub": f"mailto:{vapid_claims_email}",
                },
            )
        except WebPushException as e:
            status = getattr(e.response, "status_code", None) if e.response else None
            if status in (404, 410):
                stale_endpoints.append(sub.endpoint)
            else:
                logger.warning("Erreur push sub %s : %s", sub.pk, e)
        except Exception as e:
            logger.warning("Erreur push inattendue sub %s : %s", sub.pk, e)

    if stale_endpoints:
        PushSubscription.objects.filter(endpoint__in=stale_endpoints).delete()
        logger.info("Supprimé %d abonnements push périmés.", len(stale_endpoints))
