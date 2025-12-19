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

    # Utiliser python pour générer un bcrypt hash sécurisé
    local hashed_password
    hashed_password=$(python3 -c "
import bcrypt
import sys
password = '$password'.encode('utf-8')
hashed = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))
print(hashed.decode('utf-8'))
" 2>/dev/null) || {
        # Si python3 avec bcrypt ne fonctionne pas, utiliser htpasswd comme fallback
        hashed_password=$(echo "$password" | htpasswd -iBBC 2>/dev/null) || {
            log_error "Impossible de hasher le mot de passe (ni bcrypt ni htpasswd disponibles)"
            return 1
        }
    }

    # Échapper les caractères spéciaux pour sed
    local escaped_hash
    escaped_hash=$(printf '%s\n' "$hashed_password" | sed 's:[\/&]:\\&:g')

    # Remplacer dans le fichier .env
    if grep -q "^DASHBOARD_PASSWORD=" "$env_file"; then
        sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=${escaped_hash}|" "$env_file"
    else
        echo "DASHBOARD_PASSWORD=${hashed_password}" >> "$env_file"
    fi

    log_success "✓ Mot de passe hashé et stocké"
    return 0
}

# === KEY GENERATION ===

generate_api_key() {
    # Générer une clé API robuste (32 bytes aléatoires en base64)
    openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))"
}

generate_jwt_secret() {
    # Générer un secret JWT robuste (64 bytes aléatoires en base64)
    openssl rand -base64 64 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(64))"
}

escape_sed_string() {
    local string="$1"
    printf '%s\n' "$string" | sed 's:[\/&]:\\&:g'
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
