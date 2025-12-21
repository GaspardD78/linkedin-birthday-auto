# 📘 DOCUMENT MAÎTRE DU PROJET - LinkedIn Birthday Auto (RPi4)

**Version du document :** 1.0
**Date de génération :** 18 Décembre 2025
**Statut :** Référence Principale

Ce document consolide l'ensemble des informations techniques et fonctionnelles du projet. Il sert de source de vérité unique pour comprendre le contexte, les objectifs, l'architecture et l'implémentation du système.

---

## 1. 🌍 Contexte et Vue d'Ensemble

Le projet **LinkedIn Birthday Auto** est une solution d'automatisation complète conçue spécifiquement pour fonctionner de manière autonome sur un **Raspberry Pi 4**. Il permet de gérer les interactions LinkedIn (souhaits d'anniversaire, visites de profils, gestion des invitations) de façon intelligente, discrète et sécurisée.

Le système est conçu pour être "Set and Forget" : une fois installé, il gère son propre cycle de vie, ses mises à jour de sécurité (certificats SSL), ses sauvegardes (Google Drive) et sa résilience (redémarrage automatique en cas d'erreur).

### Points Clés du Contexte
*   **Cible Matérielle :** Raspberry Pi 4 (4GB RAM recommandés).
*   **Contraintes :** Ressources limitées (RAM, CPU, carte SD), nécessité d'éviter la surchauffe et l'usure prématurée.
*   **Philosophie :** "Discrétion et Sécurité". Le bot imite un comportement humain pour éviter la détection par LinkedIn.

---

## 2. 🎯 Objectifs

Les objectifs principaux du projet sont classés par ordre de priorité :

1.  **Automatisation du Networking :** Maintenir des relations actives en souhaitant les anniversaires (pro et perso) et en visitant des profils ciblés.
2.  **Autonomie Totale :** Minimiser l'intervention humaine après l'installation.
3.  **Sécurité et Confidentialité :**
    *   Pas de stockage de mots de passe en clair.
    *   Isolation des services via Docker.
    *   Communications chiffrées (HTTPS/SSL).
4.  **Optimisation RPi4 :**
    *   Gestion fine de la mémoire (limites strictes par conteneur).
    *   Utilisation de Docker images multi-arch (ARM64).
    *   Minimisation des écritures disques (Logs rotatifs, SQLite WAL).

---

## 3. ✨ Fonctionnalités

### 3.1 Bots d'Automatisation
*   **🎂 Birthday Bot :**
    *   Envoie des messages personnalisés pour les anniversaires de poste et de naissance.
    *   **Mode Standard :** Anniversaires du jour uniquement.
    *   **Mode Illimité (Rattrapage) :** Traite les anniversaires manqués des X derniers jours.
    *   Vérification des doublons pour ne jamais envoyer deux fois le même message.
*   **🔍 Visitor Bot :**
    *   Visite automatiquement des profils basés sur des recherches (Campagnes).
    *   Simule un comportement humain (délais aléatoires, scrolling).
    *   Objectif : Augmenter la visibilité ("Qui a consulté votre profil").
*   **🤝 Invitation Manager :**
    *   Accepte ou refuse automatiquement les demandes de connexion selon des critères (mots-clés, connexions communes).

### 3.2 Interface et Pilotage
*   **📊 Dashboard Next.js :** Interface web moderne pour visualiser les stats, les logs en temps réel et configurer les bots.
*   **📱 Responsive :** Accessible depuis mobile ou desktop.
*   **🔔 Notifications :** Alertes sur l'état du système (santé, erreurs critiques).

### 3.3 Infrastructure et Maintenance
*   **🛡️ Sécurité Automatisée :** Audit de sécurité au démarrage, HTTPS via Let's Encrypt (renouvellement auto).
*   **💾 Sauvegardes Cloud :** Backup quotidien chiffré vers Google Drive via `rclone`.
*   **⚙️ Installation Simplifiée :** Script `setup.sh` "tout-en-un" avec assistants interactifs.

---

## 4. 🏗️ Architecture Technique

Le projet repose sur une architecture micro-services orchestrée par **Docker Compose**.

### Schéma des Services
```
[Client Web / Mobile]
       │
       ▼ (HTTPS :443)
[ 🛡️ Nginx Reverse Proxy ] ───▶ Gère SSL, Rate Limiting, Compression
       │
       ├─────────────────────────┐
       ▼                         ▼
[ 🖥️ Dashboard (Next.js) ]    [ 🔌 API (FastAPI) ]
       │                         │
       │ (HTTP Interne)          │ (Socket Docker & Redis)
       └─────────────────────────┤
                                 ▼
                          [ 🧠 Redis (Queue) ]
                                 │
                                 ▼
                          [ 🤖 Worker (Python) ] ───▶ [ 🌐 LinkedIn ]
                                 │
                                 ▼
                          [ 🗄️ SQLite DB ]
```

### Composants
1.  **Nginx :** Point d'entrée unique sécurisé.
2.  **Dashboard :** Frontend React/Next.js (Port interne 3000).
3.  **API :** Backend Python FastAPI (Port interne 8000). Expose les endpoints de contrôle.
4.  **Redis :** File d'attente pour les tâches asynchrones (jobs RQ).
5.  **Worker :** Exécute les bots (Playwright) dans un environnement isolé.
6.  **SQLite :** Base de données légère, stockée sur le volume persistant `data/`.

---

## 5. 💻 Structure du Code

L'organisation du code source dans le dossier `src/` et `dashboard/` :

### Backend (`src/`)
*   **`api/`** : Code de l'API FastAPI.
    *   `routes/` : Définition des endpoints (bots, config, logs...).
    *   `app.py` : Point d'entrée de l'application API.
*   **`bots/`** : Logique métier des bots.
    *   `birthday_bot.py`, `visitor_bot.py`, `invitation_manager_bot.py`.
*   **`core/`** : Composants cœur partagés.
    *   `base_bot.py` : Classe mère gérant Selenium/Playwright, login, navigation.
    *   `database.py` : Gestionnaire de connexion SQLite (Singleton).
    *   `browser_manager.py` : Configuration de l'instance de navigateur (Playwright).
*   **`queue/`** : Gestion de la file d'attente.
    *   `worker.py` : Le processus qui consomme les tâches Redis.
*   **`utils/`** : Utilitaires (Dates, Logs, Chiffrement).

### Frontend (`dashboard/`)
*   **`app/`** : Pages Next.js (App Router).
*   **`components/`** : Composants React (UI shadcn, widgets).
*   **`lib/`** : Fonctions utilitaires et appels API (`api.ts`).

### Configuration (`config/`)
*   `config.yaml` : Configuration principale des bots (horaires, messages, limites).
*   `selectors.yaml` : Sélecteurs CSS pour le scraping (séparés du code pour maintenance facile).

---

## 6. 🗄️ Base de Données (BDD)

**Technologie :** SQLite 3 (Mode WAL)
**Fichier :** `data/linkedin.db`

### Principales Tables
*   **`contacts`** : Annuaire des profils détectés/traités.
*   **`birthday_messages`** : Historique des messages envoyés (pour éviter les doublons).
*   **`campaigns`** : Configuration des campagnes du Visitor Bot.
*   **`profile_visits`** : Historique des visites effectuées.
*   **`bot_executions`** : Logs techniques de chaque exécution (durée, succès/échec).
*   **`linkedin_selectors`** : Version dynamique des sélecteurs CSS.

---

## 7. 🔌 API et Routes

L'API est sécurisée par une clé d'API (`X-API-Key` ou Bearer Token).

### Groupes de Routes Principaux

#### 🤖 Contrôle des Bots (`/bot`)
*   `POST /bot/{name}/trigger` : Lancer un bot manuellement.
*   `POST /bot/{name}/stop` : Arrêter un bot en cours.
*   `GET /bot/{name}/status` : Obtenir l'état (running/idle) et la progression.
*   `GET /bot/list` : Lister tous les bots disponibles.

#### ⚙️ Configuration (`/config`)
*   `GET /config/yaml` : Lire la configuration actuelle.
*   `POST /config/yaml` : Mettre à jour la configuration.

#### 🗓️ Planificateur (`/scheduler`)
*   `GET /scheduler/jobs` : Voir les tâches planifiées (Cron).

#### 🔐 Authentification LinkedIn (`/auth`)
*   `POST /auth/upload` : Envoyer le fichier de cookies (`auth_state.json`).
*   `GET /auth/status` : Vérifier si la session est active/valide.

#### 🖥️ Système (`/system`)
*   `GET /system/health` : État de santé (CPU, RAM, Services).
*   `GET /system/logs` : Récupérer les logs filtrés.

---

## 8. 🛠️ Configuration et Déploiement

### Fichiers Clés
*   **`.env`** : Variables d'environnement (Secrets, Ports, API Keys). **Ne jamais commiter.**
*   **`docker-compose.yml`** : Définition des conteneurs pour la production.
*   **`setup.sh`** : Script maître d'installation.

### Flux de Déploiement (RPi4)
1.  Clonage du repo.
2.  Exécution de `./setup.sh`.
3.  Configuration interactive (HTTPS, Google Drive).
4.  Build des images Docker (optimisé multi-arch).
5.  Démarrage des conteneurs.
6.  Accès au Dashboard pour uploader les cookies LinkedIn et démarrer.

---
**Fin du Document Maître**
