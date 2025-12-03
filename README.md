# 🤖 LinkedIn Birthday Bot - Guide Raspberry Pi 4

Bienvenue ! Ce guide est conçu pour installer le bot sur un **Raspberry Pi 4** (ou autre environnement Docker).

## 📋 Prérequis

*   **Matériel** :
    *   Raspberry Pi 4 (2GB RAM minimum, 4GB+ recommandé).
    *   Carte MicroSD de **32 Go minimum**.
*   **Logiciel** :
    *   **Raspberry Pi OS Lite (64-bit)** (Recommandé).
    *   Docker et Docker Compose (installés automatiquement par le script).

---

## 🚀 Installation Automatique

Nous fournissons un script "tout-en-un" qui installe Docker, configure le système et déploie le bot.

```bash
# 1. Cloner le projet
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto

# 2. Lancer l'installation
./setup.sh
```

**Le script va :**
1. Installer les dépendances (Docker, etc.).
2. Vous aider à configurer vos cookies LinkedIn (`auth_state.json`) et préférences.
3. Déployer les conteneurs (Dashboard, API, Worker, Redis, SQLite).

> ⚠️ **Note sur connexion internet** : Le téléchargement des images Docker peut prendre 2-5 minutes selon votre connexion. Le script intègre automatiquement :
> - Retry automatique en cas de timeout (jusqu'à 5 tentatives)
> - Pull séquentiel optimisé pour connexions lentes
> - Si vous rencontrez des erreurs réseau, consultez le [Guide de Dépannage](docs/RASPBERRY_PI_TROUBLESHOOTING.md#issue-docker-image-pull-timeout-tls-handshake-timeout).

---

## 📚 Documentation

Toute la documentation technique se trouve dans le dossier `docs/` :

*   👉 **[Architecture (ARCHITECTURE.md)](docs/ARCHITECTURE.md)** : Comprendre comment ça marche (Next.js, FastAPI, RQ, SQLite).
*   👉 **[Guide de Déploiement (AUTOMATION_DEPLOYMENT_PI4.md)](docs/AUTOMATION_DEPLOYMENT_PI4.md)** : Détails sur le script d'installation et le déploiement manuel.
*   👉 **[Mise à jour (UPDATE_GUIDE.md)](docs/UPDATE_GUIDE.md)** : Comment mettre à jour le bot.
*   👉 **[Dépannage (RASPBERRY_PI_TROUBLESHOOTING.md)](docs/RASPBERRY_PI_TROUBLESHOOTING.md)** : Résoudre les problèmes courants.

---

## 🌐 Utilisation

Une fois installé :

*   **Dashboard** : `http://<IP_DE_VOTRE_RPI>:3000`
*   **API** : `http://<IP_DE_VOTRE_RPI>:8000/docs`

> ⚠️ **Trafic réseau et automatisations** : Si vous avez installé les automatisations systemd, le bot démarre **automatiquement au boot** et reste actif en permanence. Cela génère du trafic réseau continu vers LinkedIn.
> - Pour arrêter : `sudo systemctl stop linkedin-bot && docker compose -f docker-compose.pi4-standalone.yml down`
> - Pour diagnostic : `sudo ./scripts/diagnose_network_traffic.sh`
> - Pour désinstaller : `sudo ./scripts/uninstall_automation_pi4.sh`
> - Voir le [Guide de Dépannage](docs/RASPBERRY_PI_TROUBLESHOOTING.md#issue-abnormal-network-traffic-after-installing-automations)

---

## 🛠️ Commandes Utiles

Pour gérer le bot une fois installé :

```bash
# Voir les logs
docker compose -f docker-compose.pi4-standalone.yml logs -f

# Redémarrer
docker compose -f docker-compose.pi4-standalone.yml restart

# Mettre à jour (méthode recommandée)
./setup.sh
```
