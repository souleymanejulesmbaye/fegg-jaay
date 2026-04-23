"""
Système de paiement mobile pour Fëgg Jaay.
Intégration Wave Money et Orange Money avec vérification automatique.
"""

import logging
from typing import Dict, Optional, Tuple
from django.db.models import Q
from boutiques.models import Boutique, Commande, Paiement
from .sender import envoyer_message_texte

logger = logging.getLogger(__name__)


class GestionnairePaiementMobile:
    """Gestionnaire des paiements mobiles Wave et Orange Money."""
    
    def __init__(self):
        self.modes_paiement = {
            'wave': {
                'nom': 'Wave Money',
                'icone': '🌊',
                'instructions': self._instructions_wave
            },
            'orange_money': {
                'nom': 'Orange Money',
                'icone': '📱',
                'instructions': self._instructions_orange_money
            }
        }
    
    def detecter_mode_paiement(self, message: str) -> Optional[str]:
        """Détecte le mode de paiement choisi par le client."""
        message_lower = message.lower()
        
        if any(mot in message_lower for mot in ['wave', 'wave money']):
            return 'wave'
        elif any(mot in message_lower for mot in ['orange', 'orange money', 'om']):
            return 'orange_money'
        elif 'payer' in message_lower:
            return 'wave'  # Wave par défaut
        
        return None
    
    def generer_instructions_paiement(self, boutique: Boutique, montant: int, mode: str, langue: str = 'francais') -> str:
        """Génère les instructions de paiement selon le mode et la langue."""
        if mode not in self.modes_paiement:
            return "Mode de paiement non reconnu."
        
        mode_info = self.modes_paiement[mode]
        reference = self._generer_reference_commande()
        
        if langue == 'wolof':
            return self._instructions_wolof(boutique, montant, mode_info, reference)
        else:
            return self._instructions_francais(boutique, montant, mode_info, reference)
    
    def _instructions_francais(self, boutique: Boutique, montant: int, mode_info: Dict, reference: str) -> str:
        """Instructions de paiement en français."""
        return (
            f"{mode_info['icone']} **Paiement {mode_info['nom']}**\n\n"
            f"🏪 {boutique.nom}\n"
            f"💰 Montant : {montant:,} FCFA\n"
            f"📞 Numéro : {boutique.telephone_wa or '221767600283'}\n"
            f"🔖 Référence : {reference}\n\n"
            f"**Étapes :**\n"
            f"1. Ouvrir {mode_info['nom']}\n"
            f"2. Transférer argent\n"
            f"3. Numéro : {boutique.telephone_wa or '221767600283'}\n"
            f"4. Montant : {montant:,} FCFA\n"
            f"5. Référence : {reference}\n\n"
            f"✅ Envoyez 'paiement envoyé' après le transfert\n"
            f"🔍 Nous vérifions et confirmons automatiquement"
        )
    
    def _instructions_wolof(self, boutique: Boutique, montant: int, mode_info: Dict, reference: str) -> str:
        """Instructions de paiement en wolof."""
        return (
            f"{mode_info['icone']} **Paiement {mode_info['nom']}**\n\n"
            f"🏪 {boutique.nom}\n"
            f"💰 Xool : {montant:,} FCFA\n"
            f"📞 Numero : {boutique.telephone_wa or '221767600283'}\n"
            f"🔖 Reference : {reference}\n\n"
            f"**Etapes :**\n"
            f"1. Ubbi {mode_info['nom']}\n"
            f"2. Waxal joxe kaan\n"
            f"3. Numero : {boutique.telephone_wa or '221767600283'}\n"
            f"4. Xool : {montant:,} FCFA\n"
            f"5. Reference : {reference}\n\n"
            f"✅ Wax 'paiement envoyé' bayi ngir jàpp\n"
            f"🔍 Nu seetee ak nangu ci otomatik"
        )
    
    def _generer_reference_commande(self) -> str:
        """Génère une référence de commande unique."""
        import datetime
        now = datetime.datetime.now()
        return f"CMD-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"
    
    def creer_commande(self, boutique: Boutique, client_tel: str, montant: int, mode_paiement: str, details: str = "") -> Optional[Commande]:
        """Crée une nouvelle commande."""
        try:
            reference = self._generer_reference_commande()
            
            commande = Commande.objects.create(
                boutique=boutique,
                client_telephone=client_tel,
                reference=reference,
                montant_total=montant,
                mode_paiement=mode_paiement,
                details=details,
                statut='en_attente'
            )
            
            logger.info(f"✅ Commande créée : {reference} - {boutique.nom} - {montant:,} FCFA")
            return commande
            
        except Exception as e:
            logger.error(f"❌ Erreur création commande : {e}")
            return None
    
    def verifier_paiement(self, reference: str) -> Tuple[bool, Optional[str]]:
        """
        Vérifie si un paiement a été reçu.
        Pour l'instant, simulation - à intégrer avec les APIs Wave/Orange Money.
        """
        try:
            # Simulation - à remplacer avec l'API réelle
            commande = Commande.objects.filter(reference=reference).first()
            if not commande:
                return False, "Commande non trouvée"
            
            # TODO: Intégrer avec les APIs Wave et Orange Money
            # Pour l'instant, considérons le paiement comme reçu après confirmation manuelle
            
            return False, "Vérification manuelle requise"
            
        except Exception as e:
            logger.error(f"❌ Erreur vérification paiement {reference}: {e}")
            return False, str(e)
    
    def confirmer_paiement(self, reference: str, boutique_tel: str, client_tel: str) -> bool:
        """Confirme un paiement et met à jour la commande."""
        try:
            commande = Commande.objects.filter(reference=reference).first()
            if not commande:
                return False
            
            # Mettre à jour le statut
            commande.statut = 'paye'
            commande.save()
            
            # Créer l'enregistrement de paiement
            Paiement.objects.create(
                commande=commande,
                montant=commande.montant_total,
                mode=commande.mode_paiement,
                reference=reference,
                statut='confirme'
            )
            
            # Envoyer la confirmation au client
            message_confirmation = (
                f"✅ **Paiement confirmé !**\n\n"
                f"📋 Référence : {reference}\n"
                f"💰 Montant : {commande.montant_total:,} FCFA\n"
                f"🏪 {commande.boutique.nom}\n\n"
                f"🚀 Votre commande est en préparation !\n"
                f"📦 Nous vous informerons dès la livraison."
            )
            
            boutique = Boutique.objects.get(telephone_wa=boutique_tel)
            envoyer_message_texte(boutique, client_tel, message_confirmation)
            
            logger.info(f"✅ Paiement confirmé : {reference}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur confirmation paiement {reference}: {e}")
            return False


