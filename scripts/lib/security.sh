#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - SECURITY LIBRARY (v5.0)
# Password hashing, key generation, and security functions
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === CONFIGURATION ===

# Images
# Helper dédié (Prio 2)
DEFAULT_REPO="gaspardd78/linkedin-birthday-auto-dashboard"
SECURITY_IMAGE="ghcr.io/${GITHUB_REPOSITORY:-$DEFAULT_REPO}/pi-security-hash:latest"
# Image principale du dashboard (Prio 3 - contient node + scripts)
DASHBOARD_IMAGE="ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest"

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
    # PRIORITÉ 1: LOCAL PYTHON (Le plus rapide, pas de dépendances externes)
    # -------------------------------------------------------------------------
    if cmd_exists python3 && python3 -c "import bcrypt" 2>/dev/null; then
        log_debug "Méthode: Local Python (bcrypt)"
        # Note: On double les $ ici car le retour est direct
        hash=$(python3 -c "import bcrypt; print(bcrypt.hashpw(b'$password', bcrypt.gensalt()).decode('utf-8'))")
        if [[ "$hash" =~ ^\$2[abxy]\$ ]]; then
            method_used="Python (Local)"
        else
            hash="" # Invalide
        fi
    fi

    # -------------------------------------------------------------------------
    # PRIORITÉ 2: LOCAL NODE (Si repo cloné et npm install fait)
    # -------------------------------------------------------------------------
    if [[ -z "$hash" ]] && cmd_exists node; then
        local script_path="$PROJECT_ROOT/dashboard/scripts/hash_password.js"
        # On vérifie si le script ET le module bcryptjs sont dispos
        if [[ -f "$script_path" ]] && [[ -d "$PROJECT_ROOT/dashboard/node_modules" ]]; then
            log_debug "Méthode: Local Node.js"
            set +e
            hash=$(node "$script_path" "$password" --quiet 2>/dev/null)
            local exit_code=$?
            set -e

            if [[ $exit_code -eq 0 ]] && [[ "$hash" =~ ^\$2[abxy]\$ ]]; then
                 method_used="Node.js (Local)"
            else
                 hash=""
            fi
        fi
    fi

    # -------------------------------------------------------------------------
    # PRIORITÉ 3: DOCKER (Helper Image 'pi-security-hash')
    # -------------------------------------------------------------------------
    if [[ -z "$hash" ]] && cmd_exists docker; then
        log_debug "Méthode: Docker (Security Image)"

        # Tentative de pull avec retry (3 essais)
        local pull_success=false
        for i in {1..3}; do
            if docker pull "$SECURITY_IMAGE" >/dev/null 2>&1; then
                pull_success=true
                break
            fi
            log_debug "Tentative pull $i/3 échouée..."
            sleep 1
        done

        if [[ "$pull_success" == "true" ]]; then
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
        else
            log_warn "Impossible de télécharger l'image de sécurité helper."
        fi
    fi

    # -------------------------------------------------------------------------
    # PRIORITÉ 4: DOCKER (Main Dashboard Image - Fallback Robuste)
    # -------------------------------------------------------------------------
    # Si l'image helper échoue, on utilise l'image principale qui contient tout le code
    if [[ -z "$hash" ]] && cmd_exists docker; then
        log_debug "Méthode: Docker (Dashboard Image Fallback)"

        local pull_success=false
        if docker pull "$DASHBOARD_IMAGE" >/dev/null 2>&1; then
             pull_success=true
        fi

        if [[ "$pull_success" == "true" ]]; then
            # On exécute le script node présent dans l'image
            # Path dans l'image: /app/scripts/hash_password.js (supposition standard Next.js ou structure app)
            # Vérifions structure repo: dashboard/scripts/hash_password.js -> /app/scripts/...
            # Dans le Dockerfile dashboard, COPY . . -> /app/scripts est probable

            set +e
            # Note: Le path interne dépend du WORKDIR /app.
            # On essaye d'exécuter le script via node directement
            hash=$(docker run --rm --entrypoint node \
                "$DASHBOARD_IMAGE" \
                scripts/hash_password.js "$password" --quiet 2>/dev/null)
            local exit_code=$?
            set -e

            if [[ $exit_code -eq 0 ]] && [[ "$hash" =~ ^\$2[abxy]\$ ]]; then
                method_used="Docker (Dashboard Image)"
            else
                # Deuxième essai path (si structure différente)
                set +e
                hash=$(docker run --rm --entrypoint node \
                    "$DASHBOARD_IMAGE" \
                    dashboard/scripts/hash_password.js "$password" --quiet 2>/dev/null)
                 exit_code=$?
                set -e
                 if [[ $exit_code -eq 0 ]] && [[ "$hash" =~ ^\$2[abxy]\$ ]]; then
                    method_used="Docker (Dashboard Image v2)"
                else
                    hash=""
                fi
            fi
        fi
    fi

    # -------------------------------------------------------------------------
    # PRIORITÉ 5: FALLBACK OPENSSL (Dernier recours)
    # -------------------------------------------------------------------------
    if [[ -z "$hash" ]] && cmd_exists openssl; then
        log_warn "⚠️  Bcrypt indisponible (Local & Docker). Fallback sur OpenSSL (SHA-512)."
        log_warn "   Ce mode est moins sécurisé mais fonctionnel."
        hash=$(echo "$password" | openssl passwd -6 -stdin 2>/dev/null | tr -d '\n')
        if [[ -n "$hash" ]]; then
            method_used="OpenSSL (SHA-512)"
        fi
    fi

    # ÉCHEC TOTAL
    if [[ -z "$hash" ]]; then
        log_error "❌ IMPOSSIBLE DE GÉNÉRER LE HASH DU MOT DE PASSE."
        log_error "   Aucune méthode (Python, Node, Docker, OpenSSL) n'a fonctionné."
        return 1
    fi

    log_success "✓ Hash généré via : $method_used"

    # --- ÉCRITURE ATOMIQUE & SÉCURISÉE DANS .ENV ---

    # Échappement des $ pour Docker Compose ($ -> $$)
    # Ex: $2a$12$... devient $$2a$$12$$...
    # Note: Si OpenSSL ($6$...), on échappe aussi pour uniformité
    local hash_escaped="${hash//\$/\$\$}"

    # Vérifier doublage (paranoïa check)
    if [[ ! "$hash_escaped" == *"\$\$"* ]]; then
        log_warn "⚠️  L'échappement Docker Compose semble incorrect ($hash_escaped)"
    fi

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
