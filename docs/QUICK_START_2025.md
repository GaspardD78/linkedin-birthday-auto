# ⚡ QUICK START GUIDE - LinkedIn Birthday Auto (Jan 2025)
## Installation & Configuration en 10 Minutes

**Version:** 3.3+
**Cible:** Raspberry Pi 4 (4GB RAM minimum)
**OS:** Raspberry Pi OS 64-bit (Lite ou Desktop)

---

## 📋 Prérequis (2 min)

```bash
# Vérifier que vous avez:
- Raspberry Pi 4 4GB+ RAM
- Raspberry Pi OS 64-bit installé
- Connexion Internet stable
- SSH access (ou accès terminal local)
- ~2GB espace disque libre (pour Docker + données)
```

---

## 🚀 Installation (8 min)

### Step 1: Cloner le dépôt

```bash
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto
chmod +x setup.sh
```

**Temps:** ~30 sec

### Step 2: Lancer l'installation

```bash
./setup.sh
```

**Ce que le script fait automatiquement:**
- ✅ Vérifie mémoire/swap
- ✅ Configure Docker
- ✅ Crée volumes et permissions
- ✅ Vous demande les 3 décisions importantes
- ✅ Lance les conteneurs
- ✅ Affiche le rapport sécurité

**Temps:** ~8-10 minutes (dépend vitesse réseau pour Docker pulls)

### Step 3: Trois Décisions Pendant le Setup

#### 📌 **Décision 1: HTTPS (Phase 4.7)**

```
1) LAN uniquement (HTTP simple)
   → Recommandé: Test local / LAN interne

2) Let's Encrypt (production)
   → Recommandé: Accès Internet + domaine valide

3) Certificats existants (import)
   → Si vous avez déjà certificats

4) Configuration manuelle
   → Vous gérez après setup
```

**Choix Recommandé pour Premiers Déploiements:** `2` (Let's Encrypt)

#### 📌 **Décision 2: Sauvegardes Google Drive (Phase 5.1)**

```
1) Oui, avec chiffrement (recommandé)
   → Chiffre les backups avant upload

2) Oui, sans chiffrement
   → Plus rapide mais données en clair

3) Non, plus tard
   → Skip pour maintenant, config manuelle apres
```

**Choix Recommandé pour Production:** `1` (avec chiffrement)

**Note:** Si vous choisissez 1 ou 2, le script vous demandera:
- Configuration interactive rclone (si pas configuré)
- Test backup initial

#### 📌 **Décision 3: Rapport Sécurité (Automatique)**

À la fin du setup, vous voyez un **Rapport Sécurité**:

```
1. Mot de passe Dashboard... ✓ OK
2. HTTPS... ✓ PRODUCTION (Let's Encrypt)
3. Sauvegardes Google Drive... ✓ OK
4. .env secrets... ✓ OK

SCORE SÉCURITÉ : 4 / 4
🎉 EXCELLENT - Production Ready
```

---

## 🌐 Accéder au Dashboard (1 min)

```bash
# À la fin du setup, vous voyez:
╔─────────────────────────────────────┐
│  URL d'accès : https://YOUR_DOMAIN  │
│  URL locale  : http://LOCAL_IP:3000 │
│  Login       : admin                │
│  Mot de passe: <affiché à la fin>   │
└─────────────────────────────────────┘
```

1. Ouvrez votre navigateur
2. Allez à `https://YOUR_DOMAIN` (ou `http://LOCAL_IP:3000` en local)
3. Acceptez le certificat (si auto-signé)
4. Connectez-vous avec login/mot de passe
5. Profitez! 🎉

---

## 📱 Configuration LinkedIn (Post-Setup)

Connecté au dashboard:

1. **Allez à Settings** (⚙️ icon)
2. **Entrez votre login LinkedIn** et mot de passe
3. **Configurez les bots:**
   - Birthday Bot: Messages anniversaires
   - Visitor Bot: Visites profils ciblés
4. **Définissez les horaires** (Cron)
5. **Démarrez les bots**

**First run peut prendre 1-2 min** (téléchargement Chromium)

---

## 🔑 Post-Setup: Commandes Utiles

### Gérer le Mot de Passe Dashboard

```bash
# Changer/réinitialiser mot de passe
./scripts/manage_dashboard_password.sh

# Options:
# 1) Changer le mot de passe
# 2) Réinitialiser (aléatoire temporaire)
# 3) Afficher le statut
```

### Configurer Let's Encrypt

Si vous avez choisi l'option 2 (Let's Encrypt) pendant setup:

