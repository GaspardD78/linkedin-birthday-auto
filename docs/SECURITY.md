# 🛡️ POLITIQUE DE SÉCURITÉ ET HARDENING

**Version:** 3.3 (2025-01-20)
**Statut:** Production (RPi4 Optimized)

Ce document détaille les mécanismes de sécurité mis en œuvre pour protéger le système d'automatisation LinkedIn, particulièrement dans un contexte d'auto-hébergement sur Raspberry Pi 4.

---

## 1. Sécurité Applicative

### 1.1 Authentification API
L'API REST (`FastAPI`) est protégée par une clé API unique (`API_KEY`) stockée dans une variable d'environnement.
*   **Génération :** Automatique et cryptographiquement sûre (32 bytes hex) via `setup.sh` si absente.
*   **Validation :** Utilisation de `secrets.compare_digest` pour prévenir les attaques temporelles ("Timing Attacks").
*   **Interdiction :** La clé par défaut (`internal_secret_key`) est explicitement rejetée par `main.py` et `security.py`.

### 1.2 Rate Limiting (Anti-Brute Force)
Implémenté à deux niveaux :
1.  **Niveau Nginx (Infrastructure) :**
    *   **Login Dashboard :** 5 requêtes par minute (burst 5) pour `/api/auth/*`.
    *   **API Générale :** 60 requêtes par minute pour `/api/*`.
    *   **Global :** 10 requêtes par seconde par IP.
2.  **Niveau Python (Application) :**
    *   Le module `security.py` implémente un rate limiter en mémoire pour valider les clés API (max 10 échecs par IP / 15 minutes).

### 1.3 Gestion des Secrets
*   Aucun mot de passe ou clé API n'est stocké en clair dans le code.
*   Le fichier `.env` est exclu du contrôle de version (`.gitignore`).
*   Les permissions sur `.env`, `auth_state.json` et les clés SSL sont restreintes (`600` ou `400`).

---

## 2. Sécurité Infrastructure (Docker & OS)

### 2.1 Utilisateurs Non-Privilégiés (V3.3 UPDATE)
*   **API Sécurisée :** Le conteneur API ne tourne plus en mode `privileged`. Il utilise la socket Docker (`/var/run/docker.sock`) montée avec des droits restreints pour gérer les redémarrages de conteneurs, au lieu d'accéder au système hôte complet via `systemctl`.
*   Les conteneurs `api` et `bot-worker` s'exécutent avec l'utilisateur `appuser` (UID 1000), aligné sur l'utilisateur par défaut du Raspberry Pi.
*   Le conteneur `dashboard` (Next.js) s'exécute avec l'utilisateur `node` (UID 1000).
*   **Bénéfice :** En cas de compromission d'un conteneur, l'attaquant n'a pas les droits root sur l'hôte.

### 2.2 Isolation Réseau
*   Un réseau Docker dédié `linkedin-network` (bridge) isole les conteneurs.
*   **DNS Sécurisé :** Les conteneurs utilisent explicitement les DNS Cloudflare (1.1.1.1) et Google (8.8.8.8) pour éviter les détournements DNS ou les pannes de résolveurs FAI.
*   Seuls les ports nécessaires sont exposés :
    *   `80/443` (Nginx) : Public (ou LAN)
    *   `3000` (Dashboard) : Interne (exposé localement pour debug, proxifié par Nginx)
    *   `8000` (API) : Interne (proxifié par Nginx)
    *   `6379` (Redis) : Non exposé sur l'hôte.

### 2.3 Hardening Nginx
Le fichier `deployment/nginx/linkedin-bot.conf` applique les headers de sécurité recommandés par l'OWASP :
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

---

## 3. Sécurité des Données (Privacy)

### 3.1 Base de Données
*   SQLite avec mode WAL pour la robustesse.
*   Fichier `linkedin.db` stocké dans un volume Docker monté, avec permissions strictes.
*   Aucun accès externe direct à la base de données.

### 3.2 Cookies LinkedIn
*   Le fichier `auth_state.json` (contenant les cookies de session) est la donnée la plus sensible.
*   Il est protégé en lecture/écriture (`0600`) et accessible uniquement par le bot.
*   Le script de vérification (`check_login_status`) s'assure que la session est valide sans exposer les cookies dans les logs.

---

## 4. Maintenance & Mises à Jour

*   **Audit Régulier :** Le script `setup.sh` effectue des vérifications de sécurité à chaque exécution (permissions, présence de swap, etc.).
*   **Scan de Vulnérabilités :** Recommandé d'utiliser `docker scan` ou `trivy` sur les images avant déploiement en production critique.

---

**Contact Sécurité :** En cas de découverte de vulnérabilité, merci d'ouvrir une Issue privée sur le dépôt GitHub.
