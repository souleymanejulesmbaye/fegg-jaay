# 📋 Modifications à déployer sur le VPS

## 📁 Fichiers modifiés

### 1. `whatsapp/bot_engine.py`
- Remplacement de Claude API par OpenAI (GPT-4)
- Modification de la signature de `traiter_message` pour retourner `(reponse, envoyer_catalogue)`
- Modification de `_executer_action`, `_traiter_commande`, `_traiter_paiement`, `_traiter_annulation` pour retourner des tuples
- Modification de `_sauver_reference_paiement`, `_sauver_adresse_livraison` pour retourner des tuples
- Modification de `_message_erreur` pour retourner un tuple

### 2. `whatsapp/sender.py`
- Ajout de la fonction `envoyer_image()` pour envoyer des images
- Ajout de `_envoyer_image_infobip()` pour Infobip
- Ajout de `_envoyer_image_meta()` pour Meta
- Ajout de `envoyer_catalogue_avec_images()` pour envoyer le catalogue avec images

### 3. `whatsapp/views.py`
- Modification de `_traiter_message_sync()` pour gérer le catalogue avec images
- Appel de `envoyer_catalogue_avec_images()` quand l'intent est "catalogue"

### 4. `fegg_jaay/settings.py`
- Déplacement de `OPENAI_API_KEY` avant `ANTHROPIC_API_KEY`

### 5. `templates/dashboard/base.html`
- Modification du chemin du logo pour utiliser `/` au lieu de `\`

### 6. `static/img/fegg_jaay_icon.svg`
- Nouveau fichier logo SVG créé

### 7. `whatsapp/bot_engine_commercant.py`
- Nouveau fichier pour la gestion WhatsApp des commerçants

## 🔧 Variables d'environnement à configurer sur le VPS

Ajoutez ceci à votre fichier `.env` sur le VPS :

```bash
# OpenAI (GPT-4)
OPENAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Infobip
INFOBIP_API_KEY=votre_clé_infobip
INFOBIP_BASE_URL=api.infobip.com
INFOBIP_SENDER_NUMBER=221767600283

# Autres
SITE_URL=https://votre-domaine.com
```

## 🚀 Commandes de déploiement sur le VPS

```bash
# 1. Se connecter au VPS
ssh votre_user@vps_ip

# 2. Aller dans le dossier du projet
cd /path/to/fegg_jaay

# 3. Pull les modifications depuis git (si vous utilisez git)
git pull

# 4. Ou copier manuellement les fichiers modifiés :
# - whatsapp/bot_engine.py
# - whatsapp/sender.py
# - whatsapp/views.py
# - whatsapp/bot_engine_commercant.py
# - fegg_jaay/settings.py
# - templates/dashboard/base.html
# - static/img/fegg_jaay_icon.svg

# 5. Appliquer les migrations
python manage.py migrate

# 6. Redémarrer le serveur
sudo systemctl restart gunicorn
# Ou avec supervisor :
sudo supervisorctl restart fegg_jaay

# 7. Vérifier les logs
tail -f /var/log/fegg_jaay/gunicorn.log
```

## ✅ Fonctionnalités ajoutées

1. **Catalogue avec images** : Quand un client demande le catalogue, le bot envoie les images des produits
2. **GPT-4** : Remplacement de Claude par GPT-4 pour des réponses plus intelligentes
3. **Logo** : Logo SVG ajouté pour le dashboard
4. **Gestion commerçant** : Interface WhatsApp complète pour les commerçants

## 🧪 Tests à effectuer

1. **Test côté client** : Envoyez "catalogue" au bot depuis un numéro différent
2. **Test côté commerçant** : Envoyez "/menu" depuis votre numéro personnel
3. **Test catalogue images** : Vérifiez que les images sont envoyées
4. **Test logo** : Vérifiez que le logo s'affiche dans le dashboard
