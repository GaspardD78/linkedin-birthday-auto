#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Script de Gestion du Mot de Passe Dashboard
# LinkedIn Birthday Auto - Refactorisé pour ARM64/Pi4
# ═══════════════════════════════════════════════════════════════════════════════
#
# Ce script permet de :
#   1. Changer le mot de passe du dashboard
#   2. Réinitialiser le mot de passe (générer un aléatoire)
#   3. Afficher le statut du mot de passe
#
# Améliorations v2 (DevOps):
#   - Autonome (pas de dépendance à l'image dashboard ou Redis)
#   - Compatible ARM64 (Raspberry Pi 4)
#   - Utilise node:20-alpine officiel
#   - Sécurisé (passage de secrets par ENV)
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
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
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
        log_error "Script interrompu (Code $exit_code)"
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

# === HELPER: Génération Hash Bcrypt (Docker Lightweight) ===
generate_bcrypt_hash() {
    local clear_password="$1"

    if [[ -z "$clear_password" ]]; then
        log_error "Mot de passe vide fourni au générateur de hash."
        return 1
    fi

    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé ou accessible."
        return 1
    fi

    log_info "Génération du hash sécurisé (via node:20-alpine)..."

    # Exécution dans un conteneur éphémère node:20-alpine
    # - --platform linux/arm64 : Crucial pour RPi4
    # - --rm : Nettoyage automatique
    # - -e PASS_INPUT : Sécurité (évite l'argument CLI visible dans ps)
    # - npm install bcryptjs : Installation à la volée (pure JS, pas de compilation C++)

    local hash_output
    hash_output=$(docker run --rm \
        --platform linux/arm64 \
        --entrypoint /bin/sh \
        -e PASS_INPUT="$clear_password" \
        node:20-alpine \
        -c "npm install bcryptjs --no-save --silent >/dev/null 2>&1 && node -e \"console.log(require('bcryptjs').hashSync(process.env.PASS_INPUT, 10))\"") || {
            log_error "Erreur lors de l'exécution du conteneur de hachage."
            return 1
        }

    # Validation du format (doit commencer par $2a$, $2b$, $2x$ ou $2y$)
    if [[ ! "$hash_output" =~ ^\$2[abxy]\$ ]]; then
        log_error "Format de hash invalide retourné : '$hash_output'"
        return 1
    fi

    echo "$hash_output"
}

# === HELPER: Mise à jour .env ===
update_env_file() {
    local hash="$1"

    # Doubler les $ pour Docker Compose ($$ = $)
    local safe_hash_compose="${hash//\$/\$\$}"

    # Échapper pour sed (les slashs et esperluettes)
    local sed_safe_hash=$(echo "$safe_hash_compose" | sed 's/[\/&]/\\&/g')

    if ! sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=${sed_safe_hash}|" "$ENV_FILE"; then
        log_error "Impossible de modifier .env"
        return 1
    fi

    return 0
}

# === HELPER: Redémarrage Dashboard ===
restart_dashboard() {
    if [[ -f "$COMPOSE_FILE" ]]; then
        if docker compose -f "$COMPOSE_FILE" ps dashboard 2>/dev/null | grep -q "Up"; then
            log_info "Redémarrage du service dashboard..."
            if docker compose -f "$COMPOSE_FILE" restart dashboard >/dev/null 2>&1; then
                log_success "Dashboard redémarré. Nouveau mot de passe actif."
            else
                log_warn "Redémarrage automatique échoué."
                log_info "Exécutez manuellement: docker compose -f $COMPOSE_FILE restart dashboard"
            fi
        else
            log_warn "Le dashboard n'est pas démarré. (Pas de redémarrage nécessaire)"
        fi
    else
         log_warn "Fichier docker-compose introuvable. Redémarrage sauté."
    fi
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

    local final_hash
    final_hash=$(generate_bcrypt_hash "$NEW_PASS") || return 1

    if update_env_file "$final_hash"; then
        log_success "Mot de passe mis à jour dans .env"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Mot de passe modifié" >> "$HISTORY_LOG"

        echo ""
        echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${BOLD}${GREEN}✓ SUCCÈS${NC}"
        echo -e "  Hash (bcrypt): ${GREEN}${final_hash}${NC}"
        echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
        echo ""

        restart_dashboard
    else
        return 1
    fi
}

