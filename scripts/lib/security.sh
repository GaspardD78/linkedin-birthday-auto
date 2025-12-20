#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - SECURITY LIBRARY (v4.0)
# Password hashing, key generation, and security functions
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === PASSWORD HASHING ===

hash_and_store_password() {
    local env_file="$1"
    local password="$2"

    # Validation du mot de passe
    if [[ -z "$password" ]]; then
        log_error "Mot de passe vide"
        return 1
    fi

    local hashed_password=""

    # -------------------------------------------------------------------------
    # Script JS robuste (lecture STDIN, pas d'arguments CLI)
    # Ce script lit le mot de passe depuis STDIN pour éviter tout problème
    # d'échappement de caractères dans les arguments du shell.
    # -------------------------------------------------------------------------
    local js_script="
    const fs = require('fs');
    try {
        const input = fs.readFileSync(0, 'utf-8').trim();
        if (!input) process.exit(1);
        const bcrypt = require('bcryptjs');
        console.log(bcrypt.hashSync(input, 12));
    } catch (e) {
        console.error(e.message);
        process.exit(1);
    }
    "

    # STRATÉGIE 1: Node.js 20 Slim (Officiel, ARM64 compatible)
    # L'utilisateur a explicitement demandé l'usage de node:20-slim.
    # Cette méthode installe bcryptjs à la volée.
    if cmd_exists docker; then
        log_info "Hashage sécurisé (Docker node:20-slim)..."

        set +e # Désactiver exit-on-error temporairement pour capturer l'échec

        # Exécution:
        # 1. On passe le mot de passe via PIPE au conteneur (STDIN)
        # 2. On passe le script JS via ENV (SCRIPT) pour éviter quoting hell dans sh -c
        # 3. sh -c installe bcryptjs, écrit le script dans un fichier et l'exécute
        local output
        output=$(echo -n "$password" | docker run --rm -i \
            --platform linux/arm64 \
            -e SCRIPT="$js_script" \
            node:20-slim \
            sh -c 'npm install --silent --no-save bcryptjs >/dev/null 2>&1 && echo "$SCRIPT" > /tmp/hash.js && node /tmp/hash.js' \
            2>&1)

        local exit_code=$?
        set -e

        # Vérification: on cherche une ligne qui ressemble à un hash bcrypt ($2a$..., $2b$...)
        if [[ $exit_code -eq 0 ]]; then
            hashed_password=$(echo "$output" | grep -E '^\$2[abxy]\$' | head -n1 || true)
        fi

        if [[ -n "$hashed_password" ]]; then
            log_success "✓ Hash généré via node:20-slim"
        else
            # Diagnostic: Afficher les 100 premiers chars de l'erreur pour aider le debug
            log_warn "Échec node:20-slim. Erreur: ${output:0:150}..."

            # STRATÉGIE 2: Image Dashboard (bcryptjs pré-installé)
            # Utile si npm install échoue (pas d'internet, etc.)
            log_info "Tentative via image Dashboard (fallback)..."

            # Pull silencieux si nécessaire
            if ! docker image inspect ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest >/dev/null 2>&1; then
                docker pull --platform linux/arm64 ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest >/dev/null 2>&1 || true
            fi

            set +e
            output=$(echo -n "$password" | docker run --rm -i \
                --platform linux/arm64 \
                -w /app \
                -e SCRIPT="$js_script" \
                ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest \
                sh -c 'echo "$SCRIPT" > /tmp/hash.js && node /tmp/hash.js' \
                2>&1)
            exit_code=$?
            set -e

            if [[ $exit_code -eq 0 ]]; then
                hashed_password=$(echo "$output" | grep -E '^\$2[abxy]\$' | head -n1 || true)
            fi

            if [[ -n "$hashed_password" ]]; then
                log_success "✓ Hash généré via Dashboard"
            else
                log_error "Échec critique du hashage Docker."
                log_error "Détails erreur: $output"
                hashed_password="" # Ensure empty so we fall through
            fi
        fi
    fi

    # STRATÉGIE 3: Fallback local (htpasswd)
    if [[ -z "$hashed_password" ]] && cmd_exists htpasswd; then
        log_info "Fallback: hashage via htpasswd (bcrypt)..."
        local htpasswd_output
        htpasswd_output=$(htpasswd -nbB dummy "$password" 2>/dev/null)
        hashed_password=$(echo "$htpasswd_output" | cut -d':' -f2)
    fi

    # Check final failure
    if [[ -z "$hashed_password" ]]; then
        log_error "Impossible de hasher le mot de passe (aucune méthode disponible)."
        return 1
    fi

    # -------------------------------------------------------------------------
    # CRITIQUE: Échappement Docker Compose ($ -> $$)
    # Le hash doit avoir ses $ doublés pour ne pas être interpolé par Docker Compose.
    # Ex: $2b$12$... -> $$2b$$12$$...
    # -------------------------------------------------------------------------
    local doubled_hash="${hashed_password//\$/\$\$}"

    # Échapper pour sed (délimiteurs / & |)
    local safe_val=$(printf '%s\n' "$doubled_hash" | sed 's:[&/|]:\\&:g')

    # Mise à jour du fichier .env
    if grep -q "^DASHBOARD_PASSWORD=" "$env_file"; then
        sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=${safe_val}|" "$env_file"
    else
        echo "DASHBOARD_PASSWORD=${safe_val}" >> "$env_file"
    fi

    log_success "✓ Mot de passe hashé et sécurisé ($$)"
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
    # Échapper /, &, et | car | est souvent utilisé comme séparateur sed
    printf '%s\n' "$string" | sed 's:[\/&|]:\\&:g'
}

