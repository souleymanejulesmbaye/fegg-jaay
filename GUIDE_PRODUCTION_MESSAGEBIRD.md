# 🚀 Guide MessageBird - Production Platform

## 🎯 Configuration pour votre plateforme déployée

**Votre plateforme** : Déjà en production avec nom de domaine
**Objectif** : Configurer MessageBird avec vos vrais numéros de commerçants

## 📱 Vrais Numéros des Commerçants

D'après votre base de données :
- **SALMON SHOP** : 221767600283
- **TASH PRESTIGE** : 221776826221  
- **TASH PRESTIGE 2** : 772000003
- **TERANGA SHOP** : +14155238886

## 🔧 Configuration Production

### Étape 1 : Webhook URL (CRUCIAL)

**Remplacez localhost par votre domaine :**
```
🔗 Webhook URL : https://VOTREDOMAINE.com/whatsapp/webhook/
```

**Exemples :**
- `https://feggjaay.shop/whatsapp/webhook/`
- `https://votreserveur.com/whatsapp/webhook/`

### Étape 2 : Variables d'environnement Production

Dans votre serveur, mettez à jour `.env` :
```bash
# MessageBird Configuration
MESSAGEBIRD_API_KEY=votre_cle_api_messagebird
MESSAGEBIRD_WEBHOOK_URL=https://VOTREDOMAINE.com/whatsapp/webhook/

# Twilio (backup si besoin)
TWILIO_ACCOUNT_SID=votre_sid_twilio
TWILIO_AUTH_TOKEN=votre_token_twilio
```

### Étape 3 : Configuration MessageBird

#### 1. Inscription MessageBird
```
🔗 https://www.messagebird.com/en/signup
📧 Email : votre email professionnel
💳 Ajoutez 20$ de crédits
```

#### 2. Configurer chaque numéro

**SALMON SHOP - 221767600283**
```
1. Channels → WhatsApp → Add WhatsApp
2. Use your own number
3. Number : 221767600283
4. Country : Sénégal (+221)
5. Display Name : SALMON SHOP
6. Webhook : https://VOTREDOMAINE.com/whatsapp/webhook/
7. Verify number (code SMS)
```

**TASH PRESTIGE - 221776826221**
```
Mêmes étapes avec :
- Number : 221776826221
- Display Name : TASH PRESTIGE
```

**TASH PRESTIGE 2 - 772000003**
```
Mêmes étapes avec :
- Number : 772000003
- Display Name : TASH PRESTIGE 2
```

**TERANGA SHOP - +14155238886**
```
Mêmes étapes avec :
- Number : +14155238886
- Display Name : TERANGA SHOP
```

## 🤖 Bot Intelligent en Production

### ✅ Déjà déployé
Votre bot intelligent bilingue fonctionne déjà sur votre plateforme :
- **Français** : "salut salmon shop" → SALMON SHOP
- **Wolof** : "maa tash" → TASH PRESTIGE
- **Catalogue** : "voir teranga" → TERANGA SHOP

### 🔧 Comment ça marche
1. **Client envoie** message à un numéro
2. **MessageBird** envoie à votre webhook
3. **Votre plateforme** traite avec le bot
4. **Réponse** envoyée via MessageBird

## 📱 Instructions pour les Clients (Production)

### Messages à partager
```
🏪 SALMON SHOP
📱 WhatsApp : 221767600283
💬 "salut salmon shop" pour commander

🏪 TASH PRESTIGE  
📱 WhatsApp : 221776826221
💬 "bonjour tash prestige" pour commander

🏪 TASH PRESTIGE 2
📱 WhatsApp : 772000003
💬 "je veux commander" 

🏪 TERANGA SHOP
📱 WhatsApp : +14155238886
💬 "catalogue teranga" pour voir les produits
```

## 🚀 Déploiement Production

### 1. Mettre à jour le code
```bash
# Sur votre serveur
cd /opt/fegg-jaay
git pull origin main
```

### 2. Mettre à jour les variables
```bash
# Éditer .env
nano .env
# Ajouter MESSAGEBIRD_API_KEY et MESSAGEBIRD_WEBHOOK_URL
```

### 3. Redémarrer les services
```bash
docker-compose restart web worker
```

### 4. Vérifier le webhook
```bash
curl -X POST https://VOTREDOMAINE.com/whatsapp/webhook/
# Doit retourner 200 OK
```

## 🧪 Tests Production

### Test chaque numéro
1. **221767600283** → Envoyez "salut salmon shop"
2. **221776826221** → Envoyez "bonjour tash prestige"  
3. **772000003** → Envoyez "je veux commander"
4. **+14155238886** → Envoyez "catalogue teranga"

### Vérifications
- ✅ Chaque numéro répond
- ✅ Bot en français/wolof
- ✅ Routing correct
- ✅ Logs dans MessageBird

## 🚨 Dépannage Production

### Si webhook ne répond pas
```bash
# Vérifier les logs
docker-compose logs web

# Vérifier si le service tourne
docker-compose ps
```

### Si MessageBird ne reçoit pas
1. **Vérifier l'URL** : https://VOTREDOMAINE.com/whatsapp/webhook/
2. **Vérifier HTTPS** : Doit être valide
3. **Vérifier les logs** : MessageBird Console

### Si numéro pas validé
- **Attendez 1-24h** pour validation WhatsApp
- **Vérifiez le code** reçu par SMS
- **Contactez support** MessageBird si bloqué

## 💰 Coûts Production

### Mensuels estimés
- **4 numéros WhatsApp** : 8$ (~5200 FCFA)
- **Messages** : Variable (0.04$ par message)
- **Total** : 6000-8000 FCFA/mois

### vs 360dialog
- **Économie** : 120.000-122.000 FCFA/mois
- **% d'économie** : 94-95%

## 📊 Monitoring Production

### Dashboard MessageBird
- **Messages envoyés** : https://dashboard.messagebird.com
- **Coûts** : Billing → Usage
- **Logs** : Developers → Logs

### Votre plateforme
- **Dashboard Django** : https://VOTREDOMAINE.com/dashboard/
- **Logs des messages** : Dans votre base de données
- **Statistiques** : Vues analytics

## 🎯 Lancement Production

### Aujourd'hui
1. **Configurez MessageBird** avec vos vrais numéros
2. **Testez** chaque numéro
3. **Déployez** les mises à jour si besoin
4. **Lancez** auprès des clients

### Demain
- **Commerçants opérationnels** avec leurs numéros
- **Clients satisfaits** du service
- **Vous économisez** 120.000 FCFA/mois

## 📞 Support Production

**Si besoin d'aide :**
- **WhatsApp** : +221778953918
- **Email** : support@feggjaay.shop
- **MessageBird** : support@messagebird.com

**Votre plateforme est prête pour MessageBird en production !** 🚀

## 🔄 Mise à jour des guides existants

Les guides précédents utilisent localhost. Remplacez :
- `http://localhost:8000` → `https://VOTREDOMAINE.com`
- Numéros de test → Vrais numéros des commerçants
- Configuration locale → Configuration production
