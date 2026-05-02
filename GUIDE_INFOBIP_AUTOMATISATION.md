# 📱 Guide Configuration Automatisée Infobip - Fëgg Jaay

## 🎯 Vue d'ensemble

Ce guide explique comment configurer automatiquement WhatsApp pour les boutiques Fëgg Jaay avec Infobip.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  COMPTE INFOBIP FËGG JAAY                                    │
│  - Un seul compte pour toutes les boutiques                 │
│  - Chaque boutique a son propre numéro WhatsApp             │
│  - Facturation centralisée                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  BOUTIQUE 1 : SALMON SHOP                                   │
│  - Numéro : 221767600283                                    │
│  - Display Name : SALMON SHOP                                │
│  - Sender : infobip_sender = "221767600283"                 │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  BOUTIQUE 2 : TASH PRESTIGE                                 │
│  - Numéro : 221776826221                                    │
│  - Display Name : TASH PRESTIGE                             │
│  - Sender : infobip_sender = "221776826221"                 │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Workflow d'inscription

### Étape 1 : Inscription du commerçant

1. Le commerçant remplit le formulaire d'inscription :
   - Nom de la boutique
   - Numéro WhatsApp souhaité
   - Email et mot de passe
   - Ville

2. Système crée automatiquement :
   - Compte utilisateur Django
   - Boutique en base de données
   - Statut "en attente configuration"

3. Email envoyé avec instructions

### Étape 2 : Configuration WhatsApp

1. Le commerçant se connecte au dashboard
2. Allez dans "Configuration WhatsApp"
3. Entrez le nom d'affichage
4. Cliquez sur "Recevoir le code"
5. Entrez le code SMS reçu
6. Configuration validée automatiquement

### Étape 3 : Bot actif

- Le bot répond automatiquement 24/7
- Les clients peuvent commander
- Le commerçant reçoit les notifications

## 🔧 Configuration technique

### Variables d'environnement

```bash
# .env
INFOBIP_API_KEY=votre_clé_infobip
INFOBIP_BASE_URL=api.infobip.com
INFOBIP_SENDER_NUMBER=221767600283  # Numéro par défaut
SITE_URL=https://votre-domaine.com
```

### Modèle Boutique

Champs ajoutés pour Infobip :

```python
infobip_sender = models.CharField(...)  # Numéro WhatsApp de la boutique
infobip_display_name = models.CharField(...)  # Nom d'affichage
infobip_config_en_cours = models.BooleanField(...)  # Configuration en cours
infobip_code_validation = models.CharField(...)  # Code SMS
infobip_code_expires_at = models.DateTimeField(...)  # Expiration du code
```

### Sender WhatsApp

Le sender utilise automatiquement le numéro de la boutique :

```python
def _envoyer_infobip(boutique: Boutique, ...):
    sender = boutique.infobip_sender or INFOBIP_SENDER_NUMBER
    # Envoi avec le sender de la boutique
```

## 📋 Gestion du compte Infobip

### Renommer le compte existant

Si votre compte est au nom de "Salmon Shop" :

1. Connectez-vous à Infobip
2. Allez dans Settings → Account Details
3. Changez le nom en "Fëgg Jaay"
4. Sauvegardez

### Ajouter un nouveau numéro

Pour chaque nouvelle boutique :

1. Connectez-vous à Infobip
2. Allez dans Channels → WhatsApp
3. Cliquez sur "Add phone number"
4. Entrez le numéro du commerçant
5. Validez avec le code SMS
6. Le numéro est maintenant actif

### Webhook configuration

Le webhook est configuré une fois pour toutes :

```
URL : https://votre-domaine.com/whatsapp/webhook/
Method : POST
Security : API Key Infobip
```

## 💰 Coûts

### Par boutique

- Numéro WhatsApp : ~1$/mois (~650 FCFA)
- Messages : ~0.04$ par message (~260 FCFA)

### Exemple avec 10 boutiques

- 10 numéros : 10$/mois (~6.500 FCFA)
- 1000 messages/jour : 40$/mois (~26.000 FCFA)
- **Total : ~50$/mois (~32.500 FCFA)**

### vs 360dialog

- Économie : ~120.000 FCFA/mois
- Pourcentage : 94-95% d'économie

## 🎯 Avantages

### Pour vous (Fëgg Jaay)

- ✅ Un seul compte Infobip
- ✅ Gestion centralisée
- ✅ Facturation unique
- ✅ Support simplifié
- ✅ Coût réduit

### Pour les commerçants

- ✅ Numéro personnel
- ✅ Branding professionnel
- ✅ Indépendance
- ✅ Configuration simple
- ✅ Support dédié

### Pour les clients

- ✅ Un numéro par commerçant
- ✅ Simple et rapide
- ✅ Bot intelligent
- ✅ Service 24/7

## 🚨 Dépannage

### Code SMS non reçu

1. Vérifiez que le numéro est correct
2. Attendez 2-3 minutes
3. Cliquez sur "Renvoyer le code"
4. Contactez le support si problème persiste

### Code invalide

1. Vérifiez que vous avez entré 6 chiffres
2. Le code expire après 15 minutes
3. Demandez un nouveau code si expiré

### Messages non envoyés

1. Vérifiez les crédits Infobip
2. Vérifiez que le numéro est validé
3. Vérifiez le webhook configuration
4. Contactez le support

## 📞 Support

- WhatsApp : +221778953918
- Email : support@feggjaay.shop
- Documentation : https://www.infobip.com/docs

## 🎉 Conclusion

Avec ce système automatisé :

- ✅ Inscription en 3 minutes
- ✅ Configuration guidée
- ✅ Validation par SMS
- ✅ Bot actif immédiatement
- ✅ Support 24/7

Les commerçants peuvent maintenant s'inscrire à distance et configurer leur WhatsApp sans intervention manuelle !
