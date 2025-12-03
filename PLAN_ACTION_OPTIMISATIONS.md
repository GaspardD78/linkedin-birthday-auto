# 📋 Plan d'Action : Optimisations et Corrections

**Date** : 2 Décembre 2025
**Projet** : LinkedIn Birthday Auto Bot
**Branche de travail** : `claude/project-audit-review-01Qyoquc67G2XBDoEJ4DFR8W`

---

## 🎯 Vue d'Ensemble

Ce document contient des **prompts prêts à l'emploi** pour implémenter les optimisations et corrections restantes identifiées dans l'audit. Chaque tâche est un "ticket" indépendant avec :

- ✅ Contexte complet
- ✅ Prompt détaillé pour IA
- ✅ Tests de validation
- ✅ Précautions pour ne pas casser l'existant

---

## 📊 Progression

| Phase | Tâches | Statut | Effort |
|-------|--------|--------|--------|
| 🔴 Critiques | 4/4 | ✅ Complété | 1-2h |
| 🟡 Importants | 0/6 | ⏳ À faire | 2-3h |
| 🟢 Mineurs | 5/5 | ✅ Complété | 30min |
| **TOTAL** | **9/15** | **60%** | **4-6h** |

---

## 🟡 PHASE 2 : PROBLÈMES IMPORTANTS (2-3h)

---

### ✅ TICKET #5 : Améliorer Gestion des Exceptions (1h)

**Priorité** : 🟡 Importante
**Effort** : 1 heure
**Risque** : Faible (amélioration logging, pas de changement logique)

#### 📋 Contexte

Le projet utilise 111 fois `except Exception` avec logging incomplet. Les stack traces sont souvent perdues, rendant le debug difficile.

**Exemples actuels problématiques** :
```python
# src/queue/tasks.py:62-64
except Exception as e:
    logger.error("task_failed", error=str(e))  # ⚠️ Pas de stack trace
    return {"success": False, "error": str(e), "bot_type": "visitor"}
```

#### 🎯 Objectif

Améliorer le logging des exceptions pour faciliter le debug sans changer la logique métier.

#### 📝 PROMPT POUR IA

```
TÂCHE : Améliorer la gestion des exceptions dans le projet LinkedIn Birthday Auto Bot

CONTEXTE :
- Le projet est un bot LinkedIn en Python utilisant structlog pour les logs
- Il y a 111 occurrences de "except Exception" avec logging incomplet
- Les stack traces sont souvent perdues, rendant le debug difficile en production

OBJECTIF :
Améliorer le logging des exceptions SANS changer la logique métier ni le comportement du code.

INSTRUCTIONS :

1. Identifier tous les blocs "except Exception" dans le répertoire src/
   Commande pour lister : grep -rn "except Exception" src/ --include="*.py"

2. Pour chaque occurrence, appliquer cette amélioration :

   AVANT :
   ```python
   except Exception as e:
       logger.error("error_message", error=str(e))
       raise e  # ou return
   ```

   APRÈS :
   ```python
   except Exception as e:
       logger.error("error_message", error=str(e), exc_info=True)
       raise  # Sans argument pour préserver stack trace
   ```

3. Règles spécifiques :
   - Toujours ajouter exc_info=True au logger.error()
   - Remplacer "raise e" par "raise" (sans argument)
   - Si le code fait "return" après le log, garder le return tel quel
   - NE PAS modifier la logique if/else dans les try/except
   - NE PAS ajouter de nouveaux imports

4. Fichiers à modifier en priorité :
   - src/queue/tasks.py
   - src/core/base_bot.py
   - src/bots/*.py
   - src/api/*.py

5. Exceptions à NE PAS modifier :
   - Les except qui capturent des exceptions spécifiques (TimeoutError, etc.)
   - Les except dans les tests (tests/)
   - Les except qui font "pass" intentionnellement pour ignorer

VALIDATION :

Après modifications, exécuter ces tests :

```bash
# 1. Vérifier syntaxe Python
python -m py_compile src/queue/tasks.py
python -m py_compile src/core/base_bot.py

# 2. Lancer tests unitaires
pytest tests/ -v

# 3. Vérifier qu'aucune régression
git diff src/ | grep -E "^-.*except|^-.*raise"
# → Vérifier qu'aucune logique métier n'a changé

# 4. Test fonctionnel : déclencher une erreur volontaire
# Vérifier que la stack trace complète apparaît dans les logs
```

LIVRABLES :
- Liste des fichiers modifiés avec nombre d'occurrences corrigées
- Exemple de stack trace avant/après dans les logs
- Confirmation que les tests passent

IMPORTANT :
- Ne modifier QUE le logging, pas la logique
- Conserver tous les "return" et "raise" existants
- Ne pas ajouter de nouveaux blocs try/except
```