```bash
# Une fois setup complété:
./scripts/setup_letsencrypt.sh

# Vous aurez besoin:
# - Domaine DNS pointant vers votre RPi
# - Ports 80/443 accessibles de l'Internet
# - Email pour notifications Let's Encrypt
```

**Certificat est automatiquement renouvellé avant expiration** ✅

### Configurer Google Drive Backup

Si vous avez choisi l'option 3 (Skip) pendant setup:

```bash
# Configuration manuelle rclone:
rclone config

# Puis lancez un backup test:
./scripts/backup_to_gdrive.sh
```

### Voir les Logs

```bash
# Logs temps réel
docker compose -f docker-compose.pi4-standalone.yml logs -f

# Logs d'un service spécifique
docker compose logs -f dashboard
docker compose logs -f api
docker compose logs -f nginx
```

### Redémarrer les Services

```bash
# Redémarrer tous les services
docker compose -f docker-compose.pi4-standalone.yml restart

# Redémarrer un service spécifique
docker compose restart dashboard
```

### Mettre à Jour le Bot

```bash
# Télécharger derniers changements
git pull

# Redémarrer setup (safe, idempotent)
./setup.sh
```

---

## ⚠️ Problèmes Courants

### Le setup prend très longtemps

**Normal!** Premier téléchargement Docker images peut durer 10-15 min.

### "Docker not found"

```bash
# Installer Docker:
curl -fsSL https://get.docker.com | sh

# Vérifier:
docker --version
```

### "Permission denied"

```bash
# Ajouter votre user au groupe docker:
sudo usermod -aG docker $USER
newgrp docker

# Puis relancer setup.sh
./setup.sh
```

### "Insufficient memory"

RPi4 4GB minimum, mais si vous avez < 6GB total (RAM + SWAP):

```bash
# Augmenter SWAP:
# (le script peut le faire interactivement)
./setup.sh

# Ou manuellement:
# Voir docs/TROUBLESHOOTING_2025.md
```

### Mot de passe oublié

```bash
# Réinitialiser et obtenir un temporaire:
./scripts/manage_dashboard_password.sh

# Choisir option 2: Reset Password
# Mot de passe temporaire s'affichera
```

---

## 📚 Docs Complets

Pour plus de détails, voir:

| Document | Pour Quoi? |
|----------|-----------|
| `docs/SETUP_HTTPS_GUIDE.md` | Details config HTTPS |
| `docs/SETUP_BACKUP_GUIDE.md` | Details sauvegardes |
| `docs/PASSWORD_MANAGEMENT_GUIDE.md` | Gestion password |
| `docs/TROUBLESHOOTING_2025.md` | Problèmes & solutions |
| `docs/ARCHITECTURE.md` | Comment ça marche |
| `docs/SECURITY.md` | Sécurité & hardening |

---

## ✅ Checklist Post-Installation

- [ ] Dashboard accessible
- [ ] Connecté avec bon login/mot de passe
- [ ] Compte LinkedIn configuré
- [ ] Birthday Bot activé et testé
- [ ] Google Drive backup configuré (optionnel)
- [ ] Let's Encrypt configuré (optionnel, pour production)
- [ ] Rapport sécurité satisfaisant (score 3-4)

---

## 🎉 C'est Fait!

Votre LinkedIn Birthday Auto Bot est **installé et configuré**! 🚀

**Questions?** Consultez les docs complets ou ouvrez une Issue sur GitHub.

---

**Besoin d'aide?** → [docs/TROUBLESHOOTING_2025.md](TROUBLESHOOTING_2025.md)
