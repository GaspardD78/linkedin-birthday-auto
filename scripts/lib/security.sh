#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - SECURITY LIBRARY (v5.0)
# Password hashing, key generation, and security functions
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === CONFIGURATION ===

# Images (Keep for fallback if python fails for some weird reason, but unlikely)
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
    local method_used=""

    # -------------------------------------------------------------------------
    # PRIORITÉ 1: LOCAL PYTHON (Bcrypt Standard) - THE GOLD STANDARD
    # -------------------------------------------------------------------------
    # Vérifier si python3 est dispo
    if cmd_exists python3; then
        # Vérifier si bcrypt est installé, sinon l'installer temporairement (si pip dispo)
        if ! python3 -c "import bcrypt" 2>/dev/null; then
             log_info "📦 Installation de python3-bcrypt pour le hachage..."
             # Essayer pip si dispo
             if cmd_exists pip3; then
                 pip3 install bcrypt --quiet --user || true
             fi
        fi

        # Générer le hash
        if python3 -c "import bcrypt" 2>/dev/null; then
            log_debug "Méthode: Local Python (bcrypt)"
            # Note: On utilise bcrypt.hashpw avec un salt généré
            hash=$(python3 -c "import bcrypt; print(bcrypt.hashpw(b'$password', bcrypt.gensalt()).decode('utf-8'))")

            if [[ "$hash" =~ ^\$2[abxy]\$ ]]; then
                method_used="Python (Local)"
            else
                hash="" # Invalide
            fi
        else
            log_warn "⚠️  Module Python 'bcrypt' manquant. Tentative de fallback..."
        fi
    fi

    # -------------------------------------------------------------------------
    # PRIORITÉ 2: DOCKER (Helper Image 'pi-security-hash')
    # -------------------------------------------------------------------------
    if [[ -z "$hash" ]] && cmd_exists docker; then
        log_debug "Méthode: Docker (Security Image)"

        # Pull discret
        docker pull "$SECURITY_IMAGE" >/dev/null 2>&1 || true

        set +e
        hash=$(docker run --rm --platform linux/arm64 --network none \
            "$SECURITY_IMAGE" "$password" 2>/dev/null)
        local exit_code=$?
        set -e

        if [[ $exit_code -eq 0 ]] && [[ "$hash" =~ ^\$2[abxy]\$ ]]; then
            method_used="Docker (Helper Image)"
        else
            hash=""
        fi
    fi

    # -------------------------------------------------------------------------
    # PRIORITÉ 3: FALLBACK OPENSSL (SHA-512) - Legacy/Compatibilité
    # -------------------------------------------------------------------------
    if [[ -z "$hash" ]] && cmd_exists openssl; then
        log_warn "⚠️  Bcrypt indisponible. Fallback sur OpenSSL (SHA-512)."
        log_warn "   Note: Le dashboard supporte ce format, mais bcrypt est recommandé."
        hash=$(echo "$password" | openssl passwd -6 -stdin 2>/dev/null | tr -d '\n')
        if [[ -n "$hash" ]]; then
            method_used="OpenSSL (SHA-512)"
        fi
    fi

    # ÉCHEC TOTAL
    if [[ -z "$hash" ]]; then
        log_error "❌ IMPOSSIBLE DE GÉNÉRER LE HASH DU MOT DE PASSE."
        log_error "   Python (bcrypt), Docker ou OpenSSL requis."
        return 1
    fi

    log_success "✓ Hash généré via : $method_used"

    # --- ÉCRITURE ATOMIQUE & SÉCURISÉE DANS .ENV ---

    # Échappement des $ pour Docker Compose ($ -> $$)
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

    log_success "✅ Mot de passe enregistré dans .env"

    # Pour setup.sh state tracking
    export SETUP_PASSWORD_HASH="$hash"

    return 0
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
