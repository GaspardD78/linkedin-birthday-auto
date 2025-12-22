#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# SCRIPT: VALIDATION ENVIRONNEMENT
# ═══════════════════════════════════════════════════════════════════════════════
# Vérifie que les variables d'environnement critiques sont correctement définies
# avant le démarrage des conteneurs.
#
# Usage:
#   ./scripts/validate_env.sh
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

# Fonctions de logging simples si non sourcées
if ! declare -f log_error >/dev/null; then
    log_error() { echo -e "${_RED}[ERROR] $1${_NC}" >&2; }
    log_warn() { echo -e "${_YELLOW}[WARN]  $1${_NC}" >&2; }
    log_info() { echo -e "[INFO]  $1"; }
    log_success() { echo -e "${_GREEN}[OK]    $1${_NC}"; }
fi

echo "🔍 Validation de l'environnement..."

# 1. Vérification du fichier .env
if [[ ! -f "$ENV_FILE" ]]; then
    log_error "Fichier .env manquant: $ENV_FILE"
    log_info "Veuillez exécuter ./setup.sh pour générer la configuration."
    exit 1
fi

# Charger les variables (sans exporter)
# On utilise une sous-shell ou grep pour éviter de polluer l'env courant,
# ou source pour les tester. Ici source est nécessaire pour tester les valeurs.
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# 2. Vérification API_KEY
if [[ -z "${API_KEY:-}" ]]; then
    log_error "Variable API_KEY manquante ou vide dans .env"
    log_info "Cette clé est requise pour sécuriser les communications inter-services."
    exit 1
fi

# 3. Vérification longueur API_KEY (Min 32 chars)
API_KEY_LEN=${#API_KEY}
if [[ "$API_KEY_LEN" -lt 32 ]]; then
    log_error "API_KEY trop courte ($API_KEY_LEN caractères)"
    log_info "La clé doit contenir au moins 32 caractères pour garantir la sécurité."
    log_info "Pour corriger: supprimez la ligne API_KEY du .env et relancez setup.sh"
    exit 1
fi

log_success "Environnement valide (API_KEY: ${API_KEY_LEN} chars)"
exit 0
