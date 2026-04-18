#!/bin/bash
# deploy.sh — Déploie Fëgg Jaay sur le VPS
# Usage: ./deploy.sh
# Appelé automatiquement par le webhook GitHub ou manuellement après git push

set -e

APP_DIR="/app"
cd "$APP_DIR"

echo "[deploy] $(date) — Début du déploiement"

# 1. Récupérer les derniers changements
git pull origin main

# 2. Migrations Django (si nouvelles migrations)
docker-compose exec -T web python manage.py migrate --no-input

# 3. Collecte des fichiers statiques
docker-compose exec -T web python manage.py collectstatic --no-input --clear

# 4. Redémarrer le serveur web et le worker Celery
docker-compose restart web worker

echo "[deploy] $(date) — Déploiement terminé ✓"