---

### ✅ TICKET #6 : Implémenter Limite Profils VisitorBot (30min)

**Priorité** : 🟡 Importante
**Effort** : 30 minutes
**Risque** : Moyen (modification comportement bot)

#### 📋 Contexte

Actuellement, le paramètre `limit` dans `run_profile_visit_task()` est accepté mais non utilisé. Le bot utilise toujours la valeur de `config.yaml`.

**Code actuel** :
```python
# src/queue/tasks.py:51-56
if limit != 10:
    logger.warning(
        f"limit parameter ({limit}) is accepted but not yet implemented in VisitorBot"
    )
```

#### 🎯 Objectif

Honorer le paramètre `limit` pour permettre des exécutions ponctuelles avec limites différentes.

#### 📝 PROMPT POUR IA

```
TÂCHE : Implémenter le paramètre limit dans VisitorBot

CONTEXTE :
- Fichier : src/bots/visitor_bot.py (VisitorBot class)
- Fichier : src/queue/tasks.py (run_profile_visit_task function)
- Actuellement : paramètre accepté mais non utilisé, bot utilise toujours config.yaml

OBJECTIF :
Permettre d'override la limite de profils via paramètre fonction, sans modifier config.yaml.

INSTRUCTIONS :

1. Lire les fichiers suivants pour comprendre l'architecture :
   - src/bots/visitor_bot.py (classe VisitorBot)
   - src/queue/tasks.py (fonction run_profile_visit_task)
   - src/core/base_bot.py (classe parente BaseLinkedInBot)

2. Modifier le constructeur VisitorBot :

   DANS : src/bots/visitor_bot.py

   AVANT :
   ```python
   class VisitorBot(BaseLinkedInBot):
       def __init__(self, config):
           super().__init__(config)
           # ...
   ```

   APRÈS :
   ```python
   class VisitorBot(BaseLinkedInBot):
       def __init__(self, config, profiles_limit_override: Optional[int] = None):
           super().__init__(config)
           # Override la limite si spécifié, sinon utilise config
           self.profiles_limit = (
               profiles_limit_override
               if profiles_limit_override is not None
               else config.visitor.limits.profiles_per_run
           )
           # ...
   ```

3. Utiliser self.profiles_limit dans la logique du bot :

   Chercher dans visitor_bot.py où config.visitor.limits.profiles_per_run est utilisé
   Remplacer par self.profiles_limit

4. Modifier run_profile_visit_task() :

   DANS : src/queue/tasks.py:58-60

   AVANT :
   ```python
   with VisitorBot(config=config) as bot:
       return bot.run()
   ```

   APRÈS :
   ```python
   with VisitorBot(config=config, profiles_limit_override=limit) as bot:
       return bot.run()
   ```

5. Supprimer le warning obsolète :

   DANS : src/queue/tasks.py:51-56

   SUPPRIMER :
   ```python
   if limit != 10:
       logger.warning(
           f"limit parameter ({limit}) is accepted but not yet implemented in VisitorBot"
       )
   ```

   REMPLACER PAR :
   ```python
   if limit != config.visitor.limits.profiles_per_run:
       logger.info(
           f"Overriding profiles limit: {config.visitor.limits.profiles_per_run} → {limit}"
       )
   ```

VALIDATION :

```bash
# 1. Vérifier syntaxe
python -m py_compile src/bots/visitor_bot.py
python -m py_compile src/queue/tasks.py

# 2. Test dry-run avec limite custom
curl -X POST http://localhost:8000/start-visitor-bot \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true, "limit": 5}'

# 3. Vérifier dans les logs :
# → "Overriding profiles limit: 15 → 5"
# → Bot traite bien 5 profils maximum, pas 15

# 4. Test avec limite par défaut (doit utiliser config)
curl -X POST http://localhost:8000/start-visitor-bot \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
# → Bot utilise config.visitor.limits.profiles_per_run
```

LIVRABLES :
- Code modifié dans visitor_bot.py et tasks.py
- Preuve que le paramètre limite fonctionne (logs ou test)

PRÉCAUTIONS :
- NE PAS modifier config.yaml
- Conserver backward compatibility (limit=None → utilise config)
- Logger clairement quand override est actif
```

---

### ✅ TICKET #7 : Nettoyer Cookies Expirés Automatiquement (30min)

**Priorité** : 🟡 Importante
**Effort** : 30 minutes
**Risque** : Moyen (manipulation cookies LinkedIn)

#### 📋 Contexte

Le fichier `src/core/auth_manager.py` contient 5 commentaires "BUGFIX: Nettoyer les cookies expirés", indiquant un problème récurrent. Les cookies expirés s'accumulent dans `auth_state.json`, causant potentiellement des échecs de login.

#### 🎯 Objectif

