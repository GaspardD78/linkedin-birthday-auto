# Configuration HTTPS - Guide Complet

## 📋 Vue d'ensemble

Ce guide explique le système de configuration HTTPS du projet LinkedIn Birthday Auto Bot. Le système support 4 modes de déploiement différents, du simple (LAN uniquement) au production-ready (Let's Encrypt automatisé).

## 🎯 Modes de Configuration HTTPS

### 1. **Mode LAN (HTTP uniquement)**
- **Cas d'usage**: Réseau local, développement, testing
- **Configuration**: HTTP sur port 80, pas de HTTPS
- **Certificats**: Aucun certificat requis
- **Template Nginx**: `linkedin-bot-lan.conf.template`
- **Sécurité**: Aucun chiffrement en transit (réseau interne seulement)

```bash
# Lors du setup, choisir option 1:
# 🏠 LAN uniquement (HTTP, pas HTTPS)
```

### 2. **Mode Let's Encrypt (Production)**
- **Cas d'usage**: Accès externe, production, domaines valides
- **Configuration**: HTTPS sur port 443, HTTP redirection vers HTTPS
- **Certificats**: Auto-générés par Certbot (Let's Encrypt)
- **Renouvellement**: Automatique via cron (tous les jours à 3h du matin)
- **Template Nginx**: `linkedin-bot-https.conf.template`
- **Prérequis**:
  - Domaine valide pointant vers votre IP publique
  - Port 80 et 443 accessibles depuis Internet
  - Script de renouvellement: `scripts/setup_letsencrypt.sh`

```bash
# Lors du setup, choisir option 2:
# 🌐 Domaine avec Let's Encrypt (production)

# Configuration ultérieure:
./scripts/setup_letsencrypt.sh
```

### 3. **Mode Certificats Existants**
- **Cas d'usage**: Certificats auto-signés, certificats d'entreprise, certificats achetés
- **Configuration**: HTTPS sur port 443, HTTP redirection vers HTTPS
- **Certificats**: Import de fichiers existants
- **Template Nginx**: `linkedin-bot-https.conf.template`
- **Prérequis**:
  - Fichier `fullchain.pem` (certificat + chaîne)
  - Fichier `privkey.pem` (clé privée)

```bash
# Lors du setup, choisir option 3:
# 🔒 Certificats existants (import)

# Fournir les chemins aux fichiers:
# Chemin fullchain.pem : /path/to/fullchain.pem
# Chemin privkey.pem : /path/to/privkey.pem
```

### 4. **Mode Configuration Manuelle**
- **Cas d'usage**: Configurations avancées, proxies spécialisés
- **Configuration**: À configurer manuellement après setup
- **Template Nginx**: Aucun template généré
- **Notes**: Le certificat temporaire est créé mais aucun renouvellement n'est configuré

```bash
# Lors du setup, choisir option 4:
# ⚙️  Configuration manuelle (plus tard)

# Configuration manuelle ultérieure requise:
# 1. Placer les certificats dans: certbot/conf/live/${DOMAIN}/
#    - fullchain.pem
#    - privkey.pem
# 2. Générer la config Nginx manuellement
# 3. Relancer les conteneurs Docker
```

## 🔧 Architecture de Configuration

### Flux de Sélection du Mode

```
Setup.sh
  ↓
[Phase 5: Configuration HTTPS]
  ↓
Demander le mode HTTPS à l'utilisateur
  ↓
  ├─ LAN → Pas de certificats
  ├─ Let's Encrypt → Setup initial + renouvellement auto
  ├─ Existants → Import des certificats
  └─ Manuel → Instructions pour configuration manuelle
  ↓
[Phase 5.1: Génération Nginx]
  ↓
  ├─ LAN → linkedin-bot-lan.conf.template (HTTP)
  └─ Autres → linkedin-bot-https.conf.template (HTTPS)
  ↓
Générer: deployment/nginx/linkedin-bot.conf (via envsubst)
  ↓
[Phase 5.3: Optionnel - Cron Renouvellement]
  ↓
Si Let's Encrypt → Configurer renouvellement automatique
```

### Templates Nginx

#### HTTP Only (LAN Mode)
- **Fichier**: `deployment/nginx/linkedin-bot-lan.conf.template`
- **Port**: 80 (HTTP)
- **Features**:
  - Rate limiting (général, API, login)
  - Proxy vers Dashboard (http://dashboard:3000)
  - Cache statique
  - Monitoring et health checks

#### HTTPS (All HTTPS Modes)
- **Fichier**: `deployment/nginx/linkedin-bot-https.conf.template`
- **Ports**: 80 (redirection) et 443 (HTTPS)
- **Features**:
  - ACME challenge pour Let's Encrypt
  - HTTP → HTTPS redirection (301)
  - TLS 1.2 et 1.3
  - Cipher suites sécurisés
  - Security headers (HSTS, CSP, X-Frame-Options, etc.)
  - Rate limiting avancé
  - Proxy vers Dashboard et API
  - Cache statique optimisé

## 📁 Structure des Fichiers

```
linkedin-birthday-auto/
├── setup.sh                           # Script de setup (Phase 5 modifiée)
├── deployment/nginx/
│   ├── linkedin-bot-https.conf.template  # Template HTTPS
│   ├── linkedin-bot-lan.conf.template    # Template LAN
│   ├── linkedin-bot.conf             # Fichier généré (ne pas éditer)
│   ├── nginx.conf                    # Config Nginx principale
│   ├── rate-limit-zones.conf         # Zones de rate limiting
│   ├── options-ssl-nginx.conf        # Options SSL/TLS
│   ├── ssl-dhparams.pem             # Paramètres DH
│   └── 429.html                      # Page erreur rate limit
├── certbot/
│   └── conf/live/
│       └── ${DOMAIN}/
│           ├── fullchain.pem        # Certificat
│           └── privkey.pem          # Clé privée
├── scripts/
│   ├── setup_letsencrypt.sh         # Configuration Let's Encrypt
│   ├── renew_certificates.sh        # Renouvellement certificats
│   └── lib/
│       └── common.sh, docker.sh, etc. # Bibliothèques partagées
└── docs/
    ├── HTTPS_CONFIGURATION.md        # Ce fichier
    ├── SETUP_V4_IMPROVEMENTS.md      # Améliorations générales
    └── ...
```

## 🚀 Procédures Courantes

### A. Installation Initiale

```bash
# 1. Lancer le setup
./setup.sh

# 2. Lors de la PHASE 5 (Configuration HTTPS), choisir le mode:
# Option 1: LAN only
# Option 2: Let's Encrypt (puis ./scripts/setup_letsencrypt.sh)
# Option 3: Certificats existants
# Option 4: Configuration manuelle

# 3. Le setup génère automatiquement:
# - deployment/nginx/linkedin-bot.conf
# - Certificats temporaires (si nécessaire)
# - Configuration de renouvellement (si Let's Encrypt)
```

### B. Passer de LAN à HTTPS (Let's Encrypt)

```bash
# 1. Avoir un domaine valide pointant vers l'IP publique

# 2. Lancer le setup de Let's Encrypt
./scripts/setup_letsencrypt.sh

# 3. Cette commande:
#    - Valide l'accès au domaine
#    - Génère les certificats via Certbot
#    - Met à jour deployment/nginx/linkedin-bot.conf
#    - Recharge Nginx dans Docker

# 4. Vérifier HTTPS
# curl https://votre-domaine.com
```

### C. Importer des Certificats Existants

```bash
# 1. Placer les fichiers:
# cp /chemin/vers/fullchain.pem certbot/conf/live/${DOMAIN}/
# cp /chemin/vers/privkey.pem certbot/conf/live/${DOMAIN}/

# 2. Régénérer la config Nginx:
# export DOMAIN="votre-domaine.com"
# envsubst '${DOMAIN}' < deployment/nginx/linkedin-bot-https.conf.template > deployment/nginx/linkedin-bot.conf

# 3. Recharger Nginx:
# docker compose exec nginx nginx -s reload
```

### D. Renouvellement Manuel des Certificats

```bash
# Pour Let's Encrypt:
./scripts/renew_certificates.sh

# Vérifier que le renouvellement est configuré en cron:
crontab -l | grep renew_certificates

# Ajouter manuellement si manquant:
# crontab -e
# Ajouter: 0 3 * * * /chemin/abs/scripts/renew_certificates.sh >> /var/log/certbot-renew.log 2>&1
```

## 🔒 Sécurité

### Headers de Sécurité (HTTPS Mode)

Le mode HTTPS ajoute automatiquement:

```nginx
# Forcer HTTPS
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload

# Clickjacking protection
X-Frame-Options: DENY

# Prevent MIME sniffing
X-Content-Type-Options: nosniff

# XSS protection
X-XSS-Protection: 1; mode=block

# Referrer policy
Referrer-Policy: strict-origin-when-cross-origin

# Permissions policy
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

### Rate Limiting

Tous les modes (LAN et HTTPS) incluent:

```nginx
# Général: 10 req/sec par IP
limit_req zone=general burst=20 nodelay;

# Login (anti brute-force): 1 req/min par IP, burst=5
limit_req zone=login burst=5 nodelay;

# API: 60 req/min par IP
limit_req zone=api burst=10 nodelay;
```

### Certificats

**LAN Mode**:
- Aucun certificat requis
- Pas d'exposition à Internet

**HTTPS Modes**:
- Certificats auto-signés temporaires au démarrage
- Let's Encrypt: certificats valides, renouvelés automatiquement
- Existants: certificats d'entreprise ou achetés
- Clés privées stockées avec permissions 600

## 🐛 Dépannage

### Erreur: "Template Nginx introuvable"
```
[ERROR] Template Nginx introuvable: deployment/nginx/linkedin-bot-lan.conf.template
```
**Solution**: Vérifier que les fichiers `linkedin-bot-*.conf.template` existent dans `deployment/nginx/`

### Erreur: "Fichiers certificats non trouvés"
```
[ERROR] Fichiers certificats non trouvés
```
**Solution**:
- Vérifier les chemins fournis
- Pour Let's Encrypt: lancer `./scripts/setup_letsencrypt.sh`
- Pour certificats existants: vérifier fullchain.pem et privkey.pem

### HTTPS ne fonctionne pas
1. Vérifier les certificats:
```bash
ls -la certbot/conf/live/$(grep DOMAIN .env | cut -d= -f2)/
```

2. Vérifier les logs Nginx:
```bash
docker compose logs nginx | tail -50
```

3. Tester la config:
```bash
docker compose exec nginx nginx -t
```

### Certificat expiré
```bash
# Renouveler manuellement:
./scripts/renew_certificates.sh

# Ou (Let's Encrypt):
docker compose exec nginx certbot renew --force-renewal
```

## 📚 Fichiers Relatifs

- `setup.sh`: Script principal (Phase 5 et 5.1 modifiées)
- `scripts/setup_letsencrypt.sh`: Configuration Let's Encrypt
- `scripts/renew_certificates.sh`: Renouvellement certificats
- `docker-compose.yml`: Configuration services (ports 80/443)
- `.env.pi4.example`: Variables (DOMAIN)

## 🔄 Évolution Future

Améliorations possibles:
- [ ] Interface web pour changer mode HTTPS après installation
- [ ] Notifications avant expiration certificats
- [ ] Support ACME DNS (au lieu de HTTP)
- [ ] Wildcard certificates
- [ ] Multiple domains support

## 📞 Support

Pour plus d'informations:
- Consulter `SETUP_V4_IMPROVEMENTS.md`
- Vérifier les logs: `./logs/`
- Executer setup.sh avec `--verbose`
