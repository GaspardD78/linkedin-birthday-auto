# LinkedIn Birthday Auto Bot - Architecture v2.0 (Architecture Actuelle)

Ce document décrit l'architecture technique du projet tel qu'il est déployé en production sur Raspberry Pi 4.

## Vue d'ensemble

Le système est une application distribuée en micro-services, conçue pour être robuste, économe en ressources et facile à maintenir. Il est composé de :

1.  **Dashboard (Frontend)** : Interface web Next.js pour le contrôle et le monitoring.
2.  **API (Backend)** : Serveur FastAPI servant de passerelle et de contrôleur.
3.  **Worker** : Processus d'arrière-plan (RQ) exécutant les scripts d'automatisation (Playwright).
4.  **Queue** : Redis pour la gestion asynchrone des tâches.
5.  **Database** : SQLite (mode WAL) pour la persistance locale partagée.

## Diagramme d'Architecture

```mermaid
graph TD
    subgraph "Raspberry Pi 4 (Docker Host)"
        subgraph "Services"
            D[Dashboard (Next.js)] -- HTTP/JSON --> A[API (FastAPI)]
            D -- SSE (Logs/Events) --> A

            A -- Enqueue Job --> R[Redis Queue]
            A -- Read/Write --> DB[(SQLite)]
            A -- Read/Write --> CFG[Config/Messages Files]

            W[Worker (Python/RQ)] -- Dequeue Job --> R
            W -- Execute --> B[Playwright Bot]
            W -- Read/Write --> DB
            W -- Read --> CFG
        end

        subgraph "External"
            User((Utilisateur)) -- Navigateur --> D
            B -- HTTPS --> L[LinkedIn.com]
        end
    end
```

## Composants Détaillés

### 1. Dashboard (Frontend)
- **Technologie** : Next.js 14 (App Router), React, TailwindCSS, Shadcn/UI.
- **Rôle** : Interface utilisateur pour voir les logs, l'état du bot, les statistiques et modifier la configuration.
- **Spécificité** : Utilise Server-Sent Events (SSE) pour afficher les logs en temps réel sans surcharger le réseau. Il communique avec l'API via un proxy interne pour éviter les problèmes de CORS.

### 2. API (Backend)
- **Technologie** : Python 3.9+, FastAPI, Uvicorn.
- **Rôle** :
    - Expose des endpoints REST pour le Dashboard.
    - Gère l'authentification interne (API Key).
    - Met en file d'attente les tâches (Jobs) dans Redis.
    - Lit les fichiers de logs pour les transmettre au Dashboard.
- **Fichier principal** : `src/api/app.py`.

### 3. Worker & Bots
- **Technologie** : Python, RQ (Redis Queue), Playwright.
- **Rôle** : Consomme les tâches de la file d'attente et exécute les scripts de navigation.
- **Bots disponibles** :
    - `BirthdayBot` : Souhaite les anniversaires (Standard ou Illimité).
    - `VisitorBot` : Visite des profils basés sur une recherche (Mots-clés/Lieu).
- **Isolation** : Chaque exécution de bot se fait dans un contexte isolé pour éviter les fuites de mémoire (critique sur RPi4).

### 4. Persistance (Data)
- **SQLite (`data/linkedin.db`)** : Stocke l'historique des messages, les profils visités et les statistiques. Configuré en mode WAL (Write-Ahead Logging) pour permettre des lectures/écritures concurrentes entre l'API et le Worker.
- **Redis** :
    - DB 0 : File d'attente des tâches (RQ).
    - DB 1 : Cache pour le Dashboard (optionnel).
- **Fichiers à plat** :
    - `config/config.yaml` : Configuration globale.
    - `data/messages.txt` : Templates de messages.
    - `auth_state.json` : Cookies de session LinkedIn (sécurisés).

## Flux de Données

### Scénario : Lancement manuel du Bot Anniversaire
1.  L'utilisateur clique sur "Démarrer" dans le Dashboard.
2.  Le Dashboard appelle `POST /api/bot/action` (Next.js) qui proxy vers `POST /trigger` (FastAPI).
3.  L'API valide la requête et pousse un job `run_bot_task` dans Redis.
4.  Le Worker détecte le nouveau job, instancie `BirthdayBot`.
5.  Le Bot lance un navigateur Headless (Chromium), charge les cookies `auth_state.json`.
6.  Le Bot navigue sur LinkedIn, détecte les anniversaires, envoie les messages.
7.  Chaque action est loggée dans `logs/linkedin_bot.log` et enregistrée dans SQLite.
8.  Le Dashboard affiche les logs en temps réel via SSE et met à jour les stats.

## Sécurité

- **Isolation Réseau** : Les conteneurs communiquent via un réseau Docker interne `linkedin-network`. Seul le Dashboard (port 3000) est exposé (ou via reverse-proxy).
- **API Key** : Communication entre Dashboard et API sécurisée par une clé générée au démarrage.
- **Cookies** : Les cookies de session sont stockés localement et jamais exposés via l'API publique.
- **Bot Stealth** : Utilisation de `playwright-stealth` et de délais aléatoires (distrib. Gaussienne) pour éviter la détection par LinkedIn.

## Structure du Code (`src/`)

```
src/
├── api/             # Code de l'API FastAPI
│   ├── routes/      # Endpoints par catégorie
│   └── app.py       # Point d'entrée de l'application
├── bots/            # Logique métier des Bots
│   ├── birthday_bot.py
│   └── visitor_bot.py
├── config/          # Gestion de la configuration (Pydantic)
├── core/            # Cœur du système
│   ├── base_bot.py  # Classe mère avec fonctions communes (Login, Nav)
│   ├── database.py  # Gestion SQLite (Singleton Thread-safe)
│   └── browser_manager.py # Gestion instance Playwright
├── queue/           # Gestion des tâches asynchrones
│   └── worker.py    # Point d'entrée du Worker RQ
└── utils/           # Utilitaires (Date, Logs, Exceptions)
```
