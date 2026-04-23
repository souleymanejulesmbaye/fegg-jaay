"""
Bot intelligent bilingue Français/Wolof pour Fëgg Jaay.
Comprend les mots-clés ET les phrases complètes dans les deux langues.
"""

import re
import logging
from typing import Dict, Optional, Tuple
from django.db.models import Q
from boutiques.models import Boutique

logger = logging.getLogger(__name__)


class BotIntelligentBilingue:
    """Bot intelligent qui comprend le français et le wolof."""
    
    def __init__(self):
        self.keywords_francais = {
            'salmon': {
                'mots': ['salmon', 'salmon shop', 'boutique salmon'],
                'phrases': [
                    r'je veux.*salmon',
                    r'commander.*salmon',
                    r'catalogue.*salmon',
                    r'prix.*salmon',
                    r'vêtements.*salmon'
                ]
            },
            'tash': {
                'mots': ['tash', 'tash prestige', 'tash prestige 2'],
                'phrases': [
                    r'je veux.*tash',
                    r'commander.*tash',
                    r'catalogue.*tash',
                    r'prix.*tash',
                    r'habits.*tash',
                    r'mode.*tash'
                ]
            },
            'teranga': {
                'mots': ['teranga', 'teranga shop'],
                'phrases': [
                    r'je veux.*teranga',
                    r'commander.*teranga',
                    r'catalogue.*teranga',
                    r'prix.*teranga',
                    r'produits.*teranga'
                ]
            }
        }
        
        self.keywords_wolof = {
            'salmon': {
                'mots': ['salmon', 'salmon shop'],
                'phrases': [
                    r'maa.*salmon',
                    r'dama.*salmon',
                    r'jang.*salmon',
                    r'prix.*salmon',
                    r'mbay.*salmon'
                ]
            },
            'tash': {
                'mots': ['tash', 'tash prestige'],
                'phrases': [
                    r'maa.*tash',
                    r'dama.*tash',
                    r'jang.*tash',
                    r'prix.*tash',
                    r'wëral.*tash'
                ]
            },
            'teranga': {
                'mots': ['teranga', 'teranga shop'],
                'phrases': [
                    r'maa.*teranga',
                    r'dama.*teranga',
                    r'jang.*teranga',
                    r'prix.*teranga',
                    r'japp.*teranga'
                ]
            }
        }
        
        # Intentions communes bilingues
        self.intentions = {
            'commande': {
                'fr': [r'commander', r'acheter', r'veux', r'merci', r'prendre', r'réserver'],
                'wo': [r'mbay', r'maa', r'dama', r'jangu', r'ñu', r'japp']
            },
            'catalogue': {
                'fr': [r'catalogue', r'voir', r'montrer', r'liste', r'disponible'],
                'wo': [r'jang', r'wone', r'list', r'disponible', r'lu']
            },
            'prix': {
                'fr': [r'prix', r'coût', r'combien', r'cher', r'argent'],
                'wo': [r'prix', r'xool', r'jombon', r'wër', r'argent']
            },
            'paiement': {
                'fr': [r'payer', r'paiement', r'confirmer', r'envoyé', r'wave', r'orange money', r'om'],
                'wo': [r'payer', r'confirme', r'envoyé', r'bayi', r'wave', r'orange money']
            },
            'salutation': {
                'fr': [r'salut', r'bonjour', r'bonsoir', r'coucou', r'yo'],
                'wo': [r'salam', r'nga', r'nga', r'asalam', r'yo']
            }
        }
    
    def detecter_langue(self, message: str) -> str:
        """Détecte si le message est en français ou en wolof."""
        message_lower = message.lower()
        
        # Mots-clés wolof spécifiques
        mots_wolof = ['maa', 'dama', 'nga', 'salam', 'jang', 'mbay', 'xool', 'wër', 'japp']
        
        for mot in mots_wolof:
            if mot in message_lower:
                return 'wolof'
        
        # Par défaut, considérer comme français
        return 'francais'
    
    def detecter_intention(self, message: str, langue: str) -> str:
        """Détecte l'intention du client (commande, catalogue, prix, etc.)."""
        message_lower = message.lower()
        
        for intention, patterns in self.intentions.items():
            patterns_langue = patterns.get(langue, patterns.get('fr', []))
            
            for pattern in patterns_langue:
                if re.search(pattern, message_lower):
                    return intention
        
        return 'general'
    
    def detecter_boutique_intelligente(self, message: str) -> Optional[Boutique]:
        """
        Détection intelligente de la boutique en français et wolof.
        Comprend les mots-clés ET les phrases complètes.
        """
        message_lower = message.lower().strip()
        langue = self.detecter_langue(message)
        
        logger.info(f"🔍 Détection boutique - Langue: {langue} - Message: '{message[:50]}...'")
        
        # Choisir le dictionnaire approprié selon la langue
        keywords = self.keywords_wolof if langue == 'wolof' else self.keywords_francais
        
        # Rechercher par mots-clés directs
        for cle, config in keywords.items():
            for mot in config['mots']:
                if mot in message_lower:
                    boutique = self._trouver_boutique_par_nom(cle)
                    if boutique:
                        logger.info(f"✅ Détection par mot-clé: {mot} → {boutique.nom}")
                        return boutique
        
        # Rechercher par patterns de phrases
        for cle, config in keywords.items():
            for pattern in config['phrases']:
                if re.search(pattern, message_lower):
                    boutique = self._trouver_boutique_par_nom(cle)
                    if boutique:
                        logger.info(f"✅ Détection par phrase: pattern={pattern} → {boutique.nom}")
                        return boutique
        
        # Si aucune boutique détectée, retourner None
        logger.info(f"❌ Aucune boutique détectée pour: '{message[:50]}...'")
        return None
    
    def _trouver_boutique_par_nom(self, cle: str) -> Optional[Boutique]:
        """Trouve une boutique par son nom ou clé."""
        correspondances = {
            'salmon': 'SALMON SHOP',
            'tash': 'TASH PRESTIGE',  # Par défaut vers TASH PRESTIGE principal
            'teranga': 'TERANGA SHOP'
        }
        
        nom_recherche = correspondances.get(cle.upper(), cle.upper())
        
        try:
            boutique = Boutique.objects.filter(
                Q(nom__icontains=nom_recherche) |
                Q(nom__icontains=cle.upper()),
                actif=True
            ).first()
            
            return boutique
        except Exception as e:
            logger.error(f"❌ Erreur recherche boutique {cle}: {e}")
            return None
    
    def generer_reponse_intelligente(self, message: str, boutique: Optional[Boutique] = None) -> str:
        """
        Génère une réponse intelligente en fonction du message et de la boutique détectée.
        """
        langue = self.detecter_langue(message)
        intention = self.detecter_intention(message, langue)
        
        if not boutique:
            return self._reponse_aucune_boutique(langue)
        
        # Réponses personnalisées selon langue et intention
        reponses = self._get_reponses_personnalisees(langue, intention, boutique)
        
        return reponses.get(intention, reponses['general'])
    
    def _get_reponses_personnalisees(self, langue: str, intention: str, boutique: Boutique) -> Dict[str, str]:
        """Retourne les réponses personnalisées selon la langue et l'intention."""
        
        if langue == 'wolof':
            return {
                'salutation': f"Salaam! Maa ngi jëm {boutique.nom}. Nanga def? Maa leen jox liggéey bu nuy wooye.",
                'commande': f"Kay {boutique.nom}, maa ngi jëm ñu. Mbay nañu lu nge soxla. Loolu nge wër?",
                'catalogue': f"{boutique.nom} - Japp nañu yu wóor. Nanga jàng wone liggéey bi?",
                'prix': f"{boutique.nom} - Xool nañu yu wóor. Nanga xool japp bi?",
                'paiement': self._generer_instructions_paiement_wolof(boutique),
                'general': f"{boutique.nom} - Maa ngi jëm ñu. Nanga def? Maa leen jox liggéey."
            }
        else:  # français
            return {
                'salutation': f"Bonjour ! Bienvenue chez {boutique.nom}. Comment puis-je vous aider ?",
                'commande': f"Bienvenue chez {boutique.nom} ! Je suis là pour prendre votre commande. Que désirez-vous ?",
                'catalogue': f"{boutique.nom} - Nous avons d'excellents produits. Souhaitez-vous voir notre catalogue ?",
                'prix': f"{boutique.nom} - Nos prix sont très abordables. Quel article vous intéresse ?",
                'paiement': self._generer_instructions_paiement_francais(boutique),
                'general': f"Bienvenue chez {boutique.nom} ! Comment puis-je vous aider aujourd'hui ?"
            }
    
    def _generer_instructions_paiement_francais(self, boutique: Boutique) -> str:
        """Génère les instructions de paiement en français."""
        return (
            f"💳 **Paiement sécurisé chez {boutique.nom}**\n\n"
            "🌊 **Wave Money** :\n"
            f"• Numéro : {boutique.telephone_wa or '221767600283'}\n"
            "• Montant : [calculé automatiquement]\n"
            "• Référence : CMD-2024-001\n\n"
            "📱 **Orange Money** :\n"
            f"• Numéro : {boutique.telephone_wa or '221767600283'}\n"
            "• Montant : [calculé automatiquement]\n"
            "• Référence : CMD-2024-001\n\n"
            "✅ Envoyez 'paiement envoyé' après le transfert\n"
            "🔍 Nous vérifions et confirmons automatiquement"
        )
    
    def _generer_instructions_paiement_wolof(self, boutique: Boutique) -> str:
        """Génère les instructions de paiement en wolof."""
        return (
            f"💳 **Paiement bu {boutique.nom}**\n\n"
            "🌊 **Wave Money** :\n"
            f"• Numero : {boutique.telephone_wa or '221767600283'}\n"
            "• Xool : [calculé automatiquement]\n"
            "• Reference : CMD-2024-001\n\n"
            "📱 **Orange Money** :\n"
            f"• Numero : {boutique.telephone_wa or '221767600283'}\n"
            "• Xool : [calculé automatiquement]\n"
            "• Reference : CMD-2024-001\n\n"
            "✅ Wax 'paiement envoyé' bayi ngir jàpp\n"
            "🔍 Nu seetee ak nangu ci otomatik"
        )
    
    def _reponse_aucune_boutique(self, langue: str) -> str:
        """Réponse quand aucune boutique n'est détectée."""
        if langue == 'wolof':
            return (
                "Salaam! Maa ngi jëm Fëgg Jaay. Nanga jàngal nu?\n\n"
                "• 'maa salmon' → Salmon Shop\n"
                "• 'dama tash' → Tash Prestige\n"
                "• 'jang teranga' → Teranga Shop"
            )
        else:
            return (
                "Bonjour ! Bienvenue sur Fëgg Jaay. Quelle boutique vous intéresse ?\n\n"
                "• 'salut salmon shop' → Salmon Shop\n"
                "• 'bonjour tash prestige' → Tash Prestige\n"
                "• 'catalogue teranga' → Teranga Shop"
            )


# Instance globale du bot
bot_bilingue = BotIntelligentBilingue()


def traiter_message_intelligent(message: str) -> Tuple[Optional[Boutique], str]:
    """
    Traite un message avec le bot intelligent bilingue.
    
    Returns:
        Tuple[Boutique, str]: (boutique détectée, réponse générée)
    """
    boutique = bot_bilingue.detecter_boutique_intelligente(message)
    reponse = bot_bilingue.generer_reponse_intelligente(message, boutique)
    
    return boutique, reponse
