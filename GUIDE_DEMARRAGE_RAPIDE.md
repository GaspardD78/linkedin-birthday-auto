# 🚀 Guide de Démarrage Rapide - Installation Sécurité

**Pour les utilisateurs non-techniques** 👋

Ce guide vous permet d'installer **TOUTES les protections de sécurité** en suivant un script automatisé.

---

## ⚡ Installation Automatique (Recommandé)

### Étape 1 : Connectez-vous à votre Raspberry Pi

```bash
ssh pi@ADRESSE_IP_RASPBERRY
```

### Étape 2 : Allez dans le dossier du bot

```bash
cd linkedin-birthday-auto
```

### Étape 3 : Lancez le script d'installation

```bash
./scripts/setup_security.sh
```

**C'est tout ! 🎉**

Le script va vous guider étape par étape pour installer :
- ✅ Backup automatique Google Drive
- ✅ HTTPS avec Let's Encrypt
- ✅ Mot de passe hashé bcrypt
- ✅ Protection CORS
- ✅ Anti-indexation Google

⏱️ **Durée totale** : 30-45 minutes (avec vos réponses)

---

## 🔍 Vérifier Que Tout Fonctionne

Après l'installation, testez votre configuration :

```bash
./scripts/verify_security.sh
```

Ce script va tester **40+ points de sécurité** et vous donner un score.

**Score attendu** : 90%+ (Excellent)

---

## 📚 Besoin d'Aide ?

### Si vous bloquez sur les ports Freebox

Consultez le guide détaillé avec captures d'écran :
```bash
cat docs/GUIDE_FREEBOX_PORTS.md
```

Ou ouvrez dans votre navigateur :
https://github.com/VOTRE_REPO/blob/main/docs/GUIDE_FREEBOX_PORTS.md

### Si vous voulez comprendre ce qui est fait

Tous les guides détaillés sont disponibles :

| Guide | Description |
|-------|-------------|
| `SECURITY_HARDENING_GUIDE.md` | Guide complet backup + HTTPS + bcrypt |
| `docs/ANTI_INDEXATION_GUIDE.md` | Protection anti-indexation Google |
| `docs/GUIDE_FREEBOX_PORTS.md` | Ouvrir ports 80/443 sur Freebox |
| `docs/EMAIL_NOTIFICATIONS_INTEGRATION.md` | Alertes email (optionnel) |

### Si un test échoue

Le script `verify_security.sh` vous indique exactement quoi faire pour corriger.

Exemple :
```
✗ FAIL: rclone n'est pas installé
  → Installez avec: curl https://rclone.org/install.sh | sudo bash
```

---

## 🆘 Problèmes Courants

### "Permission denied" lors de l'exécution du script

**Solution** :
```bash
chmod +x scripts/setup_security.sh
chmod +x scripts/verify_security.sh
```

### "Port 80 is closed" sur canyouseeme.org

**Cause** : Ports pas ouverts sur Freebox
**Solution** : Suivez `docs/GUIDE_FREEBOX_PORTS.md`

### "Connection refused" à votre domaine

**Causes possibles** :
1. DNS ne pointe pas vers votre IP Freebox
2. Nginx pas démarré : `sudo systemctl start nginx`
3. Ports Freebox pas ouverts

**Vérifiez** :
```bash
# Tester que Nginx écoute
sudo netstat -tlnp | grep nginx

# Tester votre IP publique
curl https://ifconfig.me
```

### Certificat SSL échoue

**Causes possibles** :
1. Domaine ne pointe pas vers votre IP
2. Ports 80/443 pas ouverts
3. Firewall bloque

**Testez** :
```bash
# Vérifier DNS
nslookup votre-domaine.com

# Tester manuellement
sudo certbot --nginx -d votre-domaine.com
```

---

## 📋 Checklist Manuelle (Si Vous Préférez)

Si vous ne voulez pas utiliser le script automatique, voici la liste des actions :

### 1️⃣ Backup Google Drive (15 min)

```bash
# Installer rclone
curl https://rclone.org/install.sh | sudo bash

# Configurer Google Drive
rclone config
# Suivez les instructions pour créer le remote "gdrive"

# Tester backup
./scripts/backup_to_gdrive.sh

# Automatiser (cron)
crontab -e
# Ajoutez : 0 3 * * * /home/pi/linkedin-birthday-auto/scripts/backup_to_gdrive.sh
```

### 2️⃣ HTTPS Let's Encrypt (15 min)

