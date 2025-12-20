#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# DOCKER DNS FIX - Production-Ready Solution for Raspberry Pi
# ═══════════════════════════════════════════════════════════════════════════════
#
# OBJECTIF:
#   Résoudre les problèmes de résolution DNS dans les conteneurs Docker sur RPi,
#   causés par le conflit systemd-resolved + Freebox DNS lents.
#
# APPROCHE:
#   1. Tester la santé DNS actuelle (host + conteneur)
#   2. Configurer /etc/docker/daemon.json avec DNS fiables + fallbacks
#   3. Vérifier l'idempotence (ne pas écraser la config existante)
#   4. Tester immédiatement après modification
#
# PHILOSOPHIE:
#   - Sécurité: Backup avant modification
#   - Performance: DNS multiples avec fallback intelligent
#   - Vie privée: Option pour DNS respectueux (Quad9, Cloudflare)
#   - Portabilité: Fonctionne sur changement de réseau (WiFi mobile, etc.)
#
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === CONSTANTS ===

readonly DAEMON_JSON="/etc/docker/daemon.json"
readonly DNS_TEST_DOMAIN="google.com"
readonly DNS_TIMEOUT_MS=2000  # Timeout pour les tests DNS
readonly MAX_LATENCY_MS=100   # Latence max acceptable pour DNS host

# DNS Providers (classés par priorité : Vie privée > Performance)
# Quad9     : 9.9.9.9      - Bloque malware, respecte vie privée
# Cloudflare: 1.1.1.1      - Rapide, vie privée correcte
# Google    : 8.8.8.8      - Très rapide, collecte metadata
# OpenDNS   : 208.67.222.222 - Alternatif fiable

readonly DNS_PRIMARY="1.1.1.1"         # Cloudflare (rapide + vie privée)
readonly DNS_SECONDARY="8.8.8.8"       # Google (fallback ultra-fiable)
readonly DNS_TERTIARY="9.9.9.9"        # Quad9 (sécurité)
readonly DNS_QUATERNARY="208.67.222.222" # OpenDNS (diversité)

# === LOGGING (assume common.sh is sourced) ===

log_dns() {
    local level="$1"
    shift
    case "$level" in
        info)    log_info "$@" ;;
        success) log_success "$@" ;;
        warn)    log_warn "$@" ;;
        error)   log_error "$@" ;;
    esac
}

# === DIAGNOSTIC FUNCTIONS ===

# Tester la latence d'un serveur DNS
# Usage: test_dns_latency <dns_ip>
# Return: latency en ms (ou 9999 si échec)
test_dns_latency() {
    local dns_server="$1"
    local start_time end_time latency

    start_time=$(date +%s%N)

    # Tester avec dig (si disponible) ou nslookup
    if cmd_exists dig; then
        if dig @"$dns_server" "$DNS_TEST_DOMAIN" +time=2 +tries=1 &>/dev/null; then
            end_time=$(date +%s%N)
            latency=$(( (end_time - start_time) / 1000000 ))  # Convertir ns -> ms
            echo "$latency"
            return 0
        fi
    elif cmd_exists nslookup; then
        if timeout 2 nslookup "$DNS_TEST_DOMAIN" "$dns_server" &>/dev/null; then
            end_time=$(date +%s%N)
            latency=$(( (end_time - start_time) / 1000000 ))
            echo "$latency"
            return 0
        fi
    fi

    # Échec
    echo "9999"
    return 1
}

