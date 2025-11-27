#!/bin/bash

# 🚀 Script de déploiement automatique - Dashboard LinkedIn Bot v2
# Usage: ./deploy.sh [dev|staging|production|pi]

set -e  # Exit on error

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Vérifier l'argument
ENV=${1:-dev}

info "Déploiement du Dashboard LinkedIn Bot v2"
info "Environnement: $ENV"
echo ""

# Vérifier que nous sommes dans le bon dossier
if [ ! -f "package.json" ]; then
    error "Ce script doit être exécuté depuis le dossier 'dashboard/'"
fi

# Fonction de déploiement local (dev)
deploy_dev() {
    info "Démarrage en mode développement..."

    # Installer les dépendances si nécessaire
    if [ ! -d "node_modules" ]; then
        info "Installation des dépendances..."
        npm install
    fi

    # Créer .env.local si n'existe pas
    if [ ! -f ".env.local" ]; then
        warning "Fichier .env.local non trouvé. Création d'un template..."
        cat > .env.local << 'EOF'
# Configuration locale de développement

# Database (SQLite pour le dev)
DATABASE_URL=sqlite:///tmp/dashboard.db

# Redis local
REDIS_URL=redis://localhost:6379

# API Bot locale
BOT_API_URL=http://localhost:8000
BOT_API_KEY=dev_secret_key

# Next.js
NODE_ENV=development
EOF
        warning "Éditez .env.local avec vos vraies valeurs avant de continuer"
        exit 0
    fi

    success "Démarrage du serveur de développement..."
    npm run dev
}

# Fonction de déploiement avec Docker
deploy_docker() {
    local compose_file=${1:-docker-compose.yml}

    info "Vérification de Docker..."
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé. Installez-le d'abord."
    fi

    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose n'est pas installé. Installez-le d'abord."
    fi

    # Vérifier .env
    if [ ! -f ".env" ]; then
        warning "Fichier .env non trouvé. Création d'un template..."
        cat > .env << 'EOF'
# Variables d'environnement - Dashboard LinkedIn Bot

# Database (MySQL Synology)
DATABASE_URL=mysql://linkedin_user:CHANGE_THIS@192.168.1.X:3306/linkedin_bot

# Redis
REDIS_URL=redis://redis:6379

# API Bot
BOT_API_URL=http://localhost:8000
BOT_API_KEY=CHANGE_THIS_SECRET_KEY

# Next.js
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
EOF
        warning "⚠️  Éditez le fichier .env avec vos vraies valeurs !"
        warning "IMPORTANT: Changez DATABASE_URL, BOT_API_KEY, et BOT_API_URL"
        echo ""
        read -p "Appuyez sur Entrée quand vous avez configuré .env..."
    fi

    # Arrêter les conteneurs existants
    info "Arrêt des conteneurs existants..."
    docker-compose -f "$compose_file" down || true

    # Build
    info "Build de l'image Docker..."
    docker-compose -f "$compose_file" build --no-cache

    # Démarrage
    info "Démarrage des services..."
    docker-compose -f "$compose_file" up -d

    # Attendre que le service soit prêt
    info "Vérification de la santé du service..."
    sleep 5

    # Afficher les logs
    success "✅ Déploiement terminé !"
    echo ""
    info "Le dashboard est accessible sur: http://localhost:3000"
    echo ""
    info "Commandes utiles:"
    echo "  - Voir les logs:      docker-compose logs -f"
    echo "  - Arrêter:            docker-compose down"
    echo "  - Redémarrer:         docker-compose restart"
    echo "  - Monitoring:         docker stats linkedin_dashboard"
    echo ""

    # Afficher les premiers logs
    info "Derniers logs:"
    docker-compose -f "$compose_file" logs --tail=20
}

