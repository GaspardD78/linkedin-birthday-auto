# 🚀 Déploiement - LinkedIn Birthday Auto Bot

Ce répertoire contient les fichiers de configuration pour le déploiement automatisé du LinkedIn Birthday Bot.

## 📁 Structure

```
deployment/
└── systemd/                          # Services systemd pour Raspberry Pi
    ├── linkedin-bot.service          # Service principal (auto-start)
    ├── linkedin-bot-monitor.service  # Service de monitoring
    ├── linkedin-bot-monitor.timer    # Timer monitoring (horaire)
    ├── linkedin-bot-backup.service   # Service de backup
    └── linkedin-bot-backup.timer     # Timer backup (quotidien)
```

## 🎯 Utilisation

### Installation Automatique (Recommandé)

Utilisez le script d'installation automatique qui configure tout:

```bash
sudo ./scripts/install_automation_pi4.sh
```

### Installation Manuelle

Si vous préférez installer manuellement:

```bash
# 1. Copier les fichiers systemd
sudo cp deployment/systemd/*.service /etc/systemd/system/
sudo cp deployment/systemd/*.timer /etc/systemd/system/

# 2. Adapter les chemins dans les fichiers
sudo sed -i 's|/home/pi/linkedin-birthday-auto|/votre/chemin|g' /etc/systemd/system/linkedin-bot*.service

# 3. Recharger systemd
sudo systemctl daemon-reload

# 4. Activer les services
sudo systemctl enable linkedin-bot.service
sudo systemctl enable linkedin-bot-monitor.timer
sudo systemctl enable linkedin-bot-backup.timer

# 5. Démarrer
sudo systemctl start linkedin-bot
sudo systemctl start linkedin-bot-monitor.timer
sudo systemctl start linkedin-bot-backup.timer
```

## 📋 Services Détaillés

### linkedin-bot.service

**Rôle:** Démarre automatiquement Docker Compose au boot du Raspberry Pi

**Fichier:** `systemd/linkedin-bot.service`

**Commandes:**
- Démarrer: `sudo systemctl start linkedin-bot`
- Arrêter: `sudo systemctl stop linkedin-bot`
- Statut: `sudo systemctl status linkedin-bot`
- Logs: `sudo journalctl -u linkedin-bot -f`

### linkedin-bot-monitor.timer

**Rôle:** Monitoring automatique des ressources toutes les heures

**Fichiers:**
- `systemd/linkedin-bot-monitor.service`
- `systemd/linkedin-bot-monitor.timer`

**Métriques:**
- CPU usage et température
- RAM et SWAP
- Espace disque
- État des containers

**Logs:** `/var/log/linkedin-bot-health.log`

**Commandes:**
- Statut: `sudo systemctl status linkedin-bot-monitor.timer`
- Voir logs: `tail -f /var/log/linkedin-bot-health.log`
- Test manuel: `sudo systemctl start linkedin-bot-monitor.service`

### linkedin-bot-backup.timer

**Rôle:** Backup automatique quotidien de la base de données (3h du matin)

**Fichiers:**
- `systemd/linkedin-bot-backup.service`
- `systemd/linkedin-bot-backup.timer`

**Fonctionnalités:**
- Backup compressé (gzip)
- Rotation automatique (30 derniers)
- Logs détaillés

**Logs:** `/var/log/linkedin-bot-backup.log`

**Commandes:**
- Statut: `sudo systemctl status linkedin-bot-backup.timer`
- Backup manuel: `sudo systemctl start linkedin-bot-backup.service`
- Voir backups: `ls -lh ~/linkedin-birthday-auto/backups/`

## 🔧 Configuration

### Modifier les Chemins

Les services utilisent par défaut `/home/pi/linkedin-birthday-auto`. Pour changer:

```bash
# Option 1: Via variable d'environnement lors de l'installation
export PROJECT_DIR=/votre/chemin
sudo ./scripts/install_automation_pi4.sh

# Option 2: Éditer manuellement
sudo nano /etc/systemd/system/linkedin-bot.service
# Modifier WorkingDirectory=...
sudo systemctl daemon-reload
```

