from django import template

register = template.Library()


@register.filter
def statut_label(t: dict, statut: str) -> str:
    """{{ t|statut_label:commande.statut }} — retourne le libellé traduit du statut."""
    return t.get(f"statut_{statut}", statut)
