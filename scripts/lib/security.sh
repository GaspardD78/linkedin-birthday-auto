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

    if [[ -z "$password" ]]; then
        log_error "Mot de passe vide"
        return 1
    fi

    local hashed_password=""

    # STRATÉGIE 1: Utiliser le script Node.js du dashboard (via conteneur Docker)
    # C'est la méthode la plus propre car elle réutilise le code existant
    if cmd_exists docker && docker image inspect ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest &>/dev/null; then
        log_info "Hashage via conteneur Docker (bcryptjs)..."

        # Lancer conteneur éphémère avec le script hash_password.js
        hashed_password=$(echo -n "$password" | docker run --rm -i \
            --entrypoint node \
            ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest \
            /app/scripts/hash_password.js --quiet 2>/dev/null | head -n1)

        if [[ -n "$hashed_password" ]]; then
            log_success "✓ Hash généré via conteneur Docker"
        fi
    fi

    # STRATÉGIE 2: Fallback sur htpasswd avec bcrypt (si disponible sur l'hôte)
    if [[ -z "$hashed_password" ]] && cmd_exists htpasswd; then
        log_info "Fallback: hashage via htpasswd (bcrypt)..."

        # htpasswd -nbB génère un hash bcrypt
        local htpasswd_output
        htpasswd_output=$(htpasswd -nbB dummy "$password" 2>/dev/null)

        if [[ -n "$htpasswd_output" ]]; then
            # Format: dummy:$2y$05$... → on extrait juste le hash
            hashed_password=$(echo "$htpasswd_output" | cut -d':' -f2)
            log_success "✓ Hash généré via htpasswd"
        fi
    fi

    # STRATÉGIE 3: Fallback sur OpenSSL SHA-512 (compatible Unix)
    # Note: Ce n'est PAS bcrypt, mais le dashboard accepte ce format en fallback
    if [[ -z "$hashed_password" ]] && cmd_exists openssl; then
        log_warn "Fallback: hashage via OpenSSL (SHA-512, moins sécurisé que bcrypt)..."

        # Générer un hash SHA-512 avec salt
        hashed_password=$(openssl passwd -6 "$password" 2>/dev/null)

        if [[ -n "$hashed_password" ]]; then
            log_warn "⚠️  Hash SHA-512 utilisé (pas bcrypt). Considérez installer Docker pour bcrypt."
        fi
    fi

    if [[ -z "$hashed_password" ]]; then
        log_error "Impossible de hasher le mot de passe (aucune méthode disponible)"
        log_error "Solutions:"
        log_error "  1. Installez Docker: sudo apt install docker.io"
        log_error "  2. Installez htpasswd: sudo apt install apache2-utils"
        return 1
    fi

    # CRITIQUE: Doubler les $ pour Docker Compose et shells
    # $2b$12$abc... → $$2b$$12$$abc...
    local doubled_hash
    doubled_hash="${hashed_password//\$/\$\$}"

    # Échapper les caractères spéciaux pour sed (/ et & et |)
    local escaped_hash
    escaped_hash=$(printf '%s\n' "$doubled_hash" | sed 's:[\/&|]:\\&:g')

    # Remplacer dans le fichier .env
    if grep -q "^DASHBOARD_PASSWORD=" "$env_file"; then
        sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=${escaped_hash}|" "$env_file"
    else
        echo "DASHBOARD_PASSWORD=${escaped_hash}" >> "$env_file"
    fi

    log_success "✓ Mot de passe hashé et stocké dans $env_file"
    return 0
}

# === KEY GENERATION ===

generate_api_key() {
    # Générer une clé API robuste (32 bytes aléatoires en base64)
    # tr -d '\n' pour s'assurer que c'est sur une seule ligne
    { openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))"; } | tr -d '\n'
}

generate_jwt_secret() {
    # Générer un secret JWT robuste (64 bytes aléatoires en base64)
    # tr -d '\n' pour s'assurer que c'est sur une seule ligne
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