# === FONCTION: Réinitialiser le Mot de Passe ===
reset_password() {
    log_warn "⚠️  RÉINITIALISATION DU MOT DE PASSE"
    log_info "Un mot de passe aléatoire fort sera généré."
    echo ""

    read -p "Êtes-vous sûr ? [y/N] : " -r confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "Annulé."
        return 0
    fi

    # Générer mot de passe aléatoire fort (16 chars base64)
    local temp_pass
    temp_pass=$(openssl rand -base64 12)

    local final_hash
    final_hash=$(generate_bcrypt_hash "$temp_pass") || return 1

    if update_env_file "$final_hash"; then
        log_success "Mot de passe réinitialisé dans .env"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Mot de passe réinitialisé" >> "$HISTORY_LOG"

        echo ""
        echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${BOLD}${GREEN}✓ NOUVEAU MOT DE PASSE GÉNÉRÉ${NC}"
        echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "  ${BOLD}Mot de passe (en clair):${NC} ${RED}${BOLD}${temp_pass}${NC}"
        echo -e "  ${BOLD}Hash (bcrypt):${NC} ${GREEN}${final_hash}${NC}"
        echo ""
        echo -e "  ⚠️  SAUVEGARDEZ-LE MAINTENANT !"
        echo ""
        echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
        echo ""

        restart_dashboard
    else
        return 1
    fi
}

# === FONCTION: Afficher le Statut ===
show_status() {
    echo ""
    echo -e "${BOLD}Statut du Mot de Passe Dashboard${NC}"
    echo ""

    # Regex plus souple pour détecter les hash bcrypt (avec ou sans double $, avec ou sans guillemets)
    if grep -qE "^DASHBOARD_PASSWORD=\"?(\$\$)?2[abxy]" "$ENV_FILE" 2>/dev/null; then
        HASH=$(grep "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2)
        HASH_SHORT="${HASH:0:30}..."
        echo -e "  ${GREEN}✓ Hash bcrypt présent${NC}"
        echo -e "  Hash (aperçu): $HASH_SHORT"

        if [[ -f "$HISTORY_LOG" ]]; then
            LAST_CHANGE=$(tail -1 "$HISTORY_LOG" 2>/dev/null || echo "Inconnu")
            echo -e "  Dernier changement: $LAST_CHANGE"
        fi
    elif grep -q "CHANGEZ_MOI\|your_password\|12345" "$ENV_FILE" 2>/dev/null; then
        echo -e "  ${RED}✗ CONFIGURATION MANQUANTE${NC}"
        echo -e "  Mot de passe par défaut détecté."
    else
        echo -e "  ${YELLOW}⚠️  FORMAT INCONNU${NC}"
        echo -e "  Format non reconnu dans .env"
    fi

    echo ""
}

# === HELPER: Menu Input ===
prompt_menu() {
    local title="$1"
    shift
    local options=("$@")
    local choice
    local timeout=60

    echo -e "\n${BOLD}${BLUE}${title}${NC}\n"

    local i=1
    for option in "${options[@]}"; do
        echo "  ${BOLD}${i})${NC} ${option}"
        i=$((i + 1))
    done

    echo -ne "\n${YELLOW}Votre choix [1-$#] : ${NC}"

    if ! read -r -t "$timeout" choice; then
         log_error "Timeout (60s)"
         return 1
    fi

    if ! [[ "$choice" =~ ^[0-9]+$ ]] || [[ "$choice" -lt 1 ]] || [[ "$choice" -gt $# ]]; then
        log_error "Choix invalide."
        return 2
    fi

    echo "$choice"
    return 0
}

# === MAIN ===

echo ""
echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║        Gestion du Mot de Passe Dashboard (Pi4/ARM64)      ║${NC}"
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
