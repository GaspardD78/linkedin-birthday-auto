#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURE_RPI4_KERNEL.SH - Configuration système pour Raspberry Pi 4
# ═══════════════════════════════════════════════════════════════════════════
#
# Ce script configure les paramètres kernel nécessaires pour faire tourner
# Docker/Redis/SQLite de manière optimale sur Raspberry Pi 4.
#
# POURQUOI CE SCRIPT ?
# ====================
# Les paramètres comme vm.overcommit_memory ne peuvent PAS être isolés par
# namespace Docker sur les kernels ARM64. Ils DOIVENT être configurés sur
# l'hôte (le Raspberry Pi lui-même).
#
# L'erreur typique sans cette configuration :
#   "OCI runtime create failed: sysctl vm.overcommit_memory is not in a
#    separate kernel namespace"
#
# USAGE :
#   sudo ./scripts/configure_rpi4_kernel.sh
#
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# Vérification root
if [[ $EUID -ne 0 ]]; then
    log_error "Ce script doit être exécuté en tant que root (sudo)."
    echo "Usage: sudo $0"
    exit 1
fi

# Fichier de configuration sysctl
SYSCTL_FILE="/etc/sysctl.d/99-rpi4-docker.conf"

echo -e "\n${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${BLUE}  Configuration Kernel Raspberry Pi 4 pour Docker/Redis${NC}"
echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"

# Afficher les valeurs actuelles
log_info "Valeurs kernel actuelles :"
echo "  vm.overcommit_memory = $(cat /proc/sys/vm/overcommit_memory)"
echo "  net.core.somaxconn   = $(cat /proc/sys/net/core/somaxconn)"
echo "  vm.swappiness        = $(cat /proc/sys/vm/swappiness)"
echo ""

# Créer le fichier de configuration
log_info "Création de $SYSCTL_FILE..."

cat > "$SYSCTL_FILE" <<'EOF'
# ═══════════════════════════════════════════════════════════════════════════
# Configuration kernel optimisée pour LinkedIn Bot sur Raspberry Pi 4
# ═══════════════════════════════════════════════════════════════════════════
# Généré par configure_rpi4_kernel.sh
# Documentation: docs/RASPBERRY_PI_TROUBLESHOOTING.md
#
# IMPORTANT: Ces paramètres sont GLOBAUX au système.
# Ils ne peuvent PAS être isolés par conteneur Docker sur ARM64.
# ═══════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# REDIS - Évite les warnings "Background saving" et OOM
# ─────────────────────────────────────────────────────────────────────────────
# Redis utilise fork() pour sauvegarder les données en arrière-plan.
# Avec overcommit_memory=0 (défaut), le kernel peut refuser l'allocation.
# Avec overcommit_memory=1, le kernel accepte toujours (Redis le recommande).
vm.overcommit_memory = 1

# ─────────────────────────────────────────────────────────────────────────────
# CONNEXIONS TCP - File d'attente pour Redis/Nginx
# ─────────────────────────────────────────────────────────────────────────────
# Augmente la file d'attente des connexions entrantes.
# Défaut Raspberry Pi: 128 (trop bas pour des services web)
# Redis et Nginx bénéficient d'une valeur plus élevée.
net.core.somaxconn = 1024

# ─────────────────────────────────────────────────────────────────────────────
# SWAP - Optimisation carte SD
# ─────────────────────────────────────────────────────────────────────────────
# Réduit l'agressivité du swap pour préserver la carte SD.
# Défaut: 60 (swap agressif)
# Recommandé SD: 10 (swap uniquement si vraiment nécessaire)
vm.swappiness = 10

# ─────────────────────────────────────────────────────────────────────────────
# BUFFERS RÉSEAU - Stabilité des connexions longues (LinkedIn API)
# ─────────────────────────────────────────────────────────────────────────────
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216

# ─────────────────────────────────────────────────────────────────────────────
# KEEPALIVE TCP - Détection connexions mortes
# ─────────────────────────────────────────────────────────────────────────────
# Important pour les connexions WebSocket/SSE du dashboard
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 5

# ─────────────────────────────────────────────────────────────────────────────
# INOTIFY - Surveillance fichiers (Node.js hot reload, logs)
# ─────────────────────────────────────────────────────────────────────────────
fs.inotify.max_user_watches = 524288
EOF

log_success "Fichier de configuration créé."

# Appliquer immédiatement
log_info "Application des paramètres..."
sysctl -p "$SYSCTL_FILE"

# Afficher les nouvelles valeurs
echo ""
log_success "Nouvelles valeurs kernel :"
echo "  vm.overcommit_memory = $(cat /proc/sys/vm/overcommit_memory) ${GREEN}(Redis OK)${NC}"
echo "  net.core.somaxconn   = $(cat /proc/sys/net/core/somaxconn) ${GREEN}(TCP backlog OK)${NC}"
echo "  vm.swappiness        = $(cat /proc/sys/vm/swappiness) ${GREEN}(SD card OK)${NC}"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Configuration kernel terminée avec succès !${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Ces paramètres sont persistants et seront appliqués automatiquement"
echo "au prochain redémarrage du Raspberry Pi."
echo ""
echo "Pour vérifier la configuration à tout moment :"
echo "  cat /etc/sysctl.d/99-rpi4-docker.conf"
echo ""
