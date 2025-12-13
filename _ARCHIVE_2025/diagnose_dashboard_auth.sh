#!/bin/bash

###############################################################################
# Script de diagnostic pour problèmes d'authentification Dashboard
###############################################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}  🔍 DIAGNOSTIC AUTHENTIFICATION DASHBOARD${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

###############################################################################
# Test 1 : Fichier .env existe et contient les variables
###############################################################################

echo -e "${BLUE}[1] Vérification fichier .env${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}✗ Le fichier .env n'existe PAS${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Fichier .env existe${NC}"
echo ""

# Vérifier les variables requises
echo -e "${BLUE}[2] Vérification variables d'environnement${NC}"
REQUIRED_VARS=("DASHBOARD_USER" "DASHBOARD_PASSWORD" "JWT_SECRET")

for var in "${REQUIRED_VARS[@]}"; do
    if grep -q "^${var}=" .env; then
        VALUE=$(grep "^${var}=" .env | cut -d'=' -f2-)
        if [ -n "$VALUE" ]; then
            echo -e "${GREEN}✓ $var est défini${NC}"
        else
            echo -e "${RED}✗ $var est vide${NC}"
        fi
    else
        echo -e "${RED}✗ $var n'existe pas dans .env${NC}"
    fi
done
echo ""

###############################################################################
# Test 3 : Vérifier que le dashboard container voit les variables
###############################################################################

echo -e "${BLUE}[3] Vérification variables dans le container dashboard${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠ Docker non disponible - impossible de vérifier le container${NC}"
else
    if docker ps | grep -q "dashboard"; then
        echo -e "${GREEN}✓ Container dashboard est en cours d'exécution${NC}"

        echo ""
        echo "Variables d'environnement dans le container:"
        echo "─────────────────────────────────────────────"

        docker compose -f docker-compose.pi4-standalone.yml exec dashboard env | grep -E "(DASHBOARD_USER|DASHBOARD_PASSWORD|JWT_SECRET)" | while read line; do
            VAR_NAME=$(echo "$line" | cut -d'=' -f1)
            VAR_VALUE=$(echo "$line" | cut -d'=' -f2-)

            if [ -n "$VAR_VALUE" ]; then
                echo -e "${GREEN}✓ $VAR_NAME est défini dans le container${NC}"
            else
                echo -e "${RED}✗ $VAR_NAME est VIDE dans le container${NC}"
            fi
        done
    else
        echo -e "${RED}✗ Container dashboard n'est PAS en cours d'exécution${NC}"
        echo ""
        echo "Démarrez le dashboard avec:"
        echo "  docker compose -f docker-compose.pi4-standalone.yml up -d dashboard"
    fi
fi
echo ""

###############################################################################
# Test 4 : Vérifier le format du hash bcrypt
###############################################################################

echo -e "${BLUE}[4] Vérification hash bcrypt${NC}"

DASHBOARD_PASSWORD=$(grep "^DASHBOARD_PASSWORD=" .env | cut -d'=' -f2-)

