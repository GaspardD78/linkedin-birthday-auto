#!/bin/bash
# ==============================================================================
# CLEANUP CHROMIUM ZOMBIES - Raspberry Pi 4 Memory Management
# ==============================================================================
# Description: Nettoie les processus Chromium orphelins et zombies
# Usage: ./cleanup_chromium_zombies.sh [--force]
# ==============================================================================

set -euo pipefail

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

FORCE_MODE=false
[[ "${1:-}" == "--force" ]] && FORCE_MODE=true

# Fonction pour tuer les processus Chromium zombies
cleanup_chromium_processes() {
    log_info "Recherche des processus Chromium orphelins..."

    # Trouver tous les processus chromium
    local chromium_pids=$(pgrep -f chromium || true)

    if [[ -z "$chromium_pids" ]]; then
        log_success "Aucun processus Chromium trouvé"
        return 0
    fi

    local count=$(echo "$chromium_pids" | wc -w)
    log_info "Trouvé $count processus Chromium"

    # Vérifier si ce sont des processus orphelins (pas attachés à un bot-worker actif)
    local worker_pids=$(pgrep -f "src.queue.worker" || true)

    if [[ -n "$worker_pids" ]] && [[ "$FORCE_MODE" == "false" ]]; then
        log_warn "Worker actif détecté. Utilisez --force pour forcer le nettoyage."
        return 0
    fi

    # Tuer les processus Chromium
    log_info "Nettoyage des processus Chromium..."
    for pid in $chromium_pids; do
        if kill -0 "$pid" 2>/dev/null; then
            log_info "  → Killing PID $pid (SIGTERM)..."
            kill -TERM "$pid" 2>/dev/null || true
            sleep 0.5

            # Si toujours vivant, forcer avec SIGKILL
            if kill -0 "$pid" 2>/dev/null; then
                log_warn "  → Force killing PID $pid (SIGKILL)..."
                kill -KILL "$pid" 2>/dev/null || true
            fi
        fi
    done

    log_success "Nettoyage Chromium terminé"
}

# Fonction pour nettoyer les fichiers temporaires Playwright
cleanup_playwright_temp() {
    log_info "Nettoyage des fichiers temporaires Playwright..."

    # Nettoyer les sockets et locks dans /tmp
    find /tmp -name ".X*-lock" -type f -delete 2>/dev/null || true
    find /tmp -name "playwright-*" -type d -exec rm -rf {} + 2>/dev/null || true

    # Nettoyer les core dumps Chromium
    find /tmp -name "core.chromium.*" -type f -delete 2>/dev/null || true
    find /tmp -name "Crashpad" -type d -exec rm -rf {} + 2>/dev/null || true

    log_success "Fichiers temporaires nettoyés"
}

# Fonction pour nettoyer les shared memory segments
cleanup_shm() {
    log_info "Nettoyage des segments de mémoire partagée..."

    # Nettoyer /dev/shm (utilisé par Chromium)
    if [[ -d "/dev/shm" ]]; then
        find /dev/shm -name "com.google.Chrome.*" -delete 2>/dev/null || true
        find /dev/shm -name ".org.chromium.*" -delete 2>/dev/null || true
    fi

    log_success "Mémoire partagée nettoyée"
}

# Fonction principale
main() {
    echo ""
    log_info "==================================="
    log_info "  CHROMIUM ZOMBIE CLEANUP TOOL"
    log_info "==================================="
    echo ""

    cleanup_chromium_processes
    cleanup_playwright_temp
    cleanup_shm

    # Forcer garbage collection du système
    if command -v sync &> /dev/null; then
        log_info "Synchronisation des buffers disque..."
        sync
    fi

    echo ""
    log_success "✅ Cleanup complet terminé !"
    echo ""

    # Afficher la mémoire disponible après cleanup
    if command -v free &> /dev/null; then
        log_info "Mémoire disponible :"
        free -h | grep -E "Mem|Swap"
    fi
}

main "$@"
