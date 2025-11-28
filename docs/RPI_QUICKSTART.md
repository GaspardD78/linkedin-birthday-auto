# 🥧 Guide Rapide: Raspberry Pi 4 (Docker)

> **⚠️ AVERTISSEMENT :** Ne suivez PAS la procédure d'installation standard (pip install) sur
> Raspberry Pi. Utilisez ce guide pour une installation conteneurisée (Docker) qui gère toutes les
> dépendances automatiquement.

Ce guide est optimisé pour **Raspberry Pi OS (Bookworm/Trixie) 64-bit**.

______________________________________________________________________

## 🚀 Installation "Zero to Hero"

### 1. Préparer le Raspberry Pi

Ouvrez votre terminal et clonez le projet (si ce n'est pas déjà fait) :

```bash
cd ~
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto
```

### 2. Lancer l'Installation Automatisée

Nous avons créé un script qui installe tout pour vous (Docker, Docker Compose, Services Systemd,
SWAP, etc.).

**Exécutez simplement cette commande :**

```bash
sudo ./scripts/install_automation_pi4.sh
```

> ☕ **Prenez un café !** Le script va :
>
> - Installer Docker (si manquant)
> - Configurer le SWAP pour éviter les crashs de mémoire
> - Créer les services de démarrage automatique
> - Configurer le monitoring et les backups

### 3. Configurer l'Authentification

Pendant que l'installation tourne (ou après), préparez votre configuration.

Créez le fichier `.env` à la racine :

```bash
nano .env
```

Copiez-collez le contenu suivant (remplacez la valeur de `LINKEDIN_AUTH_STATE` par vos cookies) :

```bash
# Authentification LinkedIn (Base64 des cookies exportés)
# Utilisez l'extension "Cookie-Editor" -> Export -> JSON -> Convertir en Base64
LINKEDIN_AUTH_STATE=eyJjb29raWVzIjpbeyJuYW1lIjoibGlfYXQiLC...

# Configuration du Bot
LINKEDIN_BOT_DRY_RUN=false      # Mettre à true pour tester sans envoyer
LINKEDIN_BOT_MODE=standard      # 'standard' ou 'unlimited'
```

*Pour convertir votre JSON de cookies en Base64 :*

```bash
# Si vous avez le fichier auth_state.json sur votre PC, utilisez un site comme base64encode.org
# Ou en ligne de commande locale : cat auth_state.json | base64 -w 0
```

### 4. Redémarrer

Une fois le script terminé et le fichier `.env` créé, redémarrez votre Pi pour appliquer les
changements (notamment les permissions Docker).

```bash
sudo reboot
```

### 5. Vérifier que tout fonctionne

Après le redémarrage, attendez 2-3 minutes que les conteneurs se lancent, puis vérifiez :

**Via le Terminal :**

```bash
# Vérifier que les conteneurs tournent
cd ~/linkedin-birthday-auto
docker compose -f docker-compose.pi4-standalone.yml ps

# Voir les logs du bot
docker compose -f docker-compose.pi4-standalone.yml logs -f bot-worker
```

**Via le Dashboard Web :** Ouvrez votre navigateur et allez sur : `http://<IP_DE_VOTRE_RPI>:3000`
(Exemple: `http://192.168.1.145:3000`)

______________________________________________________________________

## ❓ FAQ / Dépannage

### "Command not found: docker"

Assurez-vous d'avoir redémarré après l'installation (`sudo reboot`). Si cela persiste, exécutez
`newgrp docker`.

### "ModuleNotFoundError" ou erreurs Python

🛑 **STOP !** N'essayez pas de lancer `python main.py` directement sur le Pi. Le bot tourne **dans
Docker**. Toute commande doit passer par Docker ou utiliser le script de déploiement.

Pour lancer une commande manuellement (ex: validation) :

```bash
docker compose -f docker-compose.pi4-standalone.yml exec bot-worker python main.py validate
```

### Mettre à jour le bot

```bash
cd ~/linkedin-birthday-auto
git pull
./scripts/deploy_pi4_standalone.sh
```

______________________________________________________________________

📄 Pour une documentation technique détaillée, voir
[AUTOMATION_DEPLOYMENT_PI4.md](AUTOMATION_DEPLOYMENT_PI4.md).
