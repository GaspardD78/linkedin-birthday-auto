#!/bin/bash

# =========================================================================
# Script de monitoring léger des ressources Pi4
# =========================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() { echo -e "\n${BLUE}=== $1 ===${NC}\n"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }

# Intervalle de monitoring (secondes)
INTERVAL=${1:-300}  # Par défaut 5 minutes

print_header "🔍 Monitoring Raspberry Pi 4 - Interval: ${INTERVAL}s"
echo "Appuyez sur Ctrl+C pour arrêter"
echo ""

while true; do
    clear
    echo "=========================================="
    echo "📊 RASPBERRY PI 4 - MONITORING"
    echo "$(date '+%Y-%m-%d %H:%M:%S')"
    echo "=========================================="
    echo ""

    # Température CPU
    print_header "🌡️  Température CPU"
    TEMP=$(vcgencmd measure_temp 2>/dev/null | grep -oP '\d+\.\d+' || echo "N/A")
    if [ "$TEMP" != "N/A" ]; then
        if (( $(echo "$TEMP > 70" | bc -l 2>/dev/null || echo 0) )); then
            print_error "Température: ${TEMP}°C (ÉLEVÉE!)"
        elif (( $(echo "$TEMP > 60" | bc -l 2>/dev/null || echo 0) )); then
            print_warning "Température: ${TEMP}°C"
        else
            print_success "Température: ${TEMP}°C"
        fi
    else
        echo "Température: N/A (vcgencmd non disponible)"
    fi

    # RAM
    print_header "💾 Mémoire RAM"
    free -h | awk '/Mem:/ {
        used_gb = $3;
        total_gb = $2;
        percent = ($3/$2)*100;
        printf "  Utilisée: %s / %s (%.1f%%)\n", used_gb, total_gb, percent;
        if (percent > 85) print "  ⚠️ Utilisation RAM élevée!";
        else if (percent > 70) print "  ⚠️ Utilisation RAM modérée";
        else print "  ✅ RAM OK";
    }'

    # SWAP
    print_header "💿 Mémoire SWAP"
    SWAP_USED=$(free -h | awk '/Swap:/ {print $3}')
    SWAP_TOTAL=$(free -h | awk '/Swap:/ {print $2}')
    SWAP_PERCENT=$(free | awk '/Swap:/ {if ($2 > 0) printf "%.1f", ($3/$2)*100; else print "0"}')

    echo "  Utilisé: ${SWAP_USED} / ${SWAP_TOTAL} (${SWAP_PERCENT}%)"
    if (( $(echo "$SWAP_PERCENT > 50" | bc -l 2>/dev/null || echo 0) )); then
        print_error "  Utilisation SWAP élevée! (usure SD card)"
    elif (( $(echo "$SWAP_PERCENT > 20" | bc -l 2>/dev/null || echo 0) )); then
        print_warning "  Utilisation SWAP modérée"
    else
        print_success "  SWAP OK"
    fi

    # ZRAM (si installé)
    if lsmod | grep -q zram; then
        print_header "🗜️  ZRAM (Compression)"
        zramctl --output NAME,DISKSIZE,DATA,COMPR,TOTAL 2>/dev/null || echo "  Installé mais stats non disponibles"
    fi

    # Disque
    print_header "💾 Espace Disque (SD Card)"
    df -h / | awk 'NR==2 {
        printf "  Utilisé: %s / %s (%s)\n", $3, $2, $5;
        percent = int($5);
        if (percent > 85) print "  ⚠️ Espace faible!";
        else if (percent > 70) print "  ⚠️ Espace modéré";
        else print "  ✅ Espace OK";
    }'

    # Conteneurs Docker
    print_header "🐳 Conteneurs Docker"
    if docker ps &>/dev/null; then
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" | \
        awk 'NR==1 {print "  " $0} NR>1 {print "  " $0}'
    else
        echo "  Docker non disponible ou non démarré"
    fi

    # Charge système
    print_header "⚙️  Charge Système"
    LOAD=$(uptime | grep -oP 'load average: \K[0-9.]+')
    echo "  Load Average (1min): ${LOAD}"
    if (( $(echo "$LOAD > 3.0" | bc -l 2>/dev/null || echo 0) )); then
        print_error "  Charge système élevée!"
    elif (( $(echo "$LOAD > 2.0" | bc -l 2>/dev/null || echo 0) )); then
        print_warning "  Charge système modérée"
    else
        print_success "  Charge système normale"
    fi

    # Uptime
    echo ""
    echo "⏱️  Uptime: $(uptime -p 2>/dev/null || uptime | awk '{print $3,$4}')"

    echo ""
    echo "=========================================="
    echo "Prochain rafraîchissement dans ${INTERVAL}s..."
    echo "=========================================="

    sleep "$INTERVAL"
done
