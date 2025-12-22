# Documentation Maître du Projet (LinkedIn Automation V2)

Ce document sert de référence unique et complète pour le projet d'automatisation LinkedIn. Il couvre le contexte, l'architecture, les spécifications fonctionnelles, la base de données et l'API.

---

## 1. Contexte et Objectifs

### 1.1. Description
Ce projet est une solution d'automatisation pour LinkedIn conçue pour fonctionner de manière autonome sur un matériel à faibles ressources (Raspberry Pi 4). Il vise à gérer les interactions routinières (anniversaires), la prospection (visites de profils) et la maintenance du réseau (gestion des invitations).

### 1.2. Objectifs Principaux
1.  **Prospection (Priorité 1) :** Visiter des profils ciblés pour générer des notifications "Vu par" et encourager les visites en retour.
2.  **Réseautage (Priorité 2) :** Souhaiter les anniversaires quotidiennement pour maintenir le contact avec le réseau existant.
3.  **Discrétion ("Stealth") :** Mimétisme du comportement humain (délais aléatoires, navigation naturelle, scrolling) pour éviter la détection par LinkedIn.
4.  **Autonomie :** Fonctionnement 24/7 via Docker sur Raspberry Pi 4 avec une consommation minimale de ressources.

---

## 2. Architecture Technique

Le projet suit une architecture micro-services modernisée (V2).

### 2.1. Stack Technologique

| Composant | Technologie | Rôle |
| :--- | :--- | :--- |
| **Frontend** | Next.js 14 (App Router), React 18, Tailwind CSS, shadcn/ui | Interface utilisateur (Dashboard) pour le pilotage et le monitoring. |
| **Backend API** | Python 3.9+, FastAPI | Point d'entrée pour le Frontend, gestion de la configuration et des logs. |
| **Worker** | Python, RQ (Redis Queue), Playwright | Exécution des tâches lourdes d'automatisation (les bots). |
| **Base de Données** | SQLite (Mode WAL) | Stockage persistant léger (Contacts, Historique, Logs). |
| **Broker** | Redis | File d'attente pour les tâches asynchrones et communication temps réel (Statuts). |
| **Infrastructure** | Docker Compose | Orchestration des conteneurs (Optimisé ARM64/Pi4). |

### 2.2. Flux de Données
1.  **Commande Utilisateur :** L'utilisateur clique sur "Démarrer Bot" dans le Dashboard.
2.  **API Next.js :** Le frontend appelle son API locale (`/api/bot/action`), qui proxy la requête vers le Backend Python.
3.  **Backend Python :** FastAPI reçoit la requête, vérifie la clé API, et enfile un job dans Redis via `rq`.
4.  **Worker :** Le processus Worker dépile le job et lance le script Playwright correspondant (ex: `VisitorBot`).
5.  **Exécution :** Le bot interagit avec LinkedIn (Chrome Headless), met à jour SQLite, et envoie des logs en temps réel.
6.  **Feedback :** Le Dashboard reçoit les logs et le statut via Server-Sent Events (SSE).

---

## 3. Spécifications Fonctionnelles (Les Bots)

### 3.1. Birthday Bot (`BirthdayBot`)
*   **But :** Envoyer des messages d'anniversaire personnalisés.
*   **Fonctionnement :**
    *   Scrape la page des notifications d'anniversaire.
    *   Parse les dates (supporte "Aujourd'hui", "Hier", "Il y a 2 jours" en FR/EN).
    *   Vérifie si le contact a déjà été contacté cette année.
    *   Envoie un message aléatoire parmi une liste (`messages.txt`).
