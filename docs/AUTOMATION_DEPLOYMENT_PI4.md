# 🤖 Guide de Déploiement Automatisé sur Raspberry Pi 4

Ce document détaille le fonctionnement interne des scripts d'installation et de déploiement pour le LinkedIn Birthday Bot.

## 📋 Table des matières

- [Architecture du Déploiement](#architecture-du-déploiement)
- [Script 1 : Préparation Système (install_automation_pi4.sh)](#script-1--préparation-système)
- [Script 2 : Déploiement Applicatif (deploy_pi4_standalone.sh)](#script-2--déploiement-applicatif)
- [Installation Rapide (Guide complet)](#installation-rapide-guide-complet)
- [Services Systemd](#services-systemd)

---

## Architecture du Déploiement

Le déploiement sur Raspberry Pi 4 est divisé en deux phases distinctes pour garantir la stabilité et éviter les erreurs de configuration :

1.  **Phase Système (`root`)** : Installation des paquets, configuration du noyau (SWAP), et mise en place des services de démarrage.
2.  **Phase Applicative (`user`)** : Construction des images Docker, configuration des volumes, et lancement des conteneurs.

> ⚠️ **Important :** Cette séparation est cruciale. Le script système ne touche pas aux conteneurs, et le script applicatif ne touche pas à la configuration système profonde (sauf vérifications).

---

## Script 1 : Préparation Système

**Fichier :** `scripts/install_automation_pi4.sh`

Ce script prépare le terrain. Il doit être lancé avec `sudo`.

### Ce qu'il fait :
1.  **Dépendances :** Installe Docker, Docker Compose, Git, jq, curl.
2.  **SWAP :** Vérifie et configure un SWAP de 2GB (nécessaire pour compiler le Dashboard Next.js sans crash OOM).
3.  **Permissions :** Ajoute l'utilisateur actuel au groupe `docker`.
4.  **Systemd :** Installe et active le service `linkedin-dashboard.service` qui assurera le redémarrage automatique des conteneurs au boot.
5.  **Logs :** Crée la structure de dossiers `/var/log` (ou locale) avec les bonnes permissions.

### Ce qu'il NE fait PAS :
*   Il **ne construit pas** les images Docker.
*   Il **ne lance pas** l'application.

---

## Script 2 : Déploiement Applicatif

**Fichier :** `scripts/deploy_pi4_standalone.sh` (ou via `easy_deploy.sh`)

Ce script gère le cycle de vie de l'application. Il s'exécute sans `sudo` (une fois l'utilisateur dans le groupe docker).

### Ce qu'il fait :
1.  **Vérification :** S'assure que le SWAP est actif et que Docker tourne.
2.  **Configuration :** Génère les fichiers `api.ts` et `utils.ts` nécessaires au Dashboard.
3.  **Build :** Lance `docker compose build` pour créer les images `bot-worker` et `dashboard`.
4.  **Run :** Lance les conteneurs en mode détaché (`up -d`).
5.  **Validation :** Vérifie la santé des services via l'API.

---

## Installation Rapide (Guide complet)

Pour une installation propre, suivez scrupuleusement cet ordre :

### Étape 1 : Préparation Système
Lancez le script d'infrastructure.
```bash
sudo ./scripts/install_automation_pi4.sh
```

### Étape 2 : Configuration
Créez votre fichier `.env` avec vos cookies LinkedIn.
```bash
cp .env.example .env
nano .env
```

### Étape 3 : Déploiement Applicatif

> **⚠️ AVERTISSEMENT CRITIQUE :**
> Vous devez **impérativement** exécuter cette étape **AVANT** de redémarrer votre Raspberry Pi.
>
> Si vous redémarrez avant d'avoir lancé ce script, le service systemd tentera de construire les images Docker au démarrage.
> Sur un Raspberry Pi 4, cela saturera le CPU et la RAM, rendant le système instable ou inaccessible pendant de longues minutes.
>
> **Lancez toujours la première construction manuellement pour voir les logs et s'assurer que tout se passe bien.**

C'est ici que l'application est réellement installée.
```bash
./scripts/deploy_pi4_standalone.sh
```
*Note : Cette étape peut prendre 15-20 minutes sur un Pi 4 (compilation du Dashboard).*

### Étape 4 : Finalisation
Une fois le déploiement terminé avec succès, redémarrez pour appliquer les permissions de groupe Docker et laisser l'automatisation systemd prendre le relais sur des conteneurs déjà prêts.
```bash
sudo reboot
```

---

## Services Systemd

Le fichier de service `linkedin-dashboard.service` est configuré pour :
*   Démarrer après le service Docker.
*   Lancer `docker compose up` au démarrage du Pi.
*   Arrêter proprement les conteneurs à l'extinction.

Si vous avez besoin de contrôler le bot manuellement via systemd :
```bash
# Voir le statut
sudo systemctl status linkedin-dashboard

# Redémarrer le bot
sudo systemctl restart linkedin-dashboard

# Voir les logs du service gestionnaire
journalctl -u linkedin-dashboard -f
```
