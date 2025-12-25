# Documentation Maître du Projet V2 (LinkedIn Automation)

Ce document fournit une vue d'ensemble complète de la nouvelle architecture V2 ("Projet V2"). Cette version remplace la V1 en introduisant une structure modulaire moderne, une base de données optimisée via SQLAlchemy, et un moteur d'automatisation plus robuste.

*Statut : En cours de développement dans le dossier `app_v2/`.*

## 1. Contexte et Objectifs

### 1.1 Mission
Automatiser les interactions LinkedIn (souhaits d'anniversaire, sourcing, visites) de manière indétectable, avec une architecture capable de tourner de manière fluide sur un **Raspberry Pi 4**.

### 1.2 Évolutions V2 vs V1
*   **Modularité :** Séparation stricte entre API, Moteur (Engine), et Services.
*   **Base de Données :** Passage à **SQLAlchemy** (ORM) + **Alembic** (Migrations) au lieu de requêtes SQL brutes.
*   **Performance :** Optimisation drastique de Playwright (blocage ressources, gestion mémoire) pour le hardware limité.
*   **API First :** Tout est piloté par une API REST FastAPI structurée.

---

## 2. Architecture Technique

### 2.1 Vue d'Ensemble
L'application est un monolithe modulaire conteneurisé.

```mermaid
graph TD
    Client[Dashboard / Client API] -->|HTTP| API[FastAPI (app_v2/main.py)]
    API -->|Appels| Services[Services Métier (Birthday, Visitor)]
    Services -->|Contrôle| Engine[Moteur d'Automation (Playwright)]
    Engine -->|Web| LinkedIn[LinkedIn.com]
    API -->|ORM| DB[(SQLite V2)]
    Engine -->|ORM| DB
```

### 2.2 Structure du Code (`app_v2/`)

```text
app_v2/
├── api/                 # Interface REST
│   ├── routers/         # Endpoints (control.py, data.py)
│   └── schemas.py       # Modèles Pydantic (Entrées/Sorties)
├── core/                # Configuration globale
│   ├── config.py        # Settings (Pydantic BaseSettings)
│   └── security.py      # Gestion Auth API
├── db/                  # Couche de données
│   ├── engine.py        # Session Manager (Async)
│   └── models.py        # Modèles SQLAlchemy (Contact, Interaction, Campaign)
├── engine/              # Noyau d'automatisation (Playwright)
│   ├── browser_context.py # Gestionnaire de contexte navigateur (Optimisé RPi4)
│   ├── action_manager.py  # Actions humaines (click, scroll, type)
│   ├── auth_manager.py    # Injection de cookies & Validation session
│   └── selector_engine.py # Gestion intelligente des sélecteurs CSS
├── services/            # Logique Métier
│   ├── birthday_service.py # Orchestrateur campagne anniversaire
│   └── visitor_service.py  # Orchestrateur campagne sourcing
└── main.py              # Point d'entrée FastAPI
```

---

## 3. Base de Données (Schéma V2)

Le schéma est défini dans `app_v2/db/models.py`.

### 3.1 Tables Principales

*   **`contacts`**
    *   `id` (PK), `name`, `profile_url` (Unique).
    *   `status`: État du contact ("new", "visited", "contacted").
    *   `birth_date`: Date anniversaire.
    *   `fit_score`: Score de pertinence calculé lors du sourcing.
    *   Données JSON : `skills`, `work_history`.

*   **`interactions`**
    *   Historique immuable des actions.
    *   `type`: "birthday_sent", "profile_visit", "invitation_withdrawn".
    *   `status`: "success", "failed".
    *   `payload`: Données contextuelles (ex: message envoyé).

*   **`campaigns`**
    *   Configuration des campagnes (Nom, Type, Status).
    *   Permet de rejouer des campagnes avec les mêmes filtres.

*   **`linkedin_selectors`**
    *   Stockage dynamique des sélecteurs CSS pour résilience aux mises à jour UI.

---

## 4. API Reference (V2)

L'API est exposée via `app_v2/main.py`.

### 4.1 Control (`/campaigns`)
Permet de lancer les bots. Utilise `BackgroundTasks` pour ne pas bloquer la requête.
*   `POST /campaigns/birthday` : Lance la campagne d'anniversaires.
    *   Params : `dry_run`, `process_late`.
*   `POST /campaigns/sourcing` : Lance une session de visite/scraping.
    *   Params : `search_url`, `limit`, `criteria`.
*   `GET /campaigns/status` : Retourne l'état du worker (Actif/Inactif).

### 4.2 Data (`/data`)
Accès aux données récoltées.
*   `GET /data/contacts` : Liste paginée des contacts avec filtres.
*   `GET /data/contacts/{id}` : Détail d'un contact.
*   `GET /data/interactions` : Historique des logs d'actions.
*   `GET /data/stats/global` : Statistiques globales (KPIs).

---

## 5. Moteur d'Automation (`engine/`)

C'est le cœur critique pour la performance sur Raspberry Pi.

### 5.1 `LinkedInBrowserContext`
*   **Launch Args optimisés :** `--disable-gpu`, `--disable-dev-shm-usage`, `--single-process`.
*   **Blocage de ressources :** Intercepte les requêtes réseau pour bloquer images, polices, médias et CSS inutiles. Gain de RAM majeur.
*   **Contexte Unique :** Utilise un contexte persistant avec injection de `storage_state` (cookies).

### 5.2 `SmartSelectorEngine`
*   Gère une liste de sélecteurs candidats pour chaque élément.
*   Score de fiabilité pour choisir le meilleur sélecteur dynamiquement.

---

## 6. Installation et Déploiement

### Pré-requis
*   Python 3.9+
*   Playwright (`playwright install chromium`)
*   Fichier `.env.v2` configuré.

### Lancement
```bash
# Dans la racine du projet
uvicorn app_v2.main:app --host 0.0.0.0 --port 8000 --reload
```

### Dashboard (Frontend)
Le projet V2 est conçu pour être piloté par une interface (actuellement compatible avec le Dashboard V1 via adaptateurs API ou futur Dashboard V2). L'API expose les endpoints CORS nécessaires (`http://localhost:3000`).
