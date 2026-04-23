#!/usr/bin/env python
"""
Test du routing intelligent pour numéro WhatsApp partagé.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fegg_jaay.settings')
django.setup()

from whatsapp.routing_intelligent import test_routing_message
from boutiques.models import Boutique

def main():
    print('=== TEST ROUTING INTELLIGENT ===')
    print('')
    
    # Messages de test
    messages_test = [
        'salut salmon shop',
        'bonjour tash prestige', 
        'catalogue teranga',
        'je veux commander chez salmon',
        'tash prestige quels sont vos prix ?',
        'message sans boutique',
        'salut'
    ]
    
    print('📱 Tests de routing:')
    for msg in messages_test:
        resultat = test_routing_message(msg)
        if resultat['success']:
            print(f'✅ \"{msg}\" → {resultat["boutique_detectee"]}')
        else:
            print(f'❌ \"{msg}\" → Aucune boutique détectée')
    
    print('')
    print('🏪 Boutiques actives:')
    for boutique in Boutique.objects.filter(actif=True):
        print(f'  • {boutique.nom}')
    
    print('')
    print('🎯 Configuration terminée !')

if __name__ == '__main__':
    main()
