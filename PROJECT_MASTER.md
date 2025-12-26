# 📘 DOCUMENT MAÎTRE DU PROJET - LinkedIn Birthday Auto (RPi4)

**Version du document :** 3.0 (Production V1 + V2 Alternative)
**Date de mise à jour :** 25 Décembre 2025
**Statut :** Référence Principale

Ce document consolide l'ensemble des informations techniques, fonctionnelles et architecturales du projet. Il sert de source de vérité unique pour les développeurs et administrateurs.

⚠️ **Note Importante:**
- **V1 (Production)** : Architecture éprouvée, déployée en production sur Raspberry Pi 4, version 4.1 stable
- **V2 (Alternative)** : Refonte async-first en développement dans `./app_v2/`, non recommandée pour production sans corrections sécurité

---

## 1. 🌍 Contexte et Vue d'Ensemble

Le projet **LinkedIn Birthday Auto** est une suite d'automatisation "Set & Forget" conçue pour tourner 24/7 sur un **Raspberry Pi 4**. Il permet de gérer les interactions LinkedIn (souhaits d'anniversaire, visites de profils, gestion des invitations) de manière autonome, en imitant un comportement humain pour éviter la détection.

### Points Clés
*   **Cible Matérielle :** Raspberry Pi 4 (4GB+ RAM recommandés).
*   **Philosophie :** "Discrétion et Stabilité". Le bot privilégie la sécurité du compte LinkedIn (limites, délais aléatoires) sur la vitesse.
*   **Architecture :** Micro-services isolés via Docker, communiquant via API et Redis.

---

## 2. 🎯 Objectifs Fonctionnels

1.  **Souhaits d'Anniversaire (Birthday Bot) :**
    *   Envoi quotidien de messages personnalisés.
    *   Gestion des "retards" (mode rattrapage/unlimited) pour les jours manqués.
    *   Détection intelligente des dates (support multilingue FR/EN).
2.  **Prospection Passive (Visitor Bot) :**
    *   Visite de profils ciblés (via URL de recherche ou Campagnes).
    *   Objectif : Apparaître dans les notifications "Qui a consulté votre profil".
    *   Calcul de "Fit Score" pour qualifier les prospects.
3.  **Gestion de Réseau (Invitation Manager) :**
    *   Nettoyage automatique des invitations envoyées trop anciennes.
    *   (Optionnel) Acceptation automatique selon critères.
4.  **Pilotage Unifié (Dashboard) :**
    *   Interface Web pour le suivi temps réel, la configuration et les logs.
    *   Pas de redémarrage nécessaire pour changer les paramètres.

---

## 3. 🏗️ Architecture Technique (V1 - Production)

Le système utilise une architecture découplée orchestrée par **Docker Compose**.

### Diagramme des Flux
```mermaid
graph TD
    Client[Navigateur Web] -- HTTPS:443 --> Nginx[Nginx Reverse Proxy]
    Nginx -- HTTP:3000 --> NextJS[Dashboard (Next.js 14)]
    Nginx -- HTTP:8000 --> API[FastAPI Backend]

    NextJS -- API Call --> API
    API -- Enqueue Job --> Redis[Redis (Queue)]

    Worker[Python Worker (RQ)] -- Dequeue Job --> Redis
    Worker -- R/W --> SQLite[SQLite DB (WAL)]
    API -- R/W --> SQLite

    Worker -- Playwright --> LinkedIn[LinkedIn.com]
```

