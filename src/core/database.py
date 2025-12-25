"""
Module de gestion de la base de données SQLite pour LinkedIn Birthday Auto
Gère les contacts, messages, visites de profils, erreurs et sélecteurs LinkedIn

Version 3.0.0 - Refactorisation Complète (Phase 1):
- TransactionManager pour gestion robuste des transactions
- Système de migration versionné
- Suppression des ALTER TABLE inline
- Backups automatiques avant migration
"""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import wraps
import json
import os
import sqlite3
import threading
import time
import shutil
from typing import Any, Optional, Counter, List, Dict
from collections import Counter

from ..utils.logging import get_logger

logger = get_logger(__name__)

# Dictionnaire des migrations (Version -> Liste de requêtes SQL)
MIGRATIONS = {
    1: [
        "ALTER TABLE notification_settings ADD COLUMN smtp_host TEXT",
        "ALTER TABLE notification_settings ADD COLUMN smtp_port INTEGER",
        "ALTER TABLE notification_settings ADD COLUMN smtp_user TEXT",
        "ALTER TABLE notification_settings ADD COLUMN smtp_password TEXT",
        "ALTER TABLE notification_settings ADD COLUMN smtp_use_tls BOOLEAN DEFAULT 1",
        "ALTER TABLE notification_settings ADD COLUMN smtp_from_email TEXT"
    ],
    2: [
        # Colonnes potentiellement manquantes sur les anciennes installations (avant v2.3)
        "ALTER TABLE scraped_profiles ADD COLUMN headline TEXT",
        "ALTER TABLE scraped_profiles ADD COLUMN summary TEXT",
        "ALTER TABLE scraped_profiles ADD COLUMN skills TEXT",
        "ALTER TABLE scraped_profiles ADD COLUMN certifications TEXT",
        "ALTER TABLE scraped_profiles ADD COLUMN fit_score REAL",
        "ALTER TABLE scraped_profiles ADD COLUMN campaign_id INTEGER"
    ],
    3: [
        # Enhanced Recruiter Fields
        "ALTER TABLE scraped_profiles ADD COLUMN location TEXT",
        "ALTER TABLE scraped_profiles ADD COLUMN languages TEXT",
        "ALTER TABLE scraped_profiles ADD COLUMN work_history TEXT",
        "ALTER TABLE scraped_profiles ADD COLUMN connection_degree TEXT",
        "ALTER TABLE scraped_profiles ADD COLUMN school TEXT",
        "ALTER TABLE scraped_profiles ADD COLUMN degree TEXT",
        "ALTER TABLE scraped_profiles ADD COLUMN job_title TEXT",
        "ALTER TABLE scraped_profiles ADD COLUMN seniority_level TEXT",
        "ALTER TABLE scraped_profiles ADD COLUMN endorsements_count INTEGER",
        "ALTER TABLE scraped_profiles ADD COLUMN profile_picture_url TEXT",
        "ALTER TABLE scraped_profiles ADD COLUMN open_to_work INTEGER"
    ],
    4: [
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_no_dup_msg ON birthday_messages(contact_id, substr(sent_at, 1, 10), message_text)"
    ]
}

