#!/bin/bash

# ──────────────────────────────────────────────────────────────────────────────
# Script de déploiement automatisé pour Fëgg Jaay
# ──────────────────────────────────────────────────────────────────────────────

set -e # Arrête le script en cas d'erreur

echo "🚀 Déploiement de Fëgg Jaay sur le VPS"
echo "================================================"

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────

# Couleurs pour les messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Variables par défaut (à modifier selon votre VPS)
PROJECT_NAME="fegg_jaay"
PROJECT_DIR="/root/$PROJECT_NAME"
DOMAIN="votre-domaine.com"  # À MODIFIER
PYTHON_VERSION="3.10"
DB_NAME="feggjaay"
DB_USER="feggjaay"
DB_PASSWORD="votre_mot_de_passe_db"  # À MODIFIER
REDIS_PORT=6379
APP_PORT=8000

# ──────────────────────────────────────────────────────────────────────────────
# Fonctions utilitaires
# ──────────────────────────────────────────────────────────────────────

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# ──────────────────────────────────────────────────────────────────────────────
# Vérification des prérequis
# ──────────────────────────────────────────────────────────────────────

print_info "Vérification des prérequis..."

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 n'est pas installé"
    print_info "Installation de Python 3.10..."
    sudo apt update
    sudo apt install -y python3.10 python3.10-venv
else
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_info "Python $PYTHON_VERSION trouvé"
fi

# Vérifier pip
if ! command -v pip3 &> /dev/null; then
    print_info "Installation de pip..."
    sudo apt install -y python3-pip
fi

# Vérifier PostgreSQL
if ! command -v psql &> /dev/null; then
    print_warning "PostgreSQL n'est pas installé"
    print_info "Installation de PostgreSQL..."
    sudo apt install -y postgresql postgresql-contrib
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
else
    print_info "PostgreSQL trouvé"
fi

# Vérifier Redis
if ! command -v redis-server &> /dev/null; then
    print_warning "Redis n'est pas installé"
    print_info "Installation de Redis..."
    sudo apt install -y redis-server
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
else
    print_info "Redis trouvé"
fi

# Vérifier Nginx
if ! command -v nginx &> /dev/null; then
    print_warning "Nginx n'est pas installé"
    print_info "Installation de Nginx..."
    sudo apt install -y nginx
    sudo systemctl start nginx
    sudo systemctl enable nginx
else
    print_info "Nginx trouvé"
fi

# ──────────────────────────────────────────────────────────────────────────────
# Installation des dépendances Python
# ──────────────────────────────────────────────────────────────────────

print_info "Installation des dépendances Python..."

# Créer l'environnement virtuel
if [ ! -d "$PROJECT_DIR/venv" ]; then
    print_info "Création de l'environnement virtuel..."
    python3 -m venv "$PROJECT_DIR/venv"
fi

# Activer l'environnement virtuel
source "$PROJECT_DIR/venv/bin/activate"

# Installer les dépendances
print_info "Installation des packages Python..."
pip install --upgrade pip
pip install django gunicorn psycopg2-binary redis celery openai httpx python-decouple

# ──────────────────────────────────────────────────────────────────────────────
# Configuration de la base de données
# ──────────────────────────────────────────────────────────────────────

print_info "Configuration de la base de données..."

# Créer la base de données si elle n'existe pas
sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';" 2>/dev/null || \
    sudo -u postgres createdb "$DB_NAME"

# Créer l'utilisateur si nécessaire
sudo -u postgres psql -c "SELECT 1 FROM pg_user WHERE usename='$DB_USER';" 2>/dev/null || \
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"

# Donner les privilèges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -c "ALTER DATABASE $DB_NAME OWNER TO $DB_USER;"

print_success "Base de données configurée"

# ──────────────────────────────────────────────────────────────────────────────
# Configuration des variables d'environnement
# ──────────────────────────────────────────────────────────────────────

print_info "Configuration des variables d'environnement..."

# Créer le fichier .env s'il n'existe pas
if [ ! -f "$PROJECT_DIR/.env" ]; then
    print_warning "Fichier .env non trouvé, création du fichier par défaut..."
    cat > "$PROJECT_DIR/.env" << EOF
# ──────────────────────────────────────────────────────────────────────
# Variables d'environnement - Fëgg Jaay
# ──────────────────────────────────────────────────────────────────────

# OpenAI (GPT-4)
OPENAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Infobip
INFOBIP_API_KEY=votre_clé_infobip_ici
INFOBIP_BASE_URL=api.infobip.com
INFOBIP_SENDER_NUMBER=221767600283

# Site
SITE_URL=https://$DOMAIN

# Base de données PostgreSQL
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME

# Redis
REDIS_URL=redis://localhost:$REDIS_PORT/0

# Secret Django (générer une clé aléatoire)
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')

# Debug (False en production)
DEBUG=False

# ──────────────────────────────────────────────────────────────────────
# IMPORTANT : Modifiez les valeurs ci-dessus avant de continuer !
# ──────────────────────────────────────────────────────────────────────

