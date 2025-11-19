# 🏠 Installation Locale avec IP Résidentielle

Ce guide vous permet d'installer le bot LinkedIn Birthday sur un ordinateur personnel (PC, Mac, Raspberry Pi) pour utiliser votre **propre IP résidentielle** au lieu de GitHub Actions.

## 🎯 Avantages de l'Installation Locale

- ✅ **100% Gratuit** : Aucun coût de proxy
- ✅ **IP Résidentielle Légitime** : Votre vraie connexion internet (box SFR, Orange, Free, etc.)
- ✅ **Zéro Détection** : LinkedIn voit une connexion normale depuis votre domicile
- ✅ **Contrôle Total** : Vous gérez tout vous-même
- ✅ **Pas de Limite** : Pas de restrictions GitHub Actions
- ✅ **Plus Rapide** : Connexion directe, pas de proxy intermédiaire

## 📋 Prérequis

### Matériel Nécessaire (Choisissez UNE option)

**Option 1 : Raspberry Pi** (Recommandé pour économie d'énergie)
- Raspberry Pi 3B+ ou supérieur (35-55€)
- Carte microSD 16GB minimum (10€)
- Alimentation USB-C (incluse généralement)
- Consommation : ~3W (~0.65€/mois)

**Option 2 : PC/Laptop Existant**
- N'importe quel PC sous Windows, Mac ou Linux
- Doit rester allumé aux heures d'exécution (ex: 8h-10h chaque matin)
- Consommation : ~50-100W (~10-20€/mois selon tarif)

**Option 3 : Mini PC / NUC**
- Mini PC type Intel NUC, Beelink, etc. (100-200€)
- Consommation : ~10-20W (~2-4€/mois)

### Logiciels Requis

- Python 3.8 ou supérieur
- Git
- Connexion Internet stable

---

## 🚀 Installation Étape par Étape

### 1. Préparation du Système

#### Sur Raspberry Pi (Raspberry OS)

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer les dépendances
sudo apt install -y python3 python3-pip git

# Installer les dépendances Playwright
sudo apt install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2
```

#### Sur Ubuntu/Debian

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip git
```

#### Sur macOS

```bash
# Installer Homebrew si pas déjà installé
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Installer Python et Git
brew install python git
```

#### Sur Windows

1. Installer Python depuis [python.org](https://www.python.org/downloads/)
   - ⚠️ Cocher "Add Python to PATH" pendant l'installation
2. Installer Git depuis [git-scm.com](https://git-scm.com/download/win)

---

### 2. Cloner le Projet

```bash
# Se placer dans le dossier home
cd ~

# Cloner le repository
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto
```

---

### 3. Installation des Dépendances Python

```bash
# Installer les packages Python
pip3 install -r requirements.txt

# Installer Playwright et les navigateurs
playwright install chromium

# Si erreur de permissions sur Raspberry Pi :
pip3 install --user -r requirements.txt
```

---

### 4. Configuration des Identifiants

#### Créer le fichier de configuration

```bash
# Créer un fichier .env pour stocker vos identifiants
nano .env
```

#### Ajouter vos identifiants (dans le fichier .env)

```bash
# Identifiants LinkedIn
LINKEDIN_EMAIL=votre.email@example.com
LINKEDIN_PASSWORD=votre_mot_de_passe

# Mode de test (mettre false pour envoyer de vrais messages)
DRY_RUN=false

# Désactiver le mode headless pour voir le navigateur (optionnel)
# HEADLESS_BROWSER=false

# Débug avancé (optionnel)
# ENABLE_ADVANCED_DEBUG=true

# Proxies (désactivé car on utilise l'IP locale)
ENABLE_PROXY_ROTATION=false
```

**Sauvegarder** : `Ctrl+O` puis `Entrée`, puis `Ctrl+X`

#### Sécuriser le fichier

```bash
# Rendre le fichier accessible uniquement par vous
chmod 600 .env
```

---

### 5. Modifier les Scripts pour Charger les Variables d'Environnement

#### Créer un script de lancement

```bash
nano run_birthday_wisher.sh
```

#### Contenu du script :

```bash
#!/bin/bash

# Charger les variables d'environnement
export $(cat ~/linkedin-birthday-auto/.env | xargs)

# Se placer dans le dossier du projet
cd ~/linkedin-birthday-auto

# Lancer le script
python3 linkedin_birthday_wisher.py

# Log de fin
echo "Script exécuté le $(date)" >> ~/linkedin-birthday-auto/execution.log
```

**Sauvegarder** et rendre exécutable :

```bash
chmod +x run_birthday_wisher.sh
```

---

### 6. Test Manuel

```bash
# Lancer le script manuellement pour tester
./run_birthday_wisher.sh
```

**Vérifications** :
- ✅ Le navigateur se lance (si HEADLESS_BROWSER=false)
- ✅ Connexion à LinkedIn réussie
- ✅ Détection des anniversaires
- ✅ Messages envoyés (si DRY_RUN=false)

---

### 7. Automatisation avec Cron

#### Éditer le crontab

```bash
crontab -e
```

#### Ajouter l'automatisation

**Pour exécuter chaque matin à 8h30 :**

```bash
# LinkedIn Birthday Wisher - Tous les jours à 8h30
30 8 * * * /home/VOTRE_UTILISATEUR/linkedin-birthday-auto/run_birthday_wisher.sh >> /home/VOTRE_UTILISATEUR/linkedin-birthday-auto/cron.log 2>&1
```

**Remplacer** `VOTRE_UTILISATEUR` par votre nom d'utilisateur réel (obtenir avec `whoami`)

#### Exemples d'horaires personnalisés :

```bash
# Tous les jours à 9h15
15 9 * * * /home/user/linkedin-birthday-auto/run_birthday_wisher.sh >> /home/user/linkedin-birthday-auto/cron.log 2>&1

# Tous les jours à une heure aléatoire entre 8h et 10h (nécessite un wrapper script)
0 8 * * * sleep $((RANDOM \% 7200)) && /home/user/linkedin-birthday-auto/run_birthday_wisher.sh >> /home/user/linkedin-birthday-auto/cron.log 2>&1

# Du lundi au vendredi à 8h30 (pas le weekend)
30 8 * * 1-5 /home/user/linkedin-birthday-auto/run_birthday_wisher.sh >> /home/user/linkedin-birthday-auto/cron.log 2>&1
```

**Sauvegarder** : `Ctrl+O` puis `Entrée`, puis `Ctrl+X`

#### Vérifier que cron est actif

```bash
# Vérifier le service cron
sudo systemctl status cron

# Si inactif, l'activer
sudo systemctl enable cron
sudo systemctl start cron

# Voir les tâches cron configurées
crontab -l
```

---

### 8. Script avec Heure Aléatoire (Recommandé)

Pour encore plus de discrétion, créez un script qui s'exécute à une heure aléatoire :

```bash
nano run_birthday_wisher_random.sh
```

**Contenu** :

```bash
#!/bin/bash

# Attendre un délai aléatoire entre 0 et 2 heures (7200 secondes)
DELAY=$((RANDOM % 7200))
echo "Attente de $DELAY secondes avant exécution..." >> ~/linkedin-birthday-auto/cron.log
sleep $DELAY

# Charger les variables d'environnement
export $(cat ~/linkedin-birthday-auto/.env | xargs)

# Se placer dans le dossier du projet
cd ~/linkedin-birthday-auto

# Lancer le script
python3 linkedin_birthday_wisher.py

# Log de fin
echo "Script exécuté le $(date) après $DELAY secondes de délai" >> ~/linkedin-birthday-auto/execution.log
```

```bash
chmod +x run_birthday_wisher_random.sh
```

**Modifier le cron** pour utiliser ce script :

```bash
crontab -e
```

```bash
# Lancer à 8h, mais exécution réelle entre 8h et 10h
0 8 * * * /home/VOTRE_UTILISATEUR/linkedin-birthday-auto/run_birthday_wisher_random.sh
```

---

## 📊 Surveillance et Logs

### Voir les logs d'exécution

```bash
# Logs de cron
tail -f ~/linkedin-birthday-auto/cron.log

# Logs d'exécution
tail -f ~/linkedin-birthday-auto/execution.log

# Logs de la base de données
sqlite3 ~/linkedin-birthday-auto/linkedin_birthday.db "SELECT * FROM birthday_messages ORDER BY timestamp DESC LIMIT 10;"
```

### Vérifier les prochaines exécutions cron

```bash
# Voir les tâches cron
crontab -l

# Voir les logs système de cron
grep CRON /var/log/syslog | tail -20
```

---

## 🔧 Dépannage

### Le script ne s'exécute pas automatiquement

1. **Vérifier que cron est actif** :
   ```bash
   sudo systemctl status cron
   ```

2. **Vérifier les chemins absolus** dans le crontab :
   ```bash
   # ❌ Mauvais (chemin relatif)
   30 8 * * * ./run_birthday_wisher.sh

   # ✅ Bon (chemin absolu)
   30 8 * * * /home/user/linkedin-birthday-auto/run_birthday_wisher.sh
   ```

3. **Vérifier les permissions** :
   ```bash
   ls -la ~/linkedin-birthday-auto/run_birthday_wisher.sh
   # Doit afficher -rwxr-xr-x (exécutable)
   ```

4. **Tester le script manuellement** :
   ```bash
   /home/user/linkedin-birthday-auto/run_birthday_wisher.sh
   ```

### Erreurs de dépendances Playwright

```bash
# Réinstaller Playwright
pip3 uninstall playwright
pip3 install playwright
playwright install chromium

# Si erreur de permissions
pip3 install --user playwright
playwright install chromium
```

### Le navigateur ne se lance pas (Raspberry Pi)

```bash
# Installer les dépendances manquantes
sudo apt install -y libgbm1 libasound2

# Forcer le mode headless
echo "HEADLESS_BROWSER=true" >> ~/.env
```

### Connexion LinkedIn échoue

1. **Vérifier les identifiants** dans `.env`
2. **Désactiver le 2FA** sur LinkedIn (ou utiliser l'auth state)
3. **Régénérer l'auth state** :
   ```bash
   rm auth_state.json
   python3 linkedin_birthday_wisher.py
   ```

---

## 🔐 Sécurité

### Protéger vos identifiants

```bash
# Fichier .env accessible uniquement par vous
chmod 600 ~/linkedin-birthday-auto/.env

# Ne jamais commiter .env dans Git
echo ".env" >> ~/linkedin-birthday-auto/.gitignore
```

### Sauvegardes

```bash
# Sauvegarder la base de données régulièrement
cp ~/linkedin-birthday-auto/linkedin_birthday.db ~/linkedin-birthday-auto/linkedin_birthday_backup_$(date +%Y%m%d).db

# Automatiser la sauvegarde (ajouter au crontab)
0 0 * * 0 cp ~/linkedin-birthday-auto/linkedin_birthday.db ~/linkedin-birthday-auto/backups/linkedin_birthday_backup_$(date +\%Y\%m\%d).db
```

---

## 🌐 Accès au Dashboard depuis un autre appareil

Si vous voulez accéder au Dashboard Web depuis votre téléphone/ordinateur :

### 1. Lancer le serveur Flask

```bash
# Modifier app.py pour écouter sur toutes les interfaces
nano app.py
```

Changer :
```python
app.run(debug=True)
```

En :
```python
app.run(host='0.0.0.0', port=5000, debug=False)
```

### 2. Trouver l'IP locale du Raspberry Pi

```bash
hostname -I
# Exemple : 192.168.1.45
```

### 3. Lancer le serveur

```bash
python3 app.py
```

### 4. Accéder depuis un autre appareil

Ouvrir dans le navigateur :
```
http://192.168.1.45:5000
```

**Automatiser le lancement** (ajouter au crontab) :
```bash
@reboot sleep 30 && cd /home/user/linkedin-birthday-auto && python3 app.py >> /home/user/linkedin-birthday-auto/dashboard.log 2>&1 &
```

---

## ⚡ Optimisations Raspberry Pi

### Réduire la consommation

```bash
# Désactiver le WiFi si vous utilisez l'Ethernet
sudo nmcli radio wifi off

# Désactiver le Bluetooth
sudo systemctl disable bluetooth

# Désactiver l'interface graphique (si non nécessaire)
sudo systemctl set-default multi-user.target
```

### Redémarrage automatique en cas de crash

```bash
# Créer un script de monitoring
nano ~/check_script.sh
```

**Contenu** :
```bash
#!/bin/bash
if pgrep -f "linkedin_birthday_wisher.py" > /dev/null
then
    echo "Script running"
else
    echo "Script not running, restarting..."
    /home/user/linkedin-birthday-auto/run_birthday_wisher.sh &
fi
```

```bash
chmod +x ~/check_script.sh

# Ajouter au crontab (vérifier toutes les 15 minutes)
crontab -e
```

```bash
*/15 * * * * /home/user/check_script.sh >> /home/user/monitor.log 2>&1
```

---

## 📱 Notifications sur Téléphone

### Option 1 : Email via SMTP

Ajouter dans `.env` :
```bash
ENABLE_EMAIL_ALERTS=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=votre.email@gmail.com
SMTP_PASSWORD=votre_mot_de_passe_app
ALERT_EMAIL=votre.email@gmail.com
```

### Option 2 : Telegram Bot

```bash
pip3 install python-telegram-bot

# Ajouter dans .env
TELEGRAM_BOT_TOKEN=votre_token
TELEGRAM_CHAT_ID=votre_chat_id
```

---

## 🎯 Comparaison : Local vs GitHub Actions

| Critère | Installation Locale | GitHub Actions |
|---------|-------------------|----------------|
| **Coût** | Gratuit (3€/mois électricité) | Gratuit |
| **IP** | ✅ Résidentielle légitime | ❌ Datacenter détectable |
| **Détection** | ✅ Très faible risque | ⚠️ Risque moyen |
| **Contrôle** | ✅ Total | ⚠️ Limité |
| **Maintenance** | ⚠️ Manuelle | ✅ Aucune |
| **Setup** | ⚠️ ~1h | ✅ ~15 min |
| **Fiabilité** | ⚠️ Dépend de votre connexion | ✅ Très fiable |

---

## 🆘 Support

Si vous rencontrez des problèmes :

1. **Consultez les logs** : `tail -f ~/linkedin-birthday-auto/cron.log`
2. **Vérifiez les issues GitHub** : [github.com/GaspardD78/linkedin-birthday-auto/issues](https://github.com/GaspardD78/linkedin-birthday-auto/issues)
3. **Testez manuellement** : `./run_birthday_wisher.sh`

---

## ✅ Checklist de Vérification Finale

- [ ] Python 3.8+ installé (`python3 --version`)
- [ ] Dépendances installées (`pip3 list | grep playwright`)
- [ ] Projet cloné dans `~/linkedin-birthday-auto`
- [ ] Fichier `.env` créé avec identifiants LinkedIn
- [ ] Script `run_birthday_wisher.sh` créé et exécutable
- [ ] Test manuel réussi
- [ ] Tâche cron configurée (`crontab -l`)
- [ ] Logs accessibles et fonctionnels
- [ ] Sauvegarde de la base de données configurée

---

## 🚀 Prochaines Étapes Recommandées

1. **Laisser tourner 1 semaine** en mode test (DRY_RUN=true)
2. **Surveiller les logs** quotidiennement
3. **Activer le mode production** (DRY_RUN=false)
4. **Configurer les sauvegardes** automatiques
5. **Activer les notifications** (email/Telegram)

---

**Félicitations !** Votre bot LinkedIn tourne maintenant sur votre propre connexion résidentielle, 100% gratuit et indétectable ! 🎉