if echo "$DASHBOARD_PASSWORD" | grep -q '^\$2[aby]\$'; then
    echo -e "${GREEN}✓ Le mot de passe est au format bcrypt${NC}"
    echo "  Longueur: ${#DASHBOARD_PASSWORD} caractères (attendu: 60)"

    if [ ${#DASHBOARD_PASSWORD} -eq 60 ]; then
        echo -e "${GREEN}✓ Longueur correcte${NC}"
    else
        echo -e "${YELLOW}⚠ Longueur inhabituelle${NC}"
    fi
else
    echo -e "${RED}✗ Le mot de passe N'EST PAS au format bcrypt${NC}"
    echo "  Le mot de passe semble être en clair: ${DASHBOARD_PASSWORD:0:10}..."
fi
echo ""

###############################################################################
# Test 5 : Tester le hash bcrypt avec Node.js
###############################################################################

echo -e "${BLUE}[5] Test de validation bcrypt${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}⚠ Node.js non installé - impossible de tester bcrypt${NC}"
else
    if [ ! -f "dashboard/node_modules/bcryptjs/package.json" ]; then
        echo -e "${YELLOW}⚠ bcryptjs non installé - installation...${NC}"
        cd dashboard
        npm install bcryptjs --silent
        cd ..
    fi

    # Créer un script de test temporaire
    cat > /tmp/test_dashboard_auth.js << 'TESTEOF'
const bcrypt = require('bcryptjs');
const fs = require('fs');

// Lire le .env
const envContent = fs.readFileSync('.env', 'utf8');
const lines = envContent.split('\n');

let dashboardPassword = '';
for (const line of lines) {
    if (line.startsWith('DASHBOARD_PASSWORD=')) {
        dashboardPassword = line.substring('DASHBOARD_PASSWORD='.length).trim();
        break;
    }
}

if (!dashboardPassword) {
    console.error('❌ DASHBOARD_PASSWORD non trouvé dans .env');
    process.exit(1);
}

console.log('Hash dans .env:', dashboardPassword.substring(0, 20) + '...');
console.log('');

// Tester avec différents mots de passe
const testPasswords = [
    'LinkedinBot2024!',
    'admin',
    'admin123',
    'CHANGEZ_MOI_PAR_MOT_DE_PASSE_FORT'
];

console.log('Test de validation:');
console.log('─────────────────────────────────────────────');

let foundMatch = false;
for (const pwd of testPasswords) {
    try {
        const match = bcrypt.compareSync(pwd, dashboardPassword);
        if (match) {
            console.log(`✅ MATCH TROUVÉ: "${pwd}"`);
            foundMatch = true;
        } else {
            console.log(`❌ "${pwd}" - pas de match`);
        }
    } catch (error) {
        console.log(`❌ "${pwd}" - erreur bcrypt: ${error.message}`);
    }
}

console.log('─────────────────────────────────────────────');

if (!foundMatch) {
    console.log('');
    console.log('⚠️  AUCUN MOT DE PASSE DE TEST NE CORRESPOND');
    console.log('');
    console.log('Solutions possibles:');
    console.log('1. Le hash est corrompu - régénérez-le avec:');
    console.log('   node dashboard/scripts/hash_password.js "VotreMotDePasse"');
    console.log('');
    console.log('2. Vous utilisez un mot de passe différent');
    console.log('   Générez un nouveau hash pour votre mot de passe actuel');
}
TESTEOF

    node /tmp/test_dashboard_auth.js
    rm /tmp/test_dashboard_auth.js
fi
echo ""

###############################################################################
# Test 6 : Vérifier les logs du dashboard
###############################################################################

echo -e "${BLUE}[6] Logs récents du dashboard${NC}"

if command -v docker &> /dev/null; then
    echo "Dernières 20 lignes de logs:"
    echo "─────────────────────────────────────────────"
    docker compose -f docker-compose.pi4-standalone.yml logs dashboard --tail 20 2>&1 | grep -E "(error|Error|ERROR|warning|Warning|auth|Auth|login|Login)" || echo "Aucune erreur d'authentification dans les logs"
    echo "─────────────────────────────────────────────"
else
    echo -e "${YELLOW}⚠ Docker non disponible${NC}"
fi
echo ""

###############################################################################
# Résumé et recommandations
###############################################################################

echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}  📋 RECOMMANDATIONS${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "Pour résoudre les problèmes d'authentification:"
echo ""
echo "1. Régénérer le mot de passe:"
echo "   ${YELLOW}node dashboard/scripts/hash_password.js \"VotreNouveauMotDePasse\"${NC}"
echo ""
echo "2. Copier le hash dans .env:"
echo "   ${YELLOW}nano .env${NC}"
echo "   Remplacer DASHBOARD_PASSWORD= par le nouveau hash"
echo ""
echo "3. Redémarrer le dashboard:"
echo "   ${YELLOW}docker compose -f docker-compose.pi4-standalone.yml restart dashboard${NC}"
echo ""
echo "4. Vérifier les logs:"
echo "   ${YELLOW}docker compose -f docker-compose.pi4-standalone.yml logs -f dashboard${NC}"
echo ""
echo "5. Tester la connexion avec:"
echo "   - Utilisateur: ${GREEN}admin${NC}"
echo "   - Mot de passe: ${GREEN}VotreNouveauMotDePasse${NC} (en clair, PAS le hash)"
echo ""
