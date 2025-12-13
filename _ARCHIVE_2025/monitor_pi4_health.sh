#!/bin/bash
# Script de monitoring des ressources Pi4
# Version corrigée avec chemins relatifs

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${PROJECT_DIR}/logs/health.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# S'assurer que le dossier logs existe
mkdir -p "${PROJECT_DIR}/logs"

# Température CPU
if command -v vcgencmd &> /dev/null; then
    CPU_TEMP=$(vcgencmd measure_temp | grep -oP '\d+\.\d+' || echo "0")
else
    CPU_TEMP="0"
fi

# Utilisation RAM
RAM_USED=$(free -m | awk '/Mem:/ {printf "%.1f", $3/$2*100}')
RAM_MB=$(free -m | awk '/Mem:/ {printf "%d/%dMB", $3, $2}')

# Utilisation CPU
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 || echo "0")

# Espace disque
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
DISK_INFO=$(df -h / | awk 'NR==2 {print $3"/"$2}')

# État Docker
if command -v docker &> /dev/null; then
    DOCKER_STATUS=$(docker compose -f "${PROJECT_DIR}/docker-compose.pi4-standalone.yml" ps --format json 2>/dev/null | grep -c "running" || echo "0")
else
    DOCKER_STATUS="N/A"
fi

# Log
echo "[$DATE] CPU: ${CPU_USAGE}% | Temp: ${CPU_TEMP}°C | RAM: ${RAM_USED}% (${RAM_MB}) | Disk: ${DISK_USAGE}% (${DISK_INFO}) | Containers: ${DOCKER_STATUS}" >> "$LOG_FILE"

# Rotation des logs (garder 1000 dernières lignes)
if [ -f "$LOG_FILE" ]; then
    tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi

exit 0
