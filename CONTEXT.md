# Contexte du Projet pour IA & Développeurs

Ce fichier définit le contexte technique, l'architecture et les règles de développement pour toute intervention (humaine ou IA) sur ce projet.

## 📂 Structure du Projet

*   **`/` (Racine)** : Point d'entrée. Contient le script maître `setup.sh` et le fichier docker-compose de production `docker-compose.pi4-standalone.yml`.
*   **`/src`** : Code source Backend (Python).
    *   `api/` : Endpoints FastAPI.
    *   `bots/` : Logique métier des bots (Visitor, Birthday, etc.) utilisant Playwright.
    *   `core/` : Gestion de base de données, configuration, navigateur.
    *   `utils/` : Utilitaires (Dates, Logs).
*   **`/dashboard`** : Code source Frontend (Next.js App Router).
    *   `app/` : Pages et routes API (BFF).
    *   `components/` : Composants UI (basés sur shadcn/ui).
    *   `lib/` : Utilitaires et hooks.
*   **`/config`** : Fichiers de configuration (YAML, JSON).
*   **`/data`** : Données persistantes (SQLite, logs, fichiers auth).
*   **`/scripts`** : Scripts utilitaires appelés par `setup.sh`.
*   **`/docs`** : Documentation technique.
*   **`/_ARCHIVE_2025`** : Historique et fichiers obsolètes (ne pas modifier).

## 🛠️ Stack Technique

*   **Backend** : Python 3.11+, FastAPI, Playwright (Automation), SQLAlchemy (DB), Redis (Queue/RQ).
*   **Frontend** : Next.js 14+ (App Router), TypeScript, Tailwind CSS, shadcn/ui.
*   **Infrastructure** : Docker, Docker Compose, Nginx (Reverse Proxy).
*   **Cible** : Raspberry Pi 4 (ARM64).

## 📏 Règles de Développement

### 1. Robustesse & Types
*   **Python** : Utiliser le typage statique (`mypy` compliant) et Pydantic pour la validation des données.
*   **TypeScript** : `any` est interdit. Définir des interfaces claires pour toutes les props et réponses API.

### 2. Gestion des Erreurs
*   Ne jamais laisser un bot crasher silencieusement. Utiliser des blocs `try/except` et logger les erreurs avec le module `src.utils.logging`.
*   Les scripts Shell doivent utiliser `set -euo pipefail`.

### 3. Architecture & Déploiement
*   **Source de vérité** : `docker-compose.pi4-standalone.yml` est la SEULE config de prod.
*   **Point d'entrée** : Toute opération de déploiement ou maintenance DOIT passer par `setup.sh`.
*   **Compatibilité** : Tout code doit être compatible ARM64 (attention aux images Docker et dépendances Python/Node).

### 4. Sécurité
*   Ne jamais commiter de secrets. Utiliser `.env`.
*   Les mots de passe doivent être hashés (bcrypt) dans `.env`.
*   Permissions fichiers : `600` pour les fichiers sensibles (`.env`, `auth_state.json`).

### 5. Modification de Configuration
*   Si une nouvelle variable d'environnement est requise, l'ajouter à `.env.pi4.example` et mettre à jour `setup.sh` pour la gérer.
