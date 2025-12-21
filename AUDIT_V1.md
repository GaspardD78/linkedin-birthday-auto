# Audit de l'État Actuel

## Bugs Connus
- [x] **Fuites mémoire (où exactement ?)**
  - **Source :** Les processus **Chromium/Playwright**.
  - **Analyse :** Le code dans `src/core/browser_manager.py` montre une lutte active contre la saturation mémoire (flags `--max-old-space-size=512`, `--renderer-process-limit=1`).
  - **Symptôme :** Des processus "zombies" de Chromium restent actifs et consomment de la RAM après la fin des scripts.
  - **Preuve :** L'existence nécessaire du script `scripts/cleanup_chromium_zombies.sh` pour tuer ces processus orphelins.
- [x] **Sélecteurs qui échouent (lesquels ?)**
  - **Points critiques :** Les boutons d'action (messagerie) et de connexion sur les profils.
  - **Analyse :** Le fichier `config/selectors.yaml` révèle une migration vers des sélecteurs "heuristiques" (basés sur des scores de visibilité/texte) plutôt que des sélecteurs CSS fixes, ce qui indique que les sélecteurs simples échouaient trop souvent.
  - **Détails :** Le système inclut une table `linkedin_selectors` pour tracker la validité des sélecteurs dynamiquement.

- [x] **Plantages aléatoires (dans quelle fonction ?)**
  - **Fonction :** Accès concurrent à la base de données (`sqlite3.OperationalError: database is locked`).
  - **Analyse :** `src/core/database.py` implémente un décorateur lourd `@retry_on_lock` et force le mode WAL (Write-Ahead Logging) pour mitiger les conflits entre le Worker (bot) et l'API (dashboard).
  - **Autre crash :** `BrowserInitError` dans `BrowserManager`, traité par un `SIGKILL` en dernier recours, signe de blocages sévères du moteur de rendu.

## Points Fonctionnels

- [x] **Le login fonctionne-t-il PARFOIS ?**
  - **Oui, via Cookies uniquement.**
  - **Conditions :** Le système ne fait pas de login "User/Password". Il repose sur l'injection de cookies via `auth_state.json`.
  - **Validité :** Fonctionne tant que le cookie `li_at` n'est pas expiré. `AuthManager` valide la session via un ping réseau léger sans lancer le navigateur complet.

- [x] **Y a-t-il des parties du code qui marchent bien ?**
  - **Base de Données :** Le module `database.py` est robuste (transactions imbriquées, thread-local storage, mode WAL).
  - **Rate Limiting :** Le `RateLimiter` avec "Circuit Breaker" protège efficacement le compte contre les bannissements en cas d'erreurs répétées.
  - **Architecture :** La séparation API/Worker est bien conçue pour les contraintes du Raspberry Pi 4.

## Données Critiques

### Schéma DB (`data/linkedin.db`)
*(Reconstruit d'après `src/core/database.py`)*
```sql
CREATE TABLE schema_version (version TEXT PRIMARY KEY, applied_at TEXT);
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    linkedin_url TEXT UNIQUE,
    last_message_date TEXT,
    message_count INTEGER DEFAULT 0,
    relationship_score REAL DEFAULT 0.0,
    notes TEXT,
    created_at TEXT, updated_at TEXT
);
CREATE TABLE birthday_messages (
    id INTEGER PRIMARY KEY,
    contact_id INTEGER,
    contact_name TEXT,
    message_text TEXT,
    sent_at TEXT,
    is_late BOOLEAN,
    days_late INTEGER,
    script_mode TEXT,
    FOREIGN KEY(contact_id) REFERENCES contacts(id)
);
```
 - Autres tables: profile_visits, errors, linkedin_selectors, scraped_profiles, campaigns, bot_executions...
Variables d'env essentielles
(Issues de .env.pi4.example)

API_KEY: Critique pour la sécurité API/Dashboard.

AUTH_ENCRYPTION_KEY: Clé Fernet pour chiffrer les cookies sur le disque.

JWT_SECRET: Pour les sessions dashboard.

DATABASE_URL: sqlite:///app/data/linkedin.db

Nombre de contacts dans la DB
Commande à exécuter :

```Bash
sqlite3 data/linkedin.db "SELECT COUNT(*) FROM contacts;"
```
## Logique Métier à Préserver
- [x] Algorithme de sélection des contacts (Voir src/bots/birthday_bot.py)

  - Récupération : Scan de la page anniversaires.

  - Priorisation : "Aujourd'hui" (traité si process_today: true).

  - Rattrapage : "En retard" (traité si days_late <= max_days_late (défaut 10) et process_late: true).

  - Anti-Doublon : Vérification de l'historique sur 2 ans (avoid_repetition_years).

- [x] Format des messages (Voir messages.txt et late_messages.txt)

  - Rotation aléatoire de templates message.txt pour les anniversaire du jour et late_messages.txt pour les retards. 

- [x] Règles de rate limiting (Voir config/config.yaml)

  -  Hebdo : 100 messages max.

  - Quotidien : 15 messages max.

  - Par exécution : 15 messages max.

  - Délais : 90 à 180 secondes entre messages.

  - Horaires : 07h00 - 19h00 (Paris).
