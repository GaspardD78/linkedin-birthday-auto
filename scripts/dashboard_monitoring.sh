#!/bin/bash

# =========================================================================
# Dashboard de Monitoring en Temps Réel pour LinkedIn Bot RPi4
# Affiche les métriques système, Docker et bot en temps réel
# =========================================================================

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
NC='\033[0m'
BOLD='\033[1m'

# --- Configuration ---
PROJECT_DIR="${PROJECT_DIR:-/home/pi/linkedin-birthday-auto}"
COMPOSE_FILE="docker-compose.pi4-standalone.yml"
REFRESH_INTERVAL=2

# Fonction pour effacer l'écran
clear_screen() {
    clear
}

# Fonction pour obtenir la température CPU
get_cpu_temp() {
    if command -v vcgencmd &> /dev/null; then
        vcgencmd measure_temp | grep -oP '\d+\.\d+' || echo "N/A"
    else
        echo "N/A"
    fi
}

# Fonction pour obtenir l'utilisation CPU
get_cpu_usage() {
    top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 || echo "0"
}

# Fonction pour obtenir la RAM
get_ram_usage() {
    free -m | awk '/Mem:/ {printf "%.1f", $3/$2*100}'
}

get_ram_info() {
    free -m | awk '/Mem:/ {printf "%dMB / %dMB", $3, $2}'
}

# Fonction pour obtenir le SWAP
get_swap_usage() {
    free -m | awk '/Swap:/ {if ($2 > 0) printf "%.1f", $3/$2*100; else print "0"}'
}

get_swap_info() {
    free -m | awk '/Swap:/ {printf "%dMB / %dMB", $3, $2}'
}

# Fonction pour obtenir l'espace disque
get_disk_usage() {
    df -h / | awk 'NR==2 {print $5}' | tr -d '%'
}

get_disk_info() {
    df -h / | awk 'NR==2 {print $3" / "$2}'
}

# Fonction pour obtenir l'uptime
get_uptime() {
    uptime -p | sed 's/up //'
}

# Fonction pour obtenir les stats Docker
get_docker_stats() {
    if ! docker info &> /dev/null; then
        echo "N/A"
        return
    fi

    local containers_running=$(docker ps -q | wc -l)
    local containers_total=$(docker ps -aq | wc -l)
    echo "${containers_running}/${containers_total}"
}

# Fonction pour obtenir le statut des services
get_service_status() {
    local service=$1
    local container_name=$2

    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        local state=$(docker inspect --format='{{.State.Status}}' "$container_name" 2>/dev/null || echo "unknown")
        local health=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "N/A")

        if [ "$state" = "running" ]; then
            if [ "$health" = "healthy" ]; then
                echo -e "${GREEN}●${NC} Running (Healthy)"
            elif [ "$health" = "unhealthy" ]; then
                echo -e "${RED}●${NC} Running (Unhealthy)"
            else
                echo -e "${GREEN}●${NC} Running"
            fi
        else
            echo -e "${RED}●${NC} $state"
        fi
    else
        echo -e "${RED}●${NC} Stopped"
    fi
}

# Fonction pour obtenir les stats de la base de données
get_db_stats() {
    local db_file="$PROJECT_DIR/data/linkedin.db"

    if [ -f "$db_file" ]; then
        local size=$(du -h "$db_file" | cut -f1)
        local messages=$(sqlite3 "$db_file" "SELECT COUNT(*) FROM messages;" 2>/dev/null || echo "N/A")
        local contacts=$(sqlite3 "$db_file" "SELECT COUNT(DISTINCT contact_name) FROM messages;" 2>/dev/null || echo "N/A")
        echo "Size: $size | Messages: $messages | Contacts: $contacts"
    else
        echo "Database not found"
    fi
}

# Fonction pour obtenir les derniers logs
get_recent_logs() {
    local service=$1
    local lines=${2:-5}

    docker logs "$service" --tail "$lines" 2>/dev/null | while IFS= read -r line; do
        # Coloration basique des logs
        if echo "$line" | grep -qi "error"; then
            echo -e "${RED}$line${NC}"
        elif echo "$line" | grep -qi "warning"; then
            echo -e "${YELLOW}$line${NC}"
        elif echo "$line" | grep -qi "success"; then
            echo -e "${GREEN}$line${NC}"
        else
            echo "$line"
        fi
    done
}

# Fonction pour créer une barre de progression
progress_bar() {
    local percentage=$1
    local width=30
    local filled=$((percentage * width / 100))
    local empty=$((width - filled))

    # Couleur selon le pourcentage
    local color=$GREEN
    if [ "$percentage" -gt 75 ]; then
        color=$YELLOW
    fi
    if [ "$percentage" -gt 90 ]; then
        color=$RED
    fi

    printf "${color}["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "]${NC} %3d%%" "$percentage"
}

