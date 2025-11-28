# 🚀 Guide Rapide d'Installation - LinkedIn Birthday Bot v2.0

**Installation simplifiée tout-en-un en 3 commandes** 🎯

---

## ⚡ Installation Rapide (Méthode Recommandée)

### 1. Cloner le projet

```bash
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto
```

### 2. Lancer l'installation interactive

```bash
./setup.sh
```

### 3. C'est tout ! ✅

Le script `setup.sh` vous guide automatiquement à travers :
- ✅ Détection de votre plateforme (Raspberry Pi 4, Linux, macOS)
- ✅ Installation des prérequis (Docker, Docker Compose)
- ✅ Configuration de l'authentification LinkedIn
- ✅ Configuration du fichier `.env`
- ✅ Déploiement des services Docker
- ✅ Configuration de l'automatisation (sur Raspberry Pi uniquement)

**Durée estimée :** 20-30 minutes (dont 15-20 min de compilation)

---

## 📋 Prérequis

### Configuration minimale

| Composant | Minimum | Recommandé |
|-----------|---------|------------|
| **RAM** | 2 GB | 4 GB (Raspberry Pi 4) |
| **Disque** | 10 GB | 20 GB |
| **SWAP** | 2 GB | 2 GB (configuré automatiquement) |
| **Plateforme** | Linux 64-bit | Raspberry Pi OS 64-bit |

### Compte LinkedIn

- Compte LinkedIn actif
- **Recommandé :** 2FA activé (plus sécurisé)
- Extension navigateur "Cookie-Editor" ou "EditThisCookie"

---

## 🎯 Options d'Installation

### Installation complète (interactive)

```bash
./setup.sh
```

Le script vous pose des questions et vous guide pas à pas.

### Installation rapide (non-interactive)

```bash
./setup.sh --quick
```

Saute les vérifications détaillées (gain de temps).

### Configuration uniquement

```bash
./setup.sh --config-only
```

Configure `.env` et `auth_state.json` sans installer les services (utile pour reconfigurer).

---

## 🔑 Configuration de l'Authentification LinkedIn

Le script vous guidera, mais voici le processus complet :

### Étape 1 : Installer l'extension

