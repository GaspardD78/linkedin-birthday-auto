# 🔒 Guide de Sécurisation - LinkedIn Birthday Auto Bot
## Audit Sécurité Décembre 2025

Ce guide vous accompagne pas à pas pour sécuriser votre installation exposée sur Internet.

---

## 📋 Table des Matières

1. [Backup Automatique Google Drive](#1-backup-automatique-google-drive)
2. [HTTPS avec Let's Encrypt](#2-https-avec-lets-encrypt)
3. [Vérification Sécurité](#3-vérification-sécurité)
4. [Maintenance](#4-maintenance)

---

## 1. Backup Automatique Google Drive

### Étape 1.1 : Installation de rclone

```bash
# Sur votre Raspberry Pi
curl https://rclone.org/install.sh | sudo bash

# Vérifier l'installation
rclone version
```

### Étape 1.2 : Configuration Google Drive

```bash
# Lancer la configuration interactive
rclone config

# Suivre ces étapes :
# 1. Tapez "n" pour "New remote"
# 2. Nom : "gdrive" (IMPORTANT: utilisez exactement ce nom)
# 3. Type : Tapez "drive" ou le numéro correspondant à "Google Drive"
# 4. client_id : Laissez vide (appuyez sur Entrée)
# 5. client_secret : Laissez vide (appuyez sur Entrée)
# 6. scope : Tapez "1" (Full access)
# 7. root_folder_id : Laissez vide
# 8. service_account_file : Laissez vide
# 9. Edit advanced config? : Tapez "n"
# 10. Use auto config? : Tapez "n" (car vous êtes en SSH)
#
# 11. Vous allez voir une URL, ouvrez-la dans votre navigateur
# 12. Connectez-vous à votre compte Google
# 13. Autorisez rclone
# 14. Copiez le code d'autorisation
# 15. Collez-le dans le terminal
# 16. Configure as a Shared Drive? : Tapez "n"
# 17. Keep this remote? : Tapez "y"
# 18. Quit config : Tapez "q"
```

### Étape 1.3 : Test du Backup

```bash
cd /home/pi/linkedin-birthday-auto

# Test manuel
./scripts/backup_to_gdrive.sh

# Vérifier sur Google Drive que le fichier est bien uploadé
rclone ls gdrive:linkedin-bot-backups/
```

### Étape 1.4 : Automatisation Quotidienne

```bash
# Éditer le crontab
crontab -e

# Ajouter cette ligne (backup tous les jours à 3h du matin)
0 3 * * * /home/pi/linkedin-birthday-auto/scripts/backup_to_gdrive.sh >> /var/log/linkedin-backup-gdrive.log 2>&1

# Sauvegarder et quitter (Ctrl+X, puis Y, puis Entrée)

# Vérifier le cron
crontab -l
```

### Étape 1.5 : Restauration d'un Backup

**En cas de crash du Raspberry Pi :**

```bash
# 1. Lister les backups disponibles
rclone ls gdrive:linkedin-bot-backups/

# 2. Télécharger le backup le plus récent
rclone copy gdrive:linkedin-bot-backups/linkedin_backup_YYYYMMDD_HHMMSS.db.gz /tmp/

# 3. Décompresser et restaurer
gunzip -c /tmp/linkedin_backup_YYYYMMDD_HHMMSS.db.gz > /app/data/linkedin.db

# 4. Redémarrer le bot
docker compose -f docker-compose.pi4-standalone.yml restart
```

---

## 2. HTTPS avec Let's Encrypt

### Étape 2.1 : Prérequis

**Vous devez avoir :**
- Un nom de domaine (ex: monbot.votredomaine.com)
- Le domaine pointant vers votre IP publique Freebox
- Les ports 80 et 443 ouverts dans votre Freebox

### Étape 2.2 : Configuration Freebox (Redirection Ports)

1. Connectez-vous à votre interface Freebox : https://subscribe.free.fr/login/
2. Allez dans **Paramètres Freebox → Mode avancé → Redirections de ports**
3. Ajoutez ces redirections :

| Protocole | Port externe | Port interne | IP de destination      | Description         |
|-----------|--------------|--------------|------------------------|---------------------|
| TCP       | 80           | 80           | (IP du Raspberry Pi)   | HTTP Let's Encrypt  |
| TCP       | 443          | 443          | (IP du Raspberry Pi)   | HTTPS LinkedIn Bot  |

**Pour trouver l'IP du Raspberry Pi :**
```bash
hostname -I
# Exemple: 192.168.1.50
```

### Étape 2.3 : Installation Nginx

```bash
# Mettre à jour le système
sudo apt update
sudo apt upgrade -y

# Installer nginx et certbot
sudo apt install -y nginx certbot python3-certbot-nginx

# Vérifier nginx
sudo systemctl status nginx
```

### Étape 2.4 : Configuration Nginx

```bash
# Copier la configuration fournie
sudo cp /home/pi/linkedin-birthday-auto/deployment/nginx/linkedin-bot.conf /etc/nginx/sites-available/

# Éditer pour remplacer YOUR_DOMAIN.COM par votre vrai domaine
sudo nano /etc/nginx/sites-available/linkedin-bot.conf

# Cherchez "YOUR_DOMAIN.COM" (2 occurrences) et remplacez par votre domaine
# Exemple: monbot.votredomaine.com
# Sauvegarder : Ctrl+X, Y, Entrée

# Activer la configuration
sudo ln -s /etc/nginx/sites-available/linkedin-bot.conf /etc/nginx/sites-enabled/

# Désactiver le site par défaut
sudo rm /etc/nginx/sites-enabled/default

# Copier la page d'erreur 429
sudo mkdir -p /var/www/html
sudo cp /home/pi/linkedin-birthday-auto/deployment/nginx/429.html /var/www/html/

# Tester la configuration
sudo nginx -t

# Si OK, recharger nginx
sudo systemctl reload nginx
```

### Étape 2.5 : Obtenir le Certificat SSL

```bash
# Remplacez VOTRE_DOMAINE.COM et VOTRE_EMAIL@example.com
sudo certbot --nginx -d VOTRE_DOMAINE.COM --email VOTRE_EMAIL@example.com --agree-tos --no-eff-email

# Suivre les instructions à l'écran
# Choisissez "2" pour rediriger automatiquement HTTP → HTTPS

# Vérifier le certificat
sudo certbot certificates
```

### Étape 2.6 : Renouvellement Automatique

```bash
# Tester le renouvellement
sudo certbot renew --dry-run

# Si OK, le renouvellement automatique est déjà configuré (cron)
# Vérifier :
sudo systemctl status certbot.timer
```

### Étape 2.7 : Tester HTTPS

Ouvrez votre navigateur : **https://VOTRE_DOMAINE.COM**

✅ **Vous devriez voir** :
- Cadenas vert dans la barre d'adresse
- Redirection automatique de HTTP vers HTTPS
- Dashboard fonctionnel

❌ **Si erreur** :
```bash
# Vérifier les logs nginx
sudo tail -f /var/log/nginx/linkedin-bot-error.log

# Vérifier que le dashboard tourne
docker compose -f /home/pi/linkedin-birthday-auto/docker-compose.pi4-standalone.yml ps
```

---

## 3. Vérification Sécurité

### 3.1 : Test des Headers Sécurité

Visitez : https://securityheaders.com/?q=https://VOTRE_DOMAINE.COM

**Vous devriez obtenir un score A ou A+**

### 3.2 : Test du Rate Limiting

```bash
# Test brute force login (doit bloquer après 5 tentatives)
for i in {1..10}; do
  curl -X POST https://VOTRE_DOMAINE.COM/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"fake"}' \
    -w "\nStatus: %{http_code}\n"
done

# Après 5 tentatives, vous devriez voir "Status: 429"
```

### 3.3 : Test SSL

Visitez : https://www.ssllabs.com/ssltest/analyze.html?d=VOTRE_DOMAINE.COM

**Vous devriez obtenir un score A**

---

## 4. Maintenance

### 4.1 : Vérifier les Backups

```bash
# Lister les backups locaux
ls -lh /mnt/linkedin-data/backups/

# Lister les backups Google Drive
rclone ls gdrive:linkedin-bot-backups/

# Vérifier les logs de backup
tail -f /var/log/linkedin-backup-gdrive.log
```

### 4.2 : Vérifier les Certificats SSL

```bash
# Vérifier la date d'expiration
sudo certbot certificates

# Forcer le renouvellement si nécessaire
sudo certbot renew --force-renewal
```

### 4.3 : Vérifier les Logs Nginx

```bash
# Logs généraux
sudo tail -f /var/log/nginx/linkedin-bot-access.log

# Logs d'erreur
sudo tail -f /var/log/nginx/linkedin-bot-error.log

# Logs de rate limiting
sudo tail -f /var/log/nginx/linkedin-bot-ratelimit.log

# Logs des tentatives de login
sudo tail -f /var/log/nginx/linkedin-bot-login.log
```

### 4.4 : Monitoring Quotidien

**Créer un script de monitoring** :

```bash
cat > /home/pi/check-security.sh << 'EOF'
#!/bin/bash
echo "═══════════════════════════════════════════════════════════"
echo "Security Check - LinkedIn Birthday Bot"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo "1. Certificat SSL:"
sudo certbot certificates | grep "Expiry Date"
echo ""

echo "2. Dernier backup Google Drive:"
rclone ls gdrive:linkedin-bot-backups/ | tail -1
echo ""

echo "3. Tentatives de login (dernières 24h):"
sudo grep "auth/login" /var/log/nginx/linkedin-bot-access.log | tail -5
echo ""

echo "4. Rate limiting (dernières 24h):"
sudo grep "429" /var/log/nginx/linkedin-bot-access.log | wc -l
echo " tentatives bloquées"
echo ""

echo "5. Espace disque:"
df -h | grep -E "Filesystem|/$"
echo ""

echo "✅ Check terminé"
EOF

chmod +x /home/pi/check-security.sh

# Exécuter
./check-security.sh
```

---

## 🎯 Checklist Finale

Avant de valider que tout est sécurisé :

- [ ] Backup Google Drive fonctionne (`rclone ls gdrive:linkedin-bot-backups/`)
- [ ] Backup automatique configuré dans cron (`crontab -l`)
- [ ] HTTPS actif (cadenas vert dans le navigateur)
- [ ] Score A sur https://securityheaders.com
- [ ] Score A sur https://www.ssllabs.com/ssltest/
- [ ] Rate limiting teste (10 tentatives login → 429 après 5)
- [ ] Dashboard accessible via HTTPS uniquement
- [ ] Redirections ports Freebox configurées (80 + 443)
- [ ] Certificat SSL valide (`sudo certbot certificates`)
- [ ] Renouvellement auto actif (`sudo systemctl status certbot.timer`)

---

## 📞 Support

**En cas de problème :**

1. Vérifiez les logs : `sudo tail -f /var/log/nginx/linkedin-bot-error.log`
2. Vérifiez Docker : `docker compose ps`
3. Redémarrez tout :
   ```bash
   sudo systemctl restart nginx
   docker compose -f docker-compose.pi4-standalone.yml restart
   ```

**Contact :**
- GitHub Issues : https://github.com/GaspardD78/linkedin-birthday-auto/issues

---

**Audit réalisé par** : Claude Code (Anthropic)
**Date** : 10 Décembre 2025
**Version** : 1.0
