"""
Routing intelligent pour numéro WhatsApp partagé Fëgg Jaay.
Détecte automatiquement la boutique ciblée dans les messages des clients.
"""

import logging
from django.db.models import Q
from boutiques.models import Boutique

logger = logging.getLogger(__name__)


def detecter_boutique_dans_message(message: str) -> Boutique:
    """
    Détecte automatiquement la boutique ciblée dans le message du client.
    
    Exemples de détection:
    - "salut salmon shop" → SALMON SHOP
    - "bonjour tash prestige" → TASH PRESTIGE
    - "catalogue teranga" → TERANGA SHOP
    - "je veux commander chez tash" → TASH PRESTIGE
    - "salmon shop prix" → SALMON SHOP
    
    Args:
        message: Message du client (texte brut)
        
    Returns:
        Boutique: La boutique détectée ou None si aucune correspondance
    """
    message_lower = message.lower().strip()
    
    # Dictionnaire de mots-clés par boutique
    keywords_boutique = {
        'salmon': {
            'keywords': ['salmon', 'salmon shop'],
            'boutique_nom': 'SALMON SHOP'
        },
        'tash': {
            'keywords': ['tash', 'tash prestige', 'tash prestige 2'],
            'boutique_nom': 'TASH PRESTIGE'  # Par défaut, route vers TASH PRESTIGE principal
        },
        'teranga': {
            'keywords': ['teranga', 'teranga shop'],
            'boutique_nom': 'TERANGA SHOP'
        }
    }
    
    # Rechercher les mots-clés dans le message
    for cle, config in keywords_boutique.items():
        for keyword in config['keywords']:
            if keyword in message_lower:
                try:
                    # Trouver la boutique correspondante
                    boutique = Boutique.objects.filter(
                        Q(nom__icontains=config['boutique_nom']) |
                        Q(nom__icontains=cle.upper()),
                        actif=True
                    ).first()
                    
                    if boutique:
                        logger.info(
                            "🎯 Routing détecté: '%s' → boutique %s (keyword: %s)",
                            message[:40], boutique.nom, keyword
                        )
                        return boutique
                        
                except Exception as e:
                    logger.error(
                        "❌ Erreur routing boutique %s: %s",
                        config['boutique_nom'], e
                    )
    
    # Si aucune boutique détectée, retourner None pour traitement normal
    logger.debug(
        "🤷 Aucune boutique détectée dans: '%s'",
        message[:40]
    )
    return None


def get_instructions_routing():
    """
    Retourne les instructions de routing pour les clients.
    """
    instructions = [
        "📱 Envoyez 'salut salmon shop' pour SALMON SHOP",
        "📱 Envoyez 'bonjour tash prestige' pour TASH PRESTIGE", 
        "📱 Envoyez 'catalogue teranga' pour TERANGA SHOP",
        "📱 Ou simplement 'salut' pour le service général"
    ]
    
    return instructions


def get_boutiques_actives():
    """
    Retourne la liste des boutiques actives pour le routing.
    """
    return Boutique.objects.filter(actif=True).order_by('nom')


def test_routing_message(message: str) -> dict:
    """
    Teste le routing pour un message donné.
    
    Args:
        message: Message à tester
        
    Returns:
        dict: Résultat du test avec boutique détectée
    """
    boutique = detecter_boutique_dans_message(message)
    
    return {
        'message': message,
        'boutique_detectee': boutique.nom if boutique else None,
        'boutique_id': boutique.id if boutique else None,
        'success': boutique is not None
    }