Nettoyer automatiquement les cookies expirés à chaque chargement de `auth_state`.

#### 📝 PROMPT POUR IA

```
TÂCHE : Nettoyer automatiquement les cookies expirés dans AuthManager

CONTEXTE :
- Fichier : src/core/auth_manager.py
- Problème : Cookies expirés s'accumulent dans auth_state.json
- Impact : Fichier grossit, login peut échouer
- Indices : 5 occurrences du commentaire "BUGFIX: Nettoyer les cookies expirés"

OBJECTIF :
Implémenter nettoyage automatique et systématique des cookies expirés.

INSTRUCTIONS :

1. Lire src/core/auth_manager.py pour comprendre l'architecture :
   - Comment auth_state est chargé (load_auth_state)
   - Comment cookies sont stockés (structure JSON)
   - Où sont les tentatives actuelles de nettoyage

2. Identifier la méthode _remove_expired_cookies existante :

   Chercher dans auth_manager.py :
   ```python
   grep -n "_remove_expired_cookies\|clean.*cookie" src/core/auth_manager.py
   ```

   Si elle existe : l'utiliser
   Si elle n'existe pas : la créer

3. Créer ou améliorer _remove_expired_cookies() :

   AJOUTER dans la classe AuthManager :

   ```python
   def _remove_expired_cookies(self, cookies: list) -> list:
       """
       Retire les cookies expirés.

       Args:
           cookies: Liste de cookies (format Playwright)

       Returns:
           Liste nettoyée (uniquement cookies valides)
       """
       import time

       if not cookies:
           return []

       now = time.time()
       cleaned = []

       for cookie in cookies:
           # Cookie sans expiration = session cookie (garder)
           if "expires" not in cookie:
               cleaned.append(cookie)
               continue

           # Vérifier expiration
           expires = cookie.get("expires", float('inf'))
           if expires > now:
               cleaned.append(cookie)

       removed = len(cookies) - len(cleaned)
       if removed > 0:
           logger.info(f"Removed {removed} expired cookies")

       return cleaned
   ```

4. Appeler systématiquement lors du chargement :

   DANS : méthode load_auth_state() ou _load_from_file_or_env()

   APRÈS avoir chargé auth_state, AVANT de l'utiliser :

   ```python
   def load_auth_state(self) -> bool:
       """Charge l'état d'authentification."""
       try:
           auth_state = self._load_from_file_or_env()

           if auth_state and "cookies" in auth_state:
               # ✅ Nettoyer AVANT de charger dans le navigateur
               original_count = len(auth_state["cookies"])
               auth_state["cookies"] = self._remove_expired_cookies(auth_state["cookies"])

               # Sauvegarder version nettoyée (évite accumulation)
               if len(auth_state["cookies"]) < original_count:
                   self._save_auth_state_to_file(auth_state)
                   logger.info("Saved cleaned auth_state (removed expired cookies)")

           # Continuer avec le reste de la logique existante...
           return True

       except Exception as e:
           logger.error(f"Failed to load auth state: {e}", exc_info=True)
           return False
   ```

5. Nettoyer aussi lors de la sauvegarde :

   DANS : méthode save_auth_state() ou _save_auth_state_to_file()

   AVANT de sauvegarder :

   ```python
   def save_auth_state(self, context) -> bool:
       """Sauvegarde l'état d'authentification."""
       try:
           # Récupérer cookies
           cookies = await context.cookies()

           # ✅ Nettoyer avant de sauvegarder
           cookies = self._remove_expired_cookies(cookies)

           auth_state = {
               "cookies": cookies,
               "storage_state": await context.storage_state()
           }

           # Sauvegarder...
           return True
       except Exception as e:
           logger.error(f"Failed to save auth state: {e}", exc_info=True)
           return False
   ```

6. Supprimer les anciens commentaires BUGFIX obsolètes :

   Chercher et supprimer :
   ```bash
   grep -n "BUGFIX.*cookie" src/core/auth_manager.py
   ```

   Remplacer par commentaires clairs expliquant le nettoyage automatique.

VALIDATION :

```bash
# 1. Créer auth_state.json avec cookies expirés pour test
cat > /tmp/test_auth_state.json <<'EOF'
{
  "cookies": [
    {"name": "valid", "value": "test", "expires": 9999999999},
    {"name": "expired", "value": "old", "expires": 1000000000}
  ]
}
EOF

# 2. Test unitaire Python
python3 <<'PYTEST'
import sys
sys.path.insert(0, '/home/user/linkedin-birthday-auto')
from src.core.auth_manager import AuthManager

# Simuler chargement
auth_state = {
    "cookies": [
        {"name": "valid", "expires": 9999999999},
        {"name": "expired", "expires": 1000000000},
        {"name": "session", "value": "no_expiry"}
    ]
}