# Tester si les DNS de l'hôte fonctionnent correctement
# Return: 0 si OK, 1 si KO
check_host_dns_health() {
    log_dns info "🔍 Diagnostic DNS de l'hôte..."

    # Test 1: Résolution basique
    if ! getent hosts "$DNS_TEST_DOMAIN" &>/dev/null; then
        log_dns error "❌ L'hôte ne peut pas résoudre $DNS_TEST_DOMAIN"
        return 1
    fi

    # Test 2: Latence acceptable ?
    local host_dns
    host_dns=$(grep -v "^#" /etc/resolv.conf 2>/dev/null | grep nameserver | head -1 | awk '{print $2}')

    if [[ -z "$host_dns" ]]; then
        log_dns warn "⚠️  Impossible de détecter le DNS de l'hôte"
        return 1
    fi

    # Si c'est systemd-resolved (127.0.0.53), extraire le vrai DNS
    if [[ "$host_dns" == "127.0.0.53" ]]; then
        if cmd_exists resolvectl; then
            host_dns=$(resolvectl status 2>/dev/null | \
                       grep "DNS Servers" | \
                       head -1 | \
                       awk '{print $3}')
        fi
    fi

    local latency
    latency=$(test_dns_latency "$host_dns")

    if [[ "$latency" -gt "$MAX_LATENCY_MS" ]]; then
        log_dns warn "⚠️  DNS de l'hôte lent: ${latency}ms (seuil: ${MAX_LATENCY_MS}ms)"
        log_dns warn "    DNS testé: $host_dns"
        return 1
    fi

    log_dns success "✓ DNS de l'hôte fonctionnel (${latency}ms)"
    return 0
}

# Tester si Docker peut résoudre DNS dans un conteneur
# Return: 0 si OK, 1 si KO
check_docker_dns_health() {
    log_dns info "🐳 Test DNS dans un conteneur Docker..."

    if ! docker run --rm alpine:latest nslookup "$DNS_TEST_DOMAIN" &>/dev/null; then
        log_dns error "❌ Les conteneurs Docker ne peuvent PAS résoudre DNS"
        return 1
    fi

    log_dns success "✓ DNS fonctionnel dans les conteneurs"
    return 0
}

# === CONFIGURATION FUNCTIONS ===

# Backup du daemon.json existant
backup_daemon_json() {
    if [[ -f "$DAEMON_JSON" ]]; then
        local backup_file="${DAEMON_JSON}.backup.$(date +%Y%m%d_%H%M%S)"
        sudo cp "$DAEMON_JSON" "$backup_file"
        log_dns success "✓ Backup créé: $backup_file"
    fi
}

# Vérifier si la configuration DNS est déjà présente
# Return: 0 si DNS déjà configuré, 1 sinon
is_dns_already_configured() {
    if [[ ! -f "$DAEMON_JSON" ]]; then
        return 1
    fi

    # Vérifier si le fichier contient déjà une config DNS
    if jq -e '.dns' "$DAEMON_JSON" &>/dev/null; then
        local current_dns
        current_dns=$(jq -r '.dns[]' "$DAEMON_JSON" 2>/dev/null | tr '\n' ' ')
        log_dns info "Configuration DNS existante détectée: $current_dns"
        return 0
    fi

    return 1
}

