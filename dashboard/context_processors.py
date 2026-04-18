from django.conf import settings


def vapid_public_key(request):
    return {"VAPID_PUBLIC_KEY": getattr(settings, "VAPID_PUBLIC_KEY", "")}


def multi_boutique(request):
    """Injecte les boutiques du commerçant et la boutique active dans tous les templates."""
    if not request.user.is_authenticated:
        return {}
    from boutiques.models import Boutique
    mes_boutiques = list(Boutique.objects.filter(proprietaire=request.user).order_by("nom"))
    boutique_active_id = request.session.get("boutique_active_id")
    boutique_active = None
    if boutique_active_id:
        boutique_active = next((b for b in mes_boutiques if str(b.pk) == boutique_active_id), None)
    if not boutique_active and mes_boutiques:
        boutique_active = mes_boutiques[0]
    return {
        "mes_boutiques": mes_boutiques,
        "boutique_active": boutique_active,
    }
