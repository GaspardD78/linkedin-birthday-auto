#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Test de Validation - Hachage Bcrypt ARM64
# ═══════════════════════════════════════════════════════════════════════════════
#
# Ce script teste la nouvelle implémentation du hachage Bcrypt sur ARM64
#
# Usage:
#   ./tests/test_bcrypt_arm64.sh
#
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

# Compteurs
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# Fonction de test
test_case() {
    local name="$1"
    local command="$2"
    local expected="$3"

    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -e "\n${BLUE}[TEST $TESTS_TOTAL]${NC} $name"

    if eval "$command"; then
        if [[ "$expected" == "pass" ]]; then
            echo -e "${GREEN}✓ PASSÉ${NC}"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "${RED}✗ ÉCHOUÉ${NC} (attendu: échec, obtenu: succès)"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    else
        if [[ "$expected" == "fail" ]]; then
            echo -e "${GREEN}✓ PASSÉ${NC} (échec attendu)"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "${RED}✗ ÉCHOUÉ${NC}"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    fi
}

echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║       Test de Validation - Hachage Bcrypt ARM64          ║${NC}"
echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"

# === TEST 1: Vérification de Docker ===
test_case "Docker est installé et disponible" \
    "command -v docker >/dev/null 2>&1" \
    "pass"

# === TEST 2: Vérification de l'image Node.js ARM64 ===
echo -e "\n${YELLOW}[INFO]${NC} Pull de l'image node:20-alpine (ARM64)..."
docker pull --platform linux/arm64 node:20-alpine >/dev/null 2>&1 || true

test_case "Image node:20-alpine ARM64 disponible" \
    "docker image inspect node:20-alpine >/dev/null 2>&1" \
    "pass"

# === TEST 3: Vérification de l'architecture ===
test_case "Image est bien ARM64" \
    "[[ \$(docker inspect node:20-alpine | grep -c 'arm64') -gt 0 ]]" \
    "pass"

# === TEST 4: Test de hashage Bcrypt simple ===
echo -e "\n${YELLOW}[INFO]${NC} Test de hashage d'un mot de passe..."

TEST_PASSWORD="TestPassword123!"
NODE_SCRIPT='const bcrypt = require("bcryptjs");
const readline = require("readline");
const rl = readline.createInterface({ input: process.stdin });
rl.on("line", (password) => {
  const hash = bcrypt.hashSync(password.trim(), 12);
  console.log(hash);
  rl.close();
});'

HASH_OUTPUT=$(echo "$TEST_PASSWORD" | docker run --rm -i \
    --platform linux/arm64 \
    node:20-alpine \
    sh -c 'npm install --silent bcryptjs >/dev/null 2>&1 && node -e "'"${NODE_SCRIPT}"'"' \
    2>/dev/null | head -n1 | tr -d '\n\r' || echo "")

test_case "Hash Bcrypt généré avec succès" \
    "[[ -n '$HASH_OUTPUT' ]]" \
    "pass"

test_case "Hash commence par \$2b\$ (format Bcrypt)" \
    "[[ '$HASH_OUTPUT' =~ ^\\\$2[abxy]\\\$ ]]" \
    "pass"

test_case "Hash a la longueur correcte (60 caractères)" \
    "[[ \${#HASH_OUTPUT} -eq 60 ]]" \
    "pass"

# === TEST 5: Test du formatage "double dollar" ===
echo -e "\n${YELLOW}[INFO]${NC} Test du formatage pour Docker Compose..."

DOUBLED_HASH="${HASH_OUTPUT//\$/\$\$}"

test_case "Hash doublé contient \$\$ au lieu de \$" \
    "[[ '$DOUBLED_HASH' =~ ^\\\$\\\$2[abxy]\\\$\\\$ ]]" \
    "pass"

test_case "Nombre de \$ est doublé" \
    "[[ \$(echo '$DOUBLED_HASH' | grep -o '\$' | wc -l) -eq \$(( \$(echo '$HASH_OUTPUT' | grep -o '\$' | wc -l) * 2 )) ]]" \
    "pass"