# Fonction principale d'affichage
display_dashboard() {
    clear_screen

    # Entête
    echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║       LinkedIn Birthday Bot - Raspberry Pi 4 Monitoring Dashboard     ║${NC}"
    echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Informations système
    echo -e "${BOLD}${CYAN}┌─ SYSTÈME${NC}"
    echo -e "${CYAN}│${NC}"
    echo -e "${CYAN}│${NC} Hostname:    ${WHITE}$(hostname)${NC}"
    echo -e "${CYAN}│${NC} Uptime:      ${WHITE}$(get_uptime)${NC}"
    echo -e "${CYAN}│${NC} Date:        ${WHITE}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${CYAN}└${NC}"
    echo ""

    # Métriques système
    echo -e "${BOLD}${MAGENTA}┌─ RESSOURCES${NC}"
    echo -e "${MAGENTA}│${NC}"

    # CPU
    local cpu_usage=$(get_cpu_usage)
    local cpu_temp=$(get_cpu_temp)
    echo -e "${MAGENTA}│${NC} CPU Usage:   $(progress_bar "${cpu_usage%.*}")"
    echo -e "${MAGENTA}│${NC} CPU Temp:    ${WHITE}${cpu_temp}°C${NC}"

    # RAM
    local ram_usage=$(get_ram_usage)
    local ram_info=$(get_ram_info)
    echo -e "${MAGENTA}│${NC} RAM Usage:   $(progress_bar "${ram_usage%.*}")"
    echo -e "${MAGENTA}│${NC}              ${WHITE}${ram_info}${NC}"

    # SWAP
    local swap_usage=$(get_swap_usage)
    local swap_info=$(get_swap_info)
    echo -e "${MAGENTA}│${NC} SWAP Usage:  $(progress_bar "${swap_usage%.*}")"
    echo -e "${MAGENTA}│${NC}              ${WHITE}${swap_info}${NC}"

    # Disque
    local disk_usage=$(get_disk_usage)
    local disk_info=$(get_disk_info)
    echo -e "${MAGENTA}│${NC} Disk Usage:  $(progress_bar "$disk_usage")"
    echo -e "${MAGENTA}│${NC}              ${WHITE}${disk_info}${NC}"
    echo -e "${MAGENTA}└${NC}"
    echo ""

    # Services Docker
    echo -e "${BOLD}${YELLOW}┌─ DOCKER SERVICES${NC}"
    echo -e "${YELLOW}│${NC}"
    echo -e "${YELLOW}│${NC} Containers:  ${WHITE}$(get_docker_stats)${NC}"
    echo -e "${YELLOW}│${NC}"
    echo -e "${YELLOW}│${NC} Bot Worker:  $(get_service_status 'bot-worker' 'linkedin-bot-worker')"
    echo -e "${YELLOW}│${NC} Dashboard:   $(get_service_status 'dashboard' 'linkedin-dashboard')"
    echo -e "${YELLOW}│${NC} API:         $(get_service_status 'api' 'linkedin-bot-api')"
    echo -e "${YELLOW}│${NC} Redis Bot:   $(get_service_status 'redis-bot' 'linkedin-bot-redis')"
    echo -e "${YELLOW}│${NC} Redis Dash:  $(get_service_status 'redis-dashboard' 'linkedin-dashboard-redis')"
    echo -e "${YELLOW}└${NC}"
    echo ""

    # Base de données
    echo -e "${BOLD}${GREEN}┌─ BASE DE DONNÉES${NC}"
    echo -e "${GREEN}│${NC}"
    echo -e "${GREEN}│${NC} $(get_db_stats)"
    echo -e "${GREEN}└${NC}"
    echo ""

    # Logs récents
    echo -e "${BOLD}${WHITE}┌─ LOGS RÉCENTS (Bot Worker)${NC}"
    echo -e "${WHITE}│${NC}"
    if docker ps --format '{{.Names}}' | grep -q "linkedin-bot-worker"; then
        get_recent_logs "linkedin-bot-worker" 5 | while IFS= read -r line; do
            echo -e "${WHITE}│${NC} $line"
        done
    else
        echo -e "${WHITE}│${NC} ${RED}Container stopped${NC}"
    fi
    echo -e "${WHITE}└${NC}"
    echo ""

    # Footer
    echo -e "${BLUE}────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "${CYAN}Press Ctrl+C to exit | Refresh: ${REFRESH_INTERVAL}s${NC}"
}

# Fonction pour gérer Ctrl+C
cleanup() {
    clear_screen
    echo -e "${GREEN}Dashboard arrêté.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Boucle principale
echo -e "${CYAN}Démarrage du dashboard...${NC}"
sleep 1

while true; do
    display_dashboard
    sleep "$REFRESH_INTERVAL"
done