manager = AuthManager(config=None)
cleaned = manager._remove_expired_cookies(auth_state["cookies"])

print(f"Avant: {len(auth_state['cookies'])} cookies")
print(f"Après: {len(cleaned)} cookies")
assert len(cleaned) == 2, "Devrait garder 2 cookies (valid + session)"
print("✅ Test passed")
PYTEST

# 3. Vérifier dans les logs du bot
# → "Removed N expired cookies" doit apparaître
docker compose logs bot-worker | grep -i "expired.*cookie"
```

LIVRABLES :
- Code modifié dans auth_manager.py
- Test prouvant que nettoyage fonctionne
- Confirmation que login fonctionne toujours

PRÉCAUTIONS :
- NE PAS supprimer les cookies session (sans expires)
- NE PAS modifier la structure auth_state
- Tester avec vrai auth_state LinkedIn (dry-run)
- Logger clairement le nettoyage pour debug
```

---

### ✅ TICKET #8 : Améliorer Parsing Logs Frontend (20min)

**Priorité** : 🟡 Importante
**Effort** : 20 minutes
**Risque** : Faible (amélioration affichage, pas critique)

#### 📋 Contexte

Le dashboard parse les logs avec string splitting fragile. Si le format change, l'affichage casse.

**Code actuel** :
```typescript
// dashboard/lib/api.ts:164-179
const parts = line.split(' - ');  // ⚠️ Fragile
```

Le backend produit déjà du JSON (structlog avec `JSONRenderer` activé).

#### 📝 PROMPT POUR IA

```
TÂCHE : Améliorer le parsing des logs dans le dashboard Next.js

CONTEXTE :
- Fichier : dashboard/lib/api.ts (fonction getLogs)
- Backend : src/utils/logging.py (utilise structlog avec JSONRenderer)
- Problème : Parsing manuel fragile (string splitting)
- Backend produit DÉJÀ du JSON dans les fichiers logs

OBJECTIF :
Parser les logs JSON du backend au lieu de string splitting manuel.

INSTRUCTIONS :

1. Lire le fichier dashboard/lib/api.ts :
   - Trouver la fonction getLogs (ligne ~159)
   - Comprendre le format actuel de parsing

2. Vérifier le format logs backend :

   ```bash
   # Vérifier qu'un log contient bien du JSON
   docker compose logs bot-worker | head -5
   # OU
   cat logs/linkedin_bot.log | head -5

   # Exemple attendu :
   # {"timestamp": "2025-12-02T10:00:00", "level": "INFO", "event": "bot_started", ...}
   ```

3. Modifier la fonction getLogs dans dashboard/lib/api.ts :

   AVANT (ligne ~164-179) :
   ```typescript
   return data.logs.map((line: string) => {
       let timestamp = new Date().toISOString().split('T')[1].split('.')[0];
       let level = 'INFO';
       let message = line;
       try {
         const parts = line.split(' - ');  // ⚠️ Fragile
         // ...
       } catch(e) {}
       return { timestamp, level, message };
   });
   ```

   APRÈS :
   ```typescript
   return data.logs.map((line: string) => {
       try {
           // Tenter de parser JSON (format structlog)
           const parsed = JSON.parse(line);

           return {
               timestamp: parsed.timestamp || parsed.event_time || new Date().toISOString(),
               level: (parsed.level || parsed.log_level || 'INFO').toUpperCase(),
               message: parsed.event || parsed.message || parsed.msg || line
           };
       } catch (e) {
           // Fallback si le log n'est pas JSON (compatibilité)
           // Garder le parsing simple pour anciens logs
           const timestampMatch = line.match(/(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})/);
           const levelMatch = line.match(/\b(DEBUG|INFO|WARNING|ERROR|CRITICAL)\b/i);

           return {
               timestamp: timestampMatch ? timestampMatch[1] : new Date().toISOString(),
               level: levelMatch ? levelMatch[1].toUpperCase() : 'INFO',
               message: line
           };
       }
   });
   ```

4. Tester la robustesse avec différents formats :

   Exemples de logs à supporter :
   ```json
   {"timestamp": "2025-12-02T10:00:00", "level": "INFO", "event": "bot_started"}
   {"event_time": "2025-12-02T10:00:00", "log_level": "ERROR", "message": "Failed"}
   Plain text log line without JSON
   2025-12-02 10:00:00 - INFO - Old format log
   ```

5. Ajouter types TypeScript pour clarté :

   AJOUTER en haut de api.ts :
   ```typescript
   interface StructlogEntry {
       timestamp?: string;
       event_time?: string;
       level?: string;
       log_level?: string;
       event?: string;
       message?: string;
       msg?: string;
   }
   ```

VALIDATION :

```bash
# 1. Build dashboard
cd dashboard
npm run build
# → Pas d'erreurs TypeScript

