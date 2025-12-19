# 💾 GUIDE SAUVEGARDE GOOGLE DRIVE
## Setup Automatisé Backups vers Google Drive

**Version:** 3.3+
**Date:** Jan 2025
**Type:** Backup SQL + Config + .env
**Fréquence:** Quotidien (02:00 par défaut)
**Rétention:** 30 jours

---

## 📋 Table des Matières

1. [Concepts Backup](#concepts-backup)
2. [Setup Initial (Phase 5.1)](#setup-initial-phase-51)
3. [Configuration Avancée](#configuration-avancée)
4. [Restore & Recovery](#restore--recovery)
5. [Troubleshooting](#troubleshooting)

---

## 🎯 Concepts Backup

### Qu'est-ce qu'on Sauvegarde?

| Item | Contenu | Taille |
|------|---------|--------|
| **linkedin.db** | Base SQLite (messages, logs, etc) | ~50-200MB |
| **config/** | Fichiers configuration | ~1-5MB |
| **.env** | Variables d'environnement | <1MB |

**Total typique:** 50-250MB par backup (dépend activité)

### Rétention Automatique

```bash
# Ancien = supprimé automatiquement
Local:  > 30 jours → DELETE
Google: > 30 jours → DELETE

# Exemple:
# 2025-01-01: Backup créé
# 2025-02-01: Automatiquement supprimé (> 30 jours)
```

### Chiffrement (Optionnel)

**Sans chiffrement:**
- Données Google Drive en clair
- Chiffrement HTTPS pendant transfer
- Plus rapide

**Avec chiffrement (Recommandé):**
- Chiffrement client-side via rclone
- Données Google Drive chiffrées
- Clé de chiffrement localement
- Nécessite GPG

---

## 🚀 Setup Initial (Phase 5.1)

### During setup.sh

```bash
./setup.sh

# À Phase 5.1, vous voyez menu:
╔─────────────────────────────────────────┐
│ Activation des Sauvegardes Google Drive │
├─────────────────────────────────────────┤
│ 1) Oui, activer avec chiffrement        │
│ 2) Oui, activer sans chiffrement        │
│ 3) Non, configurer plus tard            │
├─────────────────────────────────────────┤
│ Votre choix [1-3] :                     │
└─────────────────────────────────────────┘
```

### Option 1: Avec Chiffrement (Recommandé)

```bash
# Choisir: 1
```

**Étapes:**
1. **Installe rclone** (si absent)
2. **Détecte/configure remote Google Drive**
   - Si déjà configuré → détecte automatiquement
   - Si absent → wizard interactif `rclone config`
3. **Ajoute cron quotidien** (02:00)
4. **Test backup initial** (optionnel)

**Configuration rclone (si nouveau):**
```bash
# Le script lance interactivement:
rclone config

# Steps:
# 1. Création nouveau remote
# 2. Type: "drive" (Google Drive)
# 3. OAuth flow (navigateur)
# 4. Authorize "rclone" app dans Google
# 5. Remote créé
```

**Cron Added:**
```bash
# Vérifier:
crontab -l

# Doit voir:
0 2 * * * cd /home/user/linkedin-birthday-auto && \
  ./scripts/backup_to_gdrive.sh >> logs/cron.log 2>&1
```

**Résultat:**
```bash
✓ Sauvegardes Google Drive configurées
  Remote détecté: 'gdrive'
  Cron ajouté (backup quotidien 02:00)

  Backup directories:
    Local: data/backups/
    Google: gdrive:LinkedInBot_Backups

  Chiffrement: ACTIVÉ (rclone crypt)
```

### Option 2: Sans Chiffrement

```bash
# Choisir: 2
```

**Plus simple mais:**
- ❌ Données en clair sur Google Drive
- ⚠️ Pas recommandé pour données sensibles

**Même étapes que Option 1, juste sans GPG**

### Option 3: Plus Tard

```bash
# Choisir: 3
```

**Skip pour maintenant. Configuration manuelle:**
```bash
# Plus tard:
rclone config
./scripts/backup_to_gdrive.sh
```

---

## ⚙️ Configuration Avancée

### Modifier Fréquence Backup

**Par défaut:** 02:00 chaque jour

**Changer:**
```bash
# Éditer crontab:
crontab -e

# Modifier ligne backup:
# Format: minute heure * * *

# Exemples:
0 3 * * *      # 03:00 chaque jour
30 1 * * *     # 01:30 chaque jour
0 2 * * 0      # 02:00 le dimanche
*/6 * * * *    # Chaque 6 heures
```

**Vérifier:**
```bash
crontab -l | grep backup_to_gdrive
```

### Modifier Rétention Backups

**Par défaut:** 30 jours

**Changer:**
```bash
# Éditer script:
nano scripts/backup_to_gdrive.sh

# Trouver ligne:
RETENTION_DAYS=30

# Changer à (ex 60 jours):
RETENTION_DAYS=60
```

### Notifications Slack (Optionnel)

**Setup:**
1. Créer Webhook Slack
2. Ajouter variable d'environnement
3. Backup enverra notifications automatiquement

**Étape 1: Créer Webhook**

```bash
# Dans Slack workspace:
# 1. Settings → Manage apps
# 2. Search "Incoming Webhooks"
# 3. Create New → Select channel
# 4. Copy Webhook URL
```

**Étape 2: Ajouter au .env**

```bash
# Éditer .env:
nano .env

# Ajouter:
SLACK_WEBHOOK=https://hooks.slack.com/services/T00000000/B00000000/...
```

**Étape 3: Test**

```bash
# Exécuter backup test:
./scripts/backup_to_gdrive.sh

# Vérifier message Slack ✓
```

**Message Exemple:**
```
✅ Backup LinkedIn Bot terminé avec succès
├─ Archive: backup_20250119_020015.tar.gz (125MB)
├─ Remote: gdrive:LinkedInBot_Backups
├─ Timestamp: 2025-01-19 02:00:15
└─ Rétention: 30 jours
```

---

## 🔄 Restore & Recovery

### Backup Test Automatique (Mensuel)

```bash
# Automatiquement le 1er du mois:
# - Télécharge latest backup depuis Google Drive
# - Valide intégrité (tar validation)
# - Logs résultat dans logs/backup_gdrive.log
```

**Vérifier logs:**
```bash
grep "Test restore" logs/backup_gdrive.log
```

### Restore Manuel

**Scenario:** Vous devez restaurer data

```bash
# 1. Lister backups disponibles:
rclone ls gdrive:LinkedInBot_Backups

# Output:
#  128507520 2025-01-19_020015_backup.tar.gz
#  125984620 2025-01-18_020015_backup.tar.gz
#  ...

# 2. Télécharger backup voulu:
rclone copy gdrive:LinkedInBot_Backups/2025-01-19_020015_backup.tar.gz /tmp/

# 3. Extraire:
cd /tmp
tar -xzf 2025-01-19_020015_backup.tar.gz

# Output:
# ./data/linkedin.db
# ./config/
# ./.env

# 4. Restaurer fichiers:
cp data/linkedin.db YOUR_PROJECT/data/
cp -r config/* YOUR_PROJECT/config/
cp .env YOUR_PROJECT/

# 5. Redémarrer services:
docker compose restart
```

### Validate Restore

```bash
# Vérifier DB OK:
sqlite3 data/linkedin.db ".tables"

# Doit voir tables (birthdays, logs, etc)

# Vérifier config:
ls -la config/

# Doit voir fichiers configuration
```

---

## 🐛 Troubleshooting

### ❌ "rclone n'est pas installé"

```bash
# Installer:
sudo apt-get update
sudo apt-get install -y rclone

# Vérifier:
rclone version
```

### ❌ "Aucun remote rclone configuré"

**Cause:** rclone pas configuré pour Google Drive

```bash
# Configuration interactive:
rclone config

# Steps (copy-paste les commandes):
# 1. New remote
# 2. Name: gdrive (ou votre choix)
# 3. Type: drive
# 4. OAuth → Browser opens → Authorize → Copy code
# 5. Remote créé
```

### ❌ "Backup script échoue"

**Checker logs:**
```bash
# Logs backup:
cat logs/backup_gdrive.log

# Rechercher ERROR:
grep ERROR logs/backup_gdrive.log

# Logs cron:
grep backup_to_gdrive /var/log/syslog 2>/dev/null
```

**Problèmes courants:**

1. **Network failure**
   ```bash
   # Tester Internet:
   ping 8.8.8.8

   # Tester Google Drive:
   rclone ls gdrive:
   ```

2. **Permission denied**
   ```bash
   # Vérifier data/ permissions:
   ls -la data/

   # Doit être: user:user (pas root)
   ```

3. **Space insufficient**
   ```bash
   # Vérifier espace:
   df -h

   # Doit avoir >2GB libre
   ```

### ❌ "Slack notifications échouent"

```bash
# Vérifier webhook valid:
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test"}' \
  $SLACK_WEBHOOK

# Doit retourner OK
```

### ❌ "Restore échoue: archive corrompue"

```bash
# Valider archive:
tar -tzf backup_file.tar.gz > /dev/null

# Si erreur → archive corrompue
# Solution: Télécharger plus ancien backup
```

---

## 📊 Monitoring Backups

### Voir logs temps réel

```bash
# Voir tous backups logs:
tail -f logs/backup_gdrive.log

# Ou mensuel lors du test restore:
grep "$(date +%d)" logs/backup_gdrive.log
```

### Cron job status

```bash
# Voir quand cron a run:
grep "backup_to_gdrive" /var/log/syslog | tail -20

# Ou check dernière exécution:
stat logs/backup_gdrive.log
```

### List backups

```bash
# Local:
ls -lh data/backups/

# Google Drive:
rclone ls gdrive:LinkedInBot_Backups
```

---

## ✅ Checklist Backup

- [ ] Rclone installé (`rclone version`)
- [ ] Remote Google Drive configuré (`rclone listremotes`)
- [ ] Cron job setup (`crontab -l`)
- [ ] Premier backup réussi
- [ ] Vérifier logs (`tail logs/backup_gdrive.log`)
- [ ] (Optionnel) Slack notifications testées
- [ ] (Optionnel) Monthly restore test validée

---

## 🎯 Recommandations

1. **Utilisez chiffrement** (Option 1 pendant setup)
2. **Vérifiez logs régulièrement** pour détecter problèmes
3. **Testez restore** au moins une fois (validate DR)
4. **Augmentez rétention** si données critiques (ex 60-90 jours)
5. **Configurez Slack** pour notifications success/failure

---

**Besoin d'aide?** Consultez [docs/TROUBLESHOOTING_2025.md](TROUBLESHOOTING_2025.md)
