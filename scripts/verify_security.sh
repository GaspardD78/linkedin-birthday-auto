#!/bin/bash

###############################################################################
# 🔍 Script de Vérification Sécurité - LinkedIn Birthday Bot
# Version: 2.0 - Avec réparation automatique
# Teste TOUTES les protections de sécurité installées
###############################################################################

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

# Compteurs
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNING_TESTS=0
FIXED_COUNT=0
FAILED_FIX_COUNT=0

# Mode de réparation
FIX_MODE=false
if [ "$1" = "--fix" ] || [ "$1" = "-f" ]; then
    FIX_MODE=true
fi

# Tableaux pour stocker les problèmes à réparer
declare -a ISSUES_TO_FIX
declare -a FIX_FUNCTIONS

# Fonction pour afficher des titres
print_header() {
    echo ""
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${BOLD}  $1${NC}"
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Fonction pour tester
test_check() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    TEST_NAME="$1"
    echo -n "  [$TOTAL_TESTS] $TEST_NAME... "
}

# Fonction pour succès
test_pass() {
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    if [ -n "$1" ]; then
        echo -e "      ${GREEN}→ $1${NC}"
    fi
}

# Fonction pour échec
test_fail() {
    echo -e "${RED}✗ FAIL${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    if [ -n "$1" ]; then
        echo -e "      ${RED}→ $1${NC}"
    fi
    # Enregistrer le problème si une fonction de réparation est fournie
    if [ -n "$2" ]; then
        ISSUES_TO_FIX+=("$1")
        FIX_FUNCTIONS+=("$2")
    fi
}

# Fonction pour avertissement
test_warn() {
    echo -e "${YELLOW}⚠ WARN${NC}"
    WARNING_TESTS=$((WARNING_TESTS + 1))
    if [ -n "$1" ]; then
        echo -e "      ${YELLOW}→ $1${NC}"
    fi
    # Enregistrer le problème si une fonction de réparation est fournie
    if [ -n "$2" ]; then
        ISSUES_TO_FIX+=("$1")
        FIX_FUNCTIONS+=("$2")
    fi
}

###############################################################################
# FONCTIONS DE RÉPARATION
###############################################################################