# 2. Lancer dashboard en dev
npm run dev

# 3. Ouvrir dashboard dans navigateur
# → Aller sur page Logs
# → Vérifier que logs s'affichent correctement

# 4. Tester avec différents formats logs
# Créer logs de test :
cat >> logs/test.log <<'EOF'
{"timestamp": "2025-12-02T10:00:00", "level": "INFO", "event": "test JSON log"}
Plain text log without JSON
2025-12-02 10:05:00 - ERROR - Old format error
EOF

# → Recharger dashboard, vérifier que les 3 formats s'affichent
```

LIVRABLES :
- Code modifié dans dashboard/lib/api.ts
- Screenshot ou vidéo du dashboard affichant logs correctement
- Preuve que formats JSON et texte sont supportés

PRÉCAUTIONS :
- Garder fallback pour anciens logs non-JSON
- Ne pas casser l'affichage actuel
- Tester avec vrais logs de production
- Types TypeScript doivent passer (npm run build)
```

---

### ✅ TICKET #9 : Refactoring Auth 2FA Session Management (1h) [OPTIONNEL]

**Priorité** : 🟡 Importante (mais optionnel)
**Effort** : 1 heure
**Risque** : Élevé (touche auth critique)

#### 📋 Contexte

Le fichier `src/api/auth_routes.py` contient une session 2FA gérée par un dictionnaire global avec multiples BUGFIX comments. Risque de memory leaks Playwright.

#### 🎯 Objectif

Implémenter cleanup automatique des sessions expirées et context manager pour Playwright.

#### 📝 PROMPT POUR IA

```
TÂCHE : Améliorer la gestion des sessions 2FA dans auth_routes.py

CONTEXTE :
- Fichier : src/api/auth_routes.py
- Problème : Session 2FA globale, risque memory leak Playwright
- Multiples BUGFIX comments indiquent fragilité
- Session timeout non automatique

OBJECTIF :
Implémenter cleanup automatique et améliorer isolation ressources.

⚠️  ATTENTION : Cette tâche est OPTIONNELLE et touche du code critique (authentification).
Ne l'implémenter que si vous êtes confiant et avez du temps pour tests approfondis.

INSTRUCTIONS :

1. Lire src/api/auth_routes.py complètement :
   - Comprendre le flow 2FA complet
   - Identifier où auth_2fa_session est utilisé
   - Noter tous les BUGFIX comments

2. Ajouter timeout automatique de session :

   AJOUTER fonction de nettoyage :
   ```python
   import time
   from datetime import datetime, timedelta

   SESSION_TIMEOUT = 300  # 5 minutes

   def cleanup_expired_session():
       """Nettoie les sessions 2FA expirées automatiquement."""
       if not auth_2fa_session.get("created_at"):
           return

       age = time.time() - auth_2fa_session["created_at"]
       if age > SESSION_TIMEOUT:
           logger.warning(
               f"Cleaning up expired 2FA session (age: {age:.0f}s, timeout: {SESSION_TIMEOUT}s)"
           )
           cleanup_2fa_session()
   ```

   APPELER avant chaque endpoint :
   ```python
   @router.post("/2fa")
   async def handle_2fa(...):
       cleanup_expired_session()  # ✅ Cleanup auto
       # ... reste du code
   ```

3. Améliorer cleanup_2fa_session() existant :

   VÉRIFIER que la fonction ferme bien Playwright :
   ```python
   def cleanup_2fa_session():
       """Nettoie la session 2FA et libère les ressources."""
       try:
           # Fermer Playwright proprement
           if auth_2fa_session.get("playwright"):
               playwright = auth_2fa_session["playwright"]
               if hasattr(playwright, 'stop'):
                   asyncio.create_task(playwright.stop())

           # Reset session
           auth_2fa_session["playwright"] = None
           auth_2fa_session["browser"] = None
           auth_2fa_session["page"] = None
           auth_2fa_session["retry_count"] = 0
           auth_2fa_session["created_at"] = None

           logger.info("2FA session cleaned up successfully")
       except Exception as e:
           logger.error(f"Error cleaning up 2FA session: {e}", exc_info=True)
   ```

4. Ajouter monitoring santé session :

   NOUVEAU endpoint pour debug :
   ```python
   @router.get("/2fa/status")
   async def get_2fa_session_status():
       """Retourne l'état de la session 2FA (debug)."""
       if not auth_2fa_session.get("created_at"):
           return {"active": False}

       age = time.time() - auth_2fa_session["created_at"]
       return {
           "active": True,
           "age_seconds": age,
           "retry_count": auth_2fa_session["retry_count"],
           "expires_in": max(0, SESSION_TIMEOUT - age)
       }
   ```

5. [BONUS] Context manager pour Playwright :

   Si temps et confiance, refactorer pour utiliser context manager :
   ```python
   from contextlib import asynccontextmanager

   @asynccontextmanager
   async def playwright_2fa_session(timeout: int = 300):
       """Context manager pour session 2FA avec cleanup auto."""
       playwright = None
       browser = None
       try:
           playwright = await async_playwright().start()
           browser = await playwright.chromium.launch(headless=True)
           context = await browser.new_context()
           page = await context.new_page()

           yield (playwright, browser, context, page)
       finally:
           if browser:
               await browser.close()
           if playwright:
               await playwright.stop()
           logger.info("Playwright 2FA session closed")
   ```

VALIDATION :

⚠️  TESTS CRITIQUES - NE PAS SKIP

```bash
# 1. Test timeout automatique
# Créer session 2FA, attendre 6 minutes, vérifier cleanup auto
curl -X POST http://localhost:8000/auth/start-2fa \
  -H "X-API-Key: YOUR_KEY"

