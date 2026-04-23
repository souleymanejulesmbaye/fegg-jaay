"""
Routing intelligent pour numéro WhatsApp partagé économique.
Permet à plusieurs commerçants d'utiliser un seul numéro avec détection automatique.
"""

import logging
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from boutiques.models import Boutique

logger = logging.getLogger(__name__)


def routing_par_message(message: str, telephone_client: str) -> Boutique:
    """
    Détecte automatiquement la boutique ciblée dans le message du client.
    
    Exemples:
    - "salut salmon shop" → SALMON SHOP
    - "bonjour tash prestige" → TASH PRESTIGE
    - "catalogue teranga" → TERANGA SHOP
    """
    message_lower = message.lower()
    
    # Mots-clés par boutique (configurable)
    keywords_boutique = {
        'salmon': ['salmon', 'salmon shop'],
        'tash': ['tash', 'tash prestige', 'tash prestige 2'],
        'teranga': ['teranga', 'teranga shop'],
    }
    
    # Rechercher les mots-clés dans le message
    for boutique_nom, keywords in keywords_boutique.items():
        for keyword in keywords:
            if keyword in message_lower:
                try:
                    # Trouver la boutique correspondante
                    boutique = Boutique.objects.filter(
                        nom__icontains=boutique_nom,
                        actif=True
                    ).first()
                    if boutique:
                        logger.info(
                            "Routing automatique: message '%s' → boutique %s",
                            message[:50], boutique.nom
                        )
                        return boutique
                except Exception as e:
                    logger.error("Erreur routing boutique %s: %s", boutique_nom, e)
    
    # Si aucune boutique détectée, utiliser la boutique par défaut
    boutique_defaut = Boutique.objects.filter(
        actif=True
    ).order_by('created_at').first()
    
    if boutique_defaut:
        logger.info(
            "Routing par défaut: message '%s' → boutique %s",
            message[:50], boutique_defaut.nom
        )
    
    return boutique_defaut


@require_http_methods(["GET", "POST"])
def page_accueil_partagee(request):
    """
    Page d'accueil pour le numéro WhatsApp partagé.
    Explique aux clients comment utiliser le service.
    """
    if request.method == "POST":
        message = request.POST.get('message', '')
        telephone = request.POST.get('telephone', '')
        
        if message and telephone:
            boutique = routing_par_message(message, telephone)
            
            return JsonResponse({
                'success': True,
                'boutique': boutique.nom if boutique else 'Non trouvée',
                'message': f"Votre message sera traité par {boutique.nom if boutique else 'notre service'}"
            })
    
    # Liste des boutiques actives
    boutiques = Boutique.objects.filter(actif=True).order_by('nom')
    
    return render(request, 'dashboard/accueil_partagee.html', {
        'boutiques': boutiques,
        'instructions': [
            "Envoyez: 'salut salmon shop' pour SALMON SHOP",
            "Envoyez: 'bonjour tash prestige' pour TASH PRESTIGE", 
            "Envoyez: 'catalogue teranga' pour TERANGA SHOP",
            "Ou simplement 'salut' pour le service général"
        ]
    })


def get_routing_stats():
    """Statistiques de routing pour monitoring."""
    stats = {
        'total_boutiques': Boutique.objects.filter(actif=True).count(),
        'messages_today': 0,  # À implémenter avec MessageLog
        'routing_success_rate': 95.2,  # À calculer
    }
    return stats
