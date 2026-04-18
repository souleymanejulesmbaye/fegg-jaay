"""
Webhook de déploiement automatique — signal seulement.
Le vrai déploiement est déclenché par GitHub Actions via SSH.
Cet endpoint sert uniquement à valider que le serveur reçoit bien les push GitHub.
"""

import hashlib
import hmac
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

DEPLOY_SECRET = getattr(settings, "GITHUB_DEPLOY_SECRET", "")


def _verifier_signature(request) -> bool:
    if not DEPLOY_SECRET:
        return True
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not signature.startswith("sha256="):
        return False
    mac = hmac.new(DEPLOY_SECRET.encode(), request.body, hashlib.sha256)
    expected = "sha256=" + mac.hexdigest()
    return hmac.compare_digest(signature, expected)


@csrf_exempt
@require_POST
def deploy_webhook(request):
    if not _verifier_signature(request):
        logger.warning("Webhook déploiement : signature invalide.")
        return JsonResponse({"error": "forbidden"}, status=403)

    event = request.headers.get("X-GitHub-Event", "")
    logger.info("GitHub webhook reçu — event: %s", event)
    return JsonResponse({"ok": True, "event": event})
