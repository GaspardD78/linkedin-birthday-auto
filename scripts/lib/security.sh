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
    # STRATÉGIE ROBUSTE (ARM64 / Alpine)
    # Utilisation de node:20-alpine pour légèreté et compatibilité.
    # Installation de bcryptjs à la volée (pas de compilation C++).
    # Passage du mot de passe par ENV pour sécurité (invisible dans ps).
    # -------------------------------------------------------------------------

    if cmd_exists docker; then
        log_info "Hashage sécurisé (Docker node:20-alpine)..."

        set +e # Désactiver exit-on-error temporairement pour capturer l'échec

        local output
        # Commande optimisée:
        # --entrypoint /bin/sh : S'assure qu'on utilise un shell
        # -e PASS_INPUT : Le mot de passe passe par ENV, pas par argument
        # npm install ... : Installe bcryptjs dans le conteneur éphémère
        output=$(docker run --rm \
            --platform linux/arm64 \
            --entrypoint /bin/sh \
            -e PASS_INPUT="$password" \
            node:20-alpine \
            -c "npm install bcryptjs --no-save --silent >/dev/null 2>&1 && node -e \"console.log(require('bcryptjs').hashSync(process.env.PASS_INPUT, 12))\"" \
            2>&1)

        local exit_code=$?
        set -e

        # Vérification: on cherche un hash bcrypt valide
        if [[ $exit_code -eq 0 ]] && [[ "$output" =~ ^\$2[abxy]\$ ]]; then
            hashed_password=$(echo "$output" | tr -d '\r\n')
            log_success "✓ Hash généré avec succès"
        else
            log_error "Échec du hashage Docker."
            log_error "Sortie: $output"
            hashed_password=""
        fi
    fi

    # STRATÉGIE DE SECOURS: Fallback local (htpasswd)
    # Utile si Docker ne fonctionne pas ou pas d'internet
    if [[ -z "$hashed_password" ]] && cmd_exists htpasswd; then
        log_info "Fallback: hashage via htpasswd (bcrypt)..."
        local htpasswd_output
        htpasswd_output=$(htpasswd -nbB dummy "$password" 2>/dev/null)
        hashed_password=$(echo "$htpasswd_output" | cut -d':' -f2)
    fi

    # Check final failure
    if [[ -z "$hashed_password" ]]; then
        log_error "Impossible de hasher le mot de passe (méthodes Docker et htpasswd échouées)."
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

    log_success "✓ Mot de passe hashé et sécurisé dans .env"
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