### Modifier la Fréquence de Monitoring

```bash
# Éditer le timer
sudo nano /etc/systemd/system/linkedin-bot-monitor.timer

# Exemples de fréquences:
# OnUnitActiveSec=30min  # Toutes les 30 minutes
# OnUnitActiveSec=2h     # Toutes les 2 heures
# OnUnitActiveSec=1h     # Toutes les heures (défaut)

# Recharger
sudo systemctl daemon-reload
sudo systemctl restart linkedin-bot-monitor.timer
```

### Modifier l'Heure de Backup

```bash
# Éditer le timer
sudo nano /etc/systemd/system/linkedin-bot-backup.timer

# Exemples:
# OnCalendar=*-*-* 03:00:00  # 3h du matin (défaut)
# OnCalendar=*-*-* 01:00:00  # 1h du matin
# OnCalendar=*-*-* 00,12:00:00  # Minuit et midi

# Recharger
sudo systemctl daemon-reload
sudo systemctl restart linkedin-bot-backup.timer
```

## 📊 Monitoring

### Vérifier les Timers

```bash
# Lister tous les timers
sudo systemctl list-timers

# Timers LinkedIn Bot seulement
sudo systemctl list-timers linkedin-bot*

# Affichage:
# NEXT                         LEFT          LAST                         PASSED       UNIT
# Thu 2024-11-28 15:00:00 CET  30min left    Thu 2024-11-28 14:00:00 CET  30min ago    linkedin-bot-monitor.timer
# Fri 2024-11-29 03:00:00 CET  12h left      Thu 2024-11-28 03:00:00 CET  11h ago      linkedin-bot-backup.timer
```

### Vérifier les Logs

```bash
# Logs service principal
sudo journalctl -u linkedin-bot -f

# Logs monitoring
tail -f /var/log/linkedin-bot-health.log

# Logs backup
tail -f /var/log/linkedin-bot-backup.log

# Tous les logs LinkedIn Bot
sudo journalctl -u "linkedin-bot*" -f
```

## 🆘 Dépannage

### Service ne démarre pas

```bash
# Vérifier le statut
sudo systemctl status linkedin-bot

# Voir les erreurs
sudo journalctl -u linkedin-bot -n 50 --no-pager

# Causes communes:
# 1. Docker non démarré
sudo systemctl start docker

# 2. Fichier compose introuvable
cd ~/linkedin-birthday-auto
ls -la docker-compose.pi4-standalone.yml

# 3. Permissions
sudo chown -R pi:pi ~/linkedin-birthday-auto
```

### Timer ne s'exécute pas

```bash
# Vérifier que le timer est activé
sudo systemctl is-enabled linkedin-bot-monitor.timer

# Si disabled:
sudo systemctl enable linkedin-bot-monitor.timer
sudo systemctl start linkedin-bot-monitor.timer

# Forcer une exécution
sudo systemctl start linkedin-bot-monitor.service
```

### Logs de monitoring vides

```bash
# Vérifier les permissions
ls -la /var/log/linkedin-bot-health.log

# Créer si nécessaire
sudo touch /var/log/linkedin-bot-health.log
sudo chmod 666 /var/log/linkedin-bot-health.log

# Tester le script
sudo -u pi bash ~/linkedin-birthday-auto/scripts/monitor_pi4_health.sh
```

## 🔗 Documentation Complète

Pour plus de détails, consultez:

- **[AUTOMATION_DEPLOYMENT_PI4.md](../AUTOMATION_DEPLOYMENT_PI4.md)** - Guide complet d'automatisation
- **[SETUP_PI4_FREEBOX.md](../SETUP_PI4_FREEBOX.md)** - Configuration initiale Pi4
- **[README.md](../README.md)** - Documentation principale

## 📞 Support

En cas de problème:

1. Vérifier les logs: `sudo journalctl -u linkedin-bot*`
2. Consulter le troubleshooting dans [AUTOMATION_DEPLOYMENT_PI4.md](../AUTOMATION_DEPLOYMENT_PI4.md#troubleshooting)
3. Ouvrir une issue sur GitHub

---

**Version:** 2.0.0
**Date:** 2024-11-28
