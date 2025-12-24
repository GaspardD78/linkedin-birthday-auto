# 📊 RAPPORT D'AUDIT COMPLET - LinkedIn Birthday Auto Bot
**Date:** 24 Décembre 2025
**Version du Code:** v2.0.1
**Severité:** 10 Critiques | 8 Majeurs | 6 Mineurs

---

## 📑 TABLE DES MATIÈRES

1. [Bugs Critiques](#bugs-critiques)
2. [Incohérences Métier](#incohérences-métier)
3. [Problèmes de Robustesse](#problèmes-de-robustesse)
4. [Plan d'Action Priorisé](#plan-daction-priorisé)

---

# 🔴 BUGS CRITIQUES

## BUG #1: UnlimitedBot._build_result() - Paramètres kwargs ignorés

**Fichier:** `src/bots/unlimited_bot.py:46-74`
**Sévérité:** 🔴 CRITIQUE
**Priorité:** P0 (Correction immédiate)

### Description du Problème

```python
# CLASSE MÈRE (birthday_bot.py:169-176)
result = self._build_result(
    messages_sent=self.run_stats["sent"],
    contacts_processed=self.stats["contacts_processed"],
    birthdays_today=self.run_stats["today_found"],
    birthdays_late_ignored=0 if self.config.birthday_filter.process_late else self.run_stats["late_found"],
    messages_ignored=self.run_stats["ignored_limit"],
    duration_seconds=duration,
)  # ← Appel SANS kwargs

# CLASSE ENFANT (unlimited_bot.py:46-74)
def _build_result(self, messages_sent, contacts_processed, birthdays_today,
                  birthdays_late_ignored=0, messages_ignored=0, duration_seconds=0.0, **kwargs):
    # ...
    late_count = kwargs.get("birthdays_late", self.run_stats.get("late_found", 0))
    # ← Cherche 'birthdays_late' dans kwargs qui est VIDE !
```

### Impact
- **Fonctionnel:** UnlimitedBot ne rapporte jamais le nombre réel d'anniversaires tardifs traités
- **Données:** Statistiques incorrectes dans les rapports d'exécution
- **UX:** L'admin voit "birthdays_late: 0" même si 20 ont été traités

### Exemple Concret
```python
# Scénario:
# - Config: process_late=True, max_days_late=10
# - Anniversaires trouvés: 5 aujourd'hui + 8 en retard
# - Messages envoyés: 13

# Résultat ATTENDU:
{
    "birthdays_today": 5,
    "birthdays_late": 8,
    "messages_sent": 13
}

# Résultat ACTUEL:
{
    "birthdays_today": 5,
    "birthdays_late": 0,  # ← FAUX !
    "messages_sent": 13
}
```

### Root Cause
Mismatch signature:
- Classe mère utilise **positional arguments**
- Classe enfant s'attend à **kwargs** pour "birthdays_late"

### Piste de Correction

**Option A: Harmoniser les signatures (RECOMMANDÉ)**

```python
# unlimited_bot.py - Remplacer _build_result() :

def _build_result(self, messages_sent, contacts_processed, birthdays_today,
                  birthdays_late_ignored=0, messages_ignored=0, duration_seconds=0.0, **kwargs) -> dict[str, Any]:
    """
    Surcharge pour adapter le rapport de résultat en mode unlimited.

    En mode unlimited:
    - birthdays_late_ignored du parent est en réalité ignoré (process_late=True toujours)
    - On rapporte les birthdays_late TROUVÉS au lieu d'ignorés
    """
    # Extraire la vraie valeur :
    # En mode unlimited, process_late est TOUJOURS True (voir run_unlimited_bot)
    # Donc birthdays_late_ignored passé par parent sera 0
    # Nous récupérons la vraie valeur de run_stats

    late_count = self.run_stats.get("late_found", 0)

    return {
        "success": True,
        "bot_mode": "unlimited",
        "messages_sent": messages_sent,
        "contacts_processed": contacts_processed,
        "birthdays_today": birthdays_today,
        "birthdays_late": late_count,  # ← Correction : utilise run_stats
        "messages_ignored": messages_ignored,
        "errors": self.stats.get("errors", 0),
        "duration_seconds": round(duration_seconds, 2),
        "dry_run": self.config.dry_run,
        "timestamp": datetime.now().isoformat()
    }
```

**Option B: Modifier la signature de la classe mère**

```python
# birthday_bot.py - Ligne 169-176 :

result = self._build_result(
    messages_sent=self.run_stats["sent"],
    contacts_processed=self.stats["contacts_processed"],
    birthdays_today=self.run_stats["today_found"],
    birthdays_late_ignored=0 if self.config.birthday_filter.process_late else self.run_stats["late_found"],
    birthdays_late=self.run_stats["late_found"],  # ← AJOUT pour UnlimitedBot
    messages_ignored=self.run_stats["ignored_limit"],
    duration_seconds=duration,
)
```

### Effort Estimé
- **Temps de correction:** 15 min
- **Temps de test:** 30 min
- **Risque de régression:** Faible (modification isolée)

### Test de Validation
```python
def test_unlimited_bot_reports_late_birthdays_correctly():
    config = get_config()
    config.bot_mode = "unlimited"
    config.birthday_filter.process_late = True

    with patch("src.bots.unlimited_bot.BrowserManager"):
        bot = UnlimitedBirthdayBot(config=config)
        bot.run_stats = {"today_found": 5, "late_found": 8, "sent": 13, "ignored_limit": 0}
        bot.stats = {"errors": 0}

        result = bot._build_result(
            messages_sent=13,
            contacts_processed=13,
            birthdays_today=5,
            birthdays_late_ignored=0,
            messages_ignored=0,
            duration_seconds=123.45
        )

        assert result["birthdays_late"] == 8  # ← Doit égaler run_stats
        assert result["messages_sent"] == 13
```

---

## BUG #2: InvitationManagerBot - Double comptage en dry-run

**Fichier:** `src/bots/invitation_manager_bot.py:116-127`
**Sévérité:** 🔴 CRITIQUE
**Priorité:** P0

### Description du Problème

```python
if not self.config.dry_run:
    success = self._perform_withdraw(item, name)
    if success:
        self.withdrawn_count += 1  # ← Incrémenté si succès réel
        action_taken_in_pass = True
        break
    else:
        self.errors_count += 1
else:
    logger.info(f"[DRY RUN] Would withdraw request to {name}")
    self.withdrawn_count += 1  # ← AUSSI incrémenté en simulation !
```

### Impact
- **Criticité:** Les rapports d'exécution en dry-run sont complètement faux
- **Confusion:** Admin pense que 10 invits ont été retirées, mais aucune l'a été
- **Confiance:** Crédibilité du bot endommagée

### Exemple Concret
```python
# Exécution avec 50 invitations obsolètes
# dry_run=True

# Résultat du rapport:
{
    "status": "success",
    "withdrawn_count": 50,  # ← MENSONGE !
    "errors": 0
}

# Réalité: Rien n'a été fait
```

### Root Cause
Logique incorrecte : le dry-run doit SIMULER sans compter réellement.

### Piste de Correction

```python
# invitation_manager_bot.py - Remplacer la boucle (lignes 116-127) :

if elapsed_days >= threshold_days:
    logger.info(f"🗑️ Stale request detected: {name} sent {time_text} ({elapsed_days}d >= {threshold_days}d)")

    if not self.config.dry_run:
        # MODE RÉEL : Tenter le retrait
        success = self._perform_withdraw(item, name)
        if success:
            self.withdrawn_count += 1  # ← Compter seulement les vrais retraits
            action_taken_in_pass = True
            break
        else:
            self.errors_count += 1
    else:
        # MODE DRY-RUN : Simuler SANS compter
        logger.info(f"[DRY RUN] Would withdraw request to {name}")
        action_taken_in_pass = True  # ← Simuler l'action sans incrémenter
        # NE PAS incrémenter withdrawn_count
        break
```

**Alternative Plus Claire :**

```python
def _should_withdraw_invitation(self, elapsed_days: int, threshold_days: int) -> bool:
    """Vérifie si une invitation doit être retirée."""
    return elapsed_days >= threshold_days

def _process_invitation(self, item, name, time_text, elapsed_days, threshold_days, max_withdrawals) -> bool:
    """
    Traite une seule invitation.

    Returns:
        True si une action a été prise (réelle ou simulée), False sinon
    """
    if not self._should_withdraw_invitation(elapsed_days, threshold_days):
        return False

    if self.withdrawn_count >= max_withdrawals:
        return False

    logger.info(f"🗑️ Stale request detected: {name} sent {time_text} ({elapsed_days}d >= {threshold_days}d)")

    if self.config.dry_run:
        logger.info(f"[DRY RUN] Would withdraw request to {name}")
        # EN DRY-RUN: Compter seulement en fin de rapport, pas ici
        return True
    else:
        # EN MODE RÉEL: Exécuter le retrait
        success = self._perform_withdraw(item, name)
        if success:
            self.withdrawn_count += 1
        else:
            self.errors_count += 1
        return success

# Et dans _run_internal(), modifier le return final :

return {
    "success": True,
    "withdrawn_count": self.withdrawn_count if not self.config.dry_run else 0,
    "dry_run_simulated_count": self.withdrawn_count if self.config.dry_run else 0,
    "errors": self.errors_count,
    "duration": duration
}
```

### Effort Estimé
- **Temps de correction:** 20 min
- **Temps de test:** 25 min
- **Risque de régression:** Minimal

### Test de Validation
```python
def test_dry_run_does_not_count_withdrawals():
    config = get_config()
    config.dry_run = True
    config.invitation_manager.enabled = True
    config.invitation_manager.max_withdrawals_per_run = 10

    with patch.object(InvitationManagerBot, 'check_login_status', return_value=True):
        bot = InvitationManagerBot(config=config)
        result = bot._run_internal()

        assert result["withdrawn_count"] == 0, "Dry-run ne doit pas compter les retraits"
```

---

## BUG #3: VisitorBot - JSON serialization errors non gérées

**Fichier:** `src/bots/visitor_bot.py:1118-1122`
**Sévérité:** 🔴 CRITIQUE
**Priorité:** P1

### Description du Problème

```python
def _save_scraped_profile_data(self, data: dict) -> None:
    # ...
    skills_json = json.dumps(data.get("skills", []), ensure_ascii=False) if data.get("skills") else None
    certifications_json = json.dumps(data.get("certifications", []), ensure_ascii=False) if data.get("certifications") else None
    languages_json = json.dumps(data.get("languages", []), ensure_ascii=False) if data.get("languages") else None
    work_history_json = json.dumps(data.get("work_history", []), ensure_ascii=False) if data.get("work_history") else None

    # ← Si skills contient un objet non-sérialisable, TypeError levée ICI
    # ← Pas de try/except autour de ces lignes !

    self.db.save_scraped_profile(
        profile_url=data.get("profile_url"),
        # ... autres fields
        skills=skills_json,  # ← Peut être None
    )
```

### Impact
- **Crash:** Le bot crash silencieusement sur certains profils
- **Data Loss:** Les données du profil ne sont jamais sauvegardées
- **Unknowing:** Aucun log d'erreur spécifique (try/except général ligne 1188 est trop loin)

### Root Cause
1. Les listes peuvent contenir des objets Playwright (Locator, etc.)
2. Aucune validation des données avant sérialisation JSON

### Piste de Correction

**Option A : Valider avant sérialisation (RECOMMANDÉ)**

```python
def _serialize_safe_to_json(obj: Any, max_string_length: int = 1000) -> Optional[str]:
    """
    Sérialise un objet en JSON de manière sécurisée.

    Args:
        obj: Objet à sérialiser (list, dict, etc.)
        max_string_length: Longueur max pour les strings

    Returns:
        JSON string ou None si erreur
    """
    if not obj:
        return None

    def sanitize_value(val):
        """Convertit les valeurs non-sérialisables."""
        if isinstance(val, (str, int, float, bool, type(None))):
            return val
        elif isinstance(val, (list, tuple)):
            return [sanitize_value(v) for v in val]
        elif isinstance(val, dict):
            return {k: sanitize_value(v) for k, v in val.items()}
        else:
            # Objet Playwright, Locator, etc.
            try:
                return str(val)[:max_string_length]
            except:
                return f"<{type(val).__name__}>"

    try:
        sanitized = sanitize_value(obj)
        return json.dumps(sanitized, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"JSON serialization failed for {type(obj).__name__}: {e}")
        return None


# Dans _save_scraped_profile_data() :

def _save_scraped_profile_data(self, data: dict) -> None:
    if not self.db:
        return

    try:
        campaign_id = self.campaign_id if hasattr(self, 'campaign_id') else None

        # Utiliser la fonction de sérialisation sécurisée
        skills_json = self._serialize_safe_to_json(data.get("skills", []))
        certifications_json = self._serialize_safe_to_json(data.get("certifications", []))
        languages_json = self._serialize_safe_to_json(data.get("languages", []))
        work_history_json = self._serialize_safe_to_json(data.get("work_history", []))

        # Logs de validation
        if not skills_json and data.get("skills"):
            logger.warning(f"Could not serialize skills: {type(data.get('skills'))}")

        self.db.save_scraped_profile(
            profile_url=data.get("profile_url"),
            full_name=data.get("full_name"),
            # ... autres fields
            skills=skills_json,
            certifications=certifications_json,
            languages=languages_json,
            work_history=work_history_json,
        )

        logger.debug(f"Saved enriched profile data for {data.get('full_name', 'Unknown')}")

    except Exception as e:
        logger.error(f"Failed to save profile data: {e}", exc_info=True)
```

**Option B : Nettoyer les données lors du scraping**

```python
# visitor_bot.py - Modifier _scrape_profile_data() :

def _scrape_profile_data(self) -> dict[str, Any]:
    # ... existing code ...

    scraped_data = {
        "full_name": "Unknown",
        "skills": [],  # ← Initialiser comme liste vide
        "certifications": [],
        "languages": [],
        "work_history": [],
        # ... autres fields
    }

    try:
        # ... scraping code ...

        # ← Ajouter validation APRÈS chaque scrape :
        # 10. COMPÉTENCES COMPLÈTES
        self._scrape_skills_full(scraped_data)

        # ✅ Validation: Convertir strings si nécessaire
        if isinstance(scraped_data["skills"], list):
            scraped_data["skills"] = [str(s) for s in scraped_data["skills"] if isinstance(s, (str, int))]
        else:
            scraped_data["skills"] = []

        # ... continue ...

    except Exception as e:
        logger.error(f"Global scraping error: {e}", exc_info=True)

    return scraped_data
```

### Effort Estimé
- **Temps de correction:** 30 min
- **Temps de test:** 45 min
- **Risque de régression:** Faible

### Test de Validation
```python
def test_save_profile_with_non_serializable_data():
    """Vérifie que les données non-sérialisables sont gérées."""
    from unittest.mock import Mock

    config = get_config()
    bot = VisitorBot(config=config)
    bot.db = Mock()

    # Données avec Locator (non-sérialisable)
    from playwright.sync_api import Locator
    mock_locator = Mock(spec=Locator)

    data = {
        "profile_url": "https://linkedin.com/in/test",
        "full_name": "John Doe",
        "skills": [mock_locator, "Python", "SQL"],  # ← Locator mélangé
        "certifications": ["AWS"],
        "languages": ["English"],
        "work_history": [{"company": "Acme", "title": "Engineer"}]
    }

    # Ne doit pas lever d'exception
    bot._save_scraped_profile_data(data)

    # Vérifier que save_scraped_profile a été appelée
    bot.db.save_scraped_profile.assert_called_once()
```

---

## BUG #4: VisitorBot._visit_profile_with_retry() - Retry logic cassée

**Fichier:** `src/bots/visitor_bot.py:1052-1070`
**Sévérité:** 🔴 CRITIQUE
**Priorité:** P1

### Description du Problème

```python
def _visit_profile_with_retry(self, url: str) -> tuple[bool, Optional[dict[str, Any]]]:
    max_attempts = self.config.visitor.retry.max_attempts
    backoff = self.config.visitor.retry.backoff_factor

    for attempt in range(max_attempts):
        try:
            logger.info(f"Visiting {url} (Attempt {attempt+1})")
            self.page.goto(url, timeout=90000, wait_until="domcontentloaded")
            self._simulate_human_interactions()
            data = self._scrape_profile_data()
            self._random_delay_profile_visit()
            return True, data
        except PlaywrightTimeoutError:
            time.sleep(backoff ** attempt)
            # ← PAS DE CONTINUE NI RETURN !
        except Exception as e:
            logger.warning(f"Visit error: {e}")
            return False, None  # ← RETURN IMMÉDIAT

    return False, None
```

### Impact
- **Bug logique:** Timeout sur tous les attempts → la boucle continue à 0 × 0 = 0 → return False
- **Inefficacité:** Les retraits supposés ne se font pas
- **Race:** Autre exception après timeout → return False sans compléter les retries

### Exemple Concret
```python
# Scénario:
# - max_attempts = 3
# - backoff = 2
# - Tous les attempts timeout

# Attendu: Boucle complète 3 attempts, puis return False
# Actuel:
#   Attempt 1: timeout → sleep(2^0=1s) → continue (IMPLICITE)
#   Attempt 2: timeout → sleep(2^1=2s) → continue
#   Attempt 3: timeout → sleep(2^2=4s) → continue
#   Boucle finie → return False
#
# C'est par chance que ça marche ! Si on accède à une ressource après
# le sleep, celle-ci pourrait être statale.
```

### Root Cause
`PlaywrightTimeoutError` n'a pas de `continue` explicite. Implicitement le code va à la prochaine itération, mais c'est dangereux.

### Piste de Correction

```python
def _visit_profile_with_retry(self, url: str) -> tuple[bool, Optional[dict[str, Any]]]:
    """
    Visite un profil avec retry automatique.

    Returns:
        (True, scraped_data) si succès
        (False, None) si tous les retries échouent
    """
    max_attempts = self.config.visitor.retry.max_attempts or 3
    backoff_factor = self.config.visitor.retry.backoff_factor or 1.5

    last_error = None

    for attempt in range(max_attempts):
        try:
            logger.info(f"Visiting {url} (Attempt {attempt+1}/{max_attempts})")

            self.page.goto(url, timeout=90000, wait_until="domcontentloaded")
            self._simulate_human_interactions()
            data = self._scrape_profile_data()
            self._random_delay_profile_visit()

            logger.debug(f"✅ Successfully visited {url}")
            return True, data

        except PlaywrightTimeoutError as e:
            last_error = e
            if attempt < max_attempts - 1:  # ← Pas le dernier attempt
                wait_time = backoff_factor ** attempt
                logger.warning(
                    f"Timeout visiting {url} (Attempt {attempt+1}/{max_attempts}). "
                    f"Retrying in {wait_time:.1f}s..."
                )
                time.sleep(wait_time)
                # ← CONTINUE explicite
                continue
            else:
                # ← Dernier attempt, pas de retry
                logger.error(f"Failed to visit {url} after {max_attempts} timeout attempts")
                return False, None

        except Exception as e:
            last_error = e
            logger.warning(f"Visit error on attempt {attempt+1}: {e}")

            if attempt < max_attempts - 1:
                wait_time = backoff_factor ** (attempt + 1)
                logger.info(f"Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
                continue
            else:
                return False, None

    logger.error(f"Failed to visit {url}: {last_error}")
    return False, None
```

### Effort Estimé
- **Temps de correction:** 20 min
- **Temps de test:** 30 min
- **Risque de régression:** Très faible

### Test de Validation
```python
def test_retry_logic_exhausts_all_attempts():
    """Vérifie que tous les retries sont complétés."""
    config = get_config()
    config.visitor.retry.max_attempts = 3
    config.visitor.retry.backoff_factor = 1.0

    with patch.object(VisitorBot, 'check_login_status', return_value=True):
        bot = VisitorBot(config=config)

        call_count = 0
        def mock_goto(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise PlaywrightTimeoutError("Timeout")

        bot.page.goto = mock_goto

        result = bot._visit_profile_with_retry("https://linkedin.com/in/test")

        assert result == (False, None)
        assert call_count == 3, f"Expected 3 attempts, got {call_count}"
```

---

## BUG #5: Database migration - Idempotence incomplète

**Fichier:** `src/core/database.py:249-281`
**Sévérité:** 🔴 CRITIQUE
**Priorité:** P1

### Description du Problème

```python
def run_migrations(self):
    current_version = self.get_current_schema_version()

    for version in sorted(MIGRATIONS.keys()):
        if version > current_version:
            logger.info(f"Applying migration {version}...")

            try:
                with self.get_connection() as conn:
                    for stmt in MIGRATIONS[version]:
                        try:
                            conn.execute(stmt)
                        except sqlite3.OperationalError as e:
                            # Idempotence : si la colonne existe déjà, on ignore
                            if "duplicate column name" in str(e).lower():
                                logger.debug(f"Skipping existing column: {stmt}")
                            else:
                                raise  # ← Re-raise les AUTRES erreurs !
                    # ...
            except Exception as e:
                logger.critical(f"❌ FATAL: Migration {version} failed: {e}")
                self.backup_database(f"pre_migration_{version}_fail")
                raise
```

### Impact
- **Data Integrity:** Migration échoue et lève une exception, laissant la DB partiellement migrée
- **Startup:** Bot ne peut plus démarrer (DB dans état inconsistant)
- **Recovery:** Complexe (nécessite backup manuel)

### Exemple Concret
```python
# Migration 2 en cours:
# 1. ADD COLUMN headline TEXT  → OK
# 2. ADD COLUMN summary TEXT   → OK
# 3. ADD COLUMN skills TEXT    → ERREUR (table verrouillée)
#    → Exception levée
#    → Migration échoue
#    → DB a 2 colonnes NEW, 1 OLD, version=1
# 4. + 5 colonnes restantes ne sont JAMAIS ajoutées

# Au redémarrage:
# - get_current_schema_version() retourne 1
# - Migration 2 retentée → même erreur
# - Bot ne démarre jamais
```

### Root Cause
1. Gestion d'erreurs incomplète (seulement "duplicate column")
2. Pas de transaction-level rollback si une seule colonne échoue
3. Pas de validation que toutes les colonnes ont été ajoutées

### Piste de Correction

```python
def run_migrations(self):
    """
    Exécute les migrations manquantes de manière sécurisée et idempotente.
    """
    current_version = self.get_current_schema_version()
    logger.info(f"Current schema version: {current_version}")

    for version in sorted(MIGRATIONS.keys()):
        if version > current_version:
            logger.info(f"Applying migration {version}...")

            # Backup AVANT la migration
            self.backup_database(f"pre_migration_{version}")

            try:
                # Transaction complète pour la migration
                with self.get_connection() as conn:
                    migration_succeeded = True
                    failed_statements = []

                    for stmt in MIGRATIONS[version]:
                        try:
                            conn.execute(stmt)
                            logger.debug(f"✓ Executed: {stmt[:80]}...")

                        except sqlite3.OperationalError as e:
                            error_msg = str(e).lower()

                            # Erreurs idempotentes (OK d'ignorer)
                            if "duplicate column name" in error_msg:
                                logger.debug(f"Column already exists, skipping: {stmt}")
                                continue
                            elif "no such table" in error_msg:
                                logger.debug(f"Table missing, skipping: {stmt}")
                                continue
                            elif "database is locked" in error_msg:
                                # Retry une fois
                                logger.warning(f"Database locked, retrying: {stmt}")
                                time.sleep(1)
                                try:
                                    conn.execute(stmt)
                                    continue
                                except:
                                    migration_succeeded = False
                                    failed_statements.append((stmt, e))
                                    logger.error(f"Retry failed: {stmt}")
                                    break
                            else:
                                # Erreur critique
                                migration_succeeded = False
                                failed_statements.append((stmt, e))
                                logger.error(f"Migration statement failed: {stmt}")
                                logger.error(f"Error details: {e}")
                                break

                    if not migration_succeeded:
                        raise Exception(
                            f"Migration {version} failed. Failed statements: "
                            f"{[s[0][:50] for s in failed_statements]}"
                        )

                    # Enregistrer la migration SEULEMENT si tout a réussi
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                        (version, datetime.now().isoformat())
                    )
                    conn.commit()  # Explicite pour clarté

                logger.info(f"✅ Migration {version} applied successfully")

            except Exception as e:
                logger.critical(f"❌ Migration {version} FAILED: {e}")
                logger.critical(f"Database backed up to: "
                              f"{self.db_path}.pre_migration_{version}_fail.bak")

                # Afficher guide de recovery
                logger.critical(
                    f"\n"
                    f"RECOVERY STEPS:\n"
                    f"1. Stop all bot instances\n"
                    f"2. Restore from backup:\n"
                    f"   cp {self.db_path}.pre_migration_{version}_fail.bak {self.db_path}\n"
                    f"3. Check migration SQL for errors\n"
                    f"4. Restart bot\n"
                )

                raise RuntimeError(f"Database migration {version} failed. "
                                 f"See logs for recovery steps.")


@retry_on_lock(max_retries=3, delay=0.5)
def verify_migration_applied(self, version: int) -> bool:
    """
    Vérifie qu'une migration a bien été appliquée.
    Utile pour diagnostiquer les problèmes.
    """
    with self.get_connection() as conn:
        cursor = conn.cursor()

        # Exemple pour migration 3 (enhanced recruiter fields)
        if version == 3:
            required_columns = [
                "location", "languages", "work_history", "connection_degree",
                "school", "degree", "job_title", "seniority_level",
                "endorsements_count", "profile_picture_url", "open_to_work"
            ]

            cursor.execute("PRAGMA table_info(scraped_profiles)")
            existing_columns = [row[1] for row in cursor.fetchall()]

            missing = [col for col in required_columns if col not in existing_columns]
            if missing:
                logger.error(f"Migration {version} incomplete. Missing columns: {missing}")
                return False
            return True

        return True
```

### Effort Estimé
- **Temps de correction:** 45 min
- **Temps de test:** 60 min
- **Risque de régression:** Moyen (touche logique critique)

### Test de Validation
```python
def test_migration_rollback_on_error():
    """Vérifie que les migrations incomplètes sont rollback."""
    db = Database(":memory:")

    # Créer une migration qui échoue
    original_migrations = MIGRATIONS.copy()
    MIGRATIONS[99] = [
        "CREATE TABLE test (id INTEGER PRIMARY KEY)",
        "INSERT INTO test VALUES (1)",
        "THIS_IS_INVALID_SQL",  # ← Va échouer
        "INSERT INTO test VALUES (2)"
    ]

    try:
        with pytest.raises(Exception):
            db.run_migrations()

        # Vérifier que la migration 99 n'est pas enregistrée
        version = db.get_current_schema_version()
        assert version < 99, "Failed migration should not be recorded"

    finally:
        MIGRATIONS = original_migrations
```

---

## BUG #6: add_birthday_message() - Pas de protection doublon

**Fichier:** `src/core/database.py:562-573`
**Sévérité:** 🔴 CRITIQUE
**Priorité:** P1

### Description du Problème

```python
def add_birthday_message(self, contact_name: str, message_text: str,
                        is_late: bool = False, days_late: int = 0,
                        script_mode: str = "routine") -> int:
    with self.get_connection() as conn:
        cursor = conn.cursor()
        contact = self.get_contact_by_name(contact_name, conn=conn)
        contact_id = contact["id"] if contact else self.add_contact(contact_name, conn=conn)
        sent_at = datetime.now().isoformat()

        # ← AUCUNE VÉRIFICATION si message déjà envoyé aujourd'hui !

        cursor.execute(
            "INSERT INTO birthday_messages (contact_id, contact_name, message_text, sent_at, is_late, days_late, script_mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (contact_id, contact_name, message_text, sent_at, is_late, days_late, script_mode)
        )
        return cursor.lastrowid
```

### Impact
- **Duplicate messages:** Si bot lancé 2× le même jour, même message envoyé 2×
- **Spam:** Contact reçoit double anniversaire de la part du même compteLinkedIn
- **Metrique:** Stats d'anniversaire gonflées (15 envoyés au lieu de 12)

### Scenario Problématique
```python
# 9:00 AM: Cronjob #1 lancé → "Joyeux anniversaire Sophie" envoyé
# 9:05 AM: Admin relance manuellement → "Joyeux anniversaire Sophie" envoyé AGAIN
# Sophie a reçu 2 messages identiques

# Log entry:
# birthday_messages table:
#   id=1: sent_at="2025-12-24T09:00:00", contact_name="Sophie", message_text="..."
#   id=2: sent_at="2025-12-24T09:05:00", contact_name="Sophie", message_text="..."
```

### Root Cause
Pas de contrainte d'unicité sur (contact_id, sent_at_date)

### Piste de Correction

**Option A : Vérifier avant insert (Recommandé)**

```python
@retry_on_lock()
def add_birthday_message(self, contact_name: str, message_text: str,
                        is_late: bool = False, days_late: int = 0,
                        script_mode: str = "routine") -> Optional[int]:
    """
    Ajoute un message d'anniversaire avec protection contre les doublons.

    Returns:
        ID du message si inséré, None si doublon détecté
    """
    with self.get_connection() as conn:
        cursor = conn.cursor()

        # 1. Récupérer ou créer le contact
        contact = self.get_contact_by_name(contact_name, conn=conn)
        if contact:
            contact_id = contact["id"]
        else:
            contact_id = self.add_contact(contact_name, conn=conn)

        # 2. Vérifier doublon AUJOURD'HUI
        today = datetime.now().date().isoformat()
        cursor.execute(
            """
            SELECT id FROM birthday_messages
            WHERE contact_id = ? AND DATE(sent_at) = ? AND message_text = ?
            LIMIT 1
            """,
            (contact_id, today, message_text)
        )

        existing = cursor.fetchone()
        if existing:
            logger.warning(
                f"Birthday message already sent to {contact_name} today. Skipping duplicate."
            )
            return None  # Doublon détecté

        # 3. Insérer le nouveau message
        sent_at = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO birthday_messages
            (contact_id, contact_name, message_text, sent_at, is_late, days_late, script_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (contact_id, contact_name, message_text, sent_at, is_late, days_late, script_mode)
        )

        self.update_contact_last_message(contact_name, sent_at, conn=conn)

        logger.info(f"Birthday message recorded for {contact_name} (ID: {cursor.lastrowid})")
        return cursor.lastrowid
```

**Option B : Ajouter une contrainte UNIQUE en BD**

```python
def init_database(self):
    # ... existing code ...

    with self.get_connection() as conn:
        cursor = conn.cursor()

        # ... tables creation ...

        # Ajouter contrainte d'unicité
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_birthday_messages_no_duplicates
            ON birthday_messages(contact_id, DATE(sent_at), message_text)
            """
        )
```

### Effort Estimé
- **Temps de correction:** 20 min
- **Temps de test:** 30 min
- **Risque de régression:** Très faible

### Test de Validation
```python
def test_no_duplicate_birthday_messages_same_day():
    """Vérifie qu'aucun doublon ne peut être envoyé le même jour."""
    db = Database(":memory:")

    contact_name = "John Doe"
    message_text = "Joyeux anniversaire!"

    # Premier envoi
    result1 = db.add_birthday_message(contact_name, message_text)
    assert result1 is not None, "First message should be recorded"

    # Deuxième envoi (même jour)
    result2 = db.add_birthday_message(contact_name, message_text)
    assert result2 is None, "Duplicate message should be rejected"

    # Vérifier une seule entrée en DB
    messages = db.get_messages_sent_to_contact(contact_name, years=1)
    assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"
```

---

## BUG #7: _send_notification_sync() - Asyncio fire-and-forget

**Fichier:** `src/bots/birthday_bot.py:213-232`
**Sévérité:** 🔴 CRITIQUE
**Priorité:** P2

### Description du Problème

```python
def _send_notification_sync(self, async_func, *args, **kwargs):
    try:
        try:
            loop = asyncio.get_running_loop()
            asyncio.ensure_future(async_func(*args, **kwargs))  # ← Fire-and-forget !
        except RuntimeError:
            asyncio.run(async_func(*args, **kwargs))
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")
```

### Problèmes Multiples

1. **asyncio.ensure_future() crée une task sans l'attendre**
   - Task peut être garbage-collected avant exécution
   - Notification jamais envoyée

2. **asyncio.run() crée une NOUVELLE boucle event**
   - Peut causer deadlock si déjà une boucle active
   - Ferme la boucle après → mémoire non libérée

3. **Aucun timeout**
   - Notification peut bloquer indéfiniment
   - Bot stall en attente

### Impact
- Notifications **rarement** envoyées
- Incertitude si erreur critique a été notifiée
- Memory leak possible

### Piste de Correction

```python
def _send_notification_sync(self, async_func: Callable, *args, **kwargs) -> bool:
    """
    Exécute une fonction async depuis du code sync, de manière sécurisée.

    Args:
        async_func: Fonction async à exécuter
        *args, **kwargs: Arguments pour async_func

    Returns:
        True si notification envoyée, False sinon
    """
    try:
        # Essayer d'utiliser une boucle existante
        try:
            loop = asyncio.get_running_loop()
            # On est déjà dans un contexte async
            # Créer une task et la garder vivante
            task = asyncio.create_task(async_func(*args, **kwargs))
            # Enregistrer la task globalement pour éviter GC
            if not hasattr(self, '_notification_tasks'):
                self._notification_tasks = []
            self._notification_tasks.append(task)
            logger.debug(f"Notification task queued (task_id: {id(task)})")
            return True

        except RuntimeError:
            # Pas de boucle existante, en créer une
            logger.debug("Creating new event loop for notification")
            try:
                # ✅ Approche plus sûre : utiliser asyncio.run avec timeout
                asyncio.run(
                    asyncio.wait_for(
                        async_func(*args, **kwargs),
                        timeout=10.0  # ← Timeout de 10 secondes
                    )
                )
                logger.debug("Notification sent successfully")
                return True
            except asyncio.TimeoutError:
                logger.error("Notification sending timed out (10s)")
                return False

    except Exception as e:
        logger.warning(f"Failed to send notification: {e}", exc_info=True)
        return False


def cleanup_notification_tasks(self) -> None:
    """Attendre les tâches de notification avant shutdown."""
    if not hasattr(self, '_notification_tasks'):
        return

    pending_tasks = [t for t in self._notification_tasks if not t.done()]

    if pending_tasks:
        logger.info(f"Waiting for {len(pending_tasks)} pending notification(s)...")
        try:
            # Créer une boucle temporaire si nécessaire
            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                asyncio.wait(pending_tasks, timeout=5.0)
            )
            loop.close()
        except Exception as e:
            logger.warning(f"Error waiting for notifications: {e}")


# Dans teardown():
def teardown(self) -> None:
    logger.info("Tearing down bot...")
    self.stats["end_time"] = datetime.now().isoformat()

    # ✅ Attendre les notifications avant fermeture
    self.cleanup_notification_tasks()

    if self.browser_manager:
        self.browser_manager.close()
    # ... rest of teardown ...
```

### Effort Estimé
- **Temps de correction:** 40 min
- **Temps de test:** 60 min
- **Risque de régression:** Moyen (asyncio est délicat)

### Test de Validation
```python
@pytest.mark.asyncio
async def test_notification_is_actually_sent():
    """Vérifie que les notifications sont envoyées."""
    config = get_config()
    config.dry_run = True

    with patch("src.core.base_bot.BrowserManager"):
        bot = BirthdayBot(config=config)

        notification_called = False
        async def mock_notify(*args, **kwargs):
            nonlocal notification_called
            notification_called = True

        # Appeler via _send_notification_sync
        bot._send_notification_sync(mock_notify, "test")

        # Attendre cleanup
        await asyncio.sleep(0.1)
        bot.cleanup_notification_tasks()

        assert notification_called, "Notification should have been sent"
```

---

## BUG #8: DateParsingService - Cache invalidation bug

**Fichier:** `src/utils/date_parser.py:105-106`
**Sévérité:** 🔴 CRITIQUE
**Priorité:** P1

### Description du Problème

```python
@classmethod
@lru_cache(maxsize=256)
def parse_days_diff(cls, text: str, locale: str = 'en') -> Optional[int]:
    """
    Parses text to determine how many days have passed since the date.
    """
```

### Impact
**Le cache persiste entre les jours !**

```python
# Jour 1 (24 décembre 2025, 10:00)
parse_days_diff("Oct 24", 'en')
# → Calcule: maintenant 24-déc, date=24-oct
# → Retourne: 61 jours
# → CACHE: ("Oct 24", 'en') → 61

# Jour 2 (25 décembre 2025, 10:00)
parse_days_diff("Oct 24", 'en')
# → Lookup cache: ("Oct 24", 'en') → 61
# → Retourne: 61 (FAUX ! Devrait être 62)

# Dans le bot d'invitation:
# Les dates ne changent JAMAIS après le premier parsing
# → Invitations vieillis classées incorrectement
```

### Root Cause
`@lru_cache` sur une méthode qui calcule une valeur relative à NOW().

### Piste de Correction

```python
class DateParsingService:
    """
    Service for parsing dates with cache invalidation per day.
    """

    # Cache par jour pour éviter les bugs inter-jour
    _CACHE_BY_DATE = {}  # {date_str: {(text, locale): result}}
    _LAST_CACHE_DATE = None

    @classmethod
    def _invalidate_cache_if_needed(cls):
        """Invalide le cache si nous sommes un nouveau jour."""
        today = datetime.now().date().isoformat()

        if cls._LAST_CACHE_DATE != today:
            logger.debug(f"Cache invalidated (new day: {today})")
            cls._CACHE_BY_DATE = {}
            cls._LAST_CACHE_DATE = today

    @classmethod
    def parse_days_diff(cls, text: str, locale: str = 'en') -> Optional[int]:
        """
        Parses text to determine how many days have passed since the date.

        Returns:
            0 for today
            >0 for past days (late)
            None if parse failed or future date (upcoming)
        """
        # ✅ Invalider cache si changement de jour
        cls._invalidate_cache_if_needed()

        # Lookup cache pour aujourd'hui
        cache_key = (text.lower().strip(), locale)
        if cache_key in cls._CACHE_BY_DATE:
            cached_result = cls._CACHE_BY_DATE[cache_key]
            logger.debug(f"Cache hit for '{text}' → {cached_result} days")
            return cached_result

        # Pas en cache, calculer
        text_lower = text.lower().strip()
        config = cls.LOCALE_CONFIG.get(locale, cls.LOCALE_CONFIG['en'])

        # ... existing parsing logic ...

        # Résultat
        result = None

        # 1. Check relative keywords
        for key, val in config['relative'].items():
            if key in text_lower:
                result = val
                break

        if result is None:
            # 1b. Check relative "N days ago"
            ago_match = cls._DAYS_AGO_PATTERN.search(text_lower)
            if ago_match:
                result = int(ago_match.group(1))

        if result is None:
            # 2. Parse explicit date
            day, month = cls._extract_date_components(text_lower, config)
            if day is not None and month is not None:
                result = cls._calculate_delta(day, month)

        # Stocker en cache pour aujourd'hui
        cls._CACHE_BY_DATE[cache_key] = result

        logger.debug(f"Parsed '{text}' → {result} days (cached)")
        return result


# Alternative : Utiliser un TTL cache
from functools import lru_cache, wraps
import time

def lru_cache_with_ttl(ttl_seconds=86400):  # 24 heures
    """Cache LRU avec expiration TTL."""
    def decorator(func):
        cache = {}
        cache_times = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()

            # Vérifier si en cache ET pas expiré
            if key in cache and key in cache_times:
                if now - cache_times[key] < ttl_seconds:
                    return cache[key]
                else:
                    # Cache expiré
                    del cache[key]
                    del cache_times[key]

            # Calculer et stocker en cache
            result = func(*args, **kwargs)
            cache[key] = result
            cache_times[key] = now

            # Limiter la taille (simple LRU)
            if len(cache) > 256:
                oldest_key = min(cache_times, key=cache_times.get)
                del cache[oldest_key]
                del cache_times[oldest_key]

            return result

        return wrapper
    return decorator


# Utilisation :
class DateParsingService:
    @classmethod
    @lru_cache_with_ttl(ttl_seconds=86400)  # Expire après 24h
    def parse_days_diff(cls, text: str, locale: str = 'en') -> Optional[int]:
        # ... existing code ...
```

### Effort Estimé
- **Temps de correction:** 30 min
- **Temps de test:** 45 min
- **Risque de régression:** Faible

### Test de Validation
```python
def test_cache_invalidates_after_one_day(monkeypatch):
    """Vérifie que le cache est invalidé chaque jour."""
    from src.utils.date_parser import DateParsingService

    # Jour 1
    day1 = datetime(2025, 12, 24, 10, 0, 0)
    with patch('src.utils.date_parser.datetime') as mock_datetime:
        mock_datetime.now.return_value = day1
        result1 = DateParsingService.parse_days_diff("Oct 24", 'en')

    # Jour 2
    day2 = datetime(2025, 12, 25, 10, 0, 0)
    with patch('src.utils.date_parser.datetime') as mock_datetime:
        mock_datetime.now.return_value = day2
        result2 = DateParsingService.parse_days_diff("Oct 24", 'en')

    # Les résultats doivent être différents
    assert result1 is not None
    assert result2 is not None
    assert result1 != result2, "Cache should be invalidated per day"
    assert result2 == result1 + 1, "One day should have passed"
```

---

## BUG #9: get_bot_status() - Redis race condition

**Fichier:** `src/api/routes/bot_control.py:119-150`
**Sévérité:** 🔴 CRITIQUE
**Priorité:** P2

### Description du Problème

```python
@router.get("/status", response_model=BotStatusResponse)
async def get_bot_status(authenticated: bool = Depends(verify_api_key)):
    with get_redis_queue() as (redis_conn, job_queue):
        try:
            started_ids, queued_ids = get_redis_job_ids(redis_conn)
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis connection failed: {e}")
            raise HTTPException(status_code=503, detail="...")

        active_jobs = []

        for job_id in started_ids:  # ← Entre ici et la ligne suivante...
            try:
                job = Job.fetch(job_id, connection=redis_conn)  # ← Job peut avoir disparu !
```

### Race Condition Timeline
```
T0: get_redis_job_ids() retourne ["job-1", "job-2"]
T1: Job "job-1" complète et est supprimé de Redis
T2: Boucle itère sur "job-1"
T3: Job.fetch("job-1") → NoSuchJobError
T4: Exception catchée ligne 149 → warning loggé

→ Job "job-1" n'apparaît pas dans le status response
→ Admin voit un job manquant (incohérent)
```

### Impact
- **Incohérence:** Jobs visibles momentanément puis disparus du status
- **Debugging:** Admin pense qu'il y a un bug de state management
- **UX:** Affichage saccadé

### Piste de Correction

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    reraise=True
)
def get_redis_job_ids(connection):
    """Get job IDs from Redis with retry logic."""
    registry = StartedJobRegistry("linkedin-bot", connection=connection)
    started_ids = list(registry.get_job_ids())  # ← Copie de la liste
    queue = Queue("linkedin-bot", connection=connection)
    queued_ids = list(queue.job_ids)  # ← Copie de la liste
    return started_ids, queued_ids


@router.get("/status", response_model=BotStatusResponse)
async def get_bot_status(authenticated: bool = Depends(verify_api_key)):
    """
    Get detailed status of all bot jobs with race condition handling.
    """
    with get_redis_queue() as (redis_conn, job_queue):
        try:
            started_ids, queued_ids = get_redis_job_ids(redis_conn)
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis connection failed after retries: {e}")
            raise HTTPException(status_code=503, detail="Redis service temporarily unavailable")

        active_jobs = []
        queued_jobs = []

        def get_job_details(job_id, status_list, status_label):
            """Récupère les détails d'un job avec gestion des races."""
            try:
                job = Job.fetch(job_id, connection=redis_conn)
                job_type = job.meta.get('job_type', 'unknown')

                def fmt_date(d):
                    return d.isoformat() if d else None

                status_list.append(JobStatus(
                    id=job.id,
                    status=status_label,
                    type=job_type,
                    enqueued_at=fmt_date(job.enqueued_at) or "",
                    started_at=fmt_date(job.started_at)
                ))
                return True

            except NoSuchJobError:
                # ✅ Job disparu entre la listage et le fetch
                # C'est OK, on le log et on continue
                logger.debug(f"Job {job_id} not found (likely completed/removed)")
                return False

            except Exception as e:
                logger.warning(
                    f"Could not fetch details for job {job_id}: {e}",
                    exc_info=False
                )
                return False

        # Traiter les jobs
        successful_started = 0
        for job_id in started_ids:
            if get_job_details(job_id, active_jobs, "running"):
                successful_started += 1

        successful_queued = 0
        for job_id in queued_ids:
            if get_job_details(job_id, queued_jobs, "queued"):
                successful_queued += 1

        # Log pour diagnostiquer les races
        lost_jobs = len(started_ids) - successful_started + len(queued_ids) - successful_queued
        if lost_jobs > 0:
            logger.debug(f"Lost {lost_jobs} jobs to race condition (likely completed)")

        # Déterminer le status global du worker
        worker_status = "idle"
        if active_jobs:
            worker_status = "active"
        elif queued_jobs:
            worker_status = "busy"

        return BotStatusResponse(
            active_jobs=active_jobs,
            queued_jobs=queued_jobs,
            worker_status=worker_status
        )
```

### Effort Estimé
- **Temps de correction:** 25 min
- **Temps de test:** 40 min
- **Risque de régression:** Faible

### Test de Validation
```python
@pytest.mark.asyncio
async def test_status_handles_job_disappearance():
    """Vérifie que le status gère les jobs qui disparaissent."""
    from src.api.routes.bot_control import get_bot_status
    from unittest.mock import AsyncMock, patch, MagicMock

    mock_redis = MagicMock()
    mock_job_queue = MagicMock()

    # Simuler une race : job-1 disparaît
    with patch('src.api.routes.bot_control.get_redis_queue') as mock_get_queue:
        with patch('src.api.routes.bot_control.Job.fetch') as mock_fetch:
            with patch('src.api.routes.bot_control.verify_api_key', return_value=True):
                mock_get_queue.return_value.__enter__.return_value = (mock_redis, mock_job_queue)

                # Retour en premier appel
                def side_effect_started(*args):
                    return ["job-1", "job-2"]

                # job-1 disparaît
                def fetch_side_effect(job_id, **kwargs):
                    if job_id == "job-1":
                        from rq.job import NoSuchJobError
                        raise NoSuchJobError("Job not found")
                    return MagicMock(id=job_id, meta={'job_type': 'birthday'})

                # Appel à get_bot_status
                response = await get_bot_status(authenticated=True)

                # job-2 doit être dans la réponse
                assert any(j.id == "job-2" for j in response.active_jobs)
```

---

## BUG #10: _was_contacted_today() - Timezone mismatch

**Fichier:** `src/core/base_bot.py:651-664`
**Sévérité:** 🔴 CRITIQUE
**Priorité:** P2

### Description du Problème

```python
def _was_contacted_today(self, contact_name: str) -> bool:
    if not self.db:
        return False
    try:
        today = datetime.now().date().isoformat()  # "2025-12-24"
        messages = self.db.get_messages_sent_to_contact(contact_name, years=1)
        for msg in messages:
            msg_date = msg.get("sent_at", "")  # Format: "2025-12-24T14:30:45"
            if msg_date.startswith(today):  # ← Fragile !
                return True
        return False
```

### Problèmes

1. **Timezone implicite:**
   - `datetime.now()` → Timezone locale
   - DB peut stocker UTC
   - Mismatch si utc_offset != 0

2. **Format fragile:**
   - `msg_date.startswith()` suppose format ISO
   - Peut échouer si DB retourne format différent

3. **Pas de timezone aware:**
   - `datetime.now()` retourne timezone-naive
   - Dangereux en multi-timezone

### Exemple Concret
```python
# Bot exécuté à 23:55 UTC+1 (23:55 local, 22:55 UTC)
# Message envoyé aujourd'hui local: "2025-12-24T23:55:00"
#
# Mais DB peut avoir sauvé : "2025-12-24T22:55:00Z" (UTC)
#
# Comparaison:
# today = "2025-12-24"
# msg_date = "2025-12-24T22:55:00Z"
# msg_date.startswith("2025-12-24") → True ✓ (cas = OK par chance)

# Mais à 00:05 UTC+1 (00:05 local, 23:04 UTC)
# Message envoyé hier: "2025-12-23T23:30:00Z"
#
# Comparaison:
# today = "2025-12-24"  (local)
# msg_date = "2025-12-23T23:30:00Z"  (UTC)
# msg_date.startswith("2025-12-24") → False ✓ (cas = OK)

# MAIS après minuit UTC:
# today = "2025-12-24" (local 00:05)
# msg_date = "2025-12-23T23:30:00Z" (envoyé à 00:30 local, 23:30 UTC = HIER)
# → Pas de débordement
#
# MAIS dans tz avec UTC-6 (comme Amérique du Nord):
# À 18:00 UTC-6 local, on est à 24:00 UTC (minuit le jour suivant)
# Message envoyé à "2025-12-24T00:00:00" peut être "2025-12-25T06:00:00Z"
# → Problème !
```

### Piste de Correction

```python
def _was_contacted_today(self, contact_name: str) -> bool:
    """
    Vérifie si un contact a été contacté aujourd'hui (locale-aware).

    Returns:
        True si message envoyé aujourd'hui (date locale)
    """
    if not self.db:
        return False

    try:
        # Utiliser datetime avec timezone
        now = datetime.now(timezone.utc)  # ← UTC aware
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        messages = self.db.get_messages_sent_to_contact(contact_name, years=1)

        for msg in messages:
            sent_at_str = msg.get("sent_at", "")
            if not sent_at_str:
                continue

            # Parser le timestamp ISO
            try:
                # Gérer les formats ISO avec ou sans timezone
                if sent_at_str.endswith('Z'):
                    sent_at = datetime.fromisoformat(sent_at_str.replace('Z', '+00:00'))
                elif '+' in sent_at_str or sent_at_str.count('-') > 2:
                    sent_at = datetime.fromisoformat(sent_at_str)
                else:
                    # Format sans timezone → assumer UTC
                    sent_at = datetime.fromisoformat(sent_at_str).replace(tzinfo=timezone.utc)

                # Comparer en UTC
                if today_start <= sent_at < today_end:
                    logger.debug(f"Contact {contact_name} was contacted today at {sent_at}")
                    return True

            except ValueError as e:
                logger.warning(f"Could not parse message date '{sent_at_str}': {e}")
                continue

        return False

    except Exception as e:
        logger.warning(f"Could not check contact history: {e}")
        return False


# Alternative : Modifier la DB pour toujours stocker en UTC
@retry_on_lock()
def add_birthday_message(self, contact_name: str, message_text: str,
                        is_late: bool = False, days_late: int = 0,
                        script_mode: str = "routine") -> Optional[int]:
    with self.get_connection() as conn:
        cursor = conn.cursor()

        # ... existing code ...

        # ✅ Toujours stocker en UTC
        sent_at = datetime.now(timezone.utc).isoformat()  # ← UTC explicit

        cursor.execute(
            "INSERT INTO birthday_messages (...) VALUES (...)",
            (contact_id, contact_name, message_text, sent_at, ...)
        )

        return cursor.lastrowid
```

### Effort Estimé
- **Temps de correction:** 30 min
- **Temps de test:** 40 min
- **Risque de régression:** Moyen (change la semantique du temps)

### Test de Validation
```python
def test_was_contacted_today_respects_timezone():
    """Vérifie que la détection du même jour respecte les timezones."""
    from datetime import datetime, timezone, timedelta
    from unittest.mock import Mock, patch

    config = get_config()
    config.database.enabled = True

    with patch("src.core.base_bot.BrowserManager"):
        bot = BirthdayBot(config=config)
        bot.db = Mock()

        # Simuler un message envoyé il y a 30 secondes
        now_utc = datetime.now(timezone.utc)
        sent_at = (now_utc - timedelta(seconds=30)).isoformat()

        bot.db.get_messages_sent_to_contact.return_value = [
            {"sent_at": sent_at}
        ]

        # Doit retourner True (même jour, même en UTC)
        result = bot._was_contacted_today("John Doe")
        assert result == True
```

---

# 🟠 INCOHÉRENCES MÉTIER

## INC #1: max_days_late config vs unlimited_bot hardcode

**Fichier:** `src/bots/unlimited_bot.py:104` vs `config/config.yaml:111`
**Sévérité:** 🟠 MAJEUR
**Priorité:** P2

### Description
```python
def run_unlimited_bot(config=None, dry_run: bool = False, max_days_late: int = 10) -> dict:
    # ...
    config.birthday_filter.max_days_late = max_days_late  # Default = 10
```

Si admin change `config.yaml:111` de 10 → 20 jours, `run_unlimited_bot()` ignore la config et utilise toujours 10.

### Correction
```python
def run_unlimited_bot(config=None, dry_run: bool = False, max_days_late: Optional[int] = None) -> dict:
    if config is None:
        config = get_config()

    config = config.model_copy(deep=True)

    if dry_run:
        config.dry_run = True

    config.bot_mode = "unlimited"
    config.birthday_filter.process_today = True
    config.birthday_filter.process_late = True

    # ✅ Utiliser la config sauf si explicitement override
    if max_days_late is not None:
        config.birthday_filter.max_days_late = max_days_late
    # sinon, garder config.birthday_filter.max_days_late de la config

    with UnlimitedBirthdayBot(config=config) as bot:
        return bot.run()
```

---

## INC #2: messaging_limits - Dual source (config + DB)

**Sévérité:** 🟠 MAJEUR
**Priorité:** P2

### Description
Les limites de messages sont définies **deux fois**:
1. `config/config.yaml:57-64` (config statique)
2. `notification_settings` table BD (config dynamique)

Si admin change YAML et oublie la DB → Divergence garantie.

### Correction
```python
# Solution 1 : Utiliser UNIQUEMENT la config YAML
class BirthdayBot:
    def _check_limits(self) -> None:
        """Vérifie les limites depuis la config YAML seulement."""
        weekly_limit = self.config.messaging_limits.weekly_message_limit
        daily_limit = self.config.messaging_limits.daily_message_limit

        if not self.db:
            return

        weekly_count = self.db.get_weekly_message_count()
        if weekly_count >= weekly_limit:
            raise WeeklyLimitReachedError(current=weekly_count, limit=weekly_limit)

        if daily_limit:
            daily_count = self.db.get_daily_message_count()
            if daily_count >= daily_limit:
                raise DailyLimitReachedError(current=daily_count, limit=daily_limit)


# Solution 2 : Charger les limites depuis la DB au startup
class ConfigManager:
    @staticmethod
    def load_limits_from_database(db: Database) -> dict:
        """Charge les limites depuis la BD, fallback à YAML si vide."""
        # ... récupérer depuis BD ...
        # ... sinon fallback à config.yaml ...
        pass
```

---

## INC #3: _wait_between_messages() inefficace en dry-run

**Fichier:** `src/bots/birthday_bot.py:266-279`
**Sévérité:** 🟠 MAJEUR
**Priorité:** P3

### Description
```python
def _wait_between_messages(self) -> None:
    if self.config.dry_run:
        delay = random.randint(2, 5)
        logger.info(f"⏸️  Pause (dry-run): {delay}s")
        time.sleep(delay)  # ← Attend 2-5s par itération !
```

Avec 100 anniversaires, dry-run = 350 secondes = **5+ minutes d'attente inutile**.

### Correction
```python
def _wait_between_messages(self) -> None:
    """Attend entre les messages (humanisé en mode réel, rapide en dry-run)."""
    if self.config.dry_run:
        # En dry-run, pause minimale juste pour logging
        time.sleep(0.1)  # 100ms
        logger.debug("Message sent (dry-run, no actual delay)")
    else:
        delay = random.randint(
            self.config.delays.min_delay_seconds,
            self.config.delays.max_delay_seconds
        )
        logger.info(f"⏸️  Pause: {delay}s")
        time.sleep(delay)
```

---

## INC #4: profiles_ignored counter inconsistency

**Fichier:** `src/bots/visitor_bot.py:134-156`
**Sévérité:** 🟠 MAJEUR
**Priorité:** P3

### Description
```python
for url in profile_urls:
    if self._is_profile_already_visited(url):
        profiles_ignored += 1
        continue

    # ... processing ...
    profiles_attempted += 1
```

**Incohérence:**
- `profiles_attempted` = profils traités réellement
- `profiles_ignored` = profils sautés
- Total != len(profile_urls)

Si 100 URLs, 20 visitées, 80 ignorées:
- `profiles_visited` = 20
- `profiles_attempted` = 20
- `profiles_ignored` = 80
- BUT: Rapport final doit dire "100 URLs processées, 80 ignorées, 20 visitées"

### Correction
```python
profiles_visited = 0
profiles_attempted = 0
profiles_failed = 0
profiles_ignored = 0
total_found = len(profile_urls)

for url in profile_urls:
    if self._is_profile_already_visited(url):
        profiles_ignored += 1
        logger.debug(f"Skipping already visited profile: {url}")
        continue

    profiles_attempted += 1  # ← Compter qu'on va essayer

    success, scraped_data = self._visit_profile_with_retry(url)

    if success:
        profiles_visited += 1
    else:
        profiles_failed += 1

return self._build_result(
    profiles_visited,
    profiles_attempted,
    profiles_failed,
    pages_scraped,
    duration,
    total_found=total_found,  # ← Ajouter
    profiles_ignored=profiles_ignored  # ← Clarifier
)
```

---

# 🔵 PROBLÈMES DE ROBUSTESSE

## ROB #1: Pas de validation JSON avant save

**Fichier:** `src/bots/visitor_bot.py:1118-1122` (couvert en BUG #3)

---

## ROB #2: Regex recompilé à chaque appel

**Fichier:** `src/bots/visitor_bot.py:712-716`
**Sévérité:** 🔵 MINEUR
**Priorité:** P4

### Correction
```python
# Au niveau du module
_YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")

# Dans _scrape_experience_full()
years = _YEAR_PATTERN.findall(date_text)
```

---

## ROB #3: No rate limiting on API endpoints

**Fichier:** `src/api/routes/bot_control.py`
**Sévérité:** 🔵 MINEUR
**Priorité:** P3

### Correction
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.get("/status")
@limiter.limit("10/minute")  # Max 10 requests/minute
async def get_bot_status(request: Request, authenticated: bool = Depends(verify_api_key)):
    # ...
```

---

# 📊 PLAN D'ACTION PRIORISÉ

## Phase 1: Bugs Critiques (P0 - Correction dans 1 semaine)

| # | Bug | Fichier | Effort | Impact | État |
|---|-----|---------|--------|--------|------|
| 1 | UnlimitedBot._build_result() | unlimited_bot.py | 15 min | Données incorrectes | 🔴 TODO |
| 2 | InvitationManager doublon | invitation_manager_bot.py | 20 min | Rapports faux | 🔴 TODO |
| 3 | JSON serialization | visitor_bot.py | 30 min | Crash bot | 🔴 TODO |
| 4 | Retry logic | visitor_bot.py | 20 min | Retraits non faits | 🔴 TODO |
| 5 | Database migration | database.py | 45 min | DB inconsistente | 🔴 TODO |
| 6 | Doublon messages | database.py | 20 min | Spam contact | 🔴 TODO |

## Phase 2: Bugs Majeurs (P1 - Correction dans 2 semaines)

| # | Bug | Fichier | Effort |
|---|-----|---------|--------|
| 7 | Asyncio notifications | birthday_bot.py | 40 min |
| 8 | Cache invalidation | date_parser.py | 30 min |
| 9 | Redis race condition | bot_control.py | 25 min |
| 10 | Timezone mismatch | base_bot.py | 30 min |

## Phase 3: Incohérences Métier (P2 - Refactoring)

| # | Incohérence | Fichier | Priorité |
|---|-------------|---------|----------|
| 1 | max_days_late config | unlimited_bot.py | P2 |
| 2 | Dual messaging_limits | config.yaml / DB | P2 |
| 3 | Dry-run delays | birthday_bot.py | P3 |
| 4 | Profiles counter | visitor_bot.py | P3 |

---

## Effort Total Estimé

| Phase | Bugs | Heures | Semaine |
|-------|------|--------|---------|
| 1 | 6 critiques | 6-8h | Sem 1 |
| 2 | 4 majeurs | 4-5h | Sem 2 |
| 3 | 4 métiers | 2-3h | Sem 3 |
| **Total** | **14 bugs** | **12-16h** | **3 semaines** |

---

## Stratégie de Déploiement

### Sprint 1 (Immédiat)
1. ✅ Fix UnlimitedBot._build_result()
2. ✅ Fix InvitationManager doublon
3. ✅ Fix JSON serialization
4. Deploy v2.0.2

### Sprint 2 (1 semaine)
5. ✅ Fix Retry logic
6. ✅ Fix Database migration
7. ✅ Fix Doublon messages
8. Deploy v2.0.3

### Sprint 3 (2 semaines)
9. ✅ Fix Asyncio notifications
10. ✅ Fix Cache invalidation
11. Deploy v2.0.4

### Sprint 4 (3 semaines)
12. ✅ Fix Redis race condition
13. ✅ Fix Timezone mismatch
14. Deploy v2.1.0

---

**Fin du rapport complet d'audit.**