# Fonction de déploiement Raspberry Pi
deploy_pi() {
    info "Déploiement optimisé pour Raspberry Pi 4..."

    # Vérifier l'architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" != "aarch64" && "$ARCH" != "armv7l" ]]; then
        warning "Ce script est optimisé pour ARM64. Vous utilisez: $ARCH"
        read -p "Continuer quand même? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    # Utiliser le Dockerfile optimisé si disponible
    if [ -f "Dockerfile.prod.pi4" ]; then
        info "Utilisation du Dockerfile optimisé pour Pi4..."
        export DOCKERFILE=Dockerfile.prod.pi4
    fi

    # Vérifier la mémoire disponible
    TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_MEM" -lt 3000 ]; then
        warning "Mémoire disponible: ${TOTAL_MEM}MB - Recommandé: 4GB"
        warning "Le dashboard peut être lent ou crasher"
    fi

    deploy_docker "docker-compose.yml"
}

# Fonction de déploiement production
deploy_production() {
    warning "⚠️  DÉPLOIEMENT EN PRODUCTION"
    echo ""
    info "Vérifications avant déploiement:"

    # Checklist de sécurité
    checks_passed=true

    # 1. Vérifier .env
    if grep -q "CHANGE_THIS" .env 2>/dev/null; then
        error "❌ Le fichier .env contient encore des valeurs par défaut (CHANGE_THIS)"
        checks_passed=false
    else
        success "✅ Fichier .env configuré"
    fi

    # 2. Vérifier les secrets
    if grep -q "dev_secret_key\|secret_key_here" .env 2>/dev/null; then
        error "❌ Clés de sécurité faibles détectées dans .env"
        checks_passed=false
    else
        success "✅ Clés de sécurité configurées"
    fi

    # 3. Vérifier NODE_ENV
    if grep -q "NODE_ENV=production" .env 2>/dev/null; then
        success "✅ NODE_ENV=production"
    else
        warning "⚠️  NODE_ENV n'est pas défini sur 'production'"
    fi

    if [ "$checks_passed" = false ]; then
        error "Certaines vérifications ont échoué. Corrigez les erreurs avant de continuer."
    fi

    echo ""
    read -p "Continuer le déploiement en production? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "Déploiement annulé"
        exit 0
    fi

    deploy_docker "docker-compose.yml"

    # Tests post-déploiement
    info "Tests post-déploiement..."
    sleep 10

    if curl -f http://localhost:3000/api/health &>/dev/null; then
        success "✅ Health check OK"
    else
        error "❌ Health check échoué - Vérifiez les logs"
    fi
}

# Fonction de mise à jour
update() {
    info "Mise à jour du dashboard..."

    # Pull des dernières modifications
    info "Récupération des dernières modifications..."
    git pull origin main

    # Rebuild
    if [ -f "docker-compose.yml" ]; then
        info "Rebuild des conteneurs..."
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        success "✅ Mise à jour terminée (Docker)"
    else
        info "Mise à jour des dépendances..."
        npm install
        info "Rebuild de l'application..."
        npm run build
        info "Redémarrage avec PM2..."
        pm2 restart linkedin-dashboard || npm start
        success "✅ Mise à jour terminée"
    fi
}

# Menu principal
case $ENV in
    dev|development)
        deploy_dev
        ;;
    staging)
        info "Déploiement staging avec Docker..."
        deploy_docker "docker-compose.yml"
        ;;
    production|prod)
        deploy_production
        ;;
    pi|raspberry)
        deploy_pi
        ;;
    update)
        update
        ;;
    *)
        echo "Usage: $0 [dev|staging|production|pi|update]"
        echo ""
        echo "Environnements disponibles:"
        echo "  dev         - Démarrage en mode développement (npm run dev)"
        echo "  staging     - Déploiement Docker pour staging"
        echo "  production  - Déploiement Docker pour production (avec checks)"
        echo "  pi          - Déploiement optimisé pour Raspberry Pi 4"
        echo "  update      - Mise à jour du dashboard (git pull + rebuild)"
        echo ""
        echo "Exemples:"
        echo "  $0 dev              # Développement local"
        echo "  $0 pi               # Déploiement sur Raspberry Pi"
        echo "  $0 production       # Déploiement production"
        echo "  $0 update           # Mise à jour"
        exit 1
        ;;
esac
