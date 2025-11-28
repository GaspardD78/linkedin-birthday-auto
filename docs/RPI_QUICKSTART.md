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

### 2. Préparation de l'Infrastructure Système

Nous avons créé un script qui prépare votre Raspberry Pi (Installation de Docker, SWAP, Services Systemd).

> **Note importante :** Ce script ne lance pas encore le bot. Il prépare uniquement le système d'exploitation.

**Exécutez cette commande :**

```bash
sudo ./scripts/install_automation_pi4.sh
```

> ☕ **Prenez un café !** Le script va :
>
> - Installer Docker et ses dépendances
> - Configurer le SWAP (critique pour éviter les crashs)
> - Installer les services systemd (pour le démarrage auto)
> - Préparer les permissions et dossiers

⚠️ **IMPORTANT : Ne redémarrez PAS encore !**
Même si le script vous invite à le faire, attendez d'avoir terminé l'étape 4 (Déploiement) ci-dessous. Redémarrer maintenant forcerait le système à construire les images au démarrage en arrière-plan, ce qui surchargerait votre Raspberry Pi.

### 3. Configurer l'Authentification

Une fois la préparation terminée, configurez votre environnement.

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

### 4. Déploiement de l'Application

Maintenant que le système est prêt, nous allons construire et lancer les conteneurs **avant** le redémarrage. Cela garantit que les images Docker sont prêtes et évite une surcharge du CPU au prochain démarrage.

**Lancez le déploiement :**

```bash
./scripts/deploy_pi4_standalone.sh
```

> *Alternative : Vous pouvez aussi utiliser `./scripts/easy_deploy.sh` pour un assistant interactif.*

### 5. Redémarrer (Finalisation)

**Uniquement une fois le déploiement terminé avec succès**, redémarrez votre Pi.
Cela permet de finaliser les permissions Docker et de laisser les services systemd prendre le relais proprement sur des conteneurs déjà existants.

```bash
sudo reboot
```

### 6. Vérifier que tout fonctionne

Après le redémarrage, attendez 2-3 minutes que les services systemd relancent les conteneurs, puis vérifiez :

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

**Méthode Simple (Recommandée) :**
```bash
cd ~/linkedin-birthday-auto
git pull
./scripts/easy_deploy.sh
```

Le script `easy_deploy.sh` vous guidera automatiquement à travers toutes les étapes nécessaires.

**Méthode Manuelle :**
```bash
cd ~/linkedin-birthday-auto
git pull
./scripts/full_cleanup_deployment.sh -y
./scripts/deploy_pi4_standalone.sh
```

______________________________________________________________________

📄 Pour une documentation technique détaillée, voir
[AUTOMATION_DEPLOYMENT_PI4.md](AUTOMATION_DEPLOYMENT_PI4.md).