# Attendre 360 secondes
sleep 360

# Vérifier status
curl http://localhost:8000/auth/2fa/status
# → Devrait retourner {"active": false}

# 2. Test memory leak
# Créer 10 sessions successives, vérifier RAM stable
for i in {1..10}; do
  curl -X POST http://localhost:8000/auth/start-2fa -H "X-API-Key: KEY"
  sleep 1
  curl -X POST http://localhost:8000/auth/cleanup-2fa -H "X-API-Key: KEY"
done

# Monitorer RAM container :
docker stats bot-api --no-stream
# → RAM ne doit pas augmenter significativement

# 3. Test fonctionnel complet 2FA
# Via dashboard : Upload auth_state.json
# → Vérifier que login 2FA fonctionne toujours
```

LIVRABLES :
- Code modifié dans auth_routes.py
- Preuve que timeout automatique fonctionne
- Preuve qu'aucun memory leak (RAM stable après 10 sessions)
- Confirmation que 2FA fonctionne toujours

PRÉCAUTIONS :
⚠️  CODE CRITIQUE - TESTER EXHAUSTIVEMENT
- Tester 2FA complet dans dashboard avant commit
- Vérifier qu'aucun Playwright process zombie
- Rollback immédiat si le moindre problème
- Considérer cette tâche comme OPTIONNELLE
```

---

## 🟢 PHASE 3 : PROBLÈMES MINEURS (30min)

---

### ✅ TICKET #10 : Nettoyer Code Commenté Docker Compose (5min) - ✅ COMPLÉTÉ

**Priorité** : 🟢 Mineure
**Effort** : 5 minutes
**Risque** : Nul
**Date de réalisation** : 2 Décembre 2025

#### 📊 Résultat
✅ **Code commenté supprimé avec succès**
- Lignes 209-211 du fichier `docker-compose.pi4-standalone.yml` supprimées
- Commentaire explicatif ajouté : "Dashboard utilise l'image officielle depuis GHCR (plus de build local pour économiser ressources Pi4)"
- Syntaxe YAML validée avec succès via `python -c "import yaml"`

#### 📝 PROMPT POUR IA

```
TÂCHE : Supprimer code commenté obsolète dans docker-compose.pi4-standalone.yml

FICHIER : docker-compose.pi4-standalone.yml

INSTRUCTIONS :

1. Lire le fichier docker-compose.pi4-standalone.yml

2. Trouver le bloc commenté (lignes ~209-211) :
   ```yaml
   # dashboard:
   #   build:
   #     context: ./dashboard
   #     dockerfile: Dockerfile.prod.pi4
   ```

3. Supprimer complètement ces lignes

4. Ajouter commentaire expliquant pourquoi pas de build local :
   ```yaml
   # Dashboard utilise l'image officielle depuis GHCR
   # (plus de build local pour économiser ressources Pi4)
   image: ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest
   ```

VALIDATION :
```bash
# Vérifier syntaxe YAML
docker compose -f docker-compose.pi4-standalone.yml config > /dev/null
echo $?  # Doit être 0

# Test démarrage
docker compose -f docker-compose.pi4-standalone.yml up -d
docker compose ps  # Tous services "healthy"
```

LIVRABLE : Fichier docker-compose.pi4-standalone.yml nettoyé
```

---

### ✅ TICKET #11 : Fix Fallback apiUrl Dashboard (2min) - ✅ COMPLÉTÉ

**Priorité** : 🟢 Mineure
**Effort** : 2 minutes
**Risque** : Nul
**Date de réalisation** : 2 Décembre 2025

