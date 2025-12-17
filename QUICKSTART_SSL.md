# 🚀 Quick Start - Déploiement HTTPS Automatisé

Ce guide vous permet de déployer l'application avec HTTPS en **moins de 5 minutes**.

## 📋 Prérequis

- Raspberry Pi 4 avec Raspberry Pi OS
- Docker et Docker Compose installés
- Accès sudo
- 4GB RAM + 2GB SWAP minimum

## 🎯 Déploiement en 3 Commandes

### Étape 1: Clone et Configuration

```bash
# Cloner le repository (si pas déjà fait)
cd ~/
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto

# Checkout de la branche avec SSL automatisé
git checkout claude/fix-rpi-service-startup-eyfP7
git pull origin claude/fix-rpi-service-startup-eyfP7
```

### Étape 2: Lancement Automatique

```bash
# Lance le setup complet (génération SSL + config Nginx + démarrage services)
./setup.sh
```

**Ce que fait automatiquement setup.sh:**
- ✅ Génère des certificats SSL auto-signés
- ✅ Configure Nginx avec votre domaine (gaspardanoukolivier.freeboxos.fr)
- ✅ Active HTTPS immédiatement
- ✅ Démarre tous les services Docker
- ✅ Vérifie la santé des services

**Durée:** 5-10 minutes (selon connexion Internet)

### Étape 3: Vérification

```bash
# Vérifier que tous les conteneurs sont "Up"
docker compose -f docker-compose.pi4-standalone.yml ps

# Accéder au dashboard
# Option 1: HTTP local (toujours disponible)
#   http://192.168.1.XX:3000

# Option 2: HTTPS avec domaine (certificat auto-signé)
#   https://gaspardanoukolivier.freeboxos.fr
#   ⚠️ Accepter l'avertissement de sécurité du navigateur
```

---

## 🔒 Upgrade vers Let's Encrypt (Production)

Pour un certificat SSL **approuvé par les navigateurs** (sans avertissement):

### Prérequis

1. **DNS configuré**
   - `gaspardanoukolivier.freeboxos.fr` doit pointer vers votre IP publique
   - Vérifier: `host gaspardanoukolivier.freeboxos.fr`

2. **Port 80 ouvert**
   - Ouvrir le port 80 sur votre Freebox
   - Rediriger vers l'IP du Raspberry Pi

### Commande

```bash
./scripts/setup_letsencrypt.sh
```

**Résultat:** Certificat Let's Encrypt obtenu en moins de 2 minutes, sans interruption de service.

---

## 🧪 Test Mode (Staging)

Pour tester sans limites de taux Let's Encrypt:

```bash
./scripts/setup_letsencrypt.sh --staging
```

---

## 📊 État des Services

### Vérification Rapide

```bash
# État des conteneurs
docker compose -f docker-compose.pi4-standalone.yml ps

# Logs en temps réel
docker compose -f docker-compose.pi4-standalone.yml logs -f

# Vérifier le certificat SSL
openssl x509 -in certbot/conf/live/gaspardanoukolivier.freeboxos.fr/fullchain.pem -text -noout | grep "Issuer\|Not After"
```

### Accès Services

| Service | URL | Identifiants |
|---------|-----|--------------|
| **Dashboard** | https://gaspardanoukolivier.freeboxos.fr | Configurés dans .env |
| **API** | http://IP_LOCAL:8000/docs | - |
| **Grafana** | http://IP_LOCAL:3001 | admin/admin |

---

## 🔧 Dépannage Express

### Nginx ne démarre pas

```bash
# Voir les logs
docker compose -f docker-compose.pi4-standalone.yml logs nginx

# Régénérer les certificats
rm -rf certbot/conf/live/gaspardanoukolivier.freeboxos.fr/
./setup.sh
```

### Certificat auto-signé non accepté

**C'est normal !** Les certificats auto-signés génèrent un avertissement.

**Solutions:**
1. **Développement:** Accepter l'avertissement (cliquer "Avancé" → "Continuer")
2. **Production:** Utiliser Let's Encrypt (`./scripts/setup_letsencrypt.sh`)

### Let's Encrypt échoue

```bash
# Vérifier DNS
host gaspardanoukolivier.freeboxos.fr

# Vérifier port 80 depuis Internet
curl -I http://gaspardanoukolivier.freeboxos.fr/.well-known/acme-challenge/test

# Mode debug
docker compose -f docker-compose.pi4-standalone.yml logs nginx | grep "acme"
```

---

## 📚 Documentation Complète

- **Configuration SSL:** [docs/SSL_SETUP.md](docs/SSL_SETUP.md)
- **Installation Raspberry Pi:** [docs/RASPBERRY_PI_DOCKER_SETUP.md](docs/RASPBERRY_PI_DOCKER_SETUP.md)
- **Dépannage:** [docs/RASPBERRY_PI_TROUBLESHOOTING.md](docs/RASPBERRY_PI_TROUBLESHOOTING.md)

---

## 🎓 Commandes Utiles

```bash
# Redémarrer tous les services
docker compose -f docker-compose.pi4-standalone.yml restart

# Arrêter proprement
docker compose -f docker-compose.pi4-standalone.yml down

# Mise à jour du code
git pull && ./setup.sh

# Renouveler Let's Encrypt manuellement
./scripts/setup_letsencrypt.sh

# Voir la config Nginx générée
cat deployment/nginx/linkedin-bot.conf

# Test config Nginx
docker compose -f docker-compose.pi4-standalone.yml exec nginx nginx -t
```

---

## ✅ Checklist Post-Installation

- [ ] `./setup.sh` exécuté sans erreur
- [ ] Tous les conteneurs "Up" (`docker compose ps`)
- [ ] Dashboard accessible en HTTP local
- [ ] HTTPS actif (même avec avertissement)
- [ ] Logs sans erreurs critiques

### Pour Production (Optionnel)

- [ ] DNS configuré
- [ ] Port 80 ouvert
- [ ] Let's Encrypt obtenu (`./scripts/setup_letsencrypt.sh`)
- [ ] Certificat valide (pas d'avertissement navigateur)
- [ ] Renouvellement automatique configuré (cron)

---

## 🚨 Support

**Problème non résolu ?**

1. Vérifier [docs/SSL_SETUP.md](docs/SSL_SETUP.md) section "Dépannage"
2. Consulter les logs: `docker compose logs --tail=100`
3. Créer une issue GitHub avec les logs

---

**🎉 Félicitations ! Votre application LinkedIn Birthday Auto est maintenant sécurisée avec HTTPS.**