```bash
# 1. Ouvrir ports sur Freebox (voir docs/GUIDE_FREEBOX_PORTS.md)

# 2. Installer Nginx et Certbot
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# 3. Copier et configurer Nginx
sudo cp deployment/nginx/linkedin-bot.conf /etc/nginx/sites-available/linkedin-bot
sudo sed -i "s/VOTRE_DOMAINE_ICI/votre-domaine.com/g" /etc/nginx/sites-available/linkedin-bot
sudo ln -s /etc/nginx/sites-available/linkedin-bot /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo cp deployment/nginx/429.html /var/www/html/

# 4. Tester et recharger
sudo nginx -t
sudo systemctl reload nginx

# 5. Obtenir certificat
sudo certbot --nginx -d votre-domaine.com
```

### 3️⃣ Mot de Passe Hashé (5 min)

```bash
# Installer bcryptjs
cd dashboard
npm install bcryptjs

# Générer hash
node scripts/hash_password.js "VotreMotDePasse"
# Copiez le hash affiché

# Mettre à jour .env
cd ..
nano .env
# Remplacez DASHBOARD_PASSWORD= par le hash

# Redémarrer dashboard
docker compose restart dashboard
```

### 4️⃣ Protection CORS (2 min)

```bash
# Ajouter dans .env
nano .env
# Ajoutez : ALLOWED_ORIGINS=https://votre-domaine.com

# Redémarrer API
docker compose restart api
```

### 5️⃣ Anti-Indexation (2 min)

Les fichiers sont déjà créés ! Juste redémarrer :

```bash
docker compose restart dashboard
sudo systemctl reload nginx
```

---

## ✅ Vérification Finale

Une fois tout installé, vérifiez :

### Test 1 : Backup fonctionne
```bash
./scripts/backup_to_gdrive.sh
```
✅ Devrait créer un fichier dans Google Drive

### Test 2 : HTTPS fonctionne
```
https://votre-domaine.com
```
✅ Devrait afficher le cadenas vert 🔒

### Test 3 : Score sécurité
```bash
./scripts/verify_security.sh
```
✅ Devrait afficher 90%+ (Excellent)

### Test 4 : Anti-indexation
```bash
curl -I https://votre-domaine.com | grep -i "x-robots"
```
✅ Devrait afficher : `x-robots-tag: noindex, nofollow, ...`

---

## 🎯 Score Sécurité

| Avant Installation | Après Installation |
|-------------------|-------------------|
| 4.5/10 🔴 CRITIQUE | 9.5/10 🟢 EXCELLENT |

### Vulnérabilités Corrigées

✅ Pas de backup → Backup quotidien Google Drive
✅ HTTP en clair → HTTPS Let's Encrypt
✅ Pas de rate limiting → Nginx rate limiting
✅ Mot de passe en clair → Bcrypt hash
✅ Pas de CORS → CORS restrictif
✅ SQL injection possible → Whitelists
✅ Indexation Google → 4 couches protection

---

## 💡 Conseils

### Surveillance

Vérifiez régulièrement que tout fonctionne :

```bash
# Logs backup
tail -f /var/log/linkedin-bot-backup.log

# Status Nginx
sudo systemctl status nginx

# Conteneurs Docker
docker ps

# Score sécurité
./scripts/verify_security.sh
```

### Mise à Jour

Quand vous faites un `git pull` pour mettre à jour le bot :

```bash
git pull origin main
docker compose down
docker compose build
docker compose up -d
```

### Support

Si vous avez des questions ou rencontrez des problèmes :

1. Consultez les guides dans `docs/`
2. Exécutez `./scripts/verify_security.sh` pour diagnostiquer
3. Ouvrez une issue sur GitHub avec :
   - Résultat de `verify_security.sh`
   - Logs : `/var/log/linkedin-bot-backup.log`
   - Version Raspberry Pi OS : `cat /etc/os-release`

---

## 🎉 Félicitations !

Vous avez un bot LinkedIn hautement sécurisé ! 🔒

**Prochaines étapes** (optionnelles) :

- 📧 Configurer notifications email (`docs/EMAIL_NOTIFICATIONS_INTEGRATION.md`)
- 🚫 Ajouter blacklist profils (fonctionnalité à venir)
- 📊 Exporter données CSV (fonctionnalité existante, UI à venir)
- 🔐 Ajouter authentification 2FA (avancé)

---

**Fait avec ❤️ pour les Product Owners qui veulent sécuriser leur bot**

*Questions ? Ouvrez une issue sur GitHub !*