def retry_on_lock(max_retries=5, delay=0.2):
    """
    Decorator pour retry automatique en cas de database lock.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "locked" in str(e):
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Database locked in {func.__name__}, retrying in {current_delay:.2f}s (attempt {attempt + 1}/{max_retries})"
                            )
                            time.sleep(current_delay)
                            current_delay *= 2
                        else:
                            logger.error(f"Database operation failed (Locked): {e}")
                            raise
                    else:
                        raise
            return None
        return wrapper
    return decorator

class TransactionManager:
    """
    Gestionnaire de contexte pour les transactions SQLite.
    Gère les transactions imbriquées via SAVEPOINT.
    """
    def __init__(self, connection, savepoints_stack: List[str]):
        self.connection = connection
        self.savepoints = savepoints_stack

    def __enter__(self):
        # Si une transaction est déjà en cours (reconnue par sqlite3 ou par notre pile)
        if self.connection.in_transaction or self.savepoints:
            sp_name = f"sp_{len(self.savepoints) + 1}_{int(time.time()*1000)}"
            logger.debug(f"BEGIN NESTED transaction (SAVEPOINT {sp_name})")
            self.connection.execute(f"SAVEPOINT {sp_name}")
            self.savepoints.append(sp_name)
            self.is_root = False
        else:
            logger.debug("BEGIN ROOT transaction")
            self.connection.execute("BEGIN")
            self.is_root = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # En cas d'erreur : Rollback
            if not self.is_root and self.savepoints:
                sp_name = self.savepoints.pop()
                logger.debug(f"ROLLBACK TO {sp_name} due to {exc_type.__name__}")
                self.connection.execute(f"ROLLBACK TO {sp_name}")
            elif self.is_root:
                logger.error(f"ROLLBACK ROOT transaction due to {exc_type.__name__}: {exc_val}")
                self.connection.rollback()
            # Ne pas masquer l'exception
            return False
        else:
            # Succès : Commit ou Release
            if not self.is_root and self.savepoints:
                sp_name = self.savepoints.pop()
                logger.debug(f"RELEASE {sp_name}")
                self.connection.execute(f"RELEASE {sp_name}")
            elif self.is_root:
                logger.debug("COMMIT ROOT transaction")
                self.connection.commit()

class Database:
    """
    Classe de gestion de la base de données SQLite.
    Singleton recommandé via get_database().
    """

    SCHEMA_VERSION = 4

    def __init__(self, db_path: str = "linkedin_automation.db"):
        self.db_path = db_path
        self._local = threading.local()
        self.init_database()

    def _create_connection(self) -> sqlite3.Connection:
        max_retries = 5
        base_delay = 0.5
        last_error = None

        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(self.db_path, timeout=60.0)
                conn.row_factory = sqlite3.Row

                # Optimisations Performance & Concurrence (WAL)
                try:
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=NORMAL")
                    conn.execute("PRAGMA busy_timeout=60000")
                    conn.execute("PRAGMA temp_store=MEMORY")
                    conn.execute("PRAGMA foreign_keys=ON")
                except Exception as e:
                    logger.warning(f"Failed to set PRAGMA optimizations: {e}")

                return conn

            except sqlite3.OperationalError as e:
                last_error = e
                wait_time = base_delay * (2 ** attempt)
                if attempt < max_retries - 1:
                    time.sleep(wait_time)

        raise last_error or sqlite3.OperationalError("Could not connect to database")

    @contextmanager
    def get_connection(self):
        """
        Retourne un contexte transactionnel (TransactionManager).
        Compatible avec l'ancienne API qui attendait `conn`.
        """
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = self._create_connection()
            self._local.savepoints = []

        # Vérification santé connexion
        try:
            self._local.conn.in_transaction
        except sqlite3.ProgrammingError:
            self._local.conn = self._create_connection()
            self._local.savepoints = []

        if not hasattr(self._local, "savepoints"):
            self._local.savepoints = []

        with TransactionManager(self._local.conn, self._local.savepoints) as txn:
            yield txn.connection

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            try:
                self._local.conn.close()
            except Exception: pass
            finally:
                self._local.conn = None

    def get_current_schema_version(self) -> int:
        """Récupère la version actuelle du schéma (int)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Vérifier si la table existe
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
                if not cursor.fetchone():
                    return 0

                # Vérifier le format (migration legacy)
                cursor.execute("PRAGMA table_info(schema_version)")
                cols = [c[1] for c in cursor.fetchall()]
                if 'id' not in cols:
                    return 0 # Legacy text version

                cursor.execute("SELECT MAX(version) FROM schema_version")
                row = cursor.fetchone()
                return row[0] if row and row[0] is not None else 0
            except Exception:
                return 0

    def backup_database(self, suffix: str):
        """Crée un backup de la BDD."""
        if not os.path.exists(self.db_path): return

        backup_path = f"{self.db_path}.{suffix}.bak"
        try:
            # Tentative VACUUM INTO (plus sûr)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f"VACUUM INTO '{backup_path}'")
            logger.info(f"Database backup created: {backup_path}")
        except Exception as e:
            logger.warning(f"VACUUM INTO backup failed ({e}), falling back to copy")
            try:
                shutil.copy2(self.db_path, backup_path)
            except Exception as copy_e:
                logger.error(f"Backup copy failed: {copy_e}")

    def run_migrations(self):
        """
        Exécute les migrations manquantes de manière sécurisée et idempotente.
        """
        current_version = self.get_current_schema_version()
        logger.info(f"Checking migrations... Current version: {current_version}")

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
                                # Robust Retry Loop for Locking
                                max_retries_lock = 5
                                for attempt in range(max_retries_lock):
                                    try:
                                        conn.execute(stmt)
                                        logger.debug(f"✓ Executed: {stmt[:80]}...")
                                        break # Success
                                    except sqlite3.OperationalError as e:
                                        if "database is locked" in str(e).lower():
                                            if attempt < max_retries_lock - 1:
                                                time.sleep(0.5 * (2**attempt))
                                                logger.warning(f"Database locked during migration, retrying ({attempt+1}/{max_retries_lock})...")
                                                continue
                                            else:
                                                raise # Exhausted retries
                                        else:
                                            raise # Not a lock error

                            except sqlite3.OperationalError as e:
                                error_msg = str(e).lower()

                                # Erreurs idempotentes (OK d'ignorer)
                                if "duplicate column name" in error_msg:
                                    logger.debug(f"Column already exists, skipping: {stmt}")
                                    continue
                                elif "no such table" in error_msg:
                                    logger.debug(f"Table missing, skipping: {stmt}")
                                    continue
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
                        conn.execute(
                            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                            (version, datetime.now(timezone.utc).isoformat())
                        )

                    logger.info(f"✅ Migration {version} applied successfully")

                except Exception as e:
                    logger.critical(f"❌ FATAL: Migration {version} FAILED: {e}")
                    logger.critical(f"Database backed up to: {self.db_path}.pre_migration_{version}.bak")
                    raise

    def init_database(self):
        """Initialise la structure de la base de données."""

        # 1. Gestion Legacy schema_version (Hors transaction pour DROP)
        conn_raw = self._create_connection()
        try:
            cursor = conn_raw.cursor()
            cursor.execute("PRAGMA table_info(schema_version)")
            cols = [c[1] for c in cursor.fetchall()]
            if 'version' in cols and 'id' not in cols:
                logger.info("Upgrading legacy schema_version table")
                cursor.execute("DROP TABLE schema_version")
                conn_raw.commit()
        except Exception:
            pass
        finally:
            conn_raw.close()

        # 2. Création des tables de base (Version 0)
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Schema Versioning
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER UNIQUE,
                    applied_at TEXT NOT NULL
                )
            """)

            # Contacts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    linkedin_url TEXT UNIQUE,
                    last_message_date TEXT,
                    message_count INTEGER DEFAULT 0,
                    relationship_score REAL DEFAULT 0.0,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Birthday Messages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS birthday_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_id INTEGER,
                    contact_name TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    sent_at TEXT NOT NULL,
                    is_late BOOLEAN DEFAULT 0,
                    days_late INTEGER DEFAULT 0,
                    response_received BOOLEAN DEFAULT 0,
                    response_text TEXT,
                    response_date TEXT,
                    script_mode TEXT,
                    FOREIGN KEY (contact_id) REFERENCES contacts (id)
                )
            """)

            # Profile Visits
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profile_visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_name TEXT NOT NULL,
                    profile_url TEXT,
                    visited_at TEXT NOT NULL,
                    source_search TEXT,
                    keywords TEXT,
                    location TEXT,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT
                )
            """)

            # Errors
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    script_name TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    error_details TEXT,
                    screenshot_path TEXT,
                    occurred_at TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT 0,
                    resolved_at TEXT
                )
            """)

            # Selectors
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS linkedin_selectors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    selector_name TEXT UNIQUE NOT NULL,
                    selector_value TEXT NOT NULL,
                    page_type TEXT NOT NULL,
                    description TEXT,
                    last_validated TEXT,
                    is_valid BOOLEAN DEFAULT 1,
                    validation_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0
                )
            """)

            # Scraped Profiles (Base Version)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraped_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id INTEGER,
                    profile_url TEXT UNIQUE NOT NULL,
                    first_name TEXT,
                    last_name TEXT,
                    full_name TEXT,
                    headline TEXT,
                    summary TEXT,
                    relationship_level TEXT,
                    current_company TEXT,
                    education TEXT,
                    years_experience INTEGER,
                    skills TEXT,
                    certifications TEXT,
                    fit_score REAL,
                    scraped_at TEXT NOT NULL,
                    FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
                )
            """)

            # Campaigns
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    search_url TEXT,
                    filters TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Bot Executions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    items_processed INTEGER DEFAULT 0,
                    items_ignored INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running'
                )
            """)

            # Notification Settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_enabled BOOLEAN DEFAULT 0,
                    email_address TEXT,
                    notify_on_error BOOLEAN DEFAULT 1,
                    notify_on_success BOOLEAN DEFAULT 0,
                    notify_on_bot_start BOOLEAN DEFAULT 0,
                    notify_on_bot_stop BOOLEAN DEFAULT 0,
                    notify_on_cookies_expiry BOOLEAN DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Notification Logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    recipient_email TEXT,
                    subject TEXT,
                    body TEXT,
                    status TEXT NOT NULL,
                    sent_at TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Blacklist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_name TEXT NOT NULL,
                    linkedin_url TEXT,
                    reason TEXT,
                    added_at TEXT NOT NULL,
                    added_by TEXT DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1
                )
            """)

            # Indices
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_birthday_messages_sent_at ON birthday_messages(sent_at)",
                "CREATE INDEX IF NOT EXISTS idx_birthday_messages_contact_name ON birthday_messages(contact_name)",
                "CREATE INDEX IF NOT EXISTS idx_profile_visits_visited_at ON profile_visits(visited_at)",
                "CREATE INDEX IF NOT EXISTS idx_profile_visits_url ON profile_visits(profile_url)",
                "CREATE INDEX IF NOT EXISTS idx_errors_occurred_at ON errors(occurred_at)",
                "CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name)",
                "CREATE INDEX IF NOT EXISTS idx_contacts_created_at ON contacts(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_scraped_profiles_url ON scraped_profiles(profile_url)",
                "CREATE INDEX IF NOT EXISTS idx_scraped_profiles_scraped_at ON scraped_profiles(scraped_at)",
                "CREATE INDEX IF NOT EXISTS idx_notification_logs_event_type ON notification_logs(event_type)",
                "CREATE INDEX IF NOT EXISTS idx_notification_logs_created_at ON notification_logs(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_bot_executions_start_time ON bot_executions(start_time)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_contact_name ON blacklist(contact_name)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_linkedin_url ON blacklist(linkedin_url)",
                "CREATE INDEX IF NOT EXISTS idx_blacklist_is_active ON blacklist(is_active)"
            ]
            for idx in indices:
                cursor.execute(idx)

        # 3. Exécuter les migrations
        self.run_migrations()

        # 4. Initialiser sélecteurs
        with self.get_connection() as conn:
            self._init_default_selectors(conn.cursor())

    def _init_default_selectors(self, cursor):
        default_selectors = [
            {"name": "birthday_card", "value": "div.occludable-update", "page_type": "birthday_feed", "description": "Carte d'anniversaire"},
            {"name": "birthday_name", "value": "span.update-components-actor__name > span > span > span:first-child", "page_type": "birthday_feed", "description": "Nom contact"},
            {"name": "birthday_date", "value": "span.update-components-actor__supplementary-actor-info", "page_type": "birthday_feed", "description": "Date anniversaire"},
            {"name": "message_button", "value": "button.message-anywhere-button", "page_type": "birthday_feed", "description": "Bouton message"},
            {"name": "message_textarea", "value": "div.msg-form__contenteditable", "page_type": "messaging", "description": "Zone texte"},
            {"name": "send_button", "value": "button.msg-form__send-button", "page_type": "messaging", "description": "Bouton envoi"},
            {"name": "profile_card", "value": "li.reusable-search__result-container", "page_type": "search", "description": "Carte profil"},
        ]
        for s in default_selectors:
            cursor.execute(
                "INSERT OR IGNORE INTO linkedin_selectors (selector_name, selector_value, page_type, description, last_validated, is_valid) VALUES (?, ?, ?, ?, ?, ?)",
                (s["name"], s["value"], s["page_type"], s["description"], datetime.now(timezone.utc).isoformat(), True)
            )

    # ==================== DATA METHODS ====================

    @retry_on_lock()
    def add_contact(self, name: str, linkedin_url: Optional[str] = None, relationship_score: float = 0.0, notes: Optional[str] = None, conn=None) -> int:
        def _op(c):
            # ✅ Utiliser UTC pour les timestamps
            now = datetime.now(timezone.utc).isoformat()
            c.execute("INSERT INTO contacts (name, linkedin_url, relationship_score, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (name, linkedin_url, relationship_score, notes, now, now))
            return c.lastrowid

        if conn: return _op(conn.cursor())
        with self.get_connection() as c: return _op(c.cursor())

    @retry_on_lock()
    def get_contact_by_name(self, name: str, conn=None) -> Optional[dict]:
        def _op(c):
            c.execute("SELECT * FROM contacts WHERE name = ?", (name,))
            row = c.fetchone()
            return dict(row) if row else None

        if conn: return _op(conn.cursor())
        with self.get_connection() as c: return _op(c.cursor())

    @retry_on_lock()
    def update_contact_last_message(self, name: str, message_date: str, conn=None):
        def _op(c):
            # ✅ Utiliser UTC pour le timestamp updated_at
            c.execute("UPDATE contacts SET last_message_date = ?, message_count = message_count + 1, updated_at = ? WHERE name = ?", (message_date, datetime.now(timezone.utc).isoformat(), name))

        if conn: _op(conn.cursor())
        else:
            with self.get_connection() as c: _op(c.cursor())

    @retry_on_lock()
    def add_birthday_message(self, contact_name: str, message_text: str,
                            is_late: bool = False, days_late: int = 0,
                            script_mode: str = "routine") -> Optional[int]:
        """
        Ajoute un message d'anniversaire avec protection contre les doublons (Atomic).

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

            # 2. Insérer le nouveau message (Atomic check via Unique Index)
            # ✅ Toujours stocker en UTC (timezone-aware)
            sent_at = datetime.now(timezone.utc).isoformat()

            try:
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

            except sqlite3.IntegrityError:
                # Doublon détecté par la contrainte UNIQUE
                logger.warning(
                    f"Birthday message already sent to {contact_name} today (caught by IntegrityError). Skipping duplicate."
                )
                return None

    @retry_on_lock()
    def get_messages_sent_to_contact(self, contact_name: str, years: int = 3) -> list:
        with self.get_connection() as conn:
            # ✅ Utiliser UTC pour les comparaisons de dates
            cutoff = (datetime.now(timezone.utc) - timedelta(days=365 * years)).isoformat()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM birthday_messages WHERE contact_name = ? AND sent_at >= ? ORDER BY sent_at DESC", (contact_name, cutoff))
            return [dict(row) for row in cursor.fetchall()]

    @retry_on_lock()
    def get_weekly_message_count(self) -> int:
        with self.get_connection() as conn:
            # ✅ Utiliser UTC pour les comparaisons de dates
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM birthday_messages WHERE sent_at >= ?", (week_ago,))
            return cursor.fetchone()["count"]

    @retry_on_lock()
    def get_daily_message_count(self, date: Optional[str] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # ✅ Utiliser UTC pour les timestamps
            if date is None: date = datetime.now(timezone.utc).date().isoformat()
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                next_day = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
                cursor.execute("SELECT COUNT(*) as count FROM birthday_messages WHERE sent_at >= ? AND sent_at < ?", (date, next_day))
            except:
                cursor.execute("SELECT COUNT(*) as count FROM birthday_messages WHERE DATE(sent_at) = ?", (date,))
            return cursor.fetchone()["count"]

    @retry_on_lock()
    def add_profile_visit(self, profile_name: str, profile_url: str = None, source_search: str = None, keywords: list = None, location: str = None, success: bool = True, error_message: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            keywords_json = json.dumps(keywords) if keywords else None
            # ✅ Utiliser UTC pour les timestamps
            cursor.execute(
                "INSERT INTO profile_visits (profile_name, profile_url, visited_at, source_search, keywords, location, success, error_message) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (profile_name, profile_url, datetime.now(timezone.utc).isoformat(), source_search, keywords_json, location, success, error_message)
            )
            return cursor.lastrowid

    @retry_on_lock()
    def get_daily_visits_count(self, date: Optional[str] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # ✅ Utiliser UTC pour les timestamps
            if date is None: date = datetime.now(timezone.utc).date().isoformat()
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                next_day = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
                cursor.execute("SELECT COUNT(*) as count FROM profile_visits WHERE visited_at >= ? AND visited_at < ?", (date, next_day))
            except:
                cursor.execute("SELECT COUNT(*) as count FROM profile_visits WHERE DATE(visited_at) = ?", (date,))
            return cursor.fetchone()["count"]

    @retry_on_lock()
    def is_profile_visited(self, profile_url: str, days: int = 30) -> bool:
        with self.get_connection() as conn:
            # ✅ Utiliser UTC pour les comparaisons de dates
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM profile_visits WHERE profile_url = ? AND visited_at >= ?", (profile_url, cutoff))
            return cursor.fetchone()["count"] > 0

    @retry_on_lock()
    def log_error(self, script_name: str, error_type: str, error_message: str, error_details: str = None, screenshot_path: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # ✅ Utiliser UTC pour les timestamps
            cursor.execute(
                "INSERT INTO errors (script_name, error_type, error_message, error_details, screenshot_path, occurred_at) VALUES (?, ?, ?, ?, ?, ?)",
                (script_name, error_type, error_message, error_details, screenshot_path, datetime.now(timezone.utc).isoformat())
            )
            return cursor.lastrowid

    @retry_on_lock()
    def get_recent_errors(self, limit: int = 50) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM errors ORDER BY occurred_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    @retry_on_lock()
    def get_selector(self, selector_name: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM linkedin_selectors WHERE selector_name = ?", (selector_name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @retry_on_lock()
    def update_selector_validation(self, selector_name: str, is_valid: bool):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            if is_valid:
                cursor.execute("UPDATE linkedin_selectors SET is_valid = 1, last_validated = ?, validation_count = validation_count + 1 WHERE selector_name = ?", (now, selector_name))
            else:
                cursor.execute("UPDATE linkedin_selectors SET is_valid = 0, last_validated = ?, failure_count = failure_count + 1 WHERE selector_name = ?", (now, selector_name))

    @retry_on_lock()
    def get_all_selectors(self) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM linkedin_selectors ORDER BY page_type, selector_name")
            return [dict(row) for row in cursor.fetchall()]

    @retry_on_lock()
    def save_scraped_profile(self, profile_url: str, **kwargs) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # ✅ Utiliser UTC pour les timestamps
            scraped_at = datetime.now(timezone.utc).isoformat()

            # Helper to safely serialize JSON
            def to_json(val): return json.dumps(val) if val else None

            # Map known fields
            fields = {
                'profile_url': profile_url, 'scraped_at': scraped_at,
                'first_name': kwargs.get('first_name'), 'last_name': kwargs.get('last_name'),
                'full_name': kwargs.get('full_name'), 'headline': kwargs.get('headline'),
                'summary': kwargs.get('summary'), 'relationship_level': kwargs.get('relationship_level'),
                'current_company': kwargs.get('current_company'), 'education': kwargs.get('education'),
                'years_experience': kwargs.get('years_experience'), 'fit_score': kwargs.get('fit_score'),
                'campaign_id': kwargs.get('campaign_id'), 'location': kwargs.get('location'),
                'connection_degree': kwargs.get('connection_degree'), 'school': kwargs.get('school'),
                'degree': kwargs.get('degree'), 'job_title': kwargs.get('job_title'),
                'seniority_level': kwargs.get('seniority_level'), 'endorsements_count': kwargs.get('endorsements_count'),
                'profile_picture_url': kwargs.get('profile_picture_url'),
                'open_to_work': 1 if kwargs.get('open_to_work') else (0 if kwargs.get('open_to_work') is False else None),
                'skills': to_json(kwargs.get('skills')), 'certifications': to_json(kwargs.get('certifications')),
                'languages': to_json(kwargs.get('languages')), 'work_history': to_json(kwargs.get('work_history'))
            }

            # Upsert Logic
            cols = list(fields.keys())
            placeholders = ",".join(["?"] * len(cols))
            updates = ",".join([f"{c}=excluded.{c}" for c in cols if c != 'profile_url'])

            sql = f"INSERT INTO scraped_profiles ({','.join(cols)}) VALUES ({placeholders}) ON CONFLICT(profile_url) DO UPDATE SET {updates}"
            cursor.execute(sql, list(fields.values()))
            return cursor.lastrowid

    @retry_on_lock()
    def get_scraped_profile(self, profile_url: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scraped_profiles WHERE profile_url = ?", (profile_url,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @retry_on_lock()
    def get_all_scraped_profiles(self, limit: int = None, offset: int = 0) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            sql = "SELECT * FROM scraped_profiles ORDER BY scraped_at DESC"
            if limit: sql += f" LIMIT {limit} OFFSET {offset}"
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]

    @retry_on_lock()
    def get_scraped_profiles_count(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM scraped_profiles")
            return cursor.fetchone()["count"]

    @retry_on_lock()
    def export_scraped_data_to_csv(self, output_path: str) -> str:
        import csv
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT profile_url, first_name, last_name, full_name, relationship_level, current_company, education, years_experience, scraped_at FROM scraped_profiles ORDER BY scraped_at DESC")
            rows = cursor.fetchall()

            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["profile_url", "first_name", "last_name", "full_name", "relationship_level", "current_company", "education", "years_experience", "scraped_at"])
                for row in rows:
                    writer.writerow([row[col] if row[col] is not None else "" for col in row.keys()])
            return output_path

    @retry_on_lock()
    def log_bot_execution(self, bot_name: str, start_time: float, items_processed: int, items_ignored: int, errors: int, status: str = "success") -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO bot_executions (bot_name, start_time, end_time, items_processed, items_ignored, errors, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (bot_name, datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(), items_processed, items_ignored, errors, status)
            )
            return cursor.lastrowid

    @retry_on_lock()
    def get_latest_execution_stats(self, bot_name: str = None) -> dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            sql = "SELECT * FROM bot_executions"
            params = []
            if bot_name:
                sql += " WHERE bot_name = ?"
                params.append(bot_name)
            sql += " ORDER BY start_time DESC LIMIT 1"
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()
            return dict(row) if row else {"items_processed": 0, "items_ignored": 0, "errors": 0}

    @retry_on_lock()
    def get_visitor_insights(self, days: int = 30) -> dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

            cursor.execute("SELECT AVG(fit_score) as avg, COUNT(*) as total, SUM(CASE WHEN fit_score > 70 THEN 1 ELSE 0 END) as qualified FROM scraped_profiles WHERE scraped_at >= ?", (cutoff,))
            stats = cursor.fetchone()

            cursor.execute("SELECT skills FROM scraped_profiles WHERE scraped_at >= ? AND skills IS NOT NULL", (cutoff,))
            c = Counter()
            for row in cursor.fetchall():
                try: c.update(json.loads(row[0]))
                except: pass

            cursor.execute("SELECT COUNT(*) as count FROM profile_visits WHERE visited_at >= ?", (cutoff,))
            visited = cursor.fetchone()["count"]

            return {
                "avg_fit_score": round(stats["avg"] or 0, 1),
                "top_skills": [{"name": k, "count": v} for k, v in c.most_common(5)],
                "funnel": {"visited": visited, "scraped": stats["total"], "qualified": stats["qualified"]}
            }

    @retry_on_lock()
    def get_statistics(self, days: int = 30) -> dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

            cursor.execute("SELECT COUNT(*) as t, SUM(CASE WHEN is_late=1 THEN 1 ELSE 0 END) as l FROM birthday_messages WHERE sent_at >= ?", (cutoff,))
            msg = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) as t, SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as s FROM profile_visits WHERE visited_at >= ?", (cutoff,))
            vis = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) as t FROM errors WHERE occurred_at >= ?", (cutoff,))
            err = cursor.fetchone()

            return {
                "messages": {"total": msg["t"], "on_time": msg["t"] - (msg["l"] or 0), "late": (msg["l"] or 0)},
                "profile_visits": {"total": vis["t"], "successful": (vis["s"] or 0)},
                "errors": {"total": err["t"]}
            }

    @retry_on_lock()
    def get_today_statistics(self) -> dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            today = datetime.now(timezone.utc).date().isoformat()
            week = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

            cursor.execute("SELECT COUNT(*) as c FROM birthday_messages WHERE sent_at >= ?", (today,))
            sent_today = cursor.fetchone()["c"]
            cursor.execute("SELECT COUNT(*) as c FROM birthday_messages WHERE sent_at >= ?", (week,))
            sent_week = cursor.fetchone()["c"]
            cursor.execute("SELECT COUNT(*) as c FROM birthday_messages")
            sent_total = cursor.fetchone()["c"]
            cursor.execute("SELECT COUNT(*) as c FROM profile_visits WHERE visited_at >= ?", (today,))
            visit_today = cursor.fetchone()["c"]
            cursor.execute("SELECT COUNT(*) as c FROM profile_visits")
            visit_total = cursor.fetchone()["c"]

            return {
                "wishes_sent_today": sent_today, "wishes_sent_week": sent_week, "wishes_sent_total": sent_total,
                "profiles_visited_today": visit_today, "profiles_visited_total": visit_total,
                "profiles_ignored_today": 0
            }

    @retry_on_lock()
    def get_daily_activity(self, days: int = 30) -> list:
        # Simplified for brevity
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
            cursor.execute("SELECT DATE(sent_at) as d, COUNT(*) as c FROM birthday_messages WHERE sent_at >= ? GROUP BY d", (cutoff,))
            msgs = {row['d']: row['c'] for row in cursor.fetchall()}
            cursor.execute("SELECT DATE(visited_at) as d, COUNT(*) as c FROM profile_visits WHERE visited_at >= ? GROUP BY d", (cutoff,))
            vis = {row['d']: row['c'] for row in cursor.fetchall()}

            dates = sorted(set(msgs.keys()) | set(vis.keys()), reverse=True)
            return [{"date": d, "messages": msgs.get(d, 0), "visits": vis.get(d, 0)} for d in dates]

    @retry_on_lock()
    def get_top_contacts(self, limit: int = 10) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT contact_name as name, COUNT(*) as count FROM birthday_messages GROUP BY name ORDER BY count DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    @retry_on_lock()
    def create_campaign(self, name: str, search_url: str, filters: dict) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("INSERT INTO campaigns (name, search_url, filters, status, created_at, updated_at) VALUES (?, ?, ?, 'pending', ?, ?)", (name, search_url, json.dumps(filters), now, now))
            return cursor.lastrowid

    @retry_on_lock()
    def get_campaigns(self) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    @retry_on_lock()
    def vacuum(self) -> dict:
        logger.info("Starting VACUUM...")
        try:
            # Requires raw connection to avoid transaction
            conn = sqlite3.connect(self.db_path)
            conn.execute("VACUUM")
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
            return {"success": True}
        except Exception as e:
            logger.error(f"VACUUM failed: {e}")
            return {"success": False, "error": str(e)}

    @retry_on_lock()
    def should_vacuum(self) -> bool:
        if not os.path.exists(self.db_path): return False
        return os.path.getsize(self.db_path) > 10 * 1024 * 1024

    @retry_on_lock()
    def auto_vacuum_if_needed(self):
        if self.should_vacuum(): self.vacuum()

    @retry_on_lock()
    def add_to_blacklist(self, contact_name: str, linkedin_url: str = None, reason: str = None, added_by: str = "user") -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO blacklist (contact_name, linkedin_url, reason, added_at, added_by, is_active) VALUES (?, ?, ?, ?, ?, 1)", (contact_name, linkedin_url, reason, datetime.now(timezone.utc).isoformat(), added_by))
            return cursor.lastrowid

    @retry_on_lock()
    def remove_from_blacklist(self, id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE blacklist SET is_active = 0 WHERE id = ?", (id,))
            return cursor.rowcount > 0

    @retry_on_lock()
    def is_blacklisted(self, contact_name: str, linkedin_url: str = None) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            sql = "SELECT COUNT(*) as c FROM blacklist WHERE is_active=1 AND (LOWER(contact_name)=LOWER(?)"
            params = [contact_name]
            if linkedin_url:
                sql += " OR linkedin_url=?"
                params.append(linkedin_url)
            sql += ")"
            cursor.execute(sql, tuple(params))
            return cursor.fetchone()["c"] > 0

    @retry_on_lock()
    def get_blacklist(self) -> list:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM blacklist WHERE is_active=1 ORDER BY added_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    @retry_on_lock()
    def get_blacklist_count(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as c FROM blacklist WHERE is_active=1")
            return cursor.fetchone()["c"]

    @retry_on_lock()
    def update_blacklist_entry(self, id: int, **kwargs) -> bool:
        if not kwargs: return False
        with self.get_connection() as conn:
            cursor = conn.cursor()
            updates = ", ".join([f"{k}=?" for k in kwargs.keys()])
            params = list(kwargs.values()) + [id]
            cursor.execute(f"UPDATE blacklist SET {updates} WHERE id=?", tuple(params))
            return cursor.rowcount > 0

    @retry_on_lock()
    def check_integrity(self) -> dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            res = cursor.fetchall()
            ok = len(res) == 1 and res[0][0] == "ok"
            return {"ok": ok, "details": [r[0] for r in res] if not ok else []}

    @retry_on_lock()
    def cleanup_old_logs(self, days: int = 30):
        with self.get_connection() as conn:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM errors WHERE occurred_at < ?", (cutoff,))
            e = cursor.rowcount
            cursor.execute("DELETE FROM notification_logs WHERE created_at < ?", (cutoff,))
            n = cursor.rowcount
            return {"errors_deleted": e, "notifications_deleted": n}

    @retry_on_lock()
    def cleanup_old_data(self, days: int = 365):
        with self.get_connection() as conn:
             cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
             cursor = conn.cursor()
             cursor.execute("DELETE FROM profile_visits WHERE visited_at < ?", (cutoff,))
             return {"visits_deleted": cursor.rowcount}

    @retry_on_lock()
    def export_to_json(self, output_path: str):
         data = {}
         with self.get_connection() as conn:
             cursor = conn.cursor()
             for table in ["contacts", "birthday_messages", "profile_visits", "errors", "linkedin_selectors"]:
                 cursor.execute(f"SELECT * FROM {table}")
                 data[table] = [dict(r) for r in cursor.fetchall()]
         with open(output_path, "w") as f:
             json.dump(data, f, default=str)

_db_instance = None
_db_lock = threading.Lock()

def get_database(db_path: str = "linkedin_automation.db") -> Database:
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = Database(db_path)
    return _db_instance

if __name__ == "__main__":
    db = Database("test_v3.db")
    print("Database initialized")
    db.add_contact("Test User")
    print("Contact added")
