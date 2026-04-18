"""
Webhook de déploiement automatique.
GitHub appelle POST /deploy/webhook/ → le VPS tire les changements et redémarre.

À ajouter dans urls.py :
    path("deploy/", include("deploy_webhook")),  # non — c'est un module standalone

Inclus directement dans fegg_jaay/urls.py via une vue simple.
"""

import hashlib
import hmac
import logging
import subprocess

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

DEPLOY_SECRET = getattr(settings, "GITHUB_DEPLOY_SECRET", "")


def _verifier_signature(request) -> bool:
    if not DEPLOY_SECRET:
        return True  # pas de secret configuré → accepter (à sécuriser en prod)
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
        return HttpResponse("Forbidden", status=403)

    event = request.headers.get("X-GitHub-Event", "")
    if event != "push":
        return HttpResponse("OK", status=200)

    logger.info("Webhook déploiement : push reçu — lancement du déploiement.")

    try:
        result = subprocess.run(
            ["/app/deploy.sh"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            logger.info("Déploiement réussi :\n%s", result.stdout[-500:])
            return HttpResponse("Deployed", status=200)
        else:
            logger.error("Déploiement échoué :\n%s\n%s", result.stdout[-500:], result.stderr[-500:])
            return HttpResponse("Deploy failed", status=500)
    except subprocess.TimeoutExpired:
        logger.error("Webhook déploiement : timeout après 120s.")
        return HttpResponse("Timeout", status=500)
    except Exception as exc:
        logger.exception("Webhook déploiement : erreur inattendue : %s", exc)
        return HttpResponse("Error", status=500)
