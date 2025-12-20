#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Script de Gestion du Mot de Passe Dashboard
# LinkedIn Birthday Auto - Modification & Récupération sécurisée
# ═══════════════════════════════════════════════════════════════════════════════
#
# Ce script permet de :
#   1. Changer le mot de passe du dashboard
#   2. Réinitialiser le mot de passe (générer un aléatoire)
#   3. Afficher le statut du mot de passe
#
# Usage:
#   ./scripts/manage_dashboard_password.sh
#
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# --- Couleurs ---
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_ROOT}/.env"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.pi4-standalone.yml"
LOG_DIR="${PROJECT_ROOT}/logs"
HISTORY_LOG="${LOG_DIR}/password_history.log"

# --- Logging ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Gestion d'erreurs ---
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Script échoué (Code $exit_code)"
    fi
}
trap cleanup EXIT

# === VÉRIFICATIONS PRÉALABLES ===

if [[ ! -f "$ENV_FILE" ]]; then
    log_error ".env non trouvé."
    log_info "Lancez d'abord ./setup.sh pour initialiser l'environnement."
    exit 1
fi

mkdir -p "$LOG_DIR"

cmd_exists() { command -v "$1" &> /dev/null; }

# === FONCTION: Menu Principal ===
prompt_menu() {
    local title="$1"
    shift
    local options=("$@")
    local choice
    local timeout=30

    echo -e "\n${BOLD}${BLUE}${title}${NC}\n"

    local i=1
    for option in "${options[@]}"; do
        echo "  ${BOLD}${i})${NC} ${option}"
        i=$((i + 1))
    done

    echo -ne "\n${YELLOW}Votre choix [1-$#] (timeout ${timeout}s) : ${NC}"

    read -r -t "$timeout" choice || { log_error "Timeout"; return 1; }

    if ! [[ "$choice" =~ ^[0-9]+$ ]] || [[ "$choice" -lt 1 ]] || [[ "$choice" -gt $# ]]; then
        log_error "Choix invalide. Veuillez entrer un nombre entre 1 et $#"
        return 2
    fi

    echo "$choice"
    return 0
}

# === FONCTION: Changer le Mot de Passe ===
change_password() {
    log_info "Changement du mot de passe..."

    echo ""
    echo -e "${BOLD}Entrez le nouveau mot de passe :${NC}"
    echo -n "Mot de passe (caché) : "
    read -rs NEW_PASS
    echo ""

    echo -n "Confirmez le mot de passe : "
    read -rs NEW_PASS_CONFIRM
    echo ""

    if [[ "$NEW_PASS" != "$NEW_PASS_CONFIRM" ]]; then
        log_error "Les mots de passe ne correspondent pas."
        return 1
    fi

    if [[ -z "$NEW_PASS" ]]; then
        log_error "Mot de passe vide."
        return 1
    fi

    if [[ ${#NEW_PASS} -lt 8 ]]; then
        log_warn "⚠️  Mot de passe court (< 8 caractères). Recommandé: 12+ chars"
        read -p "Continuer ? [y/N] : " -r confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            log_info "Annulé."
            return 1
        fi
    fi

    log_info "Hachage sécurisé du mot de passe..."

    # STRATÉGIE 1: Hash via Docker Node.js alpine (ARM64-compatible)
    local node_script='const bcrypt = require("bcryptjs");
const readline = require("readline");
const rl = readline.createInterface({ input: process.stdin });
rl.on("line", (password) => {
  const hash = bcrypt.hashSync(password.trim(), 12);
  console.log(hash);
  rl.close();
});'

    HASH_OUTPUT=$(echo "$NEW_PASS" | docker run --rm -i \
        --platform linux/arm64 \
        node:20-alpine \
        sh -c 'npm install --silent bcryptjs >/dev/null 2>&1 && node -e "'"${node_script}"'"' \
        2>/dev/null | head -n1 | tr -d '\n\r' || true)

    # STRATÉGIE 2: Fallback sur image dashboard si stratégie 1 échoue
    if [[ ! "$HASH_OUTPUT" =~ ^\$2 ]]; then
        log_warn "Fallback: tentative avec image dashboard..."
        DASHBOARD_IMG="ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest"

        if ! docker image inspect "$DASHBOARD_IMG" >/dev/null 2>&1; then
            log_info "Téléchargement image dashboard pour hachage..."
            if ! docker pull --platform linux/arm64 -q "$DASHBOARD_IMG" 2>/dev/null; then
                log_error "Impossible de télécharger l'image dashboard"
                return 1
            fi
        fi

        HASH_OUTPUT=$(docker run --rm \
            --platform linux/arm64 \
            --entrypoint node \
            -e PWD_INPUT="$NEW_PASS" \
            "$DASHBOARD_IMG" \
            -e "console.log(require('bcryptjs').hashSync(process.env.PWD_INPUT, 12))" 2>/dev/null || true)
    fi

    if [[ ! "$HASH_OUTPUT" =~ ^\$2 ]]; then
        log_error "Échec du hachage bcrypt (toutes stratégies)"
        log_error "Sortie: ${HASH_OUTPUT:-vide}"
        return 1
    fi

    # Doublage des $ pour shell-safe
    SAFE_HASH=$(echo "$HASH_OUTPUT" | sed 's/\$/\$\$/g')
    ESCAPED_SAFE_HASH=$(echo "$SAFE_HASH" | sed 's/[\/&]/\\&/g')

    # Écrire dans .env
    if ! sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=${ESCAPED_SAFE_HASH}|" "$ENV_FILE"; then
        log_error "Impossible de modifier .env"
        return 1
    fi

    log_success "Mot de passe modifié et stocké dans .env"

    # Logging sécurisé (pas le mot de passe!)
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Mot de passe modifié" >> "$HISTORY_LOG"

    # Afficher le résumé sécurisé
    echo ""
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}✓ MOT DE PASSE MODIFIÉ AVEC SUCCÈS${NC}"
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BOLD}Mot de passe (en clair):${NC} ${RED}${NEW_PASS}${NC}"
    echo -e "  ${BOLD}Hash (bcrypt):${NC} ${GREEN}${HASH_OUTPUT}${NC}"
    echo ""
    echo -e "  ⚠️  ${YELLOW}SAUVEGARDEZ CES INFORMATIONS${NC}"
    echo -e "  ℹ️  Le hash est stocké dans .env (chiffré)"
    echo ""
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    # Redémarrage dashboard
    if docker compose -f "$COMPOSE_FILE" ps dashboard 2>/dev/null | grep -q "Up"; then
        log_info "Redémarrage du dashboard..."
        if docker compose -f "$COMPOSE_FILE" restart dashboard >/dev/null 2>&1; then
            log_success "Dashboard redémarré. Nouveau mot de passe actif."
        else
            log_warn "Redémarrage dashboard échoué. Redémarrez manuellement:"
            log_warn "  docker compose -f $COMPOSE_FILE restart dashboard"
        fi
    else
        log_warn "Dashboard n'est pas en cours d'exécution."
        log_info "Redémarrez: docker compose -f $COMPOSE_FILE up -d"
    fi

    return 0
}

# === FONCTION: Réinitialiser le Mot de Passe ===
reset_password() {
    log_warn "⚠️  RÉINITIALISATION DU MOT DE PASSE"
    log_info "Un mot de passe temporaire fort sera généré et affiché une seule fois."
    echo ""

    read -p "Êtes-vous sûr ? [y/N] : " -r confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "Annulé."
        return 0
    fi

    # Générer mot de passe aléatoire fort (16 chars base64)
    TEMP_PASS=$(openssl rand -base64 12)

    log_info "Hachage du mot de passe temporaire..."

    # STRATÉGIE 1: Hash via Docker Node.js alpine (ARM64-compatible)
    local node_script='const bcrypt = require("bcryptjs");
const readline = require("readline");
const rl = readline.createInterface({ input: process.stdin });
rl.on("line", (password) => {
  const hash = bcrypt.hashSync(password.trim(), 12);
  console.log(hash);
  rl.close();
});'

    HASH_OUTPUT=$(echo "$TEMP_PASS" | docker run --rm -i \
        --platform linux/arm64 \
        node:20-alpine \
        sh -c 'npm install --silent bcryptjs >/dev/null 2>&1 && node -e "'"${node_script}"'"' \
        2>/dev/null | head -n1 | tr -d '\n\r' || true)

    # STRATÉGIE 2: Fallback sur image dashboard si stratégie 1 échoue
    if [[ ! "$HASH_OUTPUT" =~ ^\$2 ]]; then
        log_warn "Fallback: tentative avec image dashboard..."
        DASHBOARD_IMG="ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest"

        if ! docker image inspect "$DASHBOARD_IMG" >/dev/null 2>&1; then
            log_info "Téléchargement image dashboard..."
            if ! docker pull --platform linux/arm64 -q "$DASHBOARD_IMG" 2>/dev/null; then
                log_error "Impossible de télécharger l'image dashboard"
                return 1
            fi
        fi

        HASH_OUTPUT=$(docker run --rm \
            --platform linux/arm64 \
            --entrypoint node \
            -e PWD_INPUT="$TEMP_PASS" \
            "$DASHBOARD_IMG" \
            -e "console.log(require('bcryptjs').hashSync(process.env.PWD_INPUT, 12))" 2>/dev/null || true)
    fi

    if [[ ! "$HASH_OUTPUT" =~ ^\$2 ]]; then
        log_error "Échec du hachage bcrypt (toutes stratégies)"
        return 1
    fi

    SAFE_HASH=$(echo "$HASH_OUTPUT" | sed 's/\$/\$\$/g')
    ESCAPED_SAFE_HASH=$(echo "$SAFE_HASH" | sed 's/[\/&]/\\&/g')

    if ! sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=${ESCAPED_SAFE_HASH}|" "$ENV_FILE"; then
        log_error "Impossible de modifier .env"
        return 1
    fi

    # Logging sécurisé
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Mot de passe réinitialisé" >> "$HISTORY_LOG"

    echo ""
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}✓ MOT DE PASSE TEMPORAIRE GÉNÉRÉ${NC}"
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BOLD}Mot de passe (en clair):${NC} ${RED}${BOLD}${TEMP_PASS}${NC}"
    echo -e "  ${BOLD}Hash (bcrypt):${NC} ${GREEN}${HASH_OUTPUT}${NC}"
    echo ""
    echo -e "  ⚠️  SAUVEGARDEZ CES INFORMATIONS MAINTENANT !"
    echo -e "  ⚠️  ILS NE SERONT PAS AFFICHÉS À NOUVEAU."
    echo ""
    echo -e "  Après connexion:"
    echo -e "    1. Changez le mot de passe via le dashboard, ou"
    echo -e "    2. Relancez ce script et choisissez 'Changer le mot de passe'"
    echo ""
    echo -e "  En cas de problème de login/mot de passe:"
    echo -e "    - Vérifiez le mot de passe en clair ci-dessus"
    echo -e "    - Vérifiez le hash dans .env: grep DASHBOARD_PASSWORD .env"
    echo -e "    - Consultez: docs/PASSWORD_MANAGEMENT_GUIDE.md"
    echo ""
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    # Redémarrage dashboard
    if docker compose -f "$COMPOSE_FILE" ps dashboard 2>/dev/null | grep -q "Up"; then
        log_info "Redémarrage du dashboard..."
        if docker compose -f "$COMPOSE_FILE" restart dashboard >/dev/null 2>&1; then
            log_success "Dashboard redémarré avec mot de passe temporaire."
        else
            log_warn "Redémarrage échoué. Redémarrez manuellement."
        fi
    fi

    return 0
}

# === FONCTION: Afficher le Statut ===
show_status() {
    echo ""
    echo -e "${BOLD}Statut du Mot de Passe Dashboard${NC}"
    echo ""

    if grep -q "^DASHBOARD_PASSWORD=\$2[aby]\$" "$ENV_FILE" 2>/dev/null; then
        HASH=$(grep "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2)
        HASH_SHORT="${HASH:0:30}..."
        echo -e "  ${GREEN}✓ Hash bcrypt présent${NC}"
        echo -e "  Hash (premiers 30 chars): $HASH_SHORT"

        if [[ -f "$HISTORY_LOG" ]]; then
            LAST_CHANGE=$(tail -1 "$HISTORY_LOG" 2>/dev/null || echo "Inconnu")
            echo -e "  Dernier changement: $LAST_CHANGE"
        fi
    elif grep -q "CHANGEZ_MOI\|your_password\|12345" "$ENV_FILE" 2>/dev/null; then
        echo -e "  ${RED}✗ CONFIGURATION MANQUANTE${NC}"
        echo -e "  Mot de passe par défaut détecté."
        echo -e "  Configurez: $0"
    else
        echo -e "  ${YELLOW}⚠️  FORMAT INCONNU${NC}"
        echo -e "  Format mot de passe non reconnu. Vérifiez .env"
    fi

    echo ""
}

# === MENU PRINCIPAL ===
echo ""
echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║        Gestion du Mot de Passe Dashboard                  ║${NC}"
echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"

choice=$(prompt_menu \
    "Que désirez-vous faire ?" \
    "Changer le mot de passe" \
    "Réinitialiser le mot de passe (générer un aléatoire)" \
    "Afficher le statut du mot de passe" \
    "Quitter")

case "$choice" in
    1)
        change_password || exit 1
        ;;
    2)
        reset_password || exit 1
        ;;
    3)
        show_status
        ;;
    4)
        log_info "Quitter."
        ;;
esac

exit 0