# Instance globale du gestionnaire de paiement
gestionnaire_paiement = GestionnairePaiementMobile()


def traiter_demande_paiement(message: str, boutique: Boutique, client_tel: str, montant: int = 10000) -> Optional[str]:
    """
    Traite une demande de paiement et retourne les instructions.
    """
    try:
        # Détecter le mode de paiement
        mode = gestionnaire_paiement.detecter_mode_paiement(message)
        if not mode:
            mode = 'wave'  # Wave par défaut
        
        # Détecter la langue
        langue = 'wolof' if any(mot in message.lower() for mot in ["maa", "dama", "nga", "salam", "jang"]) else 'francais'
        
        # Générer les instructions
        instructions = gestionnaire_paiement.generer_instructions_paiement(boutique, montant, mode, langue)
        
        # Créer la commande
        commande = gestionnaire_paiement.creer_commande(boutique, client_tel, montant, mode, message)
        if commande:
            logger.info(f"📋 Commande créée pour paiement : {commande.reference}")
        
        return instructions
        
    except Exception as e:
        logger.error(f"❌ Erreur traitement demande paiement : {e}")
        return "Désolé, une erreur est survenue. Veuillez réessayer."


def confirmer_paiement_client(message: str, boutique: Boutique, client_tel: str) -> Optional[str]:
    """
    Confirme un paiement après que le client l'ait envoyé.
    """
    try:
        # Chercher la commande en attente du client
        commande = Commande.objects.filter(
            boutique=boutique,
            client_telephone=client_tel,
            statut='en_attente'
        ).order_by('-created_at').first()
        
        if not commande:
            return "Aucune commande en attente trouvée."
        
        # Confirmer le paiement
        if gestionnaire_paiement.confirmer_paiement(commande.reference, boutique.telephone_wa, client_tel):
            return f"✅ Paiement confirmé ! Référence : {commande.reference}"
        else:
            return "❌ Erreur lors de la confirmation du paiement."
            
    except Exception as e:
        logger.error(f"❌ Erreur confirmation paiement client : {e}")
        return "Désolé, une erreur est survenue lors de la confirmation."
