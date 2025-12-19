# 🤖 LinkedIn Birthday Auto Bot (RPi4 Optimized)

[![Build Status](https://img.shields.io/github/actions/workflow/status/GaspardD78/linkedin-birthday-auto/build-images.yml?branch=main)](https://github.com/GaspardD78/linkedin-birthday-auto/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

**Système autonome d'automatisation LinkedIn conçu pour Raspberry Pi 4.**
Gère vos vœux d'anniversaire et vos visites de profils de manière intelligente, discrète et résiliente.

---

## ✨ Fonctionnalités Clés

*   **⚡ Optimisé RPi4** : Consommation RAM minimale (~600MB), gestion ZRAM/Swap automatique, Docker multi-arch (ARM64).
*   **🎂 Birthday Bot** : Envoi de messages personnalisés (Jour J ou rattrapage).
*   **🔍 Visitor Bot** : Visite automatique de profils ciblés (Mode Recruteur, Filtres Booléens).
*   **🛡️ Sécurité Renforcée (V3.3)** :
    *   **Conteneurs non-privilégiés** : L'API n'a plus d'accès root à l'hôte.
    *   **Docker Socket Proxy** : Gestion sécurisée des services via l'API Docker.
    *   **Isolation Réseau** : DNS fiables (Cloudflare/Google) forcés et hardening Nginx.
*   **📊 Dashboard** : Interface Web Next.js pour le pilotage, les logs et les statistiques.
*   **🔄 Résilient** : Retry automatique, gestion des timeouts réseaux, base de données SQLite WAL robuste.

---

## 🚀 Installation Rapide (Recommandée)

**Pré-requis :** Raspberry Pi 4 (4GB RAM minimum conseillé), Raspberry Pi OS 64-bit (Lite ou Desktop).
**Système :** `git` et `docker` installés (le script peut installer Docker pour vous).

1.  **Cloner le dépôt :**
    ```bash
    git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
    cd linkedin-birthday-auto
    ```

2.  **Lancer l'installateur :**
    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```
    *Le script gère tout : vérification mémoire/swap, configuration Docker, création certificats SSL temporaires, et lancement des conteneurs.*

3.  **Accéder au Dashboard :**
    *   Ouvrez votre navigateur : `https://<IP_DE_VOTRE_RPI>` (ou le domaine configuré).
    *   Acceptez le certificat auto-signé (si vous n'avez pas encore configuré Let's Encrypt).
    *   Connectez-vous (login par défaut affiché à la fin du script).

---

## 🏗️ Architecture V3.3

Le projet utilise une architecture micro-services sécurisée via Docker Compose :

*   **Bot Worker** (Python/Playwright) : Exécute les tâches d'automatisation dans un environnement isolé.
*   **API** (FastAPI) : Interface de contrôle, communique avec Docker via socket pour gérer les bots.
*   **Dashboard** (Next.js) : Interface utilisateur moderne.
*   **Redis** : File d'attente des tâches et cache.
*   **Nginx** : Reverse Proxy (SSL, Rate Limiting, HTTP/2).
*   **SQLite** : Stockage persistant léger et performant (fichier local).

Pour plus de détails, voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## ⚙️ Configuration

La configuration se fait principalement via le fichier `config/config.yaml` ou directement depuis le Dashboard.

**Exemple de config (`config.yaml`) :**
```yaml
bots:
  birthday:
    enabled: true
    mode: "standard" # ou "unlimited"
    schedule: "0 9 * * *" # Cron syntax (9h00 tous les jours)
    messaging:
      template: "Joyeux anniversaire {name} ! 🎉"

  visitor:
    enabled: true
    keywords: ["Recruteur", "CTO", "Tech Lead"]
    location: "Paris"
    limits:
      profiles_per_run: 20
```

---

## 📚 Documentation

*   [**Guide de Dépannage (Troubleshooting)**](docs/TROUBLESHOOTING.md) : Si quelque chose ne va pas.
*   [**Sécurité & Hardening**](docs/SECURITY.md) : Détails sur la protection des données.
*   [**Architecture Technique**](docs/ARCHITECTURE.md) : Pour les développeurs curieux.

---

## 🛠️ Commandes Utiles

**Voir les logs en temps réel :**
```bash
docker compose -f docker-compose.pi4-standalone.yml logs -f
```

**Redémarrer les services :**
```bash
docker compose -f docker-compose.pi4-standalone.yml restart
```

**Mettre à jour le bot :**
```bash
git pull
./setup.sh
```

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Merci d'ouvrir une Issue pour discuter des changements majeurs avant de soumettre une PR.

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---
*Développé avec ❤️ pour la communauté Raspberry Pi.*
