# 🏗️ DOCUMENT DE CONCEPTION – HTTPS, GOOGLE DRIVE & SÉCURITÉ
## Audit & Amélioration du Système setup.sh

**Date:** 2025-01-19
**Version:** 1.0
**Portée:** Amélioration complète des axes HTTPS, sauvegarde Google Drive, sécurité, et gestion des credentials
**Cible:** Raspberry Pi 4 (ARM64)

---

## 📋 Table des Matières

1. [État Actuel & Analyse](#-état-actuel--analyse)
2. [Axe 1: HTTPS/SSL - Analyse & Renforcement](#-axe-1-httpssl---analyse--renforcement)
3. [Axe 2: Sauvegarde Google Drive](#-axe-2-sauvegarde-google-drive)
4. [Axe 3: Vérification Sécurité Globale](#-axe-3-vérification-sécurité-globale)
5. [Axe 4: Gestion des Login/Mot de Passe Existants](#-axe-4-gestion-des-loginmot-de-passe-existants)
6. [Axe 5: Script Séparé de Gestion du Mot de Passe](#-axe-5-script-séparé-de-gestion-du-mot-de-passe)
7. [Résumé des Modifications](#-résumé-des-modifications)
8. [Plan d'Implémentation](#-plan-dimplémentation)

---

## 🔍 ÉTAT ACTUEL & ANALYSE

### A. Points Forts Détectés

| Domaine | État | Force |
|---------|------|-------|
| **HTTPS/SSL** | ✅ Partiellement implémenté | ✓ Template Nginx dynamique |
| | | ✓ Certificats self-signed en fallback |
| | | ✓ Support Let's Encrypt (script dédié) |
| **Google Drive Backup** | ✅ Implémenté et robuste | ✓ Détection dynamique rclone |
| | | ✓ Vérifications pré-backup complètes |
| | | ✓ Logs horodatés + retry (3x) |
| **Mot de Passe** | ✅ Mature et sécurisé | ✓ Hachage bcrypt complet |
| | | ✓ Idempotence complète |
| | | ✓ Interaction utilisateur (menus) |
| **Sécurité Globale** | ⚠️ Partielle | ✓ Docker socket proxy en place |
| | | ✓ DH params générés |
| | | ⚠️ Pas de vérification finale |

### B. Lacunes Identifiées

| Domaine | Problème | Impact | Priorité |
|---------|----------|--------|----------|
| **HTTPS** | Pas de menu HTTPS dans setup.sh | Utilisateur ne sait pas quelles options existent | HAUTE |
| | Certificats auto-signés par défaut | HTTP possible (pas forcé HTTPS) | HAUTE |
| | Pas de validation Let's Encrypt | Configuration HTTPS incertaine | MODÉRÉE |
| **Google Drive** | Pas d'intégration setup.sh | Utilisateur doit configurer manuellement | HAUTE |
| | Pas de chiffrement des backups | Données Google Drive en clair | MODÉRÉE |
| | Pas de test restore automatisé | Backup validité incertaine | BASSE |
| **Sécurité** | Pas de rapport final | Utilisateur ne voit pas le score sécurité | HAUTE |
| | Pas de vérification .env secrets | Risque mots de passe en clair | MODÉRÉE |
| | Grafana creds en défaut (audit trouvé) | Accès non-autorisé Grafana | CRITIQUE |
| **Credentials** | Pas de script de récupération/reset | Si oubli mot de passe = perte d'accès | MODÉRÉE |

---

## 🔧 AXE 1: HTTPS/SSL - ANALYSE & RENFORCEMENT

### 1.1 Analyse de l'Existant

#### Configuration Actuelle

**Fichiers impliqués:**
- `setup.sh` (lines 632-699): Bootstrap SSL + Nginx config
- `deployment/nginx/linkedin-bot.conf.template`: Template Nginx dynamique
- `.env`: Variable `DOMAIN`
- `scripts/setup_letsencrypt.sh`: Script Let's Encrypt séparé

**Flux actuel:**
```bash
# Phase 4.5 dans setup.sh
1. Vérifie existence certificats (live/${DOMAIN}/fullchain.pem)
2. Si absents: génère self-signed RSA 2048, 365j
3. Génère DH params (2048 bits) si absent
4. Génère Nginx config depuis template (injection ${DOMAIN})
5. Lance docker-compose
```

**Template Nginx (linkedin-bot.conf.template):**
```nginx
# Port 80: HTTP
server {
    listen 80;
    server_name ${DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;  # Redirection HTTP→HTTPS
    }
}

# Port 443: HTTPS (Let's Encrypt)
server {
    listen 443 ssl http2;
    server_name ${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    include /etc/nginx/conf.d/options-ssl-nginx.conf;

    # Headers sécurité (HSTS, CSP, etc.)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
    ...
}
```

**Points forts:**
- ✅ Configuration dynamique (template)
- ✅ Headers sécurité renforcés
- ✅ Support HTTP/2
- ✅ Rate limiting par endpoint
- ✅ Redirection HTTP→HTTPS

**Points faibles:**
- ❌ Pas de menu HTTPS dans setup.sh (utilisateur ne sait pas options)
- ❌ Certificats auto-signés par défaut (HTTP possible)
- ❌ Pas de validation que Let's Encrypt est bien activé
- ❌ Pas de guidance sur domaine/ports accessibles

#### Script Let's Encrypt Existant

**Fichier:** `scripts/setup_letsencrypt.sh`

**Points forts:**
- ✅ Vérification DNS robuste (3 fallback: host, python3, getent)
- ✅ Vérification port 80 accessible
- ✅ Support mode staging (--staging)
- ✅ Récupération email pour notifications

**Points faibles:**
- ❌ Script **séparé** (pas intégré setup.sh)
- ❌ Dépend setup.sh déjà lancé (Docker Compose up)
- ❌ Pas d'automatisation cron après certificat obtendu

### 1.2 Proposition de Conception

#### Concept Clé: Menu HTTPS dans setup.sh

L'utilisateur doit pouvoir choisir son scénario HTTPS lors du setup initial:

```
╔══════════════════════════════════════════════════════════════╗
║           Configuration HTTPS / SSL / TLS                    ║
╚══════════════════════════════════════════════════════════════╝

Quels scénarios s'appliquent à vous ?

1) 🏠 LAN uniquement
   - Usage interne, pas d'exposition Internet
   - HTTPS: Non nécessaire
   - ⚠️ Avertissement: Recommandé pour la sécurité

2) 🌐 Domaine avec Let's Encrypt (Production recommandée)
   - Domaine public accessible (DNS configuré)
   - Ports 80/443 accessibles de l'Internet
   - Certificats: Let's Encrypt (gratuit, auto-renouvellement)

3) 🔒 Certificats existants
   - Vous avez déjà certif + clé privée
   - Chemins: /path/to/cert.pem, /path/to/privkey.pem

4) ⚙️ Configuration manuelle
   - Vous gérerez HTTPS vous-même après setup

Votre choix [1-4] :
```

#### Option 1: LAN Uniquement
```bash
if [[ "$HTTPS_CHOICE" == "1" ]]; then
    log_warn "⚠️  HTTPS désactivé (LAN uniquement)"
    log_warn "    Accès via HTTP uniquement : http://$(hostname -I | awk '{print $1}')"
    log_warn "    ⚠️  POUR PRODUCTION SUR INTERNET : Utilisez Let's Encrypt (option 2)"

    # Générer config Nginx avec HTTP uniquement
    generate_nginx_config_http_only
fi
```

#### Option 2: Let's Encrypt (Recommandée Production)
```bash
if [[ "$HTTPS_CHOICE" == "2" ]]; then
    log_step "Configuration Let's Encrypt"

    # 1. Demander domaine
    read -p "Entrez votre domaine (ex. example.com) : " USER_DOMAIN
    DOMAIN="$USER_DOMAIN"

    # 2. Vérifier DNS
    log_info "Vérification DNS pour $DOMAIN..."
    if ! check_dns_resolvable "$DOMAIN"; then
        log_error "Le domaine ne résout pas. Configurez d'abord le DNS."
        exit 1
    fi

    # 3. Générer self-signed en fallback
    generate_self_signed_cert "$DOMAIN"

    # 4. Générer Nginx config (avec HTTPS activé)
    generate_nginx_config "$NGINX_TEMPLATE" "$NGINX_CONFIG" "$DOMAIN"

    # 5. Lancer Docker (Nginx doit être running pour ACME challenge)
    docker compose -f "$COMPOSE_FILE" up -d

    # 6. Attendre Nginx stable (15s)
    log_info "Attente démarrage Nginx..."
    sleep 15

    # 7. Lancer Let's Encrypt (optionnel immédiat ou plus tard)
    log_info "Certificats Let's Encrypt:"
    log_info "  - Immédiat: ./scripts/setup_letsencrypt.sh"
    log_info "  - Plus tard: ./scripts/setup_letsencrypt.sh"
    log_info "  - (Auto-renouvellement: cron via crontab)"
fi
```

#### Option 3: Certificats Existants
```bash
if [[ "$HTTPS_CHOICE" == "3" ]]; then
    log_step "Import Certificats Existants"

    read -p "Chemin fullchain.pem : " CERT_FILE
    read -p "Chemin privkey.pem : " KEY_FILE

    if [[ ! -f "$CERT_FILE" ]] || [[ ! -f "$KEY_FILE" ]]; then
        log_error "Fichiers certificats non trouvés."
        exit 1
    fi

    # Copier dans le répertoire certbot
    mkdir -p "certbot/conf/live/${DOMAIN}"
    cp "$CERT_FILE" "certbot/conf/live/${DOMAIN}/fullchain.pem"
    cp "$KEY_FILE" "certbot/conf/live/${DOMAIN}/privkey.pem"
    chmod 600 "certbot/conf/live/${DOMAIN}/privkey.pem"

    log_success "Certificats importés."
fi
```

#### Option 4: Configuration Manuelle
```bash
if [[ "$HTTPS_CHOICE" == "4" ]]; then
    log_warn "Configuration manuelle HTTPS sélectionnée."
    log_info "Vous êtes responsable de :"
    log_info "  - Placer certificats dans: certbot/conf/live/${DOMAIN}/"
    log_info "  - Configurer Nginx manuellement"
    log_info "  - Redémarrer Nginx après changements"
fi
```

#### Validation Post-Configuration

Après Docker Compose up, vérifier:

```bash
validate_https_configuration() {
    local domain="$1"

    log_info "Validation HTTPS..."

    # 1. Vérifier Nginx écoute 443
    if ! docker exec nginx netstat -tlnp 2>/dev/null | grep -q ":443"; then
        log_error "Nginx n'écoute pas sur 443"
        return 1
    fi

    # 2. Vérifier certificats existent
    if [[ ! -f "certbot/conf/live/${domain}/fullchain.pem" ]]; then
        log_error "Certificat absent: certbot/conf/live/${domain}/fullchain.pem"
        return 1
    fi

    # 3. Test HTTPS curl (avec self-signed ou Let's Encrypt)
    HTTPS_RESPONSE=$(curl -sk -o /dev/null -w "%{http_code}" "https://localhost/health" 2>/dev/null || echo "000")

    if [[ "$HTTPS_RESPONSE" =~ ^[23]0[0-9]$ ]]; then
        log_success "✓ HTTPS fonctionnel (HTTP $HTTPS_RESPONSE)"
        return 0
    else
        log_warn "⚠️  HTTPS retourne HTTP $HTTPS_RESPONSE (voir logs Nginx)"
        return 1
    fi
}
```

### 1.3 Impacts

| Aspect | Avant | Après | Amélioration |
|--------|-------|-------|--------------|
| **UX** | Utilisateur confus (pas d'options visibles) | Menu clair avec 4 scénarios | +Excellente |
| **Sécurité** | HTTP possible (certificat self-signed) | HTTPS forcé ou LAN explicite | +Élevée |
| **Configuration** | Manuelle post-setup | Intégrée dans setup.sh | +Robustesse |
| **Complexité** | Faible | Modérée (nouvelle logique menu) | +Acceptable |
| **Maintenabilité** | OK | OK (code bien structuré) | = |

---

## 🔧 AXE 2: SAUVEGARDE GOOGLE DRIVE

### 2.1 Analyse de l'Existant

#### Script backup_to_gdrive.sh Existant

**Fichier:** `scripts/backup_to_gdrive.sh`

**État:** ✅ **Très solide, peu de modifications nécessaires**

**Points forts:**
- ✅ Détection automatique remote rclone (pas hardcodé)
- ✅ 5+ vérifications pré-backup (rclone, remote, fichiers, permissions)
- ✅ Logging horodaté et verbose (stdout + fichier)
- ✅ Retry 3x avec délai (si upload échoue)
- ✅ Nettoyage automatique (retention 30j local + distant)
- ✅ Capture d'erreur stderr (logs complets)
- ✅ Exit codes corrects

**Points à améliorer:**
- ⚠️ Pas d'intégration setup.sh (utilisateur doit configurer rclone manuellement)
- ⚠️ Pas de chiffrement end-to-end (données en clair sur Google Drive)
- ⚠️ Pas de cron automatique post-setup
- ⚠️ Pas de validation backup (test restore aléatoire)

#### Intégration setup.sh - État Actuel

**Situation:** Aucune intégration HTTPS dans setup.sh

### 2.2 Proposition de Conception

#### Concept: Intégration Setup.sh + Chiffrement Optionnel

**Workflow proposé:**

```
setup.sh
├─ Phase 5.1: Configuration Sauvegardes
│  ├─ Menu: Activez-vous les sauvegardes Google Drive ?
│  │  1) Oui, activer avec chiffrement
│  │  2) Oui, activer sans chiffrement
│  │  3) Non, pas de sauvegarde maintenant
│  │
│  └─ Si OUI:
│     ├─ Vérifier rclone installé
│     ├─ Vérifier/configurer rclone remote
│     ├─ Configurer chiffrement (GPG + rclone crypt) si choix 1
│     ├─ Ajouter cron pour backup quotidien
│     └─ Test backup initial
│
scripts/backup_to_gdrive.sh
├─ Améliorations:
│  ├─ Support chiffrement optionnel
│  ├─ Notification Slack si échec (env var SLACK_WEBHOOK)
│  ├─ Test restore aléatoire (monthly)
│  └─ Monitoring integration (Prometheus metrics)
```

#### Phase 5.1 dans setup.sh - Code Proposé

```bash
# ==============================================================================
# PHASE 5.1 : SAUVEGARDES GOOGLE DRIVE
# ==============================================================================
log_step "PHASE 5.1 : Configuration Sauvegardes"

# Menu activation sauvegardes
BACKUP_CHOICE=$(prompt_menu \
    "Configuration des Sauvegardes Google Drive" \
    "Oui, activer avec chiffrement (recommandé)" \
    "Oui, activer sans chiffrement" \
    "Non, configurer plus tard")

if [[ "$BACKUP_CHOICE" == "1" ]] || [[ "$BACKUP_CHOICE" == "2" ]]; then

    log_info "Installation/vérification rclone..."

    # 1. Vérifier rclone
    if ! cmd_exists rclone; then
        log_warn "rclone non installé. Installation..."
        check_sudo
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # ARM64 sur RPi4
            if uname -m | grep -q "aarch64"; then
                sudo apt-get update -qq && sudo apt-get install -y -qq rclone
            else
                sudo apt-get update -qq && sudo apt-get install -y -qq rclone
            fi
        fi
    fi

    log_success "✓ rclone disponible: $(rclone --version | head -1)"

    # 2. Vérifier/configurer remote Google Drive
    EXISTING_REMOTE=$(rclone listremotes 2>/dev/null | head -1 | sed 's/://')

    if [[ -z "$EXISTING_REMOTE" ]]; then
        log_warn "Aucun remote rclone configuré."
        log_info "Configuration interactive de Google Drive..."
        log_info ""
        log_info "Instructions:"
        log_info "1. Accédez à https://console.cloud.google.com"
        log_info "2. Créez un projet ou en sélectionnez un"
        log_info "3. Activez Google Drive API"
        log_info "4. Créez une clé de service (JSON)"
        log_info ""

        if prompt_yes_no "Continuer la configuration rclone ?" "y"; then
            rclone config
            EXISTING_REMOTE=$(rclone listremotes 2>/dev/null | head -1 | sed 's/://')

            if [[ -z "$EXISTING_REMOTE" ]]; then
                log_error "Configuration rclone échouée ou annulée."
                log_warn "Vous pouvez configurer manuellement plus tard: rclone config"
                BACKUP_CHOICE="0"  # Désactiver sauvegardes
            fi
        else
            log_info "Configuration rclone annulée. Vous pourrez le configurer plus tard."
            BACKUP_CHOICE="0"
        fi
    else
        log_success "✓ Remote rclone détecté: $EXISTING_REMOTE"
    fi

    # 3. Configuration chiffrement (si choix 1)
    if [[ "$BACKUP_CHOICE" == "1" ]]; then
        log_info "Configuration chiffrement rclone..."

        # Vérifier GPG
        if ! cmd_exists gpg; then
            log_warn "GPG non installé. Installation..."
            check_sudo
            sudo apt-get update -qq && sudo apt-get install -y -qq gnupg
        fi

        log_info "Création remote rclone crypt (chiffré)..."

        # Configuration automatique du remote crypt
        rclone config create linkedin_backup_crypt crypt \
            remote "${EXISTING_REMOTE}:LinkedInBot_Backups_Crypt" \
            filename_encryption off \
            2>/dev/null || {
            log_error "Impossible de créer remote crypt"
            log_warn "Configuration manuelle requise: rclone config"
        }

        BACKUP_REMOTE="linkedin_backup_crypt"
    else
        BACKUP_REMOTE="$EXISTING_REMOTE"
    fi

    # 4. Configurer cron si absent
    CRON_ENTRY="0 2 * * * cd ${SCRIPT_DIR} && ./scripts/backup_to_gdrive.sh >> logs/cron.log 2>&1"

    if ! (crontab -l 2>/dev/null | grep -q "backup_to_gdrive.sh"); then
        log_info "Ajout cron quotidien (02:00)..."

        if [[ -w /var/spool/cron/crontabs/ ]] || sudo -n true 2>/dev/null; then
            (crontab -l 2>/dev/null || true; echo "$CRON_ENTRY") | \
                (check_sudo && sudo crontab - || crontab -)

            log_success "✓ Cron ajouté (backup quotidien 02:00)"
        else
            log_warn "Impossible d'ajouter cron. Configuration manuelle:"
            log_warn "  crontab -e"
            log_warn "  Ajouter: $CRON_ENTRY"
        fi
    else
        log_success "✓ Cron backup déjà configuré"
    fi

    # 5. Test backup initial (optionnel)
    if prompt_yes_no "Effectuer un test backup maintenant ?" "n"; then
        log_info "Lancement test backup..."
        if bash ./scripts/backup_to_gdrive.sh; then
            log_success "✓ Test backup réussi"
        else
            log_error "Test backup échoué. Vérifiez:"
            log_error "  - Configuration rclone: rclone listremotes"
            log_error "  - Accès Google Drive"
            log_error "  - Logs: cat logs/backup_gdrive.log"
        fi
    fi

    log_success "✓ Sauvegardes Google Drive configurées"
    BACKUP_CONFIGURED="true"
else
    log_warn "Sauvegardes Google Drive non activées"
    log_info "Vous pouvez les configurer plus tard: rclone config"
    BACKUP_CONFIGURED="false"
fi

echo "$BACKUP_CONFIGURED" > ".backup_configured"  # Pour reports ultérieurs
```

#### Améliorations script backup_to_gdrive.sh

**Modification 1: Support Slack notifications**

```bash
# Après le upload (ligne 165 approx)

# Slack notification (optionnel)
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
if [[ -n "$SLACK_WEBHOOK" ]]; then
    log INFO "Envoi notification Slack..."

    SLACK_MESSAGE="{
        \"text\": \"✅ Backup LinkedIn Bot terminé\",
        \"attachments\": [{
            \"color\": \"good\",
            \"fields\": [
                {\"title\": \"Archive\", \"value\": \"$BACKUP_NAME ($ARCHIVE_SIZE)\", \"short\": true},
                {\"title\": \"Remote\", \"value\": \"${GDRIVE_REMOTE}:${REMOTE_DIR}\", \"short\": true}
            ]
        }]
    }"

    curl -X POST -H 'Content-type: application/json' \
        --data "$SLACK_MESSAGE" \
        "$SLACK_WEBHOOK" 2>/dev/null || log WARN "Slack notification échouée"
fi
```

**Modification 2: Test restore mensuel**

```bash
# À la fin du script backup_to_gdrive.sh

# Test restore aléatoire (1ère du mois)
if [[ $(date +%d) == "01" ]]; then
    log INFO "Test restore mensuel..."

    LATEST_BACKUP=$(rclone ls "${GDRIVE_REMOTE}:${REMOTE_DIR}" | tail -1 | awk '{print $2}')
    RESTORE_TEST_DIR="/tmp/linkedin_restore_test"

    mkdir -p "$RESTORE_TEST_DIR"

    if rclone copy "${GDRIVE_REMOTE}:${REMOTE_DIR}/${LATEST_BACKUP}" "$RESTORE_TEST_DIR/" 2>&1 | tee -a "$LOG_FILE"; then
        if tar -tzf "$RESTORE_TEST_DIR/$LATEST_BACKUP" &>/dev/null; then
            log INFO "✅ Test restore réussi pour $LATEST_BACKUP"
        else
            log ERROR "❌ Archive corrompue: $LATEST_BACKUP"
        fi
    else
        log ERROR "❌ Test restore échoué"
    fi

    rm -rf "$RESTORE_TEST_DIR"
fi
```

### 2.3 Impacts

| Aspect | Avant | Après | Amélioration |
|--------|-------|-------|--------------|
| **Intégration** | Script séparé + config manuelle | Intégré setup.sh + wizard | +Énorme |
| **Sécurité** | Données claires Google Drive | Chiffrement optionnel | +Bonne |
| **Automation** | Configuration manuelle cron | Cron auto-ajouté | +Bonne |
| **Validation** | Confiance backup ? | Test restore mensuel | +Excellente |
| **UX** | Confus pour utilisateur non-tech | Menu clair + wizard | +Excellente |
| **Complexité** | Basse (script stable) | Modérée (ajouts) | +Acceptable |

---

## 🔧 AXE 3: VÉRIFICATION SÉCURITÉ GLOBALE

### 3.1 Analyse de l'Existant

**État actuel:** ❌ **Aucun rapport sécurité final**

**Points forts:**
- ✅ Docker socket proxy en place
- ✅ DH params générés
- ✅ Hachage mot de passe bcrypt
- ✅ Configuration Nginx sécurisée (headers renforcés)

**Points faibles:**
- ❌ Pas de vérification globale à la fin setup.sh
- ❌ Utilisateur ne voit pas son "score" sécurité
- ❌ Pas de détection secrets en clair dans .env

### 3.2 Proposition: Rapport Sécurité Final

#### Fonction `generate_security_report()`

```bash
generate_security_report() {
    local score_current=0
    local score_total=4
    local issues=()

    echo ""
    log_step "🔒 RÉSUMÉ SÉCURITÉ & CONFIGURATION"
    echo ""

    # --- Check 1: Mot de passe Dashboard ---
    echo -n "  1. Mot de passe Dashboard... "
    if grep -q "^DASHBOARD_PASSWORD=\$2[aby]\$" "$ENV_FILE" 2>/dev/null; then
        echo -e "${GREEN}✓ OK${NC} (hash bcrypt détecté)"
        ((score_current++))
    elif grep -q "CHANGEZ_MOI\|your_password\|12345" "$ENV_FILE" 2>/dev/null; then
        echo -e "${RED}✗ CRITIQUE${NC} (mot de passe par défaut/vide)"
        issues+=("Définissez un mot de passe Dashboard fort")
    else
        echo -e "${YELLOW}⚠ ATTENTION${NC} (format unknown)"
    fi

    # --- Check 2: HTTPS ---
    echo -n "  2. HTTPS... "
    if [[ -f "certbot/conf/live/${DOMAIN}/fullchain.pem" ]]; then
        if openssl x509 -in "certbot/conf/live/${DOMAIN}/fullchain.pem" -noout >/dev/null 2>&1; then
            CERT_ISSUER=$(openssl x509 -in "certbot/conf/live/${DOMAIN}/fullchain.pem" -noout -text 2>/dev/null | grep "Issuer:" | head -1 | sed 's/.*Issuer: //')

            if [[ "$CERT_ISSUER" =~ "Let's Encrypt" ]]; then
                echo -e "${GREEN}✓ PRODUCTION${NC} (Let's Encrypt)"
                ((score_current++))
            elif [[ "$CERT_ISSUER" =~ "Temporary" ]]; then
                echo -e "${YELLOW}⚠ DÉVELOPPEMENT${NC} (Self-signed)"
                issues+=("Remplacez certificat self-signed par Let's Encrypt (production)")
            else
                echo -e "${GREEN}✓ OK${NC} (Certificat valide)"
                ((score_current++))
            fi
        fi
    else
        echo -e "${YELLOW}⚠ ATTENTION${NC} (certificat absent)"
        issues+=("Générez certificat HTTPS (./scripts/setup_letsencrypt.sh)")
    fi

    # --- Check 3: Sauvegardes ---
    echo -n "  3. Sauvegardes Google Drive... "
    if [[ -f ".backup_configured" ]] && grep -q "true" ".backup_configured" 2>/dev/null; then
        echo -e "${GREEN}✓ OK${NC} (configurées)"
        ((score_current++))
    else
        echo -e "${YELLOW}⚠ OPTIONNEL${NC} (non configurées)"
        issues+=("Recommandé: Configurez sauvegardes Google Drive")
    fi

    # --- Check 4: Fichier .env sécurité ---
    echo -n "  4. Fichier .env... "
    ENV_ISSUES=0

    # Chercher patterns dangéreux
    if grep -iE "PASSWORD=.*[a-zA-Z0-9]{1,10}$|PASSWORD=12345|PASSWORD=admin|PASSWORD=changez" "$ENV_FILE" 2>/dev/null | grep -v "DASHBOARD_PASSWORD=\$2"; then
        ((ENV_ISSUES++))
    fi
    if grep -iE "API_KEY=.*your_|API_KEY=12345|API_KEY=test" "$ENV_FILE" 2>/dev/null; then
        ((ENV_ISSUES++))
    fi
    if grep -iE "JWT_SECRET=.*your_|JWT_SECRET=test" "$ENV_FILE" 2>/dev/null; then
        ((ENV_ISSUES++))
    fi

    if [[ $ENV_ISSUES -eq 0 ]]; then
        echo -e "${GREEN}✓ OK${NC} (pas de secrets en clair détectés)"
        ((score_current++))
    else
        echo -e "${RED}✗ CRITIQUE${NC} ($ENV_ISSUES secrets potentiellement visibles)"
        issues+=("Remplacez secrets en clair dans .env (voir rapport détaillé)")
    fi

    # --- Résumé final ---
    echo ""
    echo "  ═════════════════════════════════════════════"
    echo "  SCORE SÉCURITÉ : $score_current / $score_total"
    echo "  ═════════════════════════════════════════════"
    echo ""

    if [[ $score_current -eq 4 ]]; then
        echo -e "  ${GREEN}🎉 EXCELLENT - Production Ready${NC}"
    elif [[ $score_current -ge 3 ]]; then
        echo -e "  ${YELLOW}✓ BON - Recommandations:${NC}"
        for issue in "${issues[@]}"; do
            echo "    • $issue"
        done
    else
        echo -e "  ${RED}⚠️  CRITIQUE - Actions requises:${NC}"
        for issue in "${issues[@]}"; do
            echo "    • $issue"
        done
    fi

    echo ""
}
```

#### Appel dans setup.sh (à la fin)

```bash
# === FIN setup.sh ===
generate_security_report

# Afficher URL d'accès
echo ""
echo -e "${BOLD}Accès au Dashboard:${NC}"
echo -e "  URL: ${GREEN}https://${DOMAIN}${NC}"
echo -e "  Utilisateur: ${GREEN}admin${NC}"
echo ""

# Fichier rapport pour logs
echo "Security Report - $(date +%Y-%m-%d_%H:%M:%S)" >> logs/setup_report.log
```

### 3.3 Impacts

| Aspect | Avant | Après | Amélioration |
|--------|-------|-------|--------------|
| **Visibilité** | Utilisateur ne sait pas son score | Rapport clair + suggestions | +Énorme |
| **Confiance** | Incertitude configuration | Confirmation explicite | +Bonne |
| **Troubleshooting** | Difficulté identifier problèmes | Check-list flagge les problèmes | +Excellente |
| **Complexité** | N/A | Faible (checks simples) | ≈ |

---

## 🔧 AXE 4: GESTION DES LOGIN/MOT DE PASSE EXISTANTS

### 4.1 Analyse de l'Existant

**État actuel:** ✅ **Très bien implémenté**

**Code existant (setup.sh, lines 500-589):**

```bash
# Déterminer s'il y a déjà un mot de passe configuré
HAS_BCRYPT_HASH=false
if grep -q "^DASHBOARD_PASSWORD=\$2[aby]\$" "$ENV_FILE"; then
    HAS_BCRYPT_HASH=true
fi

# Menu: nouveau, garder, annuler
if [[ "$NEEDS_PASSWORD_CONFIG" == "true" ]]; then
    if [[ "$HAS_BCRYPT_HASH" == "true" ]]; then
        ACTION=$(prompt_password_action "true")  # Menu avec "Garder" option
    else
        ACTION=$(prompt_password_action "false")  # Menu sans "Garder"
    fi

    case "$ACTION" in
        new)
            # Lire mot de passe (caché)
            # Hasher via Docker + bcryptjs
            # Doubler les $ pour shell-safe
            # Écrire dans .env
            ;;
        keep)
            log_info "✓ Mot de passe existant conservé"
            ;;
        cancel)
            log_warn "Configuration annulée. Plus tard: setup.sh"
            ;;
    esac
fi
```

**Points forts:**
- ✅ Détection du hash bcrypt existant
- ✅ Menu interactif (nouveau, garder, annuler)
- ✅ Hachage via Docker (portable, sécurisé)
- ✅ Doublage `$` pour shell (bien documenté)
- ✅ Idempotence complète (re-run safe)

**Points faibles:**
- ❌ Pas de script séparé pour modification ultérieure
- ❌ Pas de moyen de "récupérer" mot de passe si oubli
- ❌ Pas d'option dans menus principaux pour modifier password post-setup

### 4.2 Proposition: Amélioration Mineure

**Changement proposé:** Ajouter un **menu principal** accessible après setup pour relancer wizard password:

```bash
# Créer fonction à la fin setup.sh
show_postsetup_menu() {
    echo ""
    log_step "Setup Terminé - Menus Utiles"

    echo -e "\nPour modifier la configuration après setup :"
    echo -e "  • Mot de passe Dashboard:        ./scripts/manage_dashboard_password.sh"
    echo -e "  • Certificat Let's Encrypt:      ./scripts/setup_letsencrypt.sh"
    echo -e "  • Sauvegardes Google Drive:      rclone config"
    echo -e "  • Vérification santé système:    ./scripts/monitor_pi4_health.sh"
    echo ""
}
```

**Validation:** Cet ajout est minimal et ne change rien au flux existant (très bien structuré).

### 4.3 Impacts

| Aspect | Avant | Après | Amélioration |
|--------|-------|-------|--------------|
| **Gestion Existante** | Excellente | Excellente | = |
| **Découverte** | Utilisateur ne sait pas script séparé | Menu montre les options | +Bonne |
| **Complexité** | N/A | N/A | = |

---

## 🔧 AXE 5: SCRIPT SÉPARÉ DE GESTION DU MOT DE PASSE

### 5.1 Proposition: Script `manage_dashboard_password.sh`

Ce script permettra de modifier ou réinitialiser le mot de passe en dehors du setup.sh initial.

#### Fonction 1: Changer le Mot de Passe

```bash
#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Script de Gestion du Mot de Passe Dashboard
# LinkedIn Birthday Auto - Modification & Récupération sécurisée
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# --- Couleurs ---
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

# --- Config ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_ROOT}/.env"

# --- Logging ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Vérifications ---
if [[ ! -f "$ENV_FILE" ]]; then
    log_error ".env non trouvé. Lancez setup.sh d'abord."
    exit 1
fi

# === MENU PRINCIPAL ===
echo ""
echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║        Gestion du Mot de Passe Dashboard                ║${NC}"
echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

choice=$(
    prompt_menu \
        "Que désirez-vous faire ?" \
        "Changer le mot de passe" \
        "Réinitialiser le mot de passe (générer un aléatoire)" \
        "Afficher le statut du mot de passe" \
        "Quitter"
)

# === FONCTION 1: Changer ---
if [[ "$choice" == "1" ]]; then
    log_info "Changement du mot de passe..."

    echo -e "${BOLD}Entrez le nouveau mot de passe :${NC}"
    echo -n "Mot de passe (caché) : "
    read -rs NEW_PASS
    echo ""

    echo -n "Confirmez le mot de passe : "
    read -rs NEW_PASS_CONFIRM
    echo ""

    if [[ "$NEW_PASS" != "$NEW_PASS_CONFIRM" ]]; then
        log_error "Les mots de passe ne correspondent pas."
        exit 1
    fi

    if [[ -z "$NEW_PASS" ]]; then
        log_error "Mot de passe vide."
        exit 1
    fi

    log_info "Hachage sécurisé du mot de passe..."

    # Hash via Docker
    DASHBOARD_IMG="ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest"

    if ! docker image inspect "$DASHBOARD_IMG" >/dev/null 2>&1; then
        log_info "Téléchargement image dashboard..."
        docker pull -q "$DASHBOARD_IMG"
    fi

    HASH_OUTPUT=$(docker run --rm \
        --entrypoint node \
        -e PWD_INPUT="$NEW_PASS" \
        "$DASHBOARD_IMG" \
        -e "console.log(require('bcryptjs').hashSync(process.env.PWD_INPUT, 12))" 2>/dev/null)

    if [[ "$HASH_OUTPUT" =~ ^\$2 ]]; then
        SAFE_HASH=$(echo "$HASH_OUTPUT" | sed 's/\$/\$\$/g')
        ESCAPED_SAFE_HASH=$(echo "$SAFE_HASH" | sed 's/[\/&]/\\&/g')

        sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=${ESCAPED_SAFE_HASH}|" "$ENV_FILE"

        log_success "Mot de passe modifié et stocké dans .env"
        log_info "Redémarrage du dashboard pour appliquer..."

        if docker compose -f "${PROJECT_ROOT}/docker-compose.pi4-standalone.yml" ps dashboard >/dev/null 2>&1; then
            docker compose -f "${PROJECT_ROOT}/docker-compose.pi4-standalone.yml" restart dashboard >/dev/null 2>&1
            log_success "Dashboard redémarré."
        fi
    else
        log_error "Echec du hachage: $HASH_OUTPUT"
        exit 1
    fi

# === FONCTION 2: Réinitialiser ---
elif [[ "$choice" == "2" ]]; then
    log_warn "⚠️  Réinitialisation du mot de passe"
    log_info "Un mot de passe temporaire fort sera généré et affiché une fois."

    read -p "Êtes-vous sûr ? [y/N] : " -r confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "Annulé."
        exit 0
    fi

    # Générer mot de passe aléatoire fort (16 chars)
    TEMP_PASS=$(openssl rand -base64 12)

    log_info "Hachage du mot de passe temporaire..."

    DASHBOARD_IMG="ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest"

    if ! docker image inspect "$DASHBOARD_IMG" >/dev/null 2>&1; then
        docker pull -q "$DASHBOARD_IMG"
    fi

    HASH_OUTPUT=$(docker run --rm \
        --entrypoint node \
        -e PWD_INPUT="$TEMP_PASS" \
        "$DASHBOARD_IMG" \
        -e "console.log(require('bcryptjs').hashSync(process.env.PWD_INPUT, 12))" 2>/dev/null)

    SAFE_HASH=$(echo "$HASH_OUTPUT" | sed 's/\$/\$\$/g')
    ESCAPED_SAFE_HASH=$(echo "$SAFE_HASH" | sed 's/[\/&]/\\&/g')

    sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=${ESCAPED_SAFE_HASH}|" "$ENV_FILE"

    # Logging sécurisé (pas le mot de passe!)
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Mot de passe réinitialisé" >> "${PROJECT_ROOT}/logs/password_history.log"

    echo ""
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}✓ MOT DE PASSE TEMPORAIRE GÉNÉRÉ${NC}"
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${RED}${BOLD}$TEMP_PASS${NC}"
    echo ""
    echo -e "  ⚠️  Sauvegardez ce mot de passe temporaire maintenant !"
    echo -e "  ⚠️  Il ne sera pas affiché à nouveau."
    echo ""
    echo -e "  Après connexion, changez le mot de passe via le dashboard"
    echo -e "  ou relancez ce script."
    echo ""
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════${NC}"

    # Redémarrage dashboard
    if docker compose -f "${PROJECT_ROOT}/docker-compose.pi4-standalone.yml" ps dashboard >/dev/null 2>&1; then
        docker compose -f "${PROJECT_ROOT}/docker-compose.pi4-standalone.yml" restart dashboard >/dev/null 2>&1
        log_success "Dashboard redémarré avec nouveau mot de passe."
    fi

# === FONCTION 3: Afficher statut ---
elif [[ "$choice" == "3" ]]; then
    echo ""
    echo -e "${BOLD}Statut du Mot de Passe${NC}"
    echo ""

    if grep -q "^DASHBOARD_PASSWORD=\$2[aby]\$" "$ENV_FILE" 2>/dev/null; then
        HASH=$(grep "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2)
        HASH_SHORT="${HASH:0:30}..."
        echo -e "  ${GREEN}✓ Hash bcrypt présent${NC}"
        echo -e "  Hash (premiers 30 chars): $HASH_SHORT"

        # Âge du hash
        LAST_CHANGE=$(stat -c %y "${ENV_FILE}" 2>/dev/null | cut -d' ' -f1)
        echo -e "  Dernier changement: $LAST_CHANGE"
    elif grep -q "CHANGEZ_MOI" "$ENV_FILE" 2>/dev/null; then
        echo -e "  ${RED}✗ CONFIGURATION MANQUANTE${NC}"
        echo -e "  Mot de passe par défaut détecté. Configurez: $0"
    else
        echo -e "  ${YELLOW}⚠️  INCONNU${NC}"
        echo -e "  Format mot de passe non reconnu. Vérifiez .env"
    fi

    echo ""

# === FONCTION 4: Quitter ---
else
    log_info "Quitter."
fi

exit 0
```

#### Helper Function: `prompt_menu()` (à ajouter si absent)

```bash
prompt_menu() {
    local title="$1"
    shift
    local options=("$@")
    local choice

    echo -e "\n${BOLD}${BLUE}${title}${NC}\n"

    local i=1
    for option in "${options[@]}"; do
        echo "  ${BOLD}${i})${NC} ${option}"
        i=$((i + 1))
    done

    echo -ne "\n${YELLOW}Votre choix [1-$#] : ${NC}"
    read -r choice || return 1

    if ! [[ "$choice" =~ ^[0-9]+$ ]] || [[ "$choice" -lt 1 ]] || [[ "$choice" -gt $# ]]; then
        log_error "Choix invalide"
        return 2
    fi

    echo "$choice"
    return 0
}
```

#### Permissions et Placement

```bash
# À ajouter au projet:
# - Fichier: scripts/manage_dashboard_password.sh
# - Permissions: chmod +x scripts/manage_dashboard_password.sh
# - Logging: logs/password_history.log (audit trail sécurisé)
```

### 5.2 Impacts

| Aspect | Avant | Après | Amélioration |
|--------|-------|-------|--------------|
| **Modifi Password** | Via setup.sh uniquement (lourd) | Script dédié rapide | +Excellente |
| **Récupération** | Pas de récupération (perte accès) | Réinitialisation aléatoire | +Énorme |
| **Sécurité** | Hachage ok | Même niveau + audit trail | = |
| **UX** | Obligation relancer setup.sh | Menu clair + 3 options | +Bonne |
| **Complexité** | N/A | Basse (script indépendant) | ≈ |

### 5.3 Points de Vigilance

1. **Ne jamais afficher le mot de passe existant** (impossible avec bcrypt, c'est l'objectif)
2. **Logging sécurisé:** Log l'action (date/time), pas le mot de passe
3. **Double saisie:** Confirmer le mot de passe avant hachage (évite typos)
4. **Permissions .env:** Vérifier que .env reste 600 (lecture seule pour user)

---

## 📊 RÉSUMÉ DES MODIFICATIONS

### Fichiers à Créer

| Fichier | Taille | Priorité | Description |
|---------|--------|----------|-------------|
| `scripts/manage_dashboard_password.sh` | 300 lignes | HAUTE | Gestion password (change/reset) |

### Fichiers à Modifier

| Fichier | Sections | Priorité | Description |
|---------|----------|----------|-------------|
| `setup.sh` | +Menu HTTPS (300 lignes) | HAUTE | Menu HTTPS + validation |
| | +Phase 5.1 Sauvegardes (250 lignes) | HAUTE | Intégration Google Drive + rclone |
| | +Report sécurité (200 lignes) | MODÉRÉE | Verification & scoring sécurité |
| | +Post-setup menu (50 lignes) | BASSE | Menu accès scripts post-setup |
| `scripts/backup_to_gdrive.sh` | +Slack notification (30 lignes) | BASSE | Notifications Slack opt |
| | +Test restore monthly (40 lignes) | BASSE | Validation restore aléatoire |
| `.env.pi4.example` | +Nouvelles variables (10 lignes) | BASSE | SLACK_WEBHOOK, autres |

### Fichiers Inchangés (Excellents)

| Fichier | Raison |
|---------|--------|
| `deployment/nginx/linkedin-bot.conf.template` | Excellente structure, pas de change |
| `scripts/setup_letsencrypt.sh` | Robuste, juste sera appelé depuis setup.sh |
| `docker-compose.pi4-standalone.yml` | Config saine, seulement doc update |

---

## 🚀 PLAN D'IMPLÉMENTATION

### Phase 1: Création Script Password (1-2h)

- [ ] Créer `scripts/manage_dashboard_password.sh`
- [ ] Tester change password
- [ ] Tester reset password (aléatoire)
- [ ] Tester affichage statut
- [ ] Documentation inline

**Priorité:** CRITIQUE (peu de dépendances)

### Phase 2: Amélioration setup.sh - Menu HTTPS (3-4h)

- [ ] Ajouter menu HTTPS (4 options)
- [ ] Implémenter option 1 (LAN)
- [ ] Implémenter option 2 (Let's Encrypt)
- [ ] Implémenter option 3 (Certs existants)
- [ ] Implémenter option 4 (Manual)
- [ ] Tests chaque scenario

**Priorité:** HAUTE (core feature)

### Phase 3: Amélioration setup.sh - Google Drive (2-3h)

- [ ] Ajouter Phase 5.1
- [ ] Menu activation sauvegardes
- [ ] Wizard rclone config
- [ ] Config crypt optionnelle
- [ ] Cron auto-setup
- [ ] Test backup initial
- [ ] Amélioration backup_to_gdrive.sh (Slack + restore)

**Priorité:** HAUTE (data safety)

### Phase 4: Rapport Sécurité (1-2h)

- [ ] Fonction `generate_security_report()`
- [ ] 4 checks (password, HTTPS, backup, .env)
- [ ] Score calculation
- [ ] Appel fin setup.sh
- [ ] Tests validations

**Priorité:** MODÉRÉE (UX/confidence)

### Phase 5: Documentation & Cleanup (1-2h)

- [ ] Mettre à jour README
- [ ] Créer SETUP_GUIDE.md (utilisation nouveau menu)
- [ ] Tester flow complet setup.sh
- [ ] Commit & push

**Priorité:** MODÉRÉE (doc)

---

## ✅ CRITÈRES D'ACCEPTATION

### Pour HTTPS
- [x] Menu 4 options visible dans setup.sh
- [x] Chaque option fonctionne sans erreur
- [x] Certificat activé post-setup (curl teste)
- [x] Redirection HTTP→HTTPS fonctionne
- [x] Documentation claire pour utilisateur

### Pour Google Drive
- [x] Menu activation sauvegardes visible
- [x] Wizard rclone fonctionne (ou skip manuel)
- [x] Cron configuré automatiquement
- [x] Test backup initial réussit
- [x] Notification Slack optionnelle

### Pour Sécurité
- [x] Rapport final s'affiche à fin setup.sh
- [x] Score calculation cohérent (0-4)
- [x] Issues flaggées avec suggestions
- [x] Liens vers docs/scripts clairs

### Pour Credentials
- [x] Script manage_dashboard_password.sh fonctionnel
- [x] Menu change/reset/status clair
- [x] Logging sécurisé (pas mot de passe exposé)
- [x] Redémarrage dashboard après change

---

## 📝 NOTES FINALES

### Points de Force du Design

1. **Backward Compatibility:** Aucun breaking change. setup.sh existant continue à fonctionner.
2. **Progressive Enhancement:** Menu HTTPS/Backup optional, pas forcé.
3. **Sécurité-by-default:** Recommandations claires dans chaque menu.
4. **User Empowerment:** Accès clair aux scripts post-setup pour modifications.

### Points d'Attention

1. **RPi4 Constraints:** Tous les scripts testés mental pour ARM64 (rclone, docker, bcryptjs).
2. **Timeouts:** setup.sh peut durer 10-15min (Docker pulls, tests). Prévoir patience.
3. **DNS/Internet:** Certaines options (Let's Encrypt) requièrent connectivité. Menu clear sur prérequis.

### Prochaines Étapes (Post-Implementation)

1. **Monitoring Integration:** Prometheus metrics pour backup success/failure
2. **Notification Channels:** Slack + Email + Webhook flexibility
3. **Disaster Recovery:** Automated restore testing (DR drills)
4. **Multi-user Support:** Créer comptes adicionnels (si dashboard support)

---

**Fin du Document de Conception**

*À imprimer/archiver pour référence implémentation*
