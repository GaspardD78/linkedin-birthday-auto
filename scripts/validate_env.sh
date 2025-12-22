#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# SCRIPT: VALIDATION ENVIRONNEMENT
# ═══════════════════════════════════════════════════════════════════════════════
# Vérifie que les variables d'environnement critiques sont correctement définies
# avant le démarrage des conteneurs.
#
# Usage:
#   ./scripts/validate_env.sh [--fix]
#
# Options:
#   --fix   Tente de corriger automatiquement les problèmes (génération API_KEY)
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Définition des couleurs si non définies (pour usage standalone)
if [[ -z "${_RED:-}" ]]; then
    _RED='\033[0;31m'
    _GREEN='\033[0;32m'
    _YELLOW='\033[1;33m'
    _NC='\033[0m'
fi

# Chemins
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
DATA_DIR="$PROJECT_ROOT/data"
DB_FILE="$DATA_DIR/linkedin.db"

# Mode FIX
FIX_MODE=false
if [[ "${1:-}" == "--fix" ]]; then
    FIX_MODE=true
fi

# Fonctions de logging
log_error() { echo -e "${_RED}[ERROR] $1${_NC}" >&2; }
log_warn() { echo -e "${_YELLOW}[WARN]  $1${_NC}" >&2; }
log_info() { echo -e "[INFO]  $1"; }
log_success() { echo -e "${_GREEN}[OK]    $1${_NC}"; }

# Fonction de génération de clé
generate_key() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 32
    else
        python3 -c "import secrets; print(secrets.token_hex(32))"
    fi
}

echo "🔍 Validation de l'environnement..."

# 1. Vérification du fichier .env
if [[ ! -f "$ENV_FILE" ]]; then
    log_error "Fichier .env manquant: $ENV_FILE"
    log_info "Veuillez exécuter ./setup.sh pour générer la configuration."
    exit 1
fi

# Charger les variables pour verification
# On utilise set -a et source pour charger dans le shell actuel de manière sécurisée
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

ERRORS=0

# 2. Vérification API_KEY
API_KEY_VALID=false
if [[ -z "${API_KEY:-}" ]]; then
    log_warn "Variable API_KEY manquante ou vide."
else
    API_KEY_LEN=${#API_KEY}
    if [[ "$API_KEY_LEN" -lt 32 ]]; then
        log_warn "API_KEY trop courte ($API_KEY_LEN caractères). Minimum 32 requis."
    else
        API_KEY_VALID=true
    fi
fi

if [[ "$API_KEY_VALID" == "false" ]]; then
    if [[ "$FIX_MODE" == "true" ]]; then
        log_info "🔧 Génération automatique d'une nouvelle API_KEY..."
        NEW_KEY=$(generate_key)

        # Mise à jour du fichier .env (compatible Linux/macOS)
        if grep -q "^API_KEY=" "$ENV_FILE"; then
            # Remplacement
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|^API_KEY=.*|API_KEY=${NEW_KEY}|" "$ENV_FILE"
            else
                sed -i "s|^API_KEY=.*|API_KEY=${NEW_KEY}|" "$ENV_FILE"
            fi
        else
            # Ajout
            echo "API_KEY=${NEW_KEY}" >> "$ENV_FILE"
        fi

        log_success "API_KEY mise à jour automatiquement."
        # Recharger pour la suite si besoin
        export API_KEY="$NEW_KEY"
    else
        log_error "Problème API_KEY détecté."
        log_info "Utilisez --fix pour corriger automatiquement."
        ERRORS=$((ERRORS + 1))
    fi
else
    log_success "API_KEY valide (${#API_KEY} chars)"
fi

# 3. Vérification JWT_SECRET
if [[ -z "${JWT_SECRET:-}" ]]; then
    log_error "Variable JWT_SECRET manquante ou vide."
    log_info "Cette variable est requise pour la sécurité du Dashboard."
    ERRORS=$((ERRORS + 1))
else
    log_success "JWT_SECRET présent"
fi

# 4. Vérification Permissions Database
if [[ -f "$DB_FILE" ]]; then
    if [[ ! -w "$DB_FILE" ]]; then
        log_error "Fichier base de données non accessible en écriture: $DB_FILE"
        ERRORS=$((ERRORS + 1))
    else
        log_success "Database accessible ($DB_FILE)"
    fi
elif [[ -d "$DATA_DIR" ]]; then
    if [[ ! -w "$DATA_DIR" ]]; then
        log_error "Dossier data non accessible en écriture: $DATA_DIR"
        ERRORS=$((ERRORS + 1))
    else
        log_success "Dossier data accessible (DB sera créée)"
    fi
else
    log_error "Dossier data manquant: $DATA_DIR"
    ERRORS=$((ERRORS + 1))
fi

# Résultat final
if [[ "$ERRORS" -gt 0 ]]; then
    log_error "Validation échouée avec $ERRORS erreur(s)."
    if [[ "$FIX_MODE" == "false" ]]; then
        log_info "Essayez: ./scripts/validate_env.sh --fix"
    fi
    exit 1
fi

log_success "Environnement valide."
exit 0
