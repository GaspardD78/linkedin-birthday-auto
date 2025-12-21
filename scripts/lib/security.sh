#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - SECURITY LIBRARY (v5.0)
# Password hashing, key generation, and security functions
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === CONFIGURATION ===

# Image pré-buildée via GitHub Actions pour éviter npm/compile sur le Pi
# Le nom de l'image est dynamique si possible, sinon fallback
# On suppose l'usage de ghcr.io/<owner>/<repo>/pi-security-hash:latest
# Comme le script ne connait pas l'owner/repo Git facilement s'il est hors git,
# on utilise une valeur par défaut cohérente ou on la détecte.
# Pour ce setup, on utilise la variable définie ou le fallback Gaspard.

# NOTE: Pour que cela fonctionne universellement, l'image doit être publique
# ou l'utilisateur doit être docker login.
DEFAULT_REPO="gaspardd78/linkedin-birthday-auto-dashboard"
SECURITY_IMAGE="ghcr.io/${GITHUB_REPOSITORY:-$DEFAULT_REPO}/pi-security-hash:latest"

# === PASSWORD HASHING ===

hash_and_store_password() {
    local env_file="$1"
    local password="$2"

    # Validation
    if [[ ${#password} -lt 8 ]]; then
        log_error "Mot de passe trop court (<8 caractères)"
        return 1
    fi

    log_info "🔒 Hashage sécurisé du mot de passe..."
    local hash=""

    # 1. Tentative via Image Docker Dédiée (Méthode Prioritaire)
    if cmd_exists docker; then
        log_debug "Utilisation de l'image de sécurité: $SECURITY_IMAGE"

        # Pull de l'image (silencieux sauf erreur)
        if ! docker pull "$SECURITY_IMAGE" >/dev/null 2>&1; then
             log_warn "Impossible de télécharger l'image de sécurité ($SECURITY_IMAGE)."
             log_warn "Vérifiez la connexion internet ou l'existence de l'image."
        fi

        # Exécution du hashage (OFFLINE container execution)
        # --network none : Sécurité maximale, pas d'accès réseau requis pour hasher
        set +e
        hash=$(docker run --rm --platform linux/arm64 --network none \
            "$SECURITY_IMAGE" "$password" 2>/dev/null)
        local exit_code=$?
        set -e

        if [[ $exit_code -ne 0 ]] || [[ ! "$hash" =~ ^\$2[abxy]\$ ]]; then
            log_warn "Échec du hashage Docker standard. Code: $exit_code"
            hash=""
        fi
    fi

    # 2. Fallback: Méthode htpasswd (si installé)
    if [[ -z "$hash" ]] && cmd_exists htpasswd; then
        log_info "Fallback: utilisation de htpasswd (bcrypt)..."
        local htpasswd_out
        htpasswd_out=$(htpasswd -nbB dummy "$password" 2>/dev/null)
        hash=$(echo "$htpasswd_out" | cut -d':' -f2)
    fi

    # 3. Fallback: OpenSSL (SHA512 - moins bon mais standard)
    if [[ -z "$hash" ]] && cmd_exists openssl; then
        log_warn "⚠️  Fallback sur OpenSSL (SHA-512) car bcrypt indisponible."
        hash=$(echo "$password" | openssl passwd -6 -stdin 2>/dev/null | tr -d '\n')
    fi

    # Échec critique
    if [[ -z "$hash" ]]; then
        log_error "❌ Impossible de générer un hash pour le mot de passe."
        return 1
    fi

    # --- ÉCRITURE ATOMIQUE & SÉCURISÉE DANS .ENV ---

    # Échappement des $ pour Docker Compose ($ -> $$)
    # Ex: $2a$12$... devient $$2a$$12$$...
    local hash_escaped="${hash//\$/\$\$}"

    # Création d'un fichier temporaire pour écriture atomique
    local temp_env="${env_file}.tmp"

    # Copier tout SAUF la ligne DASHBOARD_PASSWORD existante
    if [[ -f "$env_file" ]]; then
        grep -v '^DASHBOARD_PASSWORD=' "$env_file" > "$temp_env" || true
    else
        touch "$temp_env"
    fi

    # Ajouter la nouvelle ligne
    echo "DASHBOARD_PASSWORD=\"$hash_escaped\"" >> "$temp_env"

    # Swap atomique
    mv "$temp_env" "$env_file"
    chmod 600 "$env_file"

    log_success "✅ Mot de passe sécurisé et enregistré (Hash: ${hash:0:10}...)"

    # Pour setup.sh state tracking
    export SETUP_PASSWORD_HASH="$hash"

    return 0
}

# Fonction de test unitaire
test_hash() {
    local test_pass="testpassword123"
    echo "Testing hash with: $test_pass"
    hash_and_store_password "/tmp/test.env" "$test_pass"
    cat /tmp/test.env
    rm -f /tmp/test.env
}

# === KEY GENERATION ===

generate_api_key() {
    # Générer une clé API robuste (32 bytes aléatoires en base64)
    { openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))"; } | tr -d '\n'
}

generate_jwt_secret() {
    # Générer un secret JWT robuste (64 bytes aléatoires en base64)
    { openssl rand -base64 64 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(64))"; } | tr -d '\n'
}

escape_sed_string() {
    local string="$1"
    # Échapper /, &, et |
    printf '%s\n' "$string" | sed 's:[\/&|]:\\&:g'
}

# === SECURITY AUDIT ===

audit_env_security() {
    local env_file="$1"

    log_step "🔒 AUDIT SÉCURITÉ"
    local issues=0

    # Vérifier permissions
    local perms
    perms=$(stat -c %a "$env_file" 2>/dev/null || stat -f %A "$env_file" 2>/dev/null || echo "")
    if [[ -n "$perms" && "$perms" != "600" ]]; then
        log_warn "⚠️  Permissions du .env: $perms (fixé à 600)"
        chmod 600 "$env_file" 2>/dev/null || true
    else
        log_success "✓ Permissions .env: 600"
    fi

    # Vérifier variables critiques
    for var in "DASHBOARD_PASSWORD" "API_KEY" "JWT_SECRET"; do
        if ! grep -q "^${var}=" "$env_file" || grep -q "^${var}=$\|^${var}=CHANGEZ_MOI" "$env_file"; then
            log_warn "⚠️  ${var} non configuré ou insécure"
            issues=$((issues + 1))
        else
            log_success "✓ ${var} configuré"
        fi
    done

    if [[ $issues -eq 0 ]]; then
        log_success "✓ Audit sécurité réussi"
        return 0
    else
        log_warn "⚠️  $issues problèmes de sécurité détectés"
        return 0
    fi
}
