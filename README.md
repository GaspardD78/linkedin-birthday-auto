# LinkedIn Automation Bot (Raspberry Pi 4 Edition)

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Docker](https://img.shields.io/badge/docker-available-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Un outil d'automatisation LinkedIn professionnel, sécurisé et optimisé pour Raspberry Pi 4 (ARM64).
Il permet d'automatiser l'envoi de messages d'anniversaire, la visite de profils ciblés, et la gestion des invitations.

## ✨ Fonctionnalités

- **🤖 Bots Autonomes** :
  - **Birthday Bot** : Souhaite les anniversaires (avec gestion du retard et messages personnalisés).
  - **Visitor Bot** : Visite des profils basés sur une recherche (augmente la visibilité "Who viewed your profile").
  - **Invitation Manager** : Nettoie les invitations en attente trop anciennes.
- **🖥️ Dashboard Moderne** : Interface Web (Next.js) pour piloter les bots, voir les stats et les logs en temps réel.
- **🔒 Sécurité** : Authentification par cookies (pas de mot de passe stocké), API sécurisée, protection des données.
- **🚀 Optimisé RPi4** : Architecture légère (Docker), gestion des ressources, logs rotatifs, base de données SQLite optimisée (WAL).

## 🛠️ Pré-requis

- **Matériel** : Raspberry Pi 4 (4GB ou 8GB recommandés).
- **OS** : Raspberry Pi OS (64-bit) Lite ou Desktop.
- **Logiciels** :
  - Docker & Docker Compose
  - Git

## 🚀 Installation Rapide (Docker)

1. **Cloner le dépôt :**
   ```bash
   git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
   cd linkedin-automation
   sudo ./setup.sh
   ```

2. **Configuration :**
   Copiez le fichier d'exemple et éditez-le :
   ```bash
   cp .env.pi4.example .env
   nano .env
   ```
   *Remplissez les variables obligatoires (`API_KEY`, `JWT_SECRET`, etc.).*

3. **Authentification LinkedIn :**
   Le bot utilise vos cookies de session pour se connecter.
   - Connectez-vous à LinkedIn sur votre navigateur PC.
   - Utilisez une extension comme "EditThisCookie" pour exporter les cookies au format JSON.
   - Ou récupérez les valeurs `li_at` et `JSESSIONID`.
   - Une fois le dashboard lancé, vous pourrez uploader le fichier `auth_state.json` via l'interface `/auth`.

4. **Lancement :**
   Utilisez le script de déploiement optimisé :
   ```bash
   ./scripts/deploy_pi4_standalone.sh
   ```
   *Cela va construire les images, lancer les conteneurs (Redis, API, Worker, Dashboard) et configurer le réseau.*

5. **Accès :**
   - **Dashboard** : `http://<IP_RPI>:3000`
   - **API Docs** : `http://<IP_RPI>:8000/docs`

## 📂 Structure du Projet

```
.
├── config/                 # Fichiers de configuration (YAML)
├── dashboard/              # Frontend Next.js
├── data/                   # Base de données SQLite et fichiers persistants
├── logs/                   # Logs des services
├── scripts/                # Scripts utilitaires (déploiement, maintenance)
├── src/                    # Code source Python
│   ├── api/                # API FastAPI
│   ├── bots/               # Logique des bots (Playwright)
│   ├── core/               # Noyau (Base de données, Auth, Browser)
│   └── ...
├── docker-compose.pi4-standalone.yml  # Configuration Docker Production
└── requirements.txt        # Dépendances Python (épinglées)
```

## 🛡️ Maintenance & Sécurité

- **Mise à jour** :
  ```bash
  git pull
  ./scripts/deploy_pi4_standalone.sh
  ```
- **Logs** : Les logs sont accessibles via le Dashboard ou dans `logs/linkedin_bot.log`.
- **Base de données** : SQLite est configuré en mode WAL pour la robustesse. Un `VACUUM` automatique est effectué périodiquement.

## 🤝 Contribuer

Les Pull Requests sont les bienvenues. Merci de respecter les standards "Clean Code" et de vérifier la compatibilité ARM64.

## 📄 Licence

Ce projet est sous licence MIT.