# === SECURITY AUDIT ===

audit_env_security() {
    local env_file="$1"

    log_step "🔒 AUDIT SÉCURITÉ"

    local issues=0

    # Vérifier les variables de remplissage
    if grep -q "CHANGEZ_MOI\|your_secure\|your_jwt\|REPLACE_ME" "$env_file"; then
        log_warn "⚠️  Certaines variables ne sont pas configurées (CHANGEZ_MOI, REPLACE_ME)"
        issues=$((issues + 1))
    fi

    # Vérifier les permissions du fichier .env
    local perms
    perms=$(stat -c %a "$env_file" 2>/dev/null || stat -f %A "$env_file" 2>/dev/null || echo "")
    if [[ -n "$perms" && "$perms" != "600" ]]; then
        log_warn "⚠️  Permissions du .env: $perms (recommandé: 600)"
        chmod 600 "$env_file" 2>/dev/null || true
        issues=$((issues + 1))
    else
        log_success "✓ Permissions .env: 600"
    fi

    # Vérifier la présence de DASHBOARD_PASSWORD
    if ! grep -q "^DASHBOARD_PASSWORD=" "$env_file" || grep -q "^DASHBOARD_PASSWORD=$\|^DASHBOARD_PASSWORD=CHANGEZ_MOI" "$env_file"; then
        log_warn "⚠️  DASHBOARD_PASSWORD non configuré"
        issues=$((issues + 1))
    else
        log_success "✓ DASHBOARD_PASSWORD configuré"
    fi

    # Vérifier la présence de API_KEY
    if ! grep -q "^API_KEY=" "$env_file" || grep -q "^API_KEY=$\|^API_KEY=CHANGEZ_MOI" "$env_file"; then
        log_warn "⚠️  API_KEY non configurée"
        issues=$((issues + 1))
    else
        log_success "✓ API_KEY configurée"
    fi

    # Vérifier la présence de JWT_SECRET
    if ! grep -q "^JWT_SECRET=" "$env_file" || grep -q "^JWT_SECRET=$\|^JWT_SECRET=CHANGEZ_MOI" "$env_file"; then
        log_warn "⚠️  JWT_SECRET non configuré"
        issues=$((issues + 1))
    else
        log_success "✓ JWT_SECRET configuré"
    fi

    if [[ $issues -eq 0 ]]; then
        log_success "✓ Audit sécurité réussi (aucun problème détecté)"
        return 0
    else
        log_warn "⚠️  $issues problèmes de sécurité détectés"
        return 0  # Ne pas échouer, juste avertir
    fi
}
