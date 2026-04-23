#!/usr/bin/env python
"""
Test du bot intelligent bilingue pour Fëgg Jaay.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fegg_jaay.settings')
django.setup()

from whatsapp.bot_intelligent_bilingue import traiter_message_intelligent

def main():
    print('=== TEST BOT INTELLIGENT BILINGUE ===')
    print('')
    
    # Messages de test en français
    messages_fr = [
        'salut salmon shop',
        'bonjour tash prestige',
        'je veux commander chez salmon',
        'catalogue teranga',
        'prix des vêtements tash',
        'bonjour',
        'salut'
    ]
    
    # Messages de test en wolof
    messages_wo = [
        'maa salmon',
        'dama tash',
        'mbay japp teranga',
        'jang xool salmon',
        'prix wër tash',
        'salam',
        'nga'
    ]
    
    print('🇫🇷 Tests en français:')
    for msg in messages_fr:
        boutique, reponse = traiter_message_intelligent(msg)
        boutique_nom = boutique.nom if boutique else 'Aucune'
        print(f'  "{msg}" → {boutique_nom}')
        print(f'    Réponse: {reponse[:60]}...')
        print()
    
    print('🇸🇳 Tests en wolof:')
    for msg in messages_wo:
        boutique, reponse = traiter_message_intelligent(msg)
        boutique_nom = boutique.nom if boutique else 'Aucune'
        print(f'  "{msg}" → {boutique_nom}')
        print(f'    Réponse: {reponse[:60]}...')
        print()
    
    print('🎯 Tests terminés !')

if __name__ == '__main__':
    main()