- **Chrome/Edge :** [Cookie-Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
- **Firefox :** [Cookie-Editor](https://addons.mozilla.org/fr/firefox/addon/cookie-editor/)

### Étape 2 : Exporter les cookies

1. Ouvrez https://www.linkedin.com et **connectez-vous**
2. Cliquez sur l'icône de l'extension Cookie-Editor
3. Cliquez sur **"Export"** → **"JSON"**
4. Sauvegardez le fichier en tant que `auth_state.json`

### Étape 3 : Placer le fichier

Copiez `auth_state.json` à la racine du projet :

```bash
cp ~/Downloads/auth_state.json ~/linkedin-birthday-auto/auth_state.json
```

**Le script `setup.sh` vous guidera à travers ces étapes de manière interactive !**

---

## 🐳 Déploiement Docker (Raspberry Pi 4)

### Architecture optimisée

Le projet utilise une architecture Docker optimisée pour Raspberry Pi 4 (4GB RAM) :

```
┌─────────────────────────────────────┐
│        Raspberry Pi 4 (4GB)         │
│                                     │
│  ┌───────────────────────────────┐ │
│  │  Docker Compose Stack         │ │
│  │                               │ │
│  │  • Bot Worker (900MB max)    │ │
│  │  • Dashboard (400MB max)     │ │
│  │  • API (300MB max)           │ │
│  │  • Redis Bot (50MB)          │ │
│  │  • Redis Dashboard (50MB)    │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │  Systemd Services (Auto)      │ │
│  │                               │ │
│  │  • Auto-start au boot         │ │
│  │  • Monitoring horaire         │ │
│  │  • Backup quotidien (3h AM)   │ │
│  │  • Nettoyage hebdomadaire     │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Optimisations appliquées :**
- Limites mémoire strictes par service
- SWAP configuré automatiquement (2GB)
- Compilation Next.js optimisée
- Build multi-étapes pour réduire la taille des images

---

## 🛠️ Commandes Utiles

### Gestion des services

```bash
# Voir les logs en temps réel
docker compose -f docker-compose.pi4-standalone.yml logs -f

# Redémarrer tous les services
docker compose -f docker-compose.pi4-standalone.yml restart

# Redémarrer un service spécifique
docker compose -f docker-compose.pi4-standalone.yml restart bot-worker

# Arrêter tous les services
docker compose -f docker-compose.pi4-standalone.yml down

# Démarrer tous les services
docker compose -f docker-compose.pi4-standalone.yml up -d

# Voir l'état des services
docker compose -f docker-compose.pi4-standalone.yml ps
```

### Vérification de l'installation

```bash
# Vérifier l'état complet du système
./scripts/verify_rpi_docker.sh

# Dashboard de monitoring en temps réel
./scripts/dashboard_monitoring.sh
```

### Maintenance (Raspberry Pi uniquement)

```bash
# Statut du service systemd
sudo systemctl status linkedin-bot

# Logs du service
sudo journalctl -u linkedin-bot -f

# Redémarrer le service
sudo systemctl restart linkedin-bot

# Voir les timers (monitoring, backup, cleanup)
sudo systemctl list-timers linkedin-bot*

# Backup manuel de la base de données
sudo systemctl start linkedin-bot-backup.service

# Nettoyage manuel
sudo ./scripts/cleanup_pi4.sh
```

---

## 🔧 Configuration Avancée

### Modifier le fichier `.env`

```bash
nano .env
```

**Paramètres principaux :**

```bash
# Mode test (ne pas envoyer de vrais messages)
LINKEDIN_BOT_DRY_RUN=true  # Mettre à 'false' pour la production

# Mode du bot
LINKEDIN_BOT_MODE=standard  # 'standard' ou 'unlimited'

# Navigateur invisible
LINKEDIN_BOT_BROWSER_HEADLESS=true

# Limite hebdomadaire de messages (recommandé: 80)
LINKEDIN_BOT_MESSAGING_LIMITS_WEEKLY_MESSAGE_LIMIT=80
```

### Modifier la configuration YAML

Pour des options avancées :

```bash
nano config/config.yaml
```

Consultez [README.md](README.md#configuration-avancée) pour la liste complète des options.

---

## 📊 Accès au Dashboard

Après l'installation, le dashboard est accessible à :

```
http://<IP_DU_RASPBERRY_PI>:3000
```

**Exemple :** `http://192.168.1.145:3000`

**Fonctionnalités du dashboard :**
- 📈 Statistiques en temps réel
- 🎯 Liste des anniversaires
- 📝 Historique des messages
- ⚙️ Gestion des jobs
- 🛠️ Maintenance et déploiement
- 📊 Monitoring des ressources

---

## 🔄 Mise à Jour

Pour mettre à jour le bot avec les dernières modifications :

```bash
cd ~/linkedin-birthday-auto
git pull
./scripts/easy_deploy.sh
```

**Le script `easy_deploy.sh` :**
1. Vérifie l'état actuel
2. Propose un nettoyage si nécessaire
3. Rebuild les images Docker
4. Redémarre les services
5. Vérifie que tout fonctionne

---

## 🆘 Dépannage Rapide

### Le bot ne démarre pas

```bash
# Vérifier les logs
docker compose -f docker-compose.pi4-standalone.yml logs bot-worker

# Vérifier l'authentification
docker compose -f docker-compose.pi4-standalone.yml exec bot-worker python main.py validate

# Redémarrer
docker compose -f docker-compose.pi4-standalone.yml restart
```

### Le dashboard affiche une erreur 500

**C'est normal au premier démarrage !** Next.js compile lors du premier lancement.

**Solution :** Attendez 1-2 minutes et rafraîchissez la page.

```bash
# Vérifier les logs du dashboard
docker compose -f docker-compose.pi4-standalone.yml logs dashboard
```

### Problèmes de mémoire sur Raspberry Pi

```bash
# Vérifier l'utilisation mémoire
free -h

# Vérifier le SWAP
swapon --show

# Configurer le SWAP (si pas fait automatiquement)
sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile swapoff
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Erreur "Permission denied" avec Docker

**Vous n'êtes pas dans le groupe docker.**

```bash
# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER

# Redémarrer pour appliquer
sudo reboot
```

### Le service systemd ne démarre pas au boot

```bash
# Vérifier le statut
sudo systemctl status linkedin-bot

# Activer le service
sudo systemctl enable linkedin-bot

# Démarrer le service
sudo systemctl start linkedin-bot

# Voir les erreurs
sudo journalctl -u linkedin-bot -n 50
```

---

## 📚 Documentation Complète

Pour aller plus loin, consultez :

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Guide complet avec toutes les fonctionnalités |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architecture détaillée du projet |
| [docs/RPI_QUICKSTART.md](docs/RPI_QUICKSTART.md) | Guide spécifique Raspberry Pi 4 |
| [docs/DEPLOYMENT_AUTOMATION.md](docs/DEPLOYMENT_AUTOMATION.md) | Détails sur l'automatisation |
| [docs/RASPBERRY_PI_TROUBLESHOOTING.md](docs/RASPBERRY_PI_TROUBLESHOOTING.md) | Guide de dépannage complet |
| [AUTOMATION_DEPLOYMENT_PI4.md](AUTOMATION_DEPLOYMENT_PI4.md) | Documentation technique de l'automatisation |

---

## 🎯 Cas d'Usage Fréquents

### Mode DRY RUN (test sans envoyer)

Parfait pour tester sans risque :

```bash
# Modifier .env
sed -i 's/^LINKEDIN_BOT_DRY_RUN=.*/LINKEDIN_BOT_DRY_RUN=true/' .env

# Redémarrer
docker compose -f docker-compose.pi4-standalone.yml restart bot-worker
```

### Mode UNLIMITED (rattraper le retard)

Pour envoyer des messages en retard :

```bash
# Modifier .env
sed -i 's/^LINKEDIN_BOT_MODE=.*/LINKEDIN_BOT_MODE=unlimited/' .env

# Redémarrer
docker compose -f docker-compose.pi4-standalone.yml restart bot-worker
```

### Déclencher un job manuel

Via le dashboard (http://IP:3000) :
1. Aller dans "Contrôle des Scripts"
2. Choisir le mode (Birthday ou Visitor)
3. Cliquer sur "Démarrer le Job"

Ou via l'API :

```bash
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "bot_mode": "standard",
    "dry_run": false
  }'
```

---

## ⚠️ Bonnes Pratiques

### Limites recommandées

Pour éviter la détection LinkedIn :

| Paramètre | Recommandation | Raison |
|-----------|----------------|---------|
| **Messages/semaine** | 80 maximum | Limite non documentée de LinkedIn (~100/semaine) |
| **Messages/jour** | 15-20 maximum | Éviter les pics suspects |
| **Délai entre messages** | 3-5 minutes | Comportement humain |
| **Horaires** | 7h-19h | Heures ouvrables |

### Sécurité

- ✅ Ne **JAMAIS** committer `auth_state.json` ou `.env`
- ✅ Activer 2FA sur LinkedIn
- ✅ Régulièrement vérifier les logs
- ✅ Limiter l'accès au dashboard (firewall, VPN)
- ✅ Changer les clés API par défaut

### Maintenance

- 📅 Vérifier les logs hebdomadairement
- 📅 Backups automatiques quotidiens (sur Pi4)
- 📅 Nettoyage automatique hebdomadaire (sur Pi4)
- 📅 Mettre à jour le bot mensuellement (`git pull`)

---

## 🎉 Résumé

**Installation en 3 commandes :**

```bash
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto
./setup.sh
```

**Vérification que tout fonctionne :**

```bash
./scripts/verify_rpi_docker.sh
```

**Accès au dashboard :**

```
http://<IP_DU_RASPBERRY_PI>:3000
```

**Commandes essentielles :**

```bash
# Voir les logs
docker compose -f docker-compose.pi4-standalone.yml logs -f

# Redémarrer
docker compose -f docker-compose.pi4-standalone.yml restart

# Mettre à jour
git pull && ./scripts/easy_deploy.sh
```

---

**Bon usage du bot ! 🎂**

*Pour toute question, consultez la [documentation complète](README.md) ou ouvrez une [issue GitHub](https://github.com/GaspardD78/linkedin-birthday-auto/issues).*