#### 📊 Résultat
✅ **Tous les fallbacks apiUrl corrigés dans 13 fichiers**
- dashboard/app/api/bot/action/route.ts
- dashboard/app/api/contacts/route.ts
- dashboard/app/api/settings/yaml/route.ts
- dashboard/app/api/settings/late-messages/route.ts
- dashboard/app/api/settings/messages/route.ts
- dashboard/app/api/history/route.ts
- dashboard/app/api/stats/route.ts
- dashboard/app/api/auth/verify-2fa/route.ts
- dashboard/app/api/auth/upload/route.ts
- dashboard/app/api/auth/start/route.ts
- dashboard/app/api/deployment/services/route.ts
- dashboard/app/api/deployment/jobs/route.ts
- dashboard/app/api/deployment/deploy/route.ts

**Changement** : `'http://linkedin-bot-api:8000'` → `'http://api:8000'`
**Raison** : Le nom du service dans docker-compose.pi4-standalone.yml est `api`, pas `linkedin-bot-api`

#### 📝 PROMPT POUR IA

```
TÂCHE : Corriger fallback apiUrl dans dashboard route.ts

FICHIER : dashboard/app/api/bot/action/route.ts

INSTRUCTIONS :

LIGNE 11, remplacer :
```typescript
const apiUrl = process.env.BOT_API_URL || 'http://linkedin-bot-api:8000';
```

PAR :
```typescript
const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
```

RAISON : Nom service dans docker-compose.pi4-standalone.yml est "api", pas "linkedin-bot-api"

VALIDATION :
```bash
cd dashboard
npm run build
# → Pas d'erreurs
```

LIVRABLE : Fichier route.ts corrigé
```

---

### ✅ TICKET #12 : Améliorer UX Redirect 401 (10min) - ✅ COMPLÉTÉ

**Priorité** : 🟢 Mineure
**Effort** : 10 minutes
**Risque** : Faible
**Date de réalisation** : 2 Décembre 2025

#### 📊 Résultat
✅ **UX améliorée pour les redirects 401**
- Fichier modifié : `dashboard/lib/api.ts`
- Changements appliqués aux fonctions `get()` (ligne 56-69) et `post()` (ligne 88-101)
- Ajout d'un message console : `⚠️  Session expirée, redirection vers login dans 2s...`
- Délai de 2 secondes avant redirection (évite redirect brutal)
- Vérification `window !== undefined` pour compatibilité SSR
- TODO ajouté pour future intégration d'une bibliothèque de toast notifications

#### 📝 PROMPT POUR IA

```
TÂCHE : Améliorer UX lors de redirect 401 (session expirée)

FICHIER : dashboard/lib/api.ts

PROBLÈME ACTUEL :
Redirect brutal vers /login sans prévenir l'utilisateur (perte état formulaire).

INSTRUCTIONS :

LIGNES ~56-58 et ~78-80, remplacer :
```typescript
if (res.status === 401) {
    window.location.href = '/login';
    throw new Error('Unauthorized');
}
```

PAR :
```typescript
if (res.status === 401) {
    // Notifier user avant redirect
    if (typeof window !== 'undefined') {
        console.error('⚠️  Session expirée, redirection vers login dans 2s...');

        // TODO: Remplacer par toast notification si bibliothèque disponible
        // toast.error('Session expirée, redirection...')

        setTimeout(() => {
            window.location.href = '/login';
        }, 2000);
    }
    throw new Error('Session expirée');
}
```

VALIDATION :
```bash
cd dashboard
npm run build
# Test manuel : expirer token, vérifier notification console + délai
```

LIVRABLE : UX améliorée avec délai et console.error
```

---

### ✅ TICKET #13 : Vérifier Healthcheck Dashboard (5min) - ✅ COMPLÉTÉ

**Priorité** : 🟢 Mineure
**Effort** : 5 minutes
**Risque** : Faible
**Date de réalisation** : 2 Décembre 2025

#### 📊 Résultat
✅ **Endpoint healthcheck déjà présent et fonctionnel**
- Fichier existant : `dashboard/app/api/system/health/route.ts`
- Retourne : température CPU, usage mémoire, total mémoire, uptime
- Compatible avec le healthcheck Docker à la ligne 261 de docker-compose.pi4-standalone.yml
- Endpoint optimisé pour Raspberry Pi (lecture température depuis `/sys/class/thermal/thermal_zone0/temp`)
- Fallback inclus pour dev local (non-RPi)

#### 📝 PROMPT POUR IA

