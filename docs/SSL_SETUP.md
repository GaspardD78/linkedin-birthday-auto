# 🔒 Configuration SSL/HTTPS - Guide Complet

Ce guide explique la gestion des certificats SSL pour sécuriser votre application LinkedIn Birthday Auto avec HTTPS.

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Configuration Automatique](#configuration-automatique)
3. [Certificats Auto-signés](#certificats-auto-signés)
4. [Let's Encrypt](#lets-encrypt)
5. [Renouvellement Automatique](#renouvellement-automatique)
6. [Dépannage](#dépannage)

---

## Vue d'ensemble

Le système SSL est géré de manière **entièrement automatique** par le script `setup.sh`. Voici le fonctionnement:

### Architecture SSL

```
┌─────────────────────────────────────────────────────────────┐
│                         INTERNET                            │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS (443)
                         ▼
              ┌──────────────────────┐
              │   Nginx Reverse      │
              │       Proxy          │
              │  (SSL Termination)   │
              └──────────┬───────────┘
                         │ HTTP (interne)
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    Dashboard         API              Bot
    (Port 3000)    (Port 8000)      Worker
```

### Modes de Fonctionnement

| Mode | Certificat | Usage | Avertissement Navigateur |
|------|-----------|-------|--------------------------|
| **Auto-signé** | Généré localement | Test, dev, réseau local | ⚠️ Oui |
| **Let's Encrypt** | Émis par CA reconnu | Production Internet | ✅ Non |

---

## Configuration Automatique

### 1️⃣ Lors du Premier Lancement (setup.sh)

Le script `setup.sh` configure automatiquement SSL:

```bash
./setup.sh
```

**Actions effectuées automatiquement:**

1. ✅ Lecture du domaine depuis `.env` (variable `DOMAIN`)
2. ✅ Génération de certificats auto-signés si absents
3. ✅ Création des paramètres Diffie-Hellman (2048 bits)
4. ✅ Génération de la configuration Nginx dynamique
5. ✅ Activation HTTPS immédiate

**Résultat:** Application accessible en HTTPS immédiatement (avec certificat auto-signé)

### 2️⃣ Configuration du Domaine

Le domaine est défini dans `.env`:

```bash
# .env
DOMAIN=gaspardanoukolivier.freeboxos.fr
```

Ce domaine est utilisé pour:
- Générer le certificat SSL
- Configurer Nginx (`server_name`)
- Valider les challenges ACME (Let's Encrypt)

---

## Certificats Auto-signés

### Génération Automatique

Les certificats auto-signés sont **générés automatiquement** par `setup.sh` si aucun certificat n'existe:

```bash
# Emplacement
certbot/conf/live/gaspardanoukolivier.freeboxos.fr/
├── fullchain.pem   # Certificat public
├── privkey.pem     # Clé privée
```

### Caractéristiques

- **Validité:** 365 jours
- **Algorithme:** RSA 2048 bits
- **CN:** Nom du domaine configuré
- **Usage:** Test et développement

### ⚠️ Limitation

Le navigateur affichera un avertissement de sécurité car le certificat n'est pas émis par une autorité de certification reconnue.

**Pour contourner l'avertissement (Chrome/Firefox):**
1. Cliquez sur "Avancé"
2. Sélectionnez "Continuer vers le site (non sécurisé)"

---

## Let's Encrypt

Pour un certificat **approuvé par les navigateurs**, utilisez Let's Encrypt.

### Prérequis

✅ **Domaine DNS configuré**
   - Votre domaine doit pointer vers l'IP publique de votre Raspberry Pi
   - Exemple: `gaspardanoukolivier.freeboxos.fr → 86.XXX.XXX.XXX`

✅ **Port 80 accessible**
   - Ouvrir le port 80 sur votre box Internet
   - Rediriger le port 80 vers l'IP du Raspberry Pi

✅ **Services démarrés**
   - `setup.sh` déjà exécuté
   - Conteneurs Docker en cours d'exécution

### Obtention du Certificat

#### Méthode Automatique (Recommandée)

```bash
./scripts/setup_letsencrypt.sh
```

**Ce script:**
1. ✅ Vérifie la résolution DNS
2. ✅ Teste l'accessibilité HTTP (port 80)
3. ✅ Lance Certbot en mode webroot
4. ✅ Obtient le certificat pour `domain.com` et `www.domain.com`
5. ✅ Recharge Nginx automatiquement
6. ✅ Affiche les instructions de renouvellement

#### Méthode Manuelle

```bash
# 1. Certbot standalone (nécessite d'arrêter Nginx temporairement)
docker compose -f docker-compose.pi4-standalone.yml stop nginx

docker run --rm -it \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  -p 80:80 \
  certbot/certbot certonly \
  --standalone \
  --email votre@email.com \
  --agree-tos \
  -d gaspardanoukolivier.freeboxos.fr

# 2. Redémarrer Nginx
docker compose -f docker-compose.pi4-standalone.yml start nginx
```

### Test (Staging)

Pour tester sans limites de taux:

```bash
./scripts/setup_letsencrypt.sh --staging
```

---

## Renouvellement Automatique

### Configuration Cron

Les certificats Let's Encrypt expirent après **90 jours**. Configurez le renouvellement automatique:

```bash
# Éditer crontab
crontab -e

# Ajouter cette ligne (renouvellement tous les jours à 3h du matin)
0 3 * * * cd /home/pi/linkedin-birthday-auto && docker run --rm -v $(pwd)/certbot/conf:/etc/letsencrypt -v $(pwd)/certbot/www:/var/www/certbot certbot/certbot renew --webroot --webroot-path=/var/www/certbot && docker compose -f docker-compose.pi4-standalone.yml exec nginx nginx -s reload >> /var/log/certbot-renew.log 2>&1
```

### Vérification Manuelle

```bash
# Tester le renouvellement (dry-run)
docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot renew --dry-run

# Forcer le renouvellement
docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot renew --force-renewal

# Recharger Nginx
docker compose -f docker-compose.pi4-standalone.yml exec nginx nginx -s reload
```

---

## Dépannage

### ❌ Nginx ne démarre pas

**Symptôme:** Conteneur `nginx-proxy` en crash loop

**Solutions:**

```bash
# 1. Vérifier les logs
docker compose -f docker-compose.pi4-standalone.yml logs nginx

# 2. Vérifier que les certificats existent
ls -la certbot/conf/live/gaspardanoukolivier.freeboxos.fr/

# 3. Re-générer les certificats auto-signés
rm -rf certbot/conf/live/gaspardanoukolivier.freeboxos.fr/
./setup.sh  # Régénère automatiquement
```

### ❌ Certbot échoue (Let's Encrypt)

**Erreur:** `Failed to connect to http://domain.com/.well-known/acme-challenge/`

**Solutions:**

```bash
# 1. Vérifier DNS
host gaspardanoukolivier.freeboxos.fr
# Doit afficher votre IP publique

# 2. Vérifier port 80 depuis Internet
curl -I http://gaspardanoukolivier.freeboxos.fr/.well-known/acme-challenge/test

# 3. Vérifier configuration box/firewall
# - Port 80 ouvert
# - Redirection vers Raspberry Pi configurée

# 4. Tester en local
docker compose -f docker-compose.pi4-standalone.yml logs nginx | grep "acme-challenge"
```

### ❌ Certificat expiré

**Symptôme:** Navigateur affiche "Votre connexion n'est pas privée"

```bash
# Vérifier expiration
openssl x509 -in certbot/conf/live/gaspardanoukolivier.freeboxos.fr/fullchain.pem -noout -dates

# Renouveler manuellement
docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot renew --force-renewal

docker compose -f docker-compose.pi4-standalone.yml exec nginx nginx -s reload
```

### ❌ Avertissement "Auto-signé"

**C'est normal** si vous n'avez pas encore configuré Let's Encrypt.

**Solution:** Suivre la section [Let's Encrypt](#lets-encrypt)

---

## 📚 Ressources Complémentaires

- [Let's Encrypt - Documentation Officielle](https://letsencrypt.org/docs/)
- [Certbot - User Guide](https://eff-certbot.readthedocs.io/en/stable/using.html)
- [SSL Labs - Test de Configuration SSL](https://www.ssllabs.com/ssltest/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)

---

## 🔑 Commandes Utiles

```bash
# Vérifier le certificat actuel
openssl x509 -in certbot/conf/live/${DOMAIN}/fullchain.pem -text -noout

# Tester la config Nginx
docker compose -f docker-compose.pi4-standalone.yml exec nginx nginx -t

# Recharger Nginx (sans downtime)
docker compose -f docker-compose.pi4-standalone.yml exec nginx nginx -s reload

# Redémarrer Nginx
docker compose -f docker-compose.pi4-standalone.yml restart nginx

# Voir les certificats installés
docker run --rm -v $(pwd)/certbot/conf:/etc/letsencrypt certbot/certbot certificates
```

---

## ✅ Checklist de Déploiement Production

- [ ] Domaine DNS configuré et résolvant
- [ ] Port 80 et 443 ouverts sur la box
- [ ] Redirection de port configurée vers Raspberry Pi
- [ ] `setup.sh` exécuté avec succès
- [ ] Certificat Let's Encrypt obtenu (`./scripts/setup_letsencrypt.sh`)
- [ ] HTTPS accessible depuis Internet
- [ ] Renouvellement automatique configuré (cron)
- [ ] Test SSL Labs effectué (note A ou supérieure)

---

**📝 Note:** Ce système a été optimisé pour fonctionner sur Raspberry Pi 4 avec des ressources limitées. Les certificats sont stockés dans `./certbot/conf/` pour faciliter les backups et la portabilité.
