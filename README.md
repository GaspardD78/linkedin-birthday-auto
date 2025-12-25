# 🤖 LinkedIn Birthday Auto Bot (RPi4 Optimized)

[![Build Status](https://img.shields.io/github/actions/workflow/status/GaspardD78/linkedin-birthday-auto/build-images.yml?branch=main)](https://github.com/GaspardD78/linkedin-birthday-auto/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

**Système autonome d'automatisation LinkedIn conçu pour Raspberry Pi 4.**
Gère vos vœux d'anniversaire et vos visites de profils de manière intelligente, discrète et résiliente.

---

## ⚠️ Architecture du Projet (V1 vs V2)

Ce dépôt contient deux versions de l'application :

1.  **🟢 V1 Stable (Production)** : Située dans le dossier `src/`. C'est la version actuellement déployée, documentée et optimisée pour Raspberry Pi 4. **Utilisez cette version pour tout déploiement réel.**
2.  **🚧 V2 Expérimentale (Beta)** : Située dans le dossier `app_v2/`. C'est une refonte majeure (Async-First, FastAPI) en cours de développement. Elle n'est pas encore prête pour la production. [Voir le README V2](app_v2/README.md).

---

## ✨ Fonctionnalités Clés (V1 Stable)

*   **⚡ Optimisé RPi4** : Limites RAM strictes par service (~3.7GB total sur 4GB), prévention OOM kills, gestion ZRAM/Swap automatique, Docker multi-arch (ARM64).
*   **🎂 Birthday Bot** : Envoi de messages personnalisés (Jour J ou rattrapage).
*   **🔍 Visitor Bot** : Visite automatique de profils ciblés (Mode Recruteur, Filtres Booléens).
*   **🛡️ Sécurité Renforcée (V3.3+)** :
    *   **Conteneurs non-privilégiés** : L'API n'a plus d'accès root à l'hôte.
    *   **Isolation Réseau** : DNS fiables (Cloudflare/Google) forcés et hardening Nginx.
    *   **Rapport Sécurité Automatisé** : Vérification 4-points avec score (0-4) à chaque setup.
*   **🔐 Gestion HTTPS Intelligente** : Let's Encrypt automatique ou certificats existants.
*   **💾 Sauvegardes Google Drive** : Backups chiffrés et automatisés (Rclone).
*   **📊 Dashboard** : Interface Web Next.js pour le pilotage, les logs et les statistiques.

---

## 🚀 Installation Rapide

**Pré-requis :** Raspberry Pi 4 (4GB RAM minimum conseillé), Raspberry Pi OS 64-bit.

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
    *Le script gère tout : Docker, HTTPS (Let's Encrypt), Backups, et Sécurité.*

3.  **Accéder au Dashboard :**
    *   `https://<VOTRE_IP_OU_DOMAINE>`
    *   Login par défaut : `admin` (mot de passe affiché à la fin du script).

👉 **Guide de Démarrage Rapide complet :** [docs/QUICK_START_2025.md](docs/QUICK_START_2025.md)

---

## 🏗️ Architecture V1 (Stable)

Le projet utilise une architecture micro-services sécurisée via Docker Compose :

*   **Bot Worker** (`src/`): Exécute les tâches Playwright (Python).
*   **API** (`src/api/`): Interface de contrôle FastAPI.
*   **Dashboard** (`dashboard/`): Frontend Next.js.
*   **Redis & SQLite**: Queue et Persistance.

Pour plus de détails, voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 📚 Documentation

### Guides Utilisateur
*   [**Quick Start Guide**](docs/QUICK_START_2025.md) : Installation en 10 minutes.
*   [**Guide Configuration HTTPS**](docs/HTTPS_CONFIGURATION.md) : Options SSL/TLS.
*   [**Guide Sauvegardes Google Drive**](docs/SETUP_BACKUP_GUIDE.md) : Sécuriser vos données.
*   [**Guide Gestion Mot de Passe**](docs/PASSWORD_MANAGEMENT_GUIDE.md) : Sécurité du dashboard.
*   [**Troubleshooting**](docs/TROUBLESHOOTING.md) : Résolution des problèmes courants.

### Documentation Technique
*   [**Architecture V1**](docs/ARCHITECTURE.md) : Détails techniques de la version stable.
*   [**Architecture V2 (Beta)**](app_v2/README.md) : Détails sur la refonte en cours.
*   [**Rapport d'Audit V2**](docs/audit/AUDIT_REPORT_COMPLETE.md) : Analyse de la version expérimentale.
*   [**Sécurité & Hardening**](docs/SECURITY.md) : Pratiques de sécurité appliquées.

---

## ⚙️ Configuration

La configuration se fait principalement via le Dashboard ou le fichier `config/config.yaml`.

```yaml
bots:
  birthday:
    enabled: true
    schedule: "0 9 * * *" # 9h00 tous les jours
```

---

## 🛠️ Commandes Utiles

**Voir les logs :** `docker compose logs -f`
**Mettre à jour :** `git pull && ./setup.sh`
**Gérer mot de passe :** `./scripts/manage_dashboard_password.sh`

---

## 🤝 Contribution

Les contributions sont les bienvenues !
*   Pour des fixes sur la version stable, ciblez le dossier `src/`.
*   Pour travailler sur la refonte, ciblez le dossier `app_v2/`.

## 📄 Licence

Licence MIT. Voir le fichier `LICENSE`.
