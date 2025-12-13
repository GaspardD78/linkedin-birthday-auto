# 💾 Guide de Configuration du Backup Automatisé

## 📋 Vue d'ensemble

Le script `backup_database.sh` effectue un backup sécurisé de la base SQLite vers la clé USB externe et maintient une rotation automatique des backups (7 jours par défaut).

### ✨ Fonctionnalités

- ✅ **Backup sécurisé** : Utilise SQLite `.backup` (garantit cohérence)
- ✅ **Vérification d'intégrité** : `PRAGMA integrity_check` + SHA256 checksum
- ✅ **Compression automatique** : Économise ~70% d'espace (gzip)
- ✅ **Rotation intelligente** : Garde les 7 derniers backups
- ✅ **Protection carte SD** : Sauvegarde vers USB externe
- ✅ **Logs détaillés** : Suivi complet de l'opération

---

## 🚀 Installation

### 1. Vérifier que la clé USB est montée

```bash
df -h /mnt/linkedin-data
```

Si elle n'est pas montée, exécuter le script de configuration :

```bash
cd /home/user/linkedin-birthday-auto/scripts
./setup_usb_storage.sh
```

### 2. Tester le script manuellement

```bash
cd /home/user/linkedin-birthday-auto/scripts
./backup_database.sh
```

Sortie attendue :
```
✅ Backup terminé avec succès
📁 Fichier de backup : linkedin_backup_20231204_150530.db.gz
📊 Taille           : 245K (source: 890K)
🗂️  Backups stockés  : 3 (max: 7 jours)
```

### 3. Configurer le Cron (Backup quotidien)

#### Option A : Avec l'utilisateur (recommandé)

```bash
crontab -e
```

Ajouter cette ligne (backup daily à 3h du matin) :
```cron
0 3 * * * /home/user/linkedin-birthday-auto/scripts/backup_database.sh >> /var/log/linkedin-backup.log 2>&1
```

#### Option B : Avec systemd timer (avancé)

Créer le service :
```bash
sudo nano /etc/systemd/system/linkedin-backup.service
```

```ini
[Unit]
Description=LinkedIn Bot Database Backup
After=network.target

[Service]
Type=oneshot
User=user
ExecStart=/home/user/linkedin-birthday-auto/scripts/backup_database.sh
StandardOutput=append:/var/log/linkedin-backup.log
StandardError=append:/var/log/linkedin-backup.log
```

Créer le timer :
```bash
sudo nano /etc/systemd/system/linkedin-backup.timer
```

```ini
[Unit]
Description=LinkedIn Bot Daily Backup Timer
Requires=linkedin-backup.service

[Timer]
OnCalendar=daily
OnCalendar=03:00
Persistent=true

[Install]
WantedBy=timers.target
```

Activer et démarrer :
```bash
sudo systemctl daemon-reload
sudo systemctl enable linkedin-backup.timer
sudo systemctl start linkedin-backup.timer
```

Vérifier le statut :
```bash
sudo systemctl status linkedin-backup.timer
```

---

## 📊 Surveillance

### Vérifier les logs du backup

```bash
tail -f /var/log/linkedin-backup.log
```

### Lister les backups disponibles

```bash
ls -lht /mnt/linkedin-data/backups/
```

### Espace disque restant

```bash
df -h /mnt/linkedin-data
```

### Tester un backup maintenant

```bash
./scripts/backup_database.sh
```

---

## 🔄 Restauration d'un Backup

### 1. Lister les backups disponibles

```bash
ls -lht /mnt/linkedin-data/backups/
```

### 2. Arrêter les services Docker

```bash
cd /home/user/linkedin-birthday-auto
docker compose -f docker-compose.pi4-standalone.yml down
```

### 3. Restaurer le backup

```bash
# Si compressé (.gz)
gunzip -c /mnt/linkedin-data/backups/linkedin_backup_20231204_150530.db.gz > /app/data/linkedin.db

# Si non compressé
cp /mnt/linkedin-data/backups/linkedin_backup_20231204_150530.db /app/data/linkedin.db
```

### 4. Vérifier l'intégrité

```bash
sqlite3 /app/data/linkedin.db "PRAGMA integrity_check;"
# Doit retourner: ok
```

### 5. Redémarrer les services

```bash
docker compose -f docker-compose.pi4-standalone.yml up -d
```

---

## ⚙️ Configuration Avancée

### Modifier la rétention des backups

Éditer `backup_database.sh` :
```bash
nano scripts/backup_database.sh
```

Modifier la ligne :
```bash
RETENTION_DAYS=7  # Changer à 14, 30, etc.
```

### Changer la fréquence du backup

Exemples de cron :
```cron
# Toutes les 12 heures
0 */12 * * * /path/to/backup_database.sh

# Tous les dimanches à minuit
0 0 * * 0 /path/to/backup_database.sh

# Tous les jours à 2h et 14h
0 2,14 * * * /path/to/backup_database.sh
```

### Recevoir des notifications par email

Installer mailutils :
```bash
sudo apt-get install mailutils
```

Modifier le cron pour envoyer les logs par email :
```cron
0 3 * * * /home/user/linkedin-birthday-auto/scripts/backup_database.sh 2>&1 | mail -s "LinkedIn Bot Backup Report" your-email@example.com
```

---

## 🚨 Dépannage

### Erreur: "Base de données source introuvable"

Vérifier le chemin de la base :
```bash
ls -la /app/data/linkedin.db
```

Si le volume Docker n'est pas monté, vérifier docker-compose.yml.

### Erreur: "Répertoire de backup inexistant"

Monter la clé USB :
```bash
sudo mount /dev/sda1 /mnt/linkedin-data
```

### Erreur: "sqlite3 n'est pas installé"

Installer sqlite3 :
```bash
sudo apt-get update
sudo apt-get install sqlite3
```

### Backup sur carte SD au lieu d'USB

Le script affichera un warning. Pour forcer :
```bash
./backup_database.sh --force
```

**Attention** : Cela usera prématurément la carte SD !

---

## 📈 Statistiques de Performance

Sur Raspberry Pi 4 avec clé USB 3.0 :
- **Durée de backup** : ~5-10 secondes (DB de 1MB)
- **Ratio de compression** : ~70% (gzip)
- **Espace requis** : ~300KB par backup (DB de 1MB)
- **Impact CPU** : Minimal (~2-5% pendant 10s)

---

## 🔒 Sécurité

### Permissions recommandées

```bash
chmod 700 /mnt/linkedin-data/backups
chown user:user /mnt/linkedin-data/backups
```

### Chiffrement des backups (optionnel)

Pour chiffrer les backups :
```bash
# Après le backup
gpg --symmetric --cipher-algo AES256 /mnt/linkedin-data/backups/linkedin_backup_*.db.gz

# Pour déchiffrer
gpg --decrypt backup.db.gz.gpg > backup.db.gz
```

---

## 📚 Ressources

- [SQLite Backup API](https://www.sqlite.org/backup.html)
- [Cron Syntax Checker](https://crontab.guru/)
- [Systemd Timers Tutorial](https://wiki.archlinux.org/title/Systemd/Timers)

---

**Mis à jour** : 2025-12-04
**Auteur** : LinkedIn Birthday Auto Bot Team
