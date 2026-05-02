# 🔑 Guide pour obtenir les clés API - Fëgg Jaay

## 📋 Tableau des clés API nécessaires

| Variable | Service | Comment obtenir |
|----------|---------|----------------|
| `OPENAI_API_KEY` | OpenAI (GPT-4) | https://platform.openai.com/ |
| `INFOBIP_API_KEY` | Infobip | https://portal.infobip.com/ |
| `INFOBIP_SENDER_NUMBER` | Infobip | Votre numéro WhatsApp configuré |
| `INFOBIP_BASE_URL` | Infobip | `api.infobip.com` (fixe) |
| `SITE_URL` | Votre site | Votre domaine ou IP du VPS |

---

## 🔑 1. OPENAI_API_KEY (GPT-4)

### Étape 1 : Créer un compte OpenAI

1. Allez sur : **https://platform.openai.com/**
2. Cliquez sur **"Sign up"** ou **"Log in"**
3. Créez un compte avec votre email
4. Vérifiez votre email

### Étape 2 : Générer une clé API

1. Connectez-vous à votre compte OpenAI
2. Cliquez sur **"API keys"** dans le menu de gauche
3. Cliquez sur **"Create new secret key"**
4. Donnez un nom à la clé (ex: `Fëgg Jaay Production`)
5. Sélectionnez les permissions :
   - ✅ **Read** (pour lire les messages)
   - ✅ **Write** (pour envoyer des messages)
   - ✅ **Chat** (pour les conversations)
6. Cliquez sur **"Create secret key"**
7. **Copiez la clé** (commence par `sk-proj-`)

### Étape 3 : Sauvegarder la clé

⚠️ **IMPORTANT** : Vous ne pourrez plus voir la clé après l'avoir quittée !

**Coût** : GPT-4o-mini coûte environ 0.15$ par 1M tokens. Pour une utilisation modérée, comptez ~5-10$/mois.

---

## 🔑 2. INFOBIP_API_KEY (Infobip)

### Étape 1 : Connectez-vous à Infobip

1. Allez sur : **https://portal.infobip.com/**
2. Connectez-vous avec vos identifiants

### Étape 2 : Créer une clé API

1. Cliquez sur **"Developers"** dans le menu de gauche
2. Cliquez sur **"API keys"**
3. Cliquez sur **"Create API key"**
4. Sélectionnez les permissions :
   - ✅ **Messaging** (pour envoyer des messages)
   - ✅ **WhatsApp** (pour WhatsApp)
5. Cliquez sur **"Create API key"**
6. **Copiez la clé**

### Étape 3 : Configurer WhatsApp

1. Allez dans **"Channels"** → **"WhatsApp"**
2. Cliquez sur **"Get started"** ou **"Connect WhatsApp"**
3. Suivez les instructions pour configurer votre numéro

**Coût** : Vous payez à l'utilisation, pas pour la clé elle-même.

---

## 🔑 3. INFOBIP_SENDER_NUMBER

C'est **votre numéro WhatsApp configuré** dans Infobip.

1. Connectez-vous à Infobip
2. Allez dans **"Channels"** → **"WhatsApp"**
3. Regardez le numéro configuré (ex: `221767600283`)
4. C'est ce numéro que vous utilisez comme `INFOBIP_SENDER_NUMBER`

---

## 🔑 4. INFOBIP_BASE_URL

C'est l'URL de l'API Infobip. Utilisez simplement :

```
INFOBIP_BASE_URL=api.infobip.com
```

---

## 🔑 5. SITE_URL

C'est l'URL de votre site web.

**Si vous avez un domaine** : `https://votre-domaine.com`

**Si vous n'avez pas encore de domaine** : vous pouvez utiliser l'IP du VPS pour tester :
```
SITE_URL=http://vps-ip:8000
```

---

## 📝 Exemple de fichier `.env` complet

```bash
# ──────────────────────────────────────────────────────────────────────
# Variables d'environnement - Fëgg Jaay
# ──────────────────────────────────────────────────────────────────────

# OpenAI (GPT-4)
OPENAI_API_KEY=sk-proj-abc123def456789ghijklmnopqrstuvwxyz

# Infobip
INFOBIP_API_KEY=abc123def456789ghijklmnopqrstuvwxyz
INFOBIP_BASE_URL=api.infobip.com
INFOBIP_SENDER_NUMBER=221767600283

# Site
SITE_URL=https://votre-domaine.com

# Base de données PostgreSQL
DATABASE_URL=postgresql://feggjaay:votre_mot_de_passe@localhost:5432/feggjaay

# Redis
REDIS_URL=redis://localhost:6379/0

# Secret Django (générer une clé aléatoire)
SECRET_KEY=votre_secret_key_django_ici

# Debug (False en production)
DEBUG=False
```

---

## ⚠️ Sécurité

- **Ne partagez jamais vos clés API** publiquement
- **Ne les mettez pas dans le code** (utilisez des variables d'environnement)
- **Gardez-les en sécurité** sur votre VPS
- **Changez les clés** si elles sont compromises

---

## 🚀 Une fois les clés obtenues

1. Connectez-vous à votre VPS
2. Exécutez le script de déploiement :
   ```bash
   bash deploy.sh
   ```
3. Modifiez le fichier `.env` avec vos vraies clés
4. Redémarrez les services

---

## 📞 Support

- **OpenAI** : https://help.openai.com/
- **Infobip** : support@infobip.com
- **WhatsApp** : https://www.infobip.com/docs/

---

## 💡 Astuces

- **OpenAI** : Vous pouvez tester avec des crédits gratuits avant de payer
- **Infobip** : Vous pouvez tester avec des crédits gratuits avant de payer
- **Nginx** : Assurez que votre domaine pointe vers l'IP du VPS
- **Firewall** : Assurez que les ports 80, 443, 8000 sont ouverts

---

## 🎯 Résumé rapide

| Service | Comment obtenir la clé | Coût approximatif |
|--------|------------------------|-------------------|
| OpenAI (GPT-4) | platform.openai.com → API Keys → Create | 5-10$/mois |
| Infobip | portal.infobip.com → Developers → API Keys → Create | À l'utilisation |
| WhatsApp | portal.infobip.com → Channels → WhatsApp | ~1$/mois |

C'est tout ! Vous avez maintenant toutes les informations pour configurer votre projet. 🚀