# Appliquer la configuration DNS (idempotent)
# Return: 0 si modification faite, 1 si déjà configuré, 2 si erreur
apply_dns_configuration() {
    log_dns info "⚙️  Configuration Docker DNS..."

    # Vérifier si jq est installé
    if ! cmd_exists jq; then
        log_dns error "jq n'est pas installé (requis pour manipuler JSON)"
        log_dns info "Installation: sudo apt install jq"
        return 2
    fi

    # Créer daemon.json s'il n'existe pas
    if [[ ! -f "$DAEMON_JSON" ]]; then
        log_dns info "Création de $DAEMON_JSON (nouveau fichier)"
        echo '{}' | sudo tee "$DAEMON_JSON" >/dev/null
    else
        # Backup du fichier existant
        backup_daemon_json
    fi

    # Vérifier si DNS déjà configuré
    if is_dns_already_configured; then
        log_dns info "DNS déjà configuré dans daemon.json"

        # Demander si on veut forcer la reconfiguration
        if declare -f prompt_yes_no &>/dev/null; then
            if ! prompt_yes_no "Voulez-vous forcer la reconfiguration DNS ?" "n"; then
                log_dns info "Configuration conservée (pas de modification)"
                return 1
            fi
        else
            log_dns warn "Fonction prompt_yes_no non disponible, conservation de la config existante"
            return 1
        fi
    fi

    # Construire la nouvelle configuration (MERGE avec l'existant)
    local temp_file
    temp_file=$(mktemp)

    # Utiliser jq pour merger proprement
    jq --arg dns1 "$DNS_PRIMARY" \
       --arg dns2 "$DNS_SECONDARY" \
       --arg dns3 "$DNS_TERTIARY" \
       --arg dns4 "$DNS_QUATERNARY" \
       '. + {
         "dns": [$dns1, $dns2, $dns3, $dns4],
         "dns-opts": ["timeout:2", "attempts:3", "ndots:0"]
       }' "$DAEMON_JSON" > "$temp_file"

    # Valider le JSON généré
    if ! jq empty "$temp_file" 2>/dev/null; then
        log_dns error "JSON généré invalide (vérifiez le fichier)"
        rm -f "$temp_file"
        return 2
    fi

    # Appliquer la configuration
    sudo mv "$temp_file" "$DAEMON_JSON"
    sudo chmod 644 "$DAEMON_JSON"

    log_dns success "✓ Configuration DNS appliquée:"
    log_dns info "  - DNS primaire   : $DNS_PRIMARY (Cloudflare)"
    log_dns info "  - DNS secondaire : $DNS_SECONDARY (Google)"
    log_dns info "  - DNS tertiaire  : $DNS_TERTIARY (Quad9)"
    log_dns info "  - DNS quaternaire: $DNS_QUATERNARY (OpenDNS)"
    log_dns info "  - Options        : timeout 2s, 3 tentatives"

    return 0
}

# Redémarrer Docker daemon
restart_docker_daemon() {
    log_dns info "🔄 Redémarrage du démon Docker..."

    if ! sudo systemctl restart docker; then
        log_dns error "Échec du redémarrage Docker"
        return 1
    fi

    # Attendre que Docker soit prêt
    local max_wait=30
    local waited=0
    while ! docker info &>/dev/null; do
        sleep 1
        waited=$((waited + 1))
        if [[ $waited -ge $max_wait ]]; then
            log_dns error "Docker ne répond pas après ${max_wait}s"
            return 1
        fi
    done

    log_dns success "✓ Docker redémarré (${waited}s)"
    return 0
}

# === TESTING FUNCTIONS ===

# Test complet post-configuration
test_dns_post_fix() {
    log_dns info "🧪 Tests de validation DNS..."

    # Test 1: Résolution simple
    if ! docker run --rm alpine:latest nslookup google.com &>/dev/null; then
        log_dns error "❌ Test 1/4 échoué: Résolution DNS basique"
        return 1
    fi
    log_dns success "✓ Test 1/4: Résolution DNS basique OK"

    # Test 2: Résolution de pypi.org (critique pour pip install)
    if ! docker run --rm alpine:latest nslookup pypi.org &>/dev/null; then
        log_dns error "❌ Test 2/4 échoué: pypi.org (requis pour Python)"
        return 1
    fi
    log_dns success "✓ Test 2/4: pypi.org accessible"

    # Test 3: Résolution de archive.ubuntu.com (critique pour apt)
    if ! docker run --rm alpine:latest nslookup archive.ubuntu.com &>/dev/null; then
        log_dns error "❌ Test 3/4 échoué: archive.ubuntu.com (requis pour apt)"
        return 1
    fi
    log_dns success "✓ Test 3/4: archive.ubuntu.com accessible"

    # Test 4: Téléchargement réel (test HTTP)
    if ! docker run --rm alpine:latest wget -q --spider --timeout=5 https://www.google.com &>/dev/null; then
        log_dns warn "⚠️  Test 4/4 échoué: Téléchargement HTTP (peut être un problème réseau)"
        return 1
    fi
    log_dns success "✓ Test 4/4: Téléchargement HTTP OK"

    log_dns success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_dns success "✅ TOUS LES TESTS PASSÉS - DNS FONCTIONNEL"
    log_dns success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    return 0
}