# === TEST 6: Test de vérification du hash ===
echo -e "\n${YELLOW}[INFO]${NC} Test de vérification du hash..."

VERIFY_SCRIPT='const bcrypt = require("bcryptjs");
const hash = process.argv[2];
const password = process.argv[3];
const isValid = bcrypt.compareSync(password, hash);
console.log(isValid);'

IS_VALID=$(docker run --rm \
    --platform linux/arm64 \
    node:20-alpine \
    sh -c "npm install --silent bcryptjs >/dev/null 2>&1 && node -e '${VERIFY_SCRIPT}' '$HASH_OUTPUT' '$TEST_PASSWORD'" \
    2>/dev/null | head -n1 | tr -d '\n\r' || echo "false")

test_case "Hash vérifié avec le bon mot de passe" \
    "[[ '$IS_VALID' == 'true' ]]" \
    "pass"

# === TEST 7: Test avec mauvais mot de passe ===
WRONG_PASSWORD="WrongPassword456!"
IS_INVALID=$(docker run --rm \
    --platform linux/arm64 \
    node:20-alpine \
    sh -c "npm install --silent bcryptjs >/dev/null 2>&1 && node -e '${VERIFY_SCRIPT}' '$HASH_OUTPUT' '$WRONG_PASSWORD'" \
    2>/dev/null | head -n1 | tr -d '\n\r' || echo "true")

test_case "Hash rejeté avec mauvais mot de passe" \
    "[[ '$IS_INVALID' == 'false' ]]" \
    "pass"

# === TEST 8: Test de la fonction hash_and_store_password ===
echo -e "\n${YELLOW}[INFO]${NC} Test de la fonction hash_and_store_password..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
export PROJECT_ROOT

# Charger les libs
if [[ -f "$SCRIPT_DIR/scripts/lib/common.sh" ]] && [[ -f "$SCRIPT_DIR/scripts/lib/security.sh" ]]; then
    source "$SCRIPT_DIR/scripts/lib/common.sh" 2>/dev/null || true
    source "$SCRIPT_DIR/scripts/lib/security.sh" 2>/dev/null || true

    # Créer un .env de test
    TEST_ENV_FILE="/tmp/test_bcrypt_$$.env"
    echo "DASHBOARD_PASSWORD=CHANGEZ_MOI" > "$TEST_ENV_FILE"

    if hash_and_store_password "$TEST_ENV_FILE" "TestFunctionPassword123!" 2>/dev/null; then
        test_case "Fonction hash_and_store_password exécutée avec succès" \
            "true" \
            "pass"

        STORED_HASH=$(grep "^DASHBOARD_PASSWORD=" "$TEST_ENV_FILE" | cut -d'=' -f2)

        test_case "Hash stocké dans .env commence par \$\$2b\$\$ (format Docker Compose)" \
            "[[ '$STORED_HASH' =~ ^\\\$\\\$2[abxy]\\\$\\\$ ]]" \
            "pass"
    else
        test_case "Fonction hash_and_store_password exécutée avec succès" \
            "false" \
            "pass"
    fi

    # Nettoyage
    rm -f "$TEST_ENV_FILE"
else
    echo -e "${YELLOW}[SKIP]${NC} Impossible de charger les libs (test ignoré)"
fi

# === RAPPORT FINAL ===
echo -e "\n${BOLD}${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║                    RÉSULTATS DES TESTS                    ║${NC}"
echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo -e "\n  ${BOLD}Total:${NC}    $TESTS_TOTAL tests"
echo -e "  ${GREEN}Passés:${NC}   $TESTS_PASSED"
echo -e "  ${RED}Échoués:${NC}  $TESTS_FAILED"

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "\n${GREEN}${BOLD}✓ TOUS LES TESTS SONT PASSÉS${NC}\n"
    exit 0
else
    echo -e "\n${RED}${BOLD}✗ CERTAINS TESTS ONT ÉCHOUÉ${NC}\n"
    exit 1
fi