*   **Variante "Unlimited" :** Capable de rattraper les anniversaires manqués (jusqu'à 4 jours en arrière) et ignore les quotas stricts du mode standard.

### 3.2. Visitor Bot (`VisitorBot`)
*   **But :** Générer du trafic entrant en visitant des profils cibles.
*   **Fonctionnement :**
    *   Effectue une recherche LinkedIn basée sur des mots-clés et une localisation.
    *   Visite chaque profil trouvé.
    *   Scrolle pour simuler une lecture humaine.
    *   Extraits les données publiques (Titre, Entreprise, Expérience, Skills).
    *   Calcule un `fit_score` (Score de pertinence) basé sur les mots-clés trouvés dans le profil.
    *   Sauvegarde le profil dans la table `scraped_profiles`.

### 3.3. Invitation Manager (`InvitationManagerBot`)
*   **But :** Garder le compte sain en supprimant les vieilles invitations.
*   **Fonctionnement :**
    *   Liste les invitations envoyées en attente.
    *   Retire celles qui sont plus vieilles qu'un seuil configuré (ex: 1 mois).

---

## 4. Modèle de Données (SQLite)

Le fichier `src/core/database.py` définit le schéma. Voici les tables principales :

### 4.1. Tables Principales
*   **`contacts`** : Répertoire des personnes contactées.
    *   `id`, `name`, `linkedin_url`, `last_message_date`.
*   **`birthday_messages`** : Historique des vœux envoyés.
    *   `contact_name`, `message_text`, `sent_at`, `is_late` (bool).
*   **`profile_visits`** : Historique des visites effectuées.
    *   `profile_name`, `profile_url`, `visited_at`, `success` (bool).
*   **`scraped_profiles`** : Données riches extraites par le Visitor Bot.
    *   `full_name`, `headline`, `summary`, `skills` (JSON), `fit_score`, `campaign_id`.
*   **`campaigns`** : Configuration des campagnes de visite.
    *   `name`, `search_url`, `filters` (JSON), `status`.
*   **`notification_logs`** : Historique des alertes (ex: Cookie expiré).
*   **`errors`** : Logs d'erreurs avec capture d'écran optionnelle.

---

## 5. API & Communication

### 5.1. API Python (FastAPI - Port 8000)
L'API Backend expose les routes suivantes (sécurisées par `X-API-Key`) :

*   **Auth :**
    *   `POST /api/auth/login` : Login dashboard.
    *   `GET /api/auth/status` : État de la session LinkedIn (Cookie).
*   **Contrôle Bots :**
    *   `POST /api/bot/start` : Lancer un bot (`birthday`, `visitor`, etc.).
    *   `POST /api/bot/stop` : Arrêter un bot.
    *   `GET /api/bot/status` : Statut du worker (Redis).
*   **Configuration :**
    *   `GET/POST /config/yaml` : Lire/Écrire `config.yaml`.
*   **Données :**
    *   `GET /api/logs` : Lire les logs en temps réel.
    *   `GET /api/campaigns` : Gestion des campagnes.
    *   `GET /api/stats` : Statistiques globales.

### 5.2. API Next.js (BFF - Port 3000)
Le Dashboard agit comme un proxy (Backend-for-Frontend) :
*   Route `dashboard/app/api/bot/[action]/route.ts` -> Appelle `Python API`.
*   Route `dashboard/app/api/logs/route.ts` -> Appelle `Python API`.

---

## 6. Structure du Code

```text
/
├── config/                 # Fichiers de configuration (YAML, selecteurs)
├── dashboard/              # Code source Frontend (Next.js)
│   ├── app/                # Pages et Routes API (App Router)
│   ├── components/         # Composants React (UI)
│   └── lib/                # Utilitaires et Hooks
├── data/                   # Volume persistant (BDD, Backups)
├── logs/                   # Fichiers de logs
├── scripts/                # Scripts Shell de maintenance/installation
├── src/                    # Code source Backend (Python)
│   ├── api/                # Application FastAPI (Routes, Security)
│   ├── bots/               # Logique métier des Bots (Playwright)
│   ├── core/               # Noyau (Database, BrowserManager)
│   ├── queue/              # Gestion des tâches (Worker, Redis)
│   └── utils/              # Outils (DateParser, Logger)
├── docker-compose.yml      # Orchestration Docker
└── setup.sh                # Script d'installation principal
```

## 7. Déploiement & Sécurité

*   **Plateforme :** Raspberry Pi 4 (ARM64).
*   **Installation :** Via `./setup.sh` (gère Docker, Permissions, Alias).
*   **Sécurité :**
    *   Authentification Dashboard par JWT.
    *   Authentification API par Clé API (générée au premier lancement).
    *   Fichiers sensibles (`.env`, `auth_state.json`) protégés (chmod 600).
    *   Mots de passe hachés (Bcrypt).
