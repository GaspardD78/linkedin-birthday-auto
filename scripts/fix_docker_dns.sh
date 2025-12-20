#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# DOCKER DNS FIX - Script Standalone
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   ./scripts/fix_docker_dns.sh              # Mode auto (diagnostic + fix)
#   ./scripts/fix_docker_dns.sh --test-only  # Diagnostic seul
#   ./scripts/fix_docker_dns.sh --force      # Forcer la reconfiguration
#
# Description:
#   Résout les problèmes DNS dans les conteneurs Docker sur Raspberry Pi.
#   Voir docs/DOCKER_DNS_ANALYSIS.md pour l'analyse technique complète.
#
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Détecter le répertoire du script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Charger les dépendances
if [[ -f "$PROJECT_ROOT/scripts/lib/common.sh" ]]; then
    source "$PROJECT_ROOT/scripts/lib/common.sh"
else
    # Fallback minimal si common.sh non disponible
    log_info() { echo "[INFO] $*"; }
    log_success() { echo "[✓] $*"; }
    log_warn() { echo "[⚠️ ] $*"; }
    log_error() { echo "[✗] $*" >&2; }
    cmd_exists() { command -v "$1" &>/dev/null; }
fi

# Charger le module DNS Fix
if [[ -f "$PROJECT_ROOT/scripts/lib/docker_dns_fix.sh" ]]; then
    source "$PROJECT_ROOT/scripts/lib/docker_dns_fix.sh"
else
    log_error "Module docker_dns_fix.sh introuvable: $PROJECT_ROOT/scripts/lib/docker_dns_fix.sh"
    exit 1
fi

# Afficher le header
cat <<'EOF'

╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   🐳 DOCKER DNS FIX - Raspberry Pi 4                                      ║
║                                                                           ║
║   Résout les problèmes de résolution DNS dans les conteneurs Docker      ║
║   causés par systemd-resolved + Freebox DNS lents                        ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

EOF

# Parser les arguments et appeler la fonction principale
fix_docker_dns "$@"
exit_code=$?

# Afficher le footer selon le résultat
if [[ $exit_code -eq 0 ]]; then
    cat <<'EOF'

╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   ✅ SUCCÈS - Configuration DNS Docker opérationnelle                     ║
║                                                                           ║
║   📚 Documentation: docs/DOCKER_DNS_ANALYSIS.md                           ║
║   🔧 Configuration: /etc/docker/daemon.json                               ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

EOF
else
    cat <<'EOF'

╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   ⚠️  ATTENTION - Vérifications requises                                  ║
║                                                                           ║
║   📖 Consultez: docs/DOCKER_DNS_ANALYSIS.md (section Dépannage)          ║
║   🆘 Support: Créer une issue GitHub avec les logs                       ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

EOF
fi

exit $exit_code