### Composants & Stack
| Service | Technologie | Rôle |
| :--- | :--- | :--- |
| **Dashboard** | Next.js 14, React 18, Tailwind, Shadcn/UI | Interface utilisateur, authentification Dashboard. |
| **API** | Python 3.9+, FastAPI, Pydantic V2 | Point d'entrée backend, gestion config, lecture logs. |
| **Worker** | Python 3.9+, RQ (Redis Queue), Playwright | Exécution asynchrone des bots (Scraping). |
| **Database** | SQLite 3 (Mode WAL) | Stockage persistant unique (Contacts, Stats, Config). |
| **Redis** | Redis 7+ | File d'attente de tâches et cache temporaire. |
| **Proxy** | Nginx | Terminaison SSL (Let's Encrypt), Sécurité. |

---

## 4. 🗄️ Base de Données (Schéma SQLite)

Le fichier de base de données est situé dans `data/linkedin.db`. Les connexions sont gérées par un singleton thread-safe (`src/core/database.py`).

### Tables Principales

#### `contacts`
Annuaire local des relations.
- `id` (PK), `name` (Index), `linkedin_url` (Unique)
- `last_message_date` : Date du dernier message envoyé.
- `message_count` : Compteur total d'interactions.

#### `birthday_messages`
Historique des souhaits d'anniversaire (pour éviter les doublons).
- `contact_name` (Index), `message_text`, `sent_at` (Index).
- `is_late` (Bool) : Indique si le message était un rattrapage.

#### `profile_visits`
Trace des visites effectuées par le Visitor Bot.
- `profile_url` (Index), `visited_at` (Index).
- `success` (Bool), `error_message`.
- `source_search` : URL ou contexte de la recherche source.

#### `scraped_profiles` (Enrichi V2)
Données extraites lors des visites (Mini-CRM).
- `profile_url` (Unique), `full_name`, `headline`, `location`.
- `skills` (JSON), `work_history` (JSON).
- `fit_score` (Real) : Score de pertinence calculé (0-100).
- `campaign_id` (FK) : Lien vers la campagne d'origine.

#### `campaigns`
Configuration des campagnes de prospection.
- `id`, `name`, `search_url`, `filters` (JSON).
- `status` (pending/active/completed).

#### `bot_executions` & `errors`
Logs techniques structurés pour les statistiques et le débogage.

---

## 5. 🔌 API & Routes (Backend)

L'API FastAPI (Port 8000) est sécurisée par `X-API-Key`.
Toutes les réponses sont en JSON.

### 🤖 Pilotage des Bots (`/bot`)
*   `POST /bot/action` : Endpoint unifié pour démarrer/arrêter les bots.
    *   Payload Start : `{ "action": "start", "job_type": "birthday|visitor", "config": {...} }`
    *   Payload Stop : `{ "action": "stop", "job_type": "all|specific" }`
*   `GET /bot/status` : État détaillé (Jobs actifs, File d'attente, Worker status).
*   `GET /bot/jobs/{job_id}` : Suivi d'une tâche spécifique.

### ⚙️ Système & Logs (`/system` & `/logs`)
*   `GET /api/logs` : Récupère les logs (tail) avec filtrage.
    *   Params : `limit` (int), `service` (worker/api).
*   `GET /system/health` : Métriques vitales (CPU, RAM, Température RPi).

### 🔐 Authentification & Config
*   `POST /auth/upload` : Upload du fichier `auth_state.json` (Cookies LinkedIn).
*   `GET /config/yaml` : Lecture de la configuration (`config.yaml`).
*   `POST /config/yaml` : Écriture de la configuration.

---

## 6. 📂 Structure du Code

```text
.
├── config/                 # Fichiers YAML (config.yaml, selectors.yaml)
├── dashboard/              # Projet Next.js (Frontend)
│   ├── app/                # Pages & Routes (App Router)
│   ├── lib/                # api.ts (Client API), utils.ts
│   └── components/         # Widgets UI (Shadcn)
├── data/                   # Volume persistant (DB, Logs, Backups)
├── scripts/                # Scripts Shell (setup.sh, updates)
├── src/                    # Code Source Python
│   ├── api/                # Application FastAPI
│   │   ├── app.py          # Point d'entrée
│   │   └── routes/         # Découpage par fonctionnalité
│   ├── bots/               # Logique métier (BirthdayBot, VisitorBot)
│   ├── core/               # Cœur (Database, BrowserManager)
│   ├── queue/              # Worker RQ & Tâches (tasks.py)
│   └── utils/              # Helpers (DateParsing, Logging, Security)
└── docker-compose.yml      # Orchestration Production
```

---

## 7. 🚀 Workflow de Déploiement

L'installation et la maintenance reposent sur le script maître `setup.sh`.

1.  **Pré-requis :** Raspberry Pi OS (64-bit Lite), Docker, Git.
2.  **Installation :** `git clone ... && ./setup.sh`
3.  **Processus automatique :**
    *   Vérification système (Swap, Permissions).
    *   Génération des secrets (`.env`).
    *   Mise en place des conteneurs (Pull images GHCR optimisées ARM64).
    *   Configuration SSL (Certbot) et Nginx.
4.  **Post-Installation :**
    *   Connexion au Dashboard (https://mon-domaine.com).
    *   Upload du cookie `auth_state.json`.
    *   Configuration des messages et horaires.

---

## 8. 🛡️ Sécurité (V1)

*   **Session Injection :** Pas de login/password LinkedIn stockés. Utilisation de cookies de session injectés.
*   **Isolation :** Le Worker tourne dans un conteneur non-privilégié.
*   **Chiffrement :** HTTPS forcé, Backups chiffrés.
*   **Validation :** Pydantic V2 pour valider toutes les entrées API et Config.

---

## 9. 🔄 Architecture V2 (Alternative - En Développement)

**Statut :** 🔄 En développement dans `./app_v2/` - **Non recommandée pour production sans corrections**

### Différences Clés vs V1

| Aspect | V1 | V2 |
|--------|----|----|
| **Approche** | Synchrone + RQ (workers) | Async-first avec asyncio |
| **Framework** | FastAPI (sync) | FastAPI (async) + SQLAlchemy async |
| **Queue** | Redis + RQ | En développement |
| **Database** | SQLite (sync) | SQLite async + NullPool |
| **Code Quality** | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Sécurité** | ⭐⭐⭐⭐ | ⭐⭐ (problématique) |
| **Tests** | Limités | Aucun (critique) |
| **Production Ready** | ✅ OUI | ⚠️ NON |

### Points Positifs V2
- Architecture moderne et async-first (meilleur pattern Python)
- Code plus propre avec SQLAlchemy ORM
- Potentiel de meilleure scalabilité
- Séparation claire des responsabilités

### Problèmes Critiques V2
- **Sécurité** : Vulnérabilités identifiées dans la gestion des données et l'authentification
- **Tests** : Aucun test unitaire (critique avant production)
- **Documentation** : Incomplète pour le déploiement
- **Robustesse** : Manque de retry logic et gestion d'erreurs complète

### Verdict
**V2 offre une architecture excellente** mais nécessite :
1. Audit sécurité complet et corrections
2. Suite de tests complète
3. Gestion des erreurs et retry logic robuste
4. Documentation opérationnelle complète

👉 **Voir :** [APP_V2_ANALYSIS_REPORT.md](APP_V2_ANALYSIS_REPORT.md) pour l'analyse détaillée.

### Pour Développeurs Intéressés
- Code situé dans : `./app_v2/`
- Contribution : Bienvenue mais DOIT passer audit sécurité avant production
- Recommandation : Commencer par étudier V1 pour comprendre la logique métier