EOF
    print_warning "Fichier .env créé avec des valeurs par défaut"
    print_warning "MODIFIEZ le fichier .env avec vos vraies clés API !"
    print_info "Fichier .env créé : $PROJECT_DIR/.env"
else
    print_info "Fichier .env trouvé"
fi

# ──────────────────────────────────────────────────────────────────────────────
# Application des migrations
# ──────────────────────────────────────────────────────────────────────

print_info "Application des migrations Django..."

cd "$PROJECT_DIR"
source venv/bin/activate

python manage.py migrate

print_success "Migrations appliquées"

# ──────────────────────────────────────────────────────────────────────────────
# Configuration Nginx
# ──────────────────────────────────────────────────────────────────────

print_info "Configuration Nginx..."

# Créer la configuration Nginx
cat > /etc/nginx/sites-available/fegg_jaay << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location /static/ {
        alias $PROJECT_DIR/staticfiles;
        expires 30d;
    }

    location /media/ {
        alias $PROJECT_DIR/media;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-ForwardedFor \$proxy_add_x_forwarded_for;
        proxy_set_header X-ForwardedProto \$scheme;
    }
}
EOF

# Activer la configuration
ln -sf /etc/nginx/sites-available/fegg_jaay /etc/nginx/sites-enabled/

# Tester la configuration
sudo nginx -t

# Redémarrer Nginx
sudo systemctl restart nginx

print_success "Nginx configuré et redémarré"

# ──────────────────────────────────────────────────────────────────────────────
# Configuration du service systemd
# ──────────────────────────────────────────────────────────────────────

print_info "Configuration du service systemd..."

cat > /etc/systemd/system/fegg_jaay.service << EOF
[Unit]
Description=Fëgg Jaay Django Application
After=network.target postgresql.service redis.service

[Service]
User=root
Group=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/gunicorn fegg_jaay.wsgi:application --workers 3 --bind 127.0.0.1:$APP_PORT --timeout=120
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Recharger systemd
sudo systemctl daemon-reload

# Activer le service
sudo systemctl enable fegg_jaay

print_success "Service systemd configuré"

# ──────────────────────────────────────────────────────────────────────────────
# Configuration Celery (optionnel)
# ──────────────────────────────────────────────────────────────────────

print_info "Configuration Celery (optionnel)..."

cat > /etc/systemd/system/fegg_jaay-celery.service << EOF
[Unit]
Description=Fëgg Jaay Celery Worker
After=network.target redis.service

[Service]
User=root
Group=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/celery -A fegg_jaay worker --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/fegg_jaay-celery-beat.service << EOF
[Unit]
Description=Fëgg Jaay Celery Beat Scheduler
After=network.target redis.service

[Service]
User=root
Group=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/celery -A fegg_jaay beat --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable fegg_jay-celery
sudo systemctl enable fegg_jay-celery-beat

print_success "Celery configuré"

# ──────────────────────────────────────────────────────────────────────────────
# Démarrage des services
# ──────────────────────────────────────────────────────────────────────

print_info "Démarrage des services..."

# Démarrer Redis
sudo systemctl start redis-server

# Démarrer PostgreSQL
sudo systemctl start postgresql

# Démarrer Celery
sudo systemctl start fegg_jaay-celery
sudo systemctl start fegg_jay-celery-beat

# Démarrer l'application
sudo systemctl start fegg_jaay

print_success "Services démarrés"

# ──────────────────────────────────────────────────────────────────────────────
# Configuration du webhook Infobip
# ──────────────────────────────────────────────────────────────────────

print_info "Configuration du webhook Infobip..."

# Le webhook sera configuré via le dashboard ou manuellement
print_warning "Le webhook Infobip doit être configuré manuellement :"
print_info "URL du webhook : https://$DOMAIN/whatsapp/webhook/"
print_info "Méthode : POST"
print_info "Security : API Key Infobip"

# ──────────────────────────────────────────────────────────────────────────────
# Finalisation
# ──────────────────────────────────────────────────────────────────────

print_success "================================================"
print_success "🎉 Déploiement terminé avec succès !"
print_success "================================================"
echo ""
print_info "📱 Application accessible à : https://$DOMAIN"
print_info "🔧 Logs de l'application : sudo journalctl -u fegg_jaay -f"
print_info "📊 Logs Celery : sudo journalctl -u fegg_jaay-celery -f"
print_info ""
print_warning "⚠️  IMPORTANT : Modifiez le fichier .env avec vos vraies clés API !"
print_info "   Fichier : $PROJECT_DIR/.env"
echo ""
print_info "📝 Commandes utiles :"
echo "  - Redémarrer l'application : sudo systemctl restart fegg_jaay"
echo "  - Voir les logs : sudo journalctl -u fegg_jaay -f"
echo "  - Arrêter l'application : sudo systemctl stop fegg_jaay"
echo "  - Mettre à jour le code : cd $PROJECT_DIR && git pull && sudo systemctl restart fegg_jaay"
echo ""
print_success "Déploiement terminé ! 🚀"
