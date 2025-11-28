#!/bin/bash

# =========================================================================
# Script d'installation complète de l'automatisation LinkedIn Bot pour RPi4
# Ce script configure le démarrage automatique, le monitoring et les backups
# =========================================================================

set -e  # Arrêt immédiat en cas d'erreur

# --- Configuration ---
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
SYSTEMD_DIR="/etc/systemd/system"
USER="${SUDO_USER:-$(whoami)}"

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Fonctions ---
print_header() { echo -e "\n${BLUE}=== $1 ===${NC}\n"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "ℹ️  $1"; }

# Vérification des droits root
if [ "$EUID" -ne 0 ]; then
    print_error "Ce script doit être exécuté avec sudo"
    print_info "Usage: sudo ./scripts/install_automation_pi4.sh"
    exit 1
fi

# Vérification de l'emplacement
if [ ! -f "docker-compose.pi4-standalone.yml" ]; then
    print_error "Fichier docker-compose.pi4-standalone.yml introuvable !"
    print_info "Exécutez ce script à la racine du projet."
    exit 1
fi

print_header "🚀 Installation Automatisation LinkedIn Bot RPi4"
echo "Projet: $PROJECT_DIR"
echo "Utilisateur: $USER"
echo ""

# =========================================================================
# 1. Vérification des prérequis
# =========================================================================
print_header "1. Vérification des Prérequis"

# Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker n'est pas installé"
    print_info "Installez Docker: curl -fsSL https://get.docker.com | sh"
    exit 1
fi
print_success "Docker installé"

# Docker Compose V2
if ! docker compose version &> /dev/null; then
    print_error "Docker Compose V2 n'est pas installé"
    print_info "Installez avec: sudo apt install docker-compose-plugin"
    exit 1
fi
print_success "Docker Compose V2 installé"

# Permissions Docker
if ! groups "$USER" | grep -q docker; then
    print_warning "L'utilisateur $USER n'est pas dans le groupe docker"
    print_info "Ajout au groupe docker..."
    usermod -aG docker "$USER"
    print_success "Utilisateur ajouté au groupe docker (redémarrage nécessaire)"
fi

# =========================================================================
# 2. Configuration Système
# =========================================================================
print_header "2. Configuration Système"

# Vérification SWAP
SWAP_TOTAL=$(free -m | awk '/Swap:/ {print $2}')
if [ "$SWAP_TOTAL" -lt 2000 ]; then
    print_warning "SWAP insuffisant (${SWAP_TOTAL}MB). Configuration..."

    # Backup de la config actuelle
    cp /etc/dphys-swapfile /etc/dphys-swapfile.backup

    # Configuration SWAP à 2GB
    sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile

    # Redémarrage du service SWAP
    dphys-swapfile swapoff || true
    dphys-swapfile setup
    dphys-swapfile swapon

    SWAP_NEW=$(free -m | awk '/Swap:/ {print $2}')
    print_success "SWAP configuré à ${SWAP_NEW}MB"
else
    print_success "SWAP OK (${SWAP_TOTAL}MB)"
fi

# Configuration sysctl pour Docker
print_info "Configuration sysctl pour optimisation Docker..."
cat > /etc/sysctl.d/99-docker-linkedin.conf << 'EOF'
# Optimisations pour LinkedIn Bot Docker
vm.overcommit_memory = 1
net.core.somaxconn = 511
vm.swappiness = 10
EOF

sysctl -p /etc/sysctl.d/99-docker-linkedin.conf > /dev/null 2>&1
print_success "Sysctl configuré"

# =========================================================================
# 3. Installation des Services Systemd
# =========================================================================
print_header "3. Installation Services Systemd"

# Création du répertoire de déploiement
mkdir -p deployment/systemd

# Copie des fichiers service
print_info "Installation linkedin-bot.service..."
sed "s|/home/pi/linkedin-birthday-auto|$PROJECT_DIR|g" \
    deployment/systemd/linkedin-bot.service > "${SYSTEMD_DIR}/linkedin-bot.service"
print_success "linkedin-bot.service installé"

