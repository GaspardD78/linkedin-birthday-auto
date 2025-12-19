# 🔐 GUIDE CONFIGURATION HTTPS
## Setup Sécurisé SSL/TLS pour LinkedIn Auto

**Version:** 3.3+
**Date:** Jan 2025
**Cible:** Tous les utilisateurs (LAN et Production)

---

## 📋 Table des Matières

1. [Concepts HTTPS](#concepts-https)
2. [Les 4 Options](#les-4-options)
3. [Installation Setup](#installation-setup)
4. [Validation & Troubleshooting](#validation--troubleshooting)

---

## 🔒 Concepts HTTPS

### Pourquoi HTTPS?

| Aspect | HTTP | HTTPS |
|--------|------|-------|
| **Chiffrement** | ❌ Non | ✅ Oui |
| **Authentification** | ❌ Non | ✅ Oui |
| **Intégrité** | ❌ Non | ✅ Oui |
| **Sécurité Login** | ❌ Mot de passe visible | ✅ Mot de passe chiffré |
| **Score SEO** | ⚠️ Pénalisé | ✅ Favorisé |

**Recommandation:**
- LAN interne = HTTP peut suffire
- Accès Internet = HTTPS obligatoire

### Types de Certificats

| Type | Source | Coût | Validation | Durée |
|------|--------|------|-----------|-------|
| **Auto-signé** | Généré localement | Gratuit | Aucune | 365 jours |
| **Let's Encrypt** | Gratuit automatisé | Gratuit | DNS | 90 jours (auto-renew) |
| **Commercial** | DigiCert, etc. | Payant | HTTPS | 1-3 ans |

---

## 🎯 Les 4 Options

### Option 1: LAN Uniquement (HTTP)

**Quand l'utiliser:**
- ✅ Réseau interne uniquement
- ✅ Test/développement local
- ✅ Pas d'accès Internet
- ❌ Ne pas utiliser en production public!

**Configuration:**
```bash
# Pendant setup.sh, choisir Option 1:
# 🏠 LAN uniquement (HTTP simple, réseau interne)
```

**Résultat:**
```bash
✓ HTTPS désactivé (LAN uniquement)
  Accès : http://192.168.1.100:3000
  ⚠️  POUR PRODUCTION SUR INTERNET : Utilisez Let's Encrypt (option 2)
```

**Accès:**
```bash
# Local (même RPi):
http://localhost:3000

# Autre machine sur réseau:
http://192.168.1.100:3000  # Remplacer IP par votre RPi
```

**Sécurité:** ⚠️ Faible
- Mot de passe transmis en clair
- Man-in-the-middle possible
- Acceptable LAN interne seulement

---

### Option 2: Let's Encrypt (Recommandée Production)

**Quand l'utiliser:**
- ✅ Domaine public configuré
- ✅ Ports 80/443 accessibles Internet
- ✅ Production / accès externe
- ✅ Certificats gratuits auto-renouvelés

**Prérequis:**
1. **Domaine DNS** pointant vers votre RPi
   ```bash
   # Example: example.com → 1.2.3.4 (votre IP publique)
   # Test DNS:
   nslookup example.com
   ```

2. **Port 80 accessible**
   ```bash
   # Test (de externe):
   curl -I http://example.com
   # Doit retourner code 301 ou 200 (pas timeout/connection refused)
   ```

3. **Port 443 accessible**
   ```bash
   # Will be tested pendant Let's Encrypt setup
   ```

**Configuration (Phase 4.7):**
```bash
# Pendant setup.sh, choisir Option 2:
# 🌐 Domaine avec Let's Encrypt (production recommandée)
```

**Setup Let's Encrypt (Post-setup initial):**
```bash
./scripts/setup_letsencrypt.sh
```

**Interactif steps:**
1. Vérifie DNS resolution
2. Vérifie port 80 accessible
3. Demande votre email (notifications expiration)
4. Obtient certificat Let's Encrypt
5. Configure Nginx auto-renew

**Résultat:**
```bash
✓ HTTPS fonctionnel (HTTP 200)

Certificat:
  Validité: 90 jours
  Auto-renouvellement: OUI (avant expiration)
  Notifs expiration: Oui (à votre email)
```

**Accès:**
```bash
# HTTPS sécurisé:
https://example.com

# HTTP redirige automatiquement:
http://example.com → https://example.com ✅
```

**Sécurité:** ✅ Excellente
- Certificat validé par Let's Encrypt
- Chiffrement 256-bit TLS 1.3
- Auto-renouvelé automatiquement
- Recommandé pour production

---

### Option 3: Certificats Existants (Import)

**Quand l'utiliser:**
- ✅ Vous avez certificats custom
- ✅ Autorité de certification tierce
- ✅ Certificats d'entreprise
- ✅ Certificats Wildcard

**Prérequis:**
1. **Fichier fullchain.pem** (certificat + chain)
   ```bash
   # Deve contenir:
   # - Votre certificat
   # - Certificats intermédiaires
   # - (optionnel) Root CA
   ```

2. **Fichier privkey.pem** (clé privée)
   ```bash
   # Doit être en format PEM non-encrypté
   # Permissions: 600 (lecture owner seulement)
   ```

**Configuration (Phase 4.7):**
```bash
# Pendant setup.sh, choisir Option 3:
# 🔒 Certificats existants (import)
```

**Prompts:**
```bash
Chemin fullchain.pem : /path/to/fullchain.pem
Chemin privkey.pem : /path/to/privkey.pem
```

**Validation:**
```bash
# Le script vérifie:
✓ Fichiers existent
✓ Certificat est valide
✓ Clé privée correspond certificat
✓ Permissions correctes
```

**Résultat:**
```bash
✓ Certificats importés dans:
  certbot/conf/live/gaspardanoukolivier.freeboxos.fr/
  ├─ fullchain.pem
  └─ privkey.pem
```

**Renouvellement manuel:**
```bash
# Si certificat expire, le remplacer manuellement:
cp /path/to/new_fullchain.pem \
   certbot/conf/live/YOUR_DOMAIN/fullchain.pem
cp /path/to/new_privkey.pem \
   certbot/conf/live/YOUR_DOMAIN/privkey.pem

# Redémarrer Nginx:
docker compose restart nginx
```

**Sécurité:** ✅ Bonne (dépend source certificat)

---

### Option 4: Configuration Manuelle

**Quand l'utiliser:**
- ✅ Setup complexe custom
- ✅ Load balancer / reverse proxy déjà en place
- ✅ Configuration particulière
- ⚠️ Nécessite expertise Linux/Nginx

**Configuration (Phase 4.7):**
```bash
# Pendant setup.sh, choisir Option 4:
# ⚙️  Configuration manuelle (gérerez après setup)
```

**Message:**
```bash
⚠️  Configuration manuelle HTTPS sélectionnée.
Vous êtes responsable de:
  - Placer certificats dans: certbot/conf/live/YOUR_DOMAIN/
  - Configurer Nginx manuellement
  - Redémarrer Nginx après changements
```

**Étapes post-setup:**
1. Créer dossier certificats:
   ```bash
   mkdir -p certbot/conf/live/YOUR_DOMAIN
   chmod 755 certbot/conf/live/YOUR_DOMAIN
   ```

2. Placer certificats:
   ```bash
   cp fullchain.pem certbot/conf/live/YOUR_DOMAIN/
   cp privkey.pem certbot/conf/live/YOUR_DOMAIN/
   chmod 644 fullchain.pem
   chmod 600 privkey.pem
   ```

3. Configurer Nginx (optionnel):
   ```bash
   # Le template Nginx est déjà configuré
   # Vérifier: deployment/nginx/linkedin-bot.conf.template
   ```

4. Redémarrer services:
   ```bash
   docker compose restart nginx
   ```

**Sécurité:** ⚠️ Dépend votre setup

---

## ✅ Validation & Troubleshooting

### Vérifier HTTPS Fonctionne

```bash
# Test local:
curl -I https://localhost

# Test domaine:
curl -I https://example.com

# Browser:
# Ouvrir https://YOUR_DOMAIN
# Vérifier: cadenas vert + pas avertissements
```

### Voir certificat:

```bash
# Certificat auto-signé:
openssl x509 -in certbot/conf/live/YOUR_DOMAIN/fullchain.pem \
  -text -noout | grep -A 5 "Issuer:"

# Doit montrer: Issuer: CN = Temporary Certificate

# Certificat Let's Encrypt:
openssl x509 -in certbot/conf/live/YOUR_DOMAIN/fullchain.pem \
  -text -noout | grep -A 5 "Issuer:"

# Doit montrer: Issuer: C = US, O = Let's Encrypt, ...
```

### Vérifier validité certificat:

```bash
# Date expiration:
openssl x509 -in certbot/conf/live/YOUR_DOMAIN/fullchain.pem \
  -noout -dates

# Output:
# notBefore=Jan 19 12:00:00 2025 GMT
# notAfter=Apr 19 12:00:00 2025 GMT
```

### Problèmes Courants

#### ❌ "HTTP 520 Bad Gateway"

**Cause:** Nginx → services internes down

```bash
# Vérifier services:
docker compose ps

# Relancer:
docker compose up -d

# Voir logs:
docker compose logs nginx
```

#### ❌ "Certificat auto-signé = avertissement browser"

**Normal pour auto-signé.** Solutions:
1. Utiliser Let's Encrypt (Option 2) - meilleur
2. Accepter risque (bouton "Continuer")
3. Ajouter exception browser (temporaire)

#### ❌ "Let's Encrypt setup échoue"

Causes possibles:
- DNS pas configuré → Tester: `nslookup YOUR_DOMAIN`
- Port 80 pas ouvert → Vérifier firewall
- Déjà certificat expiré → Nettoyer: `sudo rm -rf /etc/letsencrypt`

**Solution:** Relancer:
```bash
./scripts/setup_letsencrypt.sh
```

#### ❌ "Port 80/443 déjà en usage"

```bash
# Trouver processus:
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443

# Arrêter processus conflictuel (ex Nginx déjà running):
sudo systemctl stop nginx

# Puis relancer compose:
docker compose up -d
```

---

## 🔄 Renouvellement Certificats

### Auto-signé (1 an)

Renouvelé automatiquement par Nginx lors du redémarrage.

### Let's Encrypt (90 jours)

Renouvelé **automatiquement** 30 jours avant expiration via cron.

**Vérifier cron:**
```bash
sudo crontab -l
# Doit voir: 0 3 * * * certbot renew --quiet
```

### Certificats Custom

Renouvellement **manuel**:
```bash
# Remplacer fichiers fullchain.pem et privkey.pem
cp new_fullchain.pem certbot/conf/live/YOUR_DOMAIN/
cp new_privkey.pem certbot/conf/live/YOUR_DOMAIN/

# Redémarrer Nginx:
docker compose restart nginx
```

---

## 📚 Ressources

- **Let's Encrypt:** https://letsencrypt.org/
- **Certbot Docs:** https://certbot.eff.org/
- **Nginx SSL:** https://nginx.org/en/docs/http/ngx_http_ssl_module.html
- **Raspberry Pi Firewall:** https://www.raspberrypi.com/tutorials/

---

## 🎯 Recommandations

| Scénario | Recommandation | Raison |
|----------|-----------------|--------|
| **Test Local** | Option 1 (LAN) | Gratuit, pas config DNS |
| **Production Internet** | Option 2 (Let's Encrypt) | Gratuit, auto-renew, secure |
| **Certificats Existants** | Option 3 (Import) | Votre infrastructure |
| **Setup Complexe** | Option 4 (Manuel) | Control total |

---

**Besoin d'aide?** Consultez [docs/TROUBLESHOOTING_2025.md](TROUBLESHOOTING_2025.md)