```
TÂCHE : Vérifier que l'endpoint healthcheck dashboard existe

FICHIERS :
- docker-compose.pi4-standalone.yml (ligne ~261)
- dashboard/app/api/system/health/route.ts

INSTRUCTIONS :

1. Vérifier que le fichier existe :
   ```bash
   ls -la dashboard/app/api/system/health/route.ts
   ```

2. Si le fichier N'EXISTE PAS, créer un endpoint simple :

   CRÉER : dashboard/app/api/system/health/route.ts
   ```typescript
   import { NextResponse } from 'next/server';

   export async function GET() {
     return NextResponse.json({
       status: 'healthy',
       timestamp: new Date().toISOString()
     });
   }
   ```

3. Si le fichier EXISTE déjà, ne rien modifier.

4. Alternative : Simplifier healthcheck dans docker-compose.yml

   OPTION si endpoint manque et création difficile :

   Dans docker-compose.pi4-standalone.yml, ligne ~261 :
   ```yaml
   healthcheck:
     test: [CMD, curl, -f, http://localhost:3000]  # Page root suffit
   ```

VALIDATION :
```bash
# Test endpoint
curl http://localhost:3000/api/system/health
# Doit retourner : {"status": "healthy", "timestamp": "..."}

# OU si page root :
curl http://localhost:3000
# Doit retourner 200
```

LIVRABLE : Healthcheck fonctionnel (endpoint créé OU config modifiée)
```

---

### ✅ TICKET #14 : Ajouter Newline Fin config.yaml (1min) - ✅ COMPLÉTÉ

**Priorité** : 🟢 Mineure
**Effort** : 1 minute
**Risque** : Nul
**Date de réalisation** : 2 Décembre 2025

#### 📊 Résultat
✅ **Newline déjà présente - Aucune modification nécessaire**
- Vérification : `tail -c 5 config/config.yaml | od -c` montre que le fichier se termine bien par `\n`
- Syntaxe YAML validée avec succès via `python -c "import yaml"`
- Fichier conforme aux bonnes pratiques

#### 📝 PROMPT POUR IA

```
TÂCHE : Ajouter newline à la fin de config/config.yaml

FICHIER : config/config.yaml

INSTRUCTIONS :

1. Vérifier dernière ligne :
   ```bash
   tail -1 config/config.yaml | od -c
   # Si pas de \n final → ajouter
   ```

2. Ajouter newline :
   ```bash
   echo "" >> config/config.yaml
   ```

3. Vérifier syntaxe YAML :
   ```bash
   python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"
   ```

LIVRABLE : config.yaml avec newline final
```

---

## 📊 Résumé des Prompts

| Ticket | Priorité | Effort | Complexité | Risque |
|--------|----------|--------|------------|--------|
| #5 - Exceptions | 🟡 | 1h | Moyenne | Faible |
| #6 - Limit Visitor | 🟡 | 30min | Moyenne | Moyen |
| #7 - Cookies expirés | 🟡 | 30min | Moyenne | Moyen |
| #8 - Parsing logs | 🟡 | 20min | Faible | Faible |
| #9 - Auth 2FA | 🟡 | 1h | Élevée | **Élevé** |
| #10 - Code commenté | 🟢 | 5min | Triviale | Nul |
| #11 - apiUrl fallback | 🟢 | 2min | Triviale | Nul |
| #12 - UX 401 | 🟢 | 10min | Faible | Faible |
| #13 - Healthcheck | 🟢 | 5min | Faible | Faible |
| #14 - Newline YAML | 🟢 | 1min | Triviale | Nul |

---

## 🎯 Ordre d'Exécution Recommandé

### Batch 1 : Mineurs rapides (23min)
```bash
# Tickets faciles, sans risque, pour commencer
#10 → #11 → #14 → #13 → #12
```

### Batch 2 : Importants moyens (1h20min)
```bash
# Tickets avec valeur, risque contrôlé
#8 → #6 → #7 → #5
```

### Batch 3 : Optionnel risqué (1h)
```bash
# Seulement si temps et confiance
#9 (Auth 2FA refactoring)
```

---

## ✅ Comment Utiliser ce Document

### Pour vous-même (humain)
Copier-coller chaque prompt dans une conversation avec une IA (Claude, ChatGPT, etc.)

### Pour une IA autonome
Chaque ticket peut être traité indépendamment :
1. Lire le prompt complet
2. Exécuter les instructions
3. Valider avec les tests fournis
4. Livrer le code + preuve de validation

### Exemple d'utilisation
```
> Copier le PROMPT POUR IA du Ticket #10
> Ouvrir nouvelle conversation Claude
> Coller le prompt
> Claude exécute et génère le code
> Valider puis commit
```

---

## 📝 Notes Importantes

1. **Branches** : Travailler sur `claude/project-audit-review-01Qyoquc67G2XBDoEJ4DFR8W`
2. **Tests** : Toujours exécuter les validations fournies
3. **Rollback** : Si problème, `git revert` immédiatement
4. **Ordre** : Respecter l'ordre recommandé (mineurs → moyens → risqués)
5. **Optionnel** : Ticket #9 (Auth 2FA) peut être skippé sans impact

---

**Document créé le** : 2 Décembre 2025
**Mainteneur** : Claude (Anthropic)
**Version** : 1.0