# Réparer la base de données manquante
fix_database() {
    echo -e "${BLUE}Création de la base de données...${NC}"
    mkdir -p data
    # Initialiser la base de données avec un script Python
    python3 -c "
import sqlite3
conn = sqlite3.connect('data/linkedin_bot.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        linkedin_url TEXT,
        birthday TEXT,
        last_message_date TEXT
    )
''')
conn.commit()
conn.close()
print('Base de données créée avec succès')
"
    return $?
}

# Réparer Nginx non actif
fix_nginx_inactive() {
    echo -e "${BLUE}Vérification de Nginx...${NC}"

    # Vérifier si nginx est installé
    if ! command -v nginx &> /dev/null; then
        echo -e "${RED}Nginx n'est pas installé${NC}"
        echo -e "${YELLOW}Pour installer et configurer Nginx automatiquement:${NC}"
        echo -e "  ./scripts/fix_nginx.sh"
        echo ""
        return 1
    fi

    # Vérifier si la configuration existe
    if [ ! -f "/etc/nginx/sites-available/linkedin-bot" ]; then
        echo -e "${RED}Configuration linkedin-bot manquante${NC}"
        echo -e "${YELLOW}Pour installer la configuration complète:${NC}"
        echo -e "  ./scripts/fix_nginx.sh"
        echo ""
        return 1
    fi

    # Vérifier les zones de rate limiting
    if ! sudo grep -q "limit_req_zone" /etc/nginx/conf.d/rate-limit-zones.conf 2>/dev/null && \
       ! sudo grep -q "limit_req_zone" /etc/nginx/nginx.conf 2>/dev/null; then
        echo -e "${YELLOW}Zones de rate limiting manquantes${NC}"
        echo -e "${YELLOW}Pour configurer automatiquement:${NC}"
        echo -e "  ./scripts/fix_nginx.sh"
        echo ""
        return 1
    fi

    # Tester la configuration
    if ! sudo nginx -t &> /dev/null; then
        echo -e "${RED}Erreurs dans la configuration Nginx${NC}"
        echo -e "${YELLOW}Détails des erreurs:${NC}"
        sudo nginx -t
        echo ""
        echo -e "${YELLOW}Pour réparer la configuration:${NC}"
        echo -e "  ./scripts/fix_nginx.sh"
        echo ""
        return 1
    fi

    # Démarrer nginx
    echo -e "${BLUE}Démarrage de Nginx...${NC}"
    sudo systemctl start nginx

    if sudo systemctl is-active --quiet nginx; then
        echo -e "${GREEN}Nginx démarré avec succès${NC}"
        return 0
    else
        echo -e "${RED}Échec du démarrage de Nginx${NC}"
        echo -e "${YELLOW}Consultez les logs: sudo journalctl -xeu nginx${NC}"
        return 1
    fi
}

# Réparer la configuration Nginx
fix_nginx_config() {
    echo -e "${BLUE}Diagnostic de la configuration Nginx...${NC}"
    echo ""

    # Vérifier si nginx est installé
    if ! command -v nginx &> /dev/null; then
        echo -e "${RED}Nginx n'est pas installé${NC}"
        echo -e "${YELLOW}Pour installer et configurer Nginx automatiquement:${NC}"
        echo -e "  ./scripts/fix_nginx.sh"
        echo ""
        return 1
    fi

    # Afficher les erreurs de configuration
    echo -e "${YELLOW}Détails des erreurs:${NC}"
    sudo nginx -t
    echo ""

    # Vérifier les zones de rate limiting
    if ! sudo grep -q "limit_req_zone" /etc/nginx/conf.d/rate-limit-zones.conf 2>/dev/null && \
       ! sudo grep -q "limit_req_zone" /etc/nginx/nginx.conf 2>/dev/null; then
        echo -e "${RED}Problème détecté: zones de rate limiting manquantes${NC}"
        echo -e "${YELLOW}Pour réparer automatiquement:${NC}"
        echo -e "  ./scripts/fix_nginx.sh"
        echo ""
        return 1
    fi

    # Si la config est maintenant valide, recharger
    if sudo nginx -t &> /dev/null; then
        echo -e "${GREEN}Configuration valide${NC}"
        if sudo systemctl is-active --quiet nginx; then
            echo -e "${BLUE}Rechargement de Nginx...${NC}"
            sudo systemctl reload nginx
            echo -e "${GREEN}✓ Nginx rechargé${NC}"
            return 0
        else
            echo -e "${BLUE}Démarrage de Nginx...${NC}"
            sudo systemctl start nginx
            return $?
        fi
    else
        echo -e "${RED}La configuration contient toujours des erreurs${NC}"
        echo -e "${YELLOW}Correction manuelle requise ou utilisez:${NC}"
        echo -e "  ./scripts/fix_nginx.sh"
        echo ""
        return 1
    fi
}

# Réparer le mot de passe en clair
fix_password_hash() {
    echo -e "${BLUE}Hashage du mot de passe...${NC}"
    if [ ! -f ".env" ]; then
        echo -e "${RED}Fichier .env manquant${NC}"
        return 1
    fi

    # Créer un backup
    cp .env ".env.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}Backup créé${NC}"

    # Lire le mot de passe actuel
    CURRENT_PASSWORD=$(grep "^DASHBOARD_PASSWORD=" .env | cut -d'=' -f2-)

    if [ -z "$CURRENT_PASSWORD" ]; then
        echo -e "${RED}Aucun mot de passe trouvé dans .env${NC}"
        return 1
    fi

    # Hasher le mot de passe
    if [ -f "dashboard/scripts/hash_password.js" ]; then
        # Utiliser le mode --quiet pour obtenir uniquement le hash
        HASHED=$(node dashboard/scripts/hash_password.js --quiet "$CURRENT_PASSWORD" 2>/dev/null)

        if [ -n "$HASHED" ]; then
            # Échapper les caractères spéciaux pour sed
            # Échapper $ et /
            ESCAPED_HASH=$(echo "$HASHED" | sed 's/[\$\/]/\\&/g')
            sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=$ESCAPED_HASH|" .env
            echo -e "${GREEN}Mot de passe hashé avec succès${NC}"
            return 0
        else
            echo -e "${RED}Échec du hashage${NC}"
            return 1
        fi
    else
        echo -e "${RED}Script de hashage introuvable${NC}"
        return 1
    fi
}

# Réparer les permissions .env
fix_env_permissions() {
    echo -e "${BLUE}Correction des permissions .env...${NC}"
    chmod 600 .env
    echo -e "${GREEN}Permissions mises à jour (600)${NC}"
    return 0
}

# Réparer les security headers Nginx
fix_security_headers() {
    echo -e "${BLUE}Ajout des security headers dans Nginx...${NC}"

    NGINX_CONF="/etc/nginx/sites-available/linkedin-bot"

    if [ ! -f "$NGINX_CONF" ]; then
        echo -e "${RED}Configuration Nginx introuvable${NC}"
        return 1
    fi

    # Créer un backup
    sudo cp "$NGINX_CONF" "$NGINX_CONF.backup.$(date +%Y%m%d_%H%M%S)"

    # Vérifier si les headers sont déjà présents
    if grep -q "X-Frame-Options" "$NGINX_CONF"; then
        echo -e "${YELLOW}Headers déjà présents${NC}"
        return 0
    fi

    # Ajouter les headers dans le bloc server
    sudo sed -i '/server {/a\    # Security headers\n    add_header X-Frame-Options "DENY" always;\n    add_header X-Content-Type-Options "nosniff" always;\n    add_header X-Robots-Tag "noindex, nofollow" always;\n    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;' "$NGINX_CONF"

    echo -e "${GREEN}Security headers ajoutés${NC}"

    # Tester la configuration
    if sudo nginx -t &> /dev/null; then
        sudo systemctl reload nginx
        echo -e "${GREEN}Nginx rechargé${NC}"
        return 0
    else
        echo -e "${RED}Erreur de configuration Nginx${NC}"
        sudo cp "$NGINX_CONF.backup.$(date +%Y%m%d_%H%M%S)" "$NGINX_CONF"
        return 1
    fi
}

# Réparer les meta tags robots
fix_meta_robots() {
    echo -e "${BLUE}Ajout des meta tags robots dans layout.tsx...${NC}"

    LAYOUT_FILE="dashboard/app/layout.tsx"

    if [ ! -f "$LAYOUT_FILE" ]; then
        echo -e "${RED}Fichier layout.tsx introuvable${NC}"
        return 1
    fi

    # Créer un backup
    cp "$LAYOUT_FILE" "$LAYOUT_FILE.backup.$(date +%Y%m%d_%H%M%S)"

    # Vérifier si les meta tags sont déjà présents
    if grep -q "robots:" "$LAYOUT_FILE"; then
        echo -e "${YELLOW}Meta tags déjà présents${NC}"
        return 0
    fi

    # Chercher la section metadata et ajouter robots
    sed -i '/export const metadata.*{/a\  robots: {\n    index: false,\n    follow: false,\n    googleBot: {\n      index: false,\n      follow: false,\n    },\n  },' "$LAYOUT_FILE"

    echo -e "${GREEN}Meta tags robots ajoutés${NC}"
    return 0
}

clear
print_header "🔍 VÉRIFICATION SÉCURITÉ - LINKEDIN BIRTHDAY BOT"

cat << 'EOF'
Ce script va tester TOUTES les protections de sécurité installées.

📋 TESTS EFFECTUÉS :
   • Backup Google Drive
   • HTTPS et certificat SSL
   • Nginx et security headers
   • Mot de passe hashé bcrypt
   • Protection CORS
   • Anti-indexation
   • Permissions fichiers
   • Ports réseau

⏱️  Durée : 30-60 secondes

EOF

if [ "$FIX_MODE" = true ]; then
    echo -e "${GREEN}${BOLD}🔧 MODE RÉPARATION AUTOMATIQUE ACTIVÉ${NC}"
    echo "Les problèmes détectés seront réparés automatiquement."
    echo ""
    read -p "Appuyez sur Entrée pour commencer..."
else
    echo "💡 Usage: $0 [--fix] pour réparer automatiquement les problèmes"
    echo ""
    read -p "Appuyez sur Entrée pour commencer les tests..."
fi
echo ""

###############################################################################
# SECTION 1 : BACKUP GOOGLE DRIVE
###############################################################################

print_header "📦 SECTION 1/7 : BACKUP GOOGLE DRIVE"

# Test 1.1 : rclone installé
test_check "rclone installé"
if command -v rclone &> /dev/null; then
    VERSION=$(rclone version | head -n 1 | awk '{print $2}')
    test_pass "Version $VERSION"
else
    test_fail "rclone n'est pas installé"
fi

# Test 1.2 : Remote gdrive configuré
test_check "Remote Google Drive configuré"
if rclone listremotes 2>/dev/null | grep -q "gdrive:"; then
    test_pass "Remote 'gdrive' trouvé"
else
    test_fail "Exécutez: rclone config"
fi

# Test 1.3 : Connexion Google Drive
test_check "Connexion à Google Drive"
if rclone lsd gdrive: &> /dev/null; then
    test_pass "Connexion réussie"
else
    test_fail "Impossible de se connecter à Google Drive"
fi

# Test 1.4 : Script de backup existe
test_check "Script de backup existe"
if [ -f "./scripts/backup_to_gdrive.sh" ]; then
    test_pass "Fichier trouvé"
else
    test_fail "Fichier manquant: scripts/backup_to_gdrive.sh"
fi

# Test 1.5 : Script exécutable
test_check "Script de backup exécutable"
if [ -x "./scripts/backup_to_gdrive.sh" ]; then
    test_pass "Permissions correctes"
else
    test_warn "Corrigez avec: chmod +x scripts/backup_to_gdrive.sh"
fi

# Test 1.6 : Backup automatique (cron)
test_check "Backup automatique configuré"
if crontab -l 2>/dev/null | grep -q "backup_to_gdrive.sh"; then
    CRON_SCHEDULE=$(crontab -l 2>/dev/null | grep "backup_to_gdrive.sh" | awk '{print $1,$2,$3,$4,$5}')
    test_pass "Planifié: $CRON_SCHEDULE"
else
    test_warn "Backup manuel uniquement (pas de cron)"
fi

# Test 1.7 : Base de données existe
test_check "Base de données SQLite existe"
if [ -f "./data/linkedin_bot.db" ]; then
    SIZE=$(du -h ./data/linkedin_bot.db | awk '{print $1}')
    test_pass "Taille: $SIZE"
else
    test_fail "Base de données manquante: data/linkedin_bot.db" "fix_database"
fi

###############################################################################
# SECTION 2 : HTTPS ET CERTIFICAT SSL
###############################################################################

print_header "🔐 SECTION 2/7 : HTTPS ET CERTIFICAT SSL"

# Test 2.1 : Nginx installé
test_check "Nginx installé"
if command -v nginx &> /dev/null; then
    VERSION=$(nginx -v 2>&1 | awk -F'/' '{print $2}')
    test_pass "Version $VERSION"
else
    test_fail "Nginx n'est pas installé"
fi

# Test 2.2 : Nginx actif
test_check "Nginx actif"
if sudo systemctl is-active --quiet nginx; then
    test_pass "Service en cours d'exécution"
else
    test_fail "Démarrez avec: sudo systemctl start nginx" "fix_nginx_inactive"
fi

# Test 2.3 : Configuration Nginx
test_check "Configuration Nginx linkedin-bot"
if [ -f "/etc/nginx/sites-available/linkedin-bot" ]; then
    test_pass "Fichier de configuration trouvé"
else
    test_fail "Configuration manquante"
fi

# Test 2.4 : Configuration activée
test_check "Configuration Nginx activée"
if [ -L "/etc/nginx/sites-enabled/linkedin-bot" ]; then
    test_pass "Lien symbolique actif"
else
    test_fail "Activez avec: sudo ln -s /etc/nginx/sites-available/linkedin-bot /etc/nginx/sites-enabled/"
fi

# Test 2.5 : Configuration Nginx valide
test_check "Configuration Nginx valide"
if sudo nginx -t &> /dev/null; then
    test_pass "Syntaxe correcte"
else
    test_fail "Erreurs de configuration détectées" "fix_nginx_config"
fi

# Test 2.6 : Certbot installé
test_check "Certbot installé"
if command -v certbot &> /dev/null; then
    VERSION=$(certbot --version 2>&1 | awk '{print $2}')
    test_pass "Version $VERSION"
else
    test_warn "Certbot n'est pas installé (HTTPS manuel uniquement)"
fi

# Test 2.7 : Certificat SSL
test_check "Certificat SSL Let's Encrypt"
if command -v certbot &> /dev/null; then
    CERT_INFO=$(sudo certbot certificates 2>/dev/null | grep "Domains:")
    if [ -n "$CERT_INFO" ]; then
        DOMAIN=$(echo "$CERT_INFO" | awk '{print $2}')
        test_pass "Certificat pour: $DOMAIN"
    else
        test_warn "Aucun certificat trouvé (obtenir avec: sudo certbot --nginx)"
    fi
else
    test_warn "Certbot non installé"
fi

# Test 2.8 : Renouvellement auto SSL
test_check "Renouvellement auto certificat"
if sudo systemctl list-timers 2>/dev/null | grep -q "certbot"; then
    test_pass "Timer certbot actif"
else
    test_warn "Timer certbot inactif (renouvellement manuel)"
fi

###############################################################################
# SECTION 3 : SECURITY HEADERS NGINX
###############################################################################

print_header "🛡️ SECTION 3/7 : SECURITY HEADERS NGINX"

# Vérifier si un domaine est configuré
DOMAIN=""
if [ -f "/etc/nginx/sites-available/linkedin-bot" ]; then
    DOMAIN=$(grep "server_name" /etc/nginx/sites-available/linkedin-bot | head -n 1 | awk '{print $2}' | tr -d ';')
fi

if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "_" ]; then
    echo -e "${YELLOW}⚠ Aucun domaine configuré - tests headers HTTP ignorés${NC}"
else
    # Test 3.1 : X-Frame-Options
    test_check "Header X-Frame-Options"
    if curl -s -I "http://localhost" 2>/dev/null | grep -iq "X-Frame-Options"; then
        test_pass "Header présent"
    else
        test_warn "Header manquant" "fix_security_headers"
    fi

    # Test 3.2 : X-Content-Type-Options
    test_check "Header X-Content-Type-Options"
    if curl -s -I "http://localhost" 2>/dev/null | grep -iq "X-Content-Type-Options"; then
        test_pass "Header présent"
    else
        test_warn "Header manquant" "fix_security_headers"
    fi

    # Test 3.3 : X-Robots-Tag
    test_check "Header X-Robots-Tag"
    if curl -s -I "http://localhost" 2>/dev/null | grep -iq "X-Robots-Tag"; then
        test_pass "Header présent"
    else
        test_warn "Header manquant" "fix_security_headers"
    fi

    # Test 3.4 : Strict-Transport-Security
    test_check "Header Strict-Transport-Security (HSTS)"
    if curl -s -I "http://localhost" 2>/dev/null | grep -iq "Strict-Transport-Security"; then
        test_pass "Header présent"
    else
        test_warn "Header manquant (normal si pas de HTTPS)" "fix_security_headers"
    fi
fi

###############################################################################
# SECTION 4 : MOT DE PASSE HASHÉ BCRYPT
###############################################################################

print_header "🔑 SECTION 4/7 : MOT DE PASSE HASHÉ BCRYPT"

# Test 4.1 : bcryptjs installé
test_check "bcryptjs installé dans dashboard"
if [ -f "dashboard/node_modules/bcryptjs/package.json" ]; then
    VERSION=$(cat dashboard/node_modules/bcryptjs/package.json | grep '"version"' | awk -F'"' '{print $4}')
    test_pass "Version $VERSION"
else
    test_fail "Installez avec: cd dashboard && npm install bcryptjs"
fi

# Test 4.2 : Script de hash existe
test_check "Script hash_password.js existe"
if [ -f "dashboard/scripts/hash_password.js" ]; then
    test_pass "Fichier trouvé"
else
    test_fail "Fichier manquant"
fi

# Test 4.3 : Mot de passe hashé dans .env
test_check "Mot de passe hashé dans .env"
if [ -f ".env" ]; then
    if grep -q '^DASHBOARD_PASSWORD=\$2[aby]\$' .env; then
        test_pass "Mot de passe hashé avec bcrypt"
    else
        PASSWORD_VALUE=$(grep "^DASHBOARD_PASSWORD=" .env | cut -d'=' -f2-)
        if [ -n "$PASSWORD_VALUE" ]; then
            test_fail "Mot de passe EN CLAIR - hashez avec: node dashboard/scripts/hash_password.js" "fix_password_hash"
        else
            test_fail "Variable DASHBOARD_PASSWORD manquante dans .env"
        fi
    fi
else
    test_fail "Fichier .env manquant"
fi

# Test 4.4 : Backup .env existe
test_check "Backup du fichier .env"
if ls .env.backup.* 1> /dev/null 2>&1; then
    BACKUP_COUNT=$(ls .env.backup.* 2>/dev/null | wc -l)
    test_pass "$BACKUP_COUNT backup(s) trouvé(s)"
else
    test_warn "Aucun backup .env (créez-en avec: cp .env .env.backup)"
fi

###############################################################################
# SECTION 5 : PROTECTION CORS
###############################################################################

print_header "🌐 SECTION 5/7 : PROTECTION CORS"

# Test 5.1 : Variable ALLOWED_ORIGINS
test_check "Variable ALLOWED_ORIGINS dans .env"
if [ -f ".env" ]; then
    if grep -q "^ALLOWED_ORIGINS=" .env; then
        ORIGINS=$(grep "^ALLOWED_ORIGINS=" .env | cut -d'=' -f2-)
        test_pass "Origins: $ORIGINS"
    else
        test_fail "Ajoutez: ALLOWED_ORIGINS=https://votre-domaine.com"
    fi
else
    test_fail "Fichier .env manquant"
fi

# Test 5.2 : CORS dans app.py
test_check "CORS configuré dans app.py"
if grep -q "CORSMiddleware" src/api/app.py 2>/dev/null; then
    test_pass "CORSMiddleware importé"
else
    test_fail "CORS non configuré dans src/api/app.py"
fi

# Test 5.3 : API active
test_check "API FastAPI active"
if curl -s http://localhost:8000/health &> /dev/null; then
    test_pass "API répond sur le port 8000"
else
    test_warn "API non accessible (normal si conteneur arrêté)"
fi

###############################################################################
# SECTION 6 : ANTI-INDEXATION
###############################################################################

print_header "🔍 SECTION 6/7 : ANTI-INDEXATION"

# Test 6.1 : robots.txt
test_check "fichier robots.txt"
if [ -f "dashboard/public/robots.txt" ]; then
    if grep -q "Disallow: /" dashboard/public/robots.txt; then
        test_pass "robots.txt bloque l'indexation"
    else
        test_warn "robots.txt existe mais ne bloque pas"
    fi
else
    test_fail "Fichier manquant: dashboard/public/robots.txt"
fi

# Test 6.2 : Meta robots dans layout.tsx
test_check "Meta tags robots dans layout.tsx"
if [ -f "dashboard/app/layout.tsx" ]; then
    if grep -q "robots:" dashboard/app/layout.tsx && grep -q "index: false" dashboard/app/layout.tsx; then
        test_pass "Meta tags noindex configurés"
    else
        test_warn "Meta tags robots non trouvés ou incomplets" "fix_meta_robots"
    fi
else
    test_fail "Fichier manquant: dashboard/app/layout.tsx"
fi

# Test 6.3 : X-Robots-Tag dans next.config.js
test_check "X-Robots-Tag dans next.config.js"
if [ -f "dashboard/next.config.js" ]; then
    if grep -q "X-Robots-Tag" dashboard/next.config.js; then
        test_pass "Header X-Robots-Tag configuré"
    else
        test_warn "Header X-Robots-Tag non trouvé"
    fi
else
    test_fail "Fichier manquant: dashboard/next.config.js"
fi

# Test 6.4 : X-Robots-Tag dans nginx
test_check "X-Robots-Tag dans Nginx"
if [ -f "deployment/nginx/linkedin-bot.conf" ]; then
    if grep -q "X-Robots-Tag" deployment/nginx/linkedin-bot.conf; then
        test_pass "Header X-Robots-Tag dans Nginx"
    else
        test_warn "Header X-Robots-Tag non trouvé dans Nginx"
    fi
else
    test_warn "Fichier Nginx non trouvé (normal si pas encore déployé)"
fi

# Test 6.5 : Guide anti-indexation
test_check "Guide anti-indexation"
if [ -f "docs/ANTI_INDEXATION_GUIDE.md" ]; then
    test_pass "Documentation disponible"
else
    test_fail "Guide manquant"
fi

###############################################################################
# SECTION 7 : PERMISSIONS ET SÉCURITÉ SYSTÈME
###############################################################################

print_header "🔒 SECTION 7/7 : PERMISSIONS ET SÉCURITÉ SYSTÈME"

# Test 7.1 : Permissions .env
test_check "Permissions fichier .env"
if [ -f ".env" ]; then
    PERMS=$(stat -c "%a" .env)
    if [ "$PERMS" = "600" ] || [ "$PERMS" = "644" ]; then
        test_pass "Permissions: $PERMS"
    else
        test_warn "Permissions: $PERMS (recommandé: 600)" "fix_env_permissions"
    fi
else
    test_fail "Fichier .env manquant"
fi

# Test 7.2 : Permissions base de données
test_check "Permissions base de données"
if [ -f "./data/linkedin_bot.db" ]; then
    PERMS=$(stat -c "%a" ./data/linkedin_bot.db)
    if [ "$PERMS" = "644" ] || [ "$PERMS" = "664" ]; then
        test_pass "Permissions: $PERMS"
    else
        test_warn "Permissions: $PERMS (recommandé: 644)"
    fi
fi

# Test 7.3 : Docker installé
test_check "Docker installé"
if command -v docker &> /dev/null; then
    VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    test_pass "Version $VERSION"
else
    test_warn "Docker non installé (installation manuelle possible)"
fi

# Test 7.4 : Docker Compose installé
test_check "Docker Compose installé"
if docker compose version &> /dev/null; then
    VERSION=$(docker compose version | awk '{print $4}')
    test_pass "Version $VERSION"
else
    test_warn "Docker Compose non installé"
fi

# Test 7.5 : Conteneurs actifs
test_check "Conteneurs Docker actifs"
if command -v docker &> /dev/null; then
    RUNNING=$(docker ps --format "{{.Names}}" 2>/dev/null | wc -l)
    if [ "$RUNNING" -gt 0 ]; then
        test_pass "$RUNNING conteneur(s) en cours d'exécution"
    else
        test_warn "Aucun conteneur actif (démarrez avec: docker compose up -d)"
    fi
fi

# Test 7.6 : Ports réseau
test_check "Ports réseau (3000, 8000)"
PORTS_OK=true
if command -v netstat &> /dev/null; then
    if ! netstat -tlnp 2>/dev/null | grep -q ":3000"; then
        PORTS_OK=false
    fi
    if ! netstat -tlnp 2>/dev/null | grep -q ":8000"; then
        PORTS_OK=false
    fi

    if [ "$PORTS_OK" = true ]; then
        test_pass "Dashboard (3000) et API (8000) actifs"
    else
        test_warn "Un ou plusieurs ports non actifs"
    fi
else
    test_warn "netstat non disponible (install avec: sudo apt install net-tools)"
fi

###############################################################################
# RÉSUMÉ
###############################################################################

print_header "📊 RÉSUMÉ DES TESTS"

echo ""
echo -e "${BOLD}RÉSULTATS :${NC}"
echo -e "  ${GREEN}✓ Tests réussis     : $PASSED_TESTS${NC}"
echo -e "  ${RED}✗ Tests échoués     : $FAILED_TESTS${NC}"
echo -e "  ${YELLOW}⚠ Avertissements    : $WARNING_TESTS${NC}"
echo -e "  ${BLUE}━ Total             : $TOTAL_TESTS${NC}"
echo ""

# Calcul du score
SCORE=$(echo "scale=1; ($PASSED_TESTS * 100) / $TOTAL_TESTS" | bc)

echo -e "${BOLD}SCORE SÉCURITÉ :${NC}"
if (( $(echo "$SCORE >= 90" | bc -l) )); then
    echo -e "  ${GREEN}${BOLD}🏆 $SCORE% - EXCELLENT${NC}"
    echo -e "  ${GREEN}Votre bot est hautement sécurisé !${NC}"
elif (( $(echo "$SCORE >= 70" | bc -l) )); then
    echo -e "  ${YELLOW}${BOLD}⚠️  $SCORE% - BON${NC}"
    echo -e "  ${YELLOW}Quelques améliorations possibles.${NC}"
else
    echo -e "  ${RED}${BOLD}❌ $SCORE% - INSUFFISANT${NC}"
    echo -e "  ${RED}Action requise pour sécuriser votre bot !${NC}"
fi

echo ""

# Recommandations
if [ "$FAILED_TESTS" -gt 0 ]; then
    echo -e "${RED}${BOLD}⚠️  ACTIONS RECOMMANDÉES :${NC}"
    echo ""
    echo "  1. Consultez les tests échoués ci-dessus"
    echo "  2. Suivez les instructions de correction"
    echo "  3. Relancez ce script pour vérifier"
    echo ""
    echo "  💡 Pour installer automatiquement : ./scripts/setup_security.sh"
    echo ""
fi

# Tests critiques échoués
CRITICAL_FAILED=false
if ! command -v rclone &> /dev/null; then
    CRITICAL_FAILED=true
fi
if ! grep -q '^DASHBOARD_PASSWORD=\$2[aby]\$' .env 2>/dev/null; then
    CRITICAL_FAILED=true
fi

if [ "$CRITICAL_FAILED" = true ]; then
    echo -e "${RED}${BOLD}🚨 VULNÉRABILITÉS CRITIQUES DÉTECTÉES${NC}"
    echo ""
    echo "  Des éléments de sécurité CRITIQUES sont manquants !"
    echo "  Votre bot est vulnérable. Installation immédiate recommandée."
    echo ""
    echo "  Exécutez : ./scripts/setup_security.sh"
    echo ""
fi

###############################################################################
# SECTION RÉPARATION
###############################################################################

# Vérifier s'il y a des problèmes à réparer
if [ ${#ISSUES_TO_FIX[@]} -gt 0 ]; then
    echo ""
    print_header "🔧 RÉPARATION AUTOMATIQUE"

    # Dédupliquer les fonctions de réparation
    declare -A UNIQUE_FIXES
    for i in "${!FIX_FUNCTIONS[@]}"; do
        UNIQUE_FIXES["${FIX_FUNCTIONS[$i]}"]="${ISSUES_TO_FIX[$i]}"
    done

    echo -e "${YELLOW}${BOLD}${#UNIQUE_FIXES[@]} problème(s) peuvent être réparés automatiquement${NC}"
    echo ""

    if [ "$FIX_MODE" = true ]; then
        echo -e "${GREEN}Mode réparation automatique activé${NC}"
        echo ""
    else
        echo "Voulez-vous réparer ces problèmes maintenant ?"
        echo ""
        read -p "Répondre (o/n) : " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[OoYy]$ ]]; then
            echo -e "${YELLOW}Réparation annulée${NC}"
            echo ""
            echo "Pour réparer automatiquement, relancez avec: $0 --fix"
            echo ""
            exit 1
        fi
    fi

    echo ""

    # Exécuter chaque fonction de réparation unique
    for fix_func in "${!UNIQUE_FIXES[@]}"; do
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BOLD}Réparation: ${UNIQUE_FIXES[$fix_func]}${NC}"
        echo ""

        if $fix_func; then
            echo -e "${GREEN}✓ Réparation réussie${NC}"
            FIXED_COUNT=$((FIXED_COUNT + 1))
        else
            echo -e "${RED}✗ Échec de la réparation${NC}"
            FAILED_FIX_COUNT=$((FAILED_FIX_COUNT + 1))
        fi
        echo ""
    done

    print_header "📊 RÉSUMÉ DES RÉPARATIONS"
    echo ""
    echo -e "${GREEN}✓ Réparations réussies : $FIXED_COUNT${NC}"
    echo -e "${RED}✗ Réparations échouées : $FAILED_FIX_COUNT${NC}"
    echo ""

    if [ $FIXED_COUNT -gt 0 ]; then
        echo -e "${GREEN}${BOLD}🎉 Certains problèmes ont été corrigés !${NC}"
        echo ""
        echo "Relancez le script pour vérifier les corrections :"
        echo "  ./scripts/verify_security.sh"
        echo ""
    fi

    if [ $FAILED_FIX_COUNT -gt 0 ]; then
        echo -e "${RED}${BOLD}⚠️  Certaines réparations ont échoué${NC}"
        echo ""
        echo "Vous devrez peut-être corriger manuellement ou consulter les logs."
        echo ""
    fi
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}  Vérification terminée${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Code de sortie
if [ "$FAILED_TESTS" -eq 0 ] && [ "$FAILED_FIX_COUNT" -eq 0 ]; then
    exit 0
else
    exit 1
fi