print_info "Installation linkedin-bot-monitor.service..."
sed "s|/home/pi/linkedin-birthday-auto|$PROJECT_DIR|g" \
    deployment/systemd/linkedin-bot-monitor.service > "${SYSTEMD_DIR}/linkedin-bot-monitor.service"
print_success "linkedin-bot-monitor.service installé"

print_info "Installation linkedin-bot-monitor.timer..."
cp deployment/systemd/linkedin-bot-monitor.timer "${SYSTEMD_DIR}/"
print_success "linkedin-bot-monitor.timer installé"

print_info "Installation linkedin-bot-backup.service..."
sed "s|/home/pi/linkedin-birthday-auto|$PROJECT_DIR|g" \
    deployment/systemd/linkedin-bot-backup.service > "${SYSTEMD_DIR}/linkedin-bot-backup.service"
print_success "linkedin-bot-backup.service installé"

print_info "Installation linkedin-bot-backup.timer..."
cp deployment/systemd/linkedin-bot-backup.timer "${SYSTEMD_DIR}/"
print_success "linkedin-bot-backup.timer installé"

# Rechargement systemd
systemctl daemon-reload
print_success "Systemd rechargé"

# =========================================================================
# 4. Création des Scripts de Monitoring et Backup
# =========================================================================
print_header "4. Création Scripts Auxiliaires"

# Script de monitoring
print_info "Création script de monitoring..."
cat > scripts/monitor_pi4_health.sh << 'MONITOR_EOF'
#!/bin/bash
# Script de monitoring des ressources Pi4
LOG_FILE="/var/log/linkedin-bot-health.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Température CPU
CPU_TEMP=$(vcgencmd measure_temp | grep -oP '\d+\.\d+')

# Utilisation RAM
RAM_USED=$(free -m | awk '/Mem:/ {printf "%.1f", $3/$2*100}')
RAM_MB=$(free -m | awk '/Mem:/ {printf "%d/%dMB", $3, $2}')

# Utilisation CPU
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)

# Espace disque
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
DISK_INFO=$(df -h / | awk 'NR==2 {print $3"/"$2}')

# État Docker
DOCKER_STATUS=$(docker compose -f /home/pi/linkedin-birthday-auto/docker-compose.pi4-standalone.yml ps --format json 2>/dev/null | jq -r '.[].State' | grep -c "running" || echo "0")

# Log
echo "[$DATE] CPU: ${CPU_USAGE}% | Temp: ${CPU_TEMP}°C | RAM: ${RAM_USED}% (${RAM_MB}) | Disk: ${DISK_USAGE}% (${DISK_INFO}) | Containers: ${DOCKER_STATUS}/4" >> "$LOG_FILE"

# Alertes
if (( $(echo "$CPU_TEMP > 75" | bc -l) )); then
    echo "[$DATE] ⚠️ ALERT: Temperature critique (${CPU_TEMP}°C)" >> "$LOG_FILE"
fi

if (( $(echo "$RAM_USED > 90" | bc -l) )); then
    echo "[$DATE] ⚠️ ALERT: RAM critique (${RAM_USED}%)" >> "$LOG_FILE"
fi

if [ "$DISK_USAGE" -gt 85 ]; then
    echo "[$DATE] ⚠️ ALERT: Disque critique (${DISK_USAGE}%)" >> "$LOG_FILE"
fi

# Rotation des logs (garder 1000 dernières lignes)
tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"

exit 0
MONITOR_EOF

chmod +x scripts/monitor_pi4_health.sh
chown "$USER:$USER" scripts/monitor_pi4_health.sh
print_success "Script de monitoring créé"

# Script de backup
print_info "Création script de backup..."
cat > scripts/backup_database.sh << 'BACKUP_EOF'
#!/bin/bash
# Script de backup automatique de la base de données

PROJECT_DIR="/home/pi/linkedin-birthday-auto"
BACKUP_DIR="$PROJECT_DIR/backups"
DB_FILE="$PROJECT_DIR/data/linkedin.db"
DATE=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="$BACKUP_DIR/linkedin_db_${DATE}.db"
LOG_FILE="/var/log/linkedin-bot-backup.log"