# === MAIN FUNCTION ===

# Point d'entrée principal
# Usage: fix_docker_dns [--force] [--test-only]
fix_docker_dns() {
    local force_mode=false
    local test_only=false

    # Parser les arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --force)
                force_mode=true
                shift
                ;;
            --test-only)
                test_only=true
                shift
                ;;
            *)
                log_dns error "Argument inconnu: $1"
                log_dns info "Usage: fix_docker_dns [--force] [--test-only]"
                return 2
                ;;
        esac
    done

    log_dns info "═══════════════════════════════════════════════════════════════"
    log_dns info "  DOCKER DNS FIX - Diagnostic & Correction Automatique"
    log_dns info "═══════════════════════════════════════════════════════════════"

    # PHASE 1: Diagnostic
    local needs_fix=false

    if ! check_host_dns_health; then
        log_dns warn "⚠️  DNS de l'hôte problématique"
        needs_fix=true
    fi

    if ! check_docker_dns_health; then
        log_dns warn "⚠️  DNS Docker non fonctionnel"
        needs_fix=true
    fi

    # Si --test-only, arrêter ici
    if [[ "$test_only" == "true" ]]; then
        if [[ "$needs_fix" == "true" ]]; then
            log_dns warn "Diagnostic: Fix DNS nécessaire (relancer sans --test-only)"
            return 1
        else
            log_dns success "Diagnostic: Aucun fix nécessaire"
            return 0
        fi
    fi

    # PHASE 2: Décision
    if [[ "$needs_fix" == "false" && "$force_mode" == "false" ]]; then
        log_dns success "✓ DNS déjà fonctionnel, aucune modification nécessaire"
        return 0
    fi

    if [[ "$force_mode" == "true" ]]; then
        log_dns warn "Mode --force: Configuration forcée même si DNS fonctionnel"
    fi

    # PHASE 3: Application
    local config_result
    apply_dns_configuration
    config_result=$?

    case $config_result in
        0)
            # Modification faite -> Redémarrer Docker
            if ! restart_docker_daemon; then
                log_dns error "Échec du redémarrage Docker"
                log_dns warn "Restaurez le backup si nécessaire:"
                log_dns warn "  sudo cp ${DAEMON_JSON}.backup.* $DAEMON_JSON"
                log_dns warn "  sudo systemctl restart docker"
                return 1
            fi
            ;;
        1)
            # Déjà configuré, pas de redémarrage nécessaire
            log_dns info "Aucune modification apportée"
            ;;
        2)
            # Erreur
            log_dns error "Erreur lors de la configuration"
            return 1
            ;;
    esac

    # PHASE 4: Validation
    log_dns info ""
    if ! test_dns_post_fix; then
        log_dns error "❌ Tests de validation échoués"
        log_dns warn "Vérifications à faire:"
        log_dns warn "  1. Vérifier la config: cat $DAEMON_JSON"
        log_dns warn "  2. Logs Docker: sudo journalctl -u docker --no-pager -n 50"
        log_dns warn "  3. Restaurer backup: sudo cp ${DAEMON_JSON}.backup.* $DAEMON_JSON"
        return 1
    fi

    log_dns info ""
    log_dns success "🎉 Configuration DNS complétée avec succès!"
    log_dns info ""
    log_dns info "Configuration active:"
    log_dns info "$(cat $DAEMON_JSON | jq .)"
    log_dns info ""

    return 0
}

# === EXPORT (si sourcé en tant que library) ===

# Si le script est sourcé (plutôt qu'exécuté), ne pas auto-exécuter
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Script exécuté directement
    fix_docker_dns "$@"
fi