# Création du répertoire de backup
mkdir -p "$BACKUP_DIR"

# Backup de la DB
if [ -f "$DB_FILE" ]; then
    cp "$DB_FILE" "$BACKUP_FILE"
    gzip "$BACKUP_FILE"

    # Log
    SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Backup créé: ${BACKUP_FILE}.gz ($SIZE)" >> "$LOG_FILE"

    # Nettoyage (garder 30 derniers backups)
    cd "$BACKUP_DIR" && ls -t linkedin_db_*.db.gz | tail -n +31 | xargs -r rm
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🧹 Anciens backups nettoyés" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ Erreur: Base de données introuvable" >> "$LOG_FILE"
    exit 1
fi

exit 0
BACKUP_EOF

chmod +x scripts/backup_database.sh
chown "$USER:$USER" scripts/backup_database.sh
print_success "Script de backup créé"

# Correction des chemins dans les scripts
sed -i "s|/home/pi/linkedin-birthday-auto|$PROJECT_DIR|g" scripts/monitor_pi4_health.sh
sed -i "s|/home/pi/linkedin-birthday-auto|$PROJECT_DIR|g" scripts/backup_database.sh

# =========================================================================
# 5. Activation des Services
# =========================================================================
print_header "5. Activation des Services"

print_info "Activation démarrage automatique..."
systemctl enable linkedin-bot.service
print_success "linkedin-bot.service activé"

print_info "Activation monitoring horaire..."
systemctl enable linkedin-bot-monitor.timer
systemctl start linkedin-bot-monitor.timer
print_success "linkedin-bot-monitor.timer activé"

print_info "Activation backup quotidien..."
systemctl enable linkedin-bot-backup.timer
systemctl start linkedin-bot-backup.timer
print_success "linkedin-bot-backup.timer activé"

# =========================================================================
# 6. Test du Monitoring
# =========================================================================
print_header "6. Test du Monitoring"

print_info "Exécution du premier monitoring..."
sudo -u "$USER" bash scripts/monitor_pi4_health.sh

if [ -f "/var/log/linkedin-bot-health.log" ]; then
    print_success "Monitoring fonctionnel"
    tail -1 /var/log/linkedin-bot-health.log
else
    print_warning "Log de monitoring non créé"
fi

# =========================================================================
# 7. Résumé Final
# =========================================================================
print_header "✅ Installation Terminée"

cat << EOF

📋 Services installés:
  • linkedin-bot.service         - Démarrage automatique au boot
  • linkedin-bot-monitor.timer   - Monitoring toutes les heures
  • linkedin-bot-backup.timer    - Backup quotidien à 3h du matin

📁 Fichiers créés:
  • /etc/systemd/system/linkedin-bot.service
  • /etc/systemd/system/linkedin-bot-monitor.{service,timer}
  • /etc/systemd/system/linkedin-bot-backup.{service,timer}
  • $PROJECT_DIR/scripts/monitor_pi4_health.sh
  • $PROJECT_DIR/scripts/backup_database.sh

📊 Commandes utiles:
  • Démarrer:     sudo systemctl start linkedin-bot
  • Arrêter:      sudo systemctl stop linkedin-bot
  • Redémarrer:   sudo systemctl restart linkedin-bot
  • Statut:       sudo systemctl status linkedin-bot
  • Logs service: sudo journalctl -u linkedin-bot -f
  • Logs health:  tail -f /var/log/linkedin-bot-health.log
  • Logs backup:  tail -f /var/log/linkedin-bot-backup.log

🔄 Prochaines étapes:
  1. Redémarrez le Pi pour appliquer tous les changements:
     sudo reboot

  2. Après redémarrage, vérifiez que tout fonctionne:
     sudo systemctl status linkedin-bot
     docker compose -f docker-compose.pi4-standalone.yml ps

${YELLOW}⚠️  IMPORTANT: Le service démarrera automatiquement au boot!${NC}
${YELLOW}   Si vous ne voulez pas de démarrage auto, exécutez:${NC}
${YELLOW}   sudo systemctl disable linkedin-bot${NC}

EOF

print_success "Installation complète réussie! 🎉"

exit 0
