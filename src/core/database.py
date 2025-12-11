"""
Module de gestion de la base de données SQLite pour LinkedIn Birthday Auto
Gère les contacts, messages, visites de profils, erreurs et sélecteurs LinkedIn

Version 2.3.0 - Robust Nested Transactions:
- Gestion intelligente des transactions imbriquées (Nested Transactions)
- Seul l'appelant le plus externe déclenche le commit
- Rollback complet en cas d'erreur
- Connexions persistantes (Thread-Local) et Mode WAL
"""

from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import wraps
import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any, Optional, Counter

# Configure logging
logger = logging.getLogger(__name__)


def retry_on_lock(max_retries=5, delay=0.2):
    """
    Decorator pour retry automatique en cas de database lock.
    Augmenté pour gérer la contention Worker/API.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Backoff exponentiel avec jitter serait idéal, mais simple exp suffit ici
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
                            current_delay *= 2  # Exponential backoff
                        else:
                            logger.error(
                                f"Database operation failed after {max_retries} attempts (Locked): {e}"
                            )
                            raise
                    else:
                        raise
            return None

        return wrapper

    return decorator


class Database:
    """
    Classe de gestion de la base de données SQLite.
    Utilise un stockage Thread-Local pour maintenir des connexions persistantes
    et gérer les transactions imbriquées.
    """

    # Version du schéma de BDD pour migrations futures
    SCHEMA_VERSION = "2.3.0"

    def __init__(self, db_path: str = "linkedin_automation.db"):
        """
        Initialise la gestion de base de données.

        Args:
            db_path: Chemin vers le fichier de base de données
        """
        self.db_path = db_path
        # Stockage local au thread pour les connexions persistantes
        self._local = threading.local()

        # Initialisation (création fichier si inexistant) via une connexion temporaire
        self.init_database()

    def _create_connection(self) -> sqlite3.Connection:
        """Crée et configure une nouvelle connexion SQLite"""
        conn = sqlite3.connect(self.db_path, timeout=60.0) # Timeout augmenté à 60s
        conn.row_factory = sqlite3.Row

        # Optimisations Performance & Concurrence
        try:
            # 🚀 OPTIMISATIONS RASPBERRY PI 4
            # WAL (Write-Ahead Logging) permet lecture et écriture simultanées
            conn.execute("PRAGMA journal_mode=WAL")
            # Synchronous NORMAL est safe avec WAL et plus rapide
            conn.execute("PRAGMA synchronous=NORMAL")
            # Timeout de busy handler (attente de verrou)
            conn.execute("PRAGMA busy_timeout=60000")
            # Cache size RÉDUIT: 20MB au lieu de 40MB (optimisé Pi4)
            conn.execute("PRAGMA cache_size=-5000")  # -5000 pages = ~20MB
            # Foreign keys enforce
            conn.execute("PRAGMA foreign_keys=ON")
            # Tables temporaires en RAM
            conn.execute("PRAGMA temp_store=MEMORY")
            # Memory-mapped I/O 256MB (accélère lectures)
            conn.execute("PRAGMA mmap_size=268435456")
            # Checkpoint tous les 1000 pages
            conn.execute("PRAGMA wal_autocheckpoint=1000")
            # Limite WAL à 4MB
            conn.execute("PRAGMA journal_size_limit=4194304")
        except Exception as e:
            logger.warning(f"Failed to set PRAGMA optimizations: {e}", exc_info=True)

        return conn

    @contextmanager
    def get_connection(self):
        """
        Context manager transactionnel intelligent.
        Gère les transactions imbriquées : seul l'appelant le plus externe déclenche le commit.
        """
        # Vérifier si une connexion existe déjà pour ce thread
        if not hasattr(self._local, "conn") or self._local.conn is None:
            logger.debug("Creating new thread-local database connection")
            self._local.conn = self._create_connection()
            self._local.transaction_depth = 0

        conn = self._local.conn

        # Vérification basique si la connexion est fermée (programming error)
        try:
            conn.in_transaction
        except sqlite3.ProgrammingError:
            logger.warning("Thread-local connection was closed/invalid, recreating.")
            self._local.conn = self._create_connection()
            self._local.transaction_depth = 0
            conn = self._local.conn

        # Initialisation du compteur de profondeur pour ce thread si nécessaire (safety)
        if not hasattr(self._local, "transaction_depth"):
            self._local.transaction_depth = 0

        try:
            self._local.transaction_depth += 1
            yield conn

            # On décrémente APRES le yield
            self._local.transaction_depth -= 1

            # On ne commit que si on est revenu au niveau 0 (transaction racine)
            if self._local.transaction_depth == 0:
                conn.commit()

        except Exception as e:
            # En cas d'erreur, on rollback tout, peu importe la profondeur
            self._local.transaction_depth = 0 # Reset forcé
            conn.rollback()
            logger.error(f"Database transaction failed (rolled back): {e}")
            raise e

    def close(self):
        """Ferme la connexion du thread courant (nettoyage explicite)"""
        if hasattr(self._local, "conn") and self._local.conn:
            try:
                self._local.conn.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {e}", exc_info=True)
            finally:
                self._local.conn = None
                self._local.transaction_depth = 0

    def init_database(self):
        """Crée les tables si elles n'existent pas"""
        # Utilise get_connection pour bénéficier de la gestion transactionnelle
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Table de versioning du schéma
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """
            )

            # Vérifier et enregistrer la version
            cursor.execute("SELECT version FROM schema_version LIMIT 1")
            existing_version = cursor.fetchone()
            if not existing_version:
                cursor.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (self.SCHEMA_VERSION, datetime.now().isoformat()),
                )

            # Table contacts
            cursor.execute(
                """
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
            """
            )

            # Table birthday_messages
            cursor.execute(
                """
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
            """
            )

            # Table profile_visits
            cursor.execute(
                """
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
            """
            )

            # Table errors
            cursor.execute(
                """
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
            """
            )

            # Table linkedin_selectors
            cursor.execute(
                """
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
            """
            )

            # Table scraped_profiles
            cursor.execute(
                """
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
            """
            )

            # Table campaigns
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    search_url TEXT,
                    filters TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """
            )

            # Table bot_executions
            cursor.execute(
                """
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
            """
            )

            # Table notification_settings
            cursor.execute(
                """
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
            """
            )

            # Table notification_logs
            cursor.execute(
                """
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
            """
            )

            # Table blacklist - Contacts exclus des envois automatiques
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_name TEXT NOT NULL,
                    linkedin_url TEXT,
                    reason TEXT,
                    added_at TEXT NOT NULL,
                    added_by TEXT DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1
                )
            """
            )

            # Index pour améliorer les performances
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_birthday_messages_sent_at ON birthday_messages(sent_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_birthday_messages_contact_name ON birthday_messages(contact_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_profile_visits_visited_at ON profile_visits(visited_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_profile_visits_url ON profile_visits(profile_url)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_errors_occurred_at ON errors(occurred_at)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_contacts_created_at ON contacts(created_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_scraped_profiles_url ON scraped_profiles(profile_url)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_scraped_profiles_scraped_at ON scraped_profiles(scraped_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_notification_logs_event_type ON notification_logs(event_type)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_notification_logs_created_at ON notification_logs(created_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_bot_executions_start_time ON bot_executions(start_time)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_blacklist_contact_name ON blacklist(contact_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_blacklist_linkedin_url ON blacklist(linkedin_url)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_blacklist_is_active ON blacklist(is_active)"
            )

            # Migration: Check columns for scraped_profiles
            cursor.execute("PRAGMA table_info(scraped_profiles)")
            columns = [info[1] for info in cursor.fetchall()]
            new_columns = {
                "headline": "TEXT",
                "summary": "TEXT",
                "skills": "TEXT",
                "certifications": "TEXT",
                "fit_score": "REAL",
                "campaign_id": "INTEGER",
                # New columns for enhanced recruiter tool
                "location": "TEXT",
                "languages": "TEXT",  # JSON array
                "work_history": "TEXT",  # JSON array of positions
                "connection_degree": "TEXT",  # 1st, 2nd, 3rd
                "school": "TEXT",
                "degree": "TEXT",
                "job_title": "TEXT",  # Extracted current job title
                "seniority_level": "TEXT",  # Entry, Mid-Senior, Director, etc.
                "endorsements_count": "INTEGER",
                "profile_picture_url": "TEXT",
                "open_to_work": "INTEGER",  # Boolean: 1 if open to work detected
            }
            # Whitelist stricte pour ALTER TABLE (sécurité SQL injection)
            ALLOWED_COLUMNS = {
                "headline", "summary", "skills", "certifications", "fit_score", "campaign_id",
                "location", "languages", "work_history", "connection_degree", "school", "degree",
                "job_title", "seniority_level", "endorsements_count", "profile_picture_url", "open_to_work"
            }
            ALLOWED_TYPES = {"TEXT", "REAL", "INTEGER", "BLOB"}

            for col, dtype in new_columns.items():
                if col not in columns:
                    # Validation stricte des identifiants (protection SQL injection)
                    if col not in ALLOWED_COLUMNS:
                        logger.error(f"SECURITY: Tentative d'ajout colonne non autorisée: {col}")
                        continue
                    if dtype not in ALLOWED_TYPES:
                        logger.error(f"SECURITY: Type SQL non autorisé: {dtype}")
                        continue

                    try:
                        # Sécurisé car col et dtype sont validés contre whitelist
                        cursor.execute(f"ALTER TABLE scraped_profiles ADD COLUMN {col} {dtype}")
                    except Exception as e:
                        logger.warning(f"Migration error for {col}: {e}")

            # Initialiser les sélecteurs par défaut
            self._init_default_selectors(cursor)

    def _init_default_selectors(self, cursor):
        """Initialise les sélecteurs LinkedIn par défaut"""
        default_selectors = [
            {
                "name": "birthday_card",
                "value": "div.occludable-update",
                "page_type": "birthday_feed",
                "description": "Carte d'anniversaire dans le fil",
            },
            {
                "name": "birthday_name",
                "value": "span.update-components-actor__name > span > span > span:first-child",
                "page_type": "birthday_feed",
                "description": "Nom du contact dans la carte d'anniversaire",
            },
            {
                "name": "birthday_date",
                "value": "span.update-components-actor__supplementary-actor-info",
                "page_type": "birthday_feed",
                "description": "Date d'anniversaire affichée",
            },
            {
                "name": "message_button",
                "value": "button.message-anywhere-button",
                "page_type": "birthday_feed",
                "description": "Bouton pour envoyer un message",
            },
            {
                "name": "message_textarea",
                "value": "div.msg-form__contenteditable",
                "page_type": "messaging",
                "description": "Zone de texte pour écrire le message",
            },
            {
                "name": "send_button",
                "value": "button.msg-form__send-button",
                "page_type": "messaging",
                "description": "Bouton d'envoi du message",
            },
            {
                "name": "profile_card",
                "value": "li.reusable-search__result-container",
                "page_type": "search",
                "description": "Carte de profil dans les résultats de recherche",
            },
        ]

        for selector in default_selectors:
            cursor.execute(
                """
                INSERT OR IGNORE INTO linkedin_selectors
                (selector_name, selector_value, page_type, description, last_validated, is_valid)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    selector["name"],
                    selector["value"],
                    selector["page_type"],
                    selector["description"],
                    datetime.now().isoformat(),
                    True,
                ),
            )

    # ==================== CONTACTS ====================

    @retry_on_lock()
    def add_contact(
        self,
        name: str,
        linkedin_url: Optional[str] = None,
        relationship_score: float = 0.0,
        notes: Optional[str] = None,
        conn=None,
    ) -> int:
        """
        Ajoute un nouveau contact

        Args:
            name: Nom du contact
            linkedin_url: URL du profil LinkedIn
            relationship_score: Score de relation (0-100)
            notes: Notes sur le contact
            conn: Connexion optionnelle (pour éviter nested connections)

        Returns:
            ID du contact créé
        """

        def _add(cursor):
            now = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO contacts (name, linkedin_url, relationship_score, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (name, linkedin_url, relationship_score, notes, now, now),
            )
            return cursor.lastrowid

        if conn:
            return _add(conn.cursor())
        else:
            with self.get_connection() as conn:
                return _add(conn.cursor())

    @retry_on_lock()
    def get_contact_by_name(self, name: str, conn=None) -> Optional[dict]:
        """Récupère un contact par son nom"""

        def _get(cursor):
            cursor.execute("SELECT * FROM contacts WHERE name = ?", (name,))
            row = cursor.fetchone()
            return dict(row) if row else None

        if conn:
            return _get(conn.cursor())
        else:
            with self.get_connection() as conn:
                return _get(conn.cursor())

    @retry_on_lock()
    def update_contact_last_message(self, name: str, message_date: str, conn=None):
        """Met à jour la date du dernier message et incrémente le compteur"""

        def _update(cursor):
            cursor.execute(
                """
                UPDATE contacts
                SET last_message_date = ?,
                    message_count = message_count + 1,
                    updated_at = ?
                WHERE name = ?
            """,
                (message_date, datetime.now().isoformat(), name),
            )

        if conn:
            _update(conn.cursor())
        else:
            with self.get_connection() as conn:
                _update(conn.cursor())

    # ==================== BIRTHDAY MESSAGES ====================

    @retry_on_lock()
    def add_birthday_message(
        self,
        contact_name: str,
        message_text: str,
        is_late: bool = False,
        days_late: int = 0,
        script_mode: str = "routine",
    ) -> int:
        """
        Enregistre un message d'anniversaire envoyé

        Args:
            contact_name: Nom du contact
            message_text: Texte du message envoyé
            is_late: Si le message est en retard
            days_late: Nombre de jours de retard
            script_mode: Mode du script (routine/unlimited)

        Returns:
            ID du message créé
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Récupérer ou créer le contact (en passant la connexion!)
            contact = self.get_contact_by_name(contact_name, conn=conn)
            contact_id = contact["id"] if contact else self.add_contact(contact_name, conn=conn)

            # Enregistrer le message
            sent_at = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO birthday_messages
                (contact_id, contact_name, message_text, sent_at, is_late, days_late, script_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (contact_id, contact_name, message_text, sent_at, is_late, days_late, script_mode),
            )

            # Mettre à jour le contact (en passant la connexion!)
            self.update_contact_last_message(contact_name, sent_at, conn=conn)

            return cursor.lastrowid

    @retry_on_lock()
    def get_messages_sent_to_contact(self, contact_name: str, years: int = 3) -> list[dict]:
        """
        Récupère les messages envoyés à un contact sur les X dernières années

        Args:
            contact_name: Nom du contact
            years: Nombre d'années à consulter

        Returns:
            Liste des messages envoyés
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=365 * years)).isoformat()

            cursor.execute(
                """
                SELECT * FROM birthday_messages
                WHERE contact_name = ? AND sent_at >= ?
                ORDER BY sent_at DESC
            """,
                (contact_name, cutoff_date),
            )

            return [dict(row) for row in cursor.fetchall()]

    @retry_on_lock()
    def get_weekly_message_count(self) -> int:
        """Retourne le nombre de messages envoyés cette semaine"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()

            cursor.execute(
                """
                SELECT COUNT(*) as count FROM birthday_messages
                WHERE sent_at >= ?
            """,
                (week_ago,),
            )

            return cursor.fetchone()["count"]

    @retry_on_lock()
    def get_daily_message_count(self, date: Optional[str] = None) -> int:
        """Retourne le nombre de messages envoyés pour une date donnée"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if date is None:
                date = datetime.now().date().isoformat()

            # Optimization: Use range search instead of DATE() function to use index
            try:
                # date is expected to be YYYY-MM-DD
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                next_day = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")

                cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM birthday_messages
                    WHERE sent_at >= ? AND sent_at < ?
                    """,
                    (date, next_day),
                )
            except ValueError:
                # Fallback for non-standard date formats
                cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM birthday_messages
                    WHERE DATE(sent_at) = ?
                    """,
                    (date,),
                )

            return cursor.fetchone()["count"]

    # ==================== PROFILE VISITS ====================

    @retry_on_lock()
    def add_profile_visit(
        self,
        profile_name: str,
        profile_url: Optional[str] = None,
        source_search: Optional[str] = None,
        keywords: Optional[list[str]] = None,
        location: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> int:
        """
        Enregistre une visite de profil

        Args:
            profile_name: Nom du profil visité
            profile_url: URL du profil
            source_search: Source de la recherche
            keywords: Mots-clés utilisés pour la recherche
            location: Localisation de la recherche
            success: Si la visite a réussi
            error_message: Message d'erreur si échec

        Returns:
            ID de la visite créée
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            keywords_json = json.dumps(keywords) if keywords else None

            cursor.execute(
                """
                INSERT INTO profile_visits
                (profile_name, profile_url, visited_at, source_search, keywords, location, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    profile_name,
                    profile_url,
                    datetime.now().isoformat(),
                    source_search,
                    keywords_json,
                    location,
                    success,
                    error_message,
                ),
            )

            return cursor.lastrowid

    @retry_on_lock()
    def get_daily_visits_count(self, date: Optional[str] = None) -> int:
        """Retourne le nombre de profils visités pour une date donnée"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if date is None:
                date = datetime.now().date().isoformat()

            # Optimization: Use range search instead of DATE() function to use index
            try:
                # date is expected to be YYYY-MM-DD
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                next_day = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")

                cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM profile_visits
                    WHERE visited_at >= ? AND visited_at < ?
                    """,
                    (date, next_day),
                )
            except ValueError:
                # Fallback for non-standard date formats
                cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM profile_visits
                    WHERE DATE(visited_at) = ?
                    """,
                    (date,),
                )

            return cursor.fetchone()["count"]

    @retry_on_lock()
    def is_profile_visited(self, profile_url: str, days: int = 30) -> bool:
        """
        Vérifie si un profil a été visité dans les X derniers jours

        Args:
            profile_url: URL du profil
            days: Nombre de jours à vérifier

        Returns:
            True si déjà visité, False sinon
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute(
                """
                SELECT COUNT(*) as count FROM profile_visits
                WHERE profile_url = ? AND visited_at >= ?
            """,
                (profile_url, cutoff_date),
            )

            return cursor.fetchone()["count"] > 0

    # ==================== ERRORS ====================

    @retry_on_lock()
    def log_error(
        self,
        script_name: str,
        error_type: str,
        error_message: str,
        error_details: Optional[str] = None,
        screenshot_path: Optional[str] = None,
    ) -> int:
        """
        Enregistre une erreur

        Args:
            script_name: Nom du script
            error_type: Type d'erreur
            error_message: Message d'erreur
            error_details: Détails supplémentaires
            screenshot_path: Chemin vers la capture d'écran

        Returns:
            ID de l'erreur créée
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO errors
                (script_name, error_type, error_message, error_details, screenshot_path, occurred_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    script_name,
                    error_type,
                    error_message,
                    error_details,
                    screenshot_path,
                    datetime.now().isoformat(),
                ),
            )

            return cursor.lastrowid

    @retry_on_lock()
    def get_recent_errors(self, limit: int = 50) -> list[dict]:
        """Récupère les erreurs récentes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM errors
                ORDER BY occurred_at DESC
                LIMIT ?
            """,
                (limit,),
            )

            return [dict(row) for row in cursor.fetchall()]

    # ==================== LINKEDIN SELECTORS ====================

    @retry_on_lock()
    def get_selector(self, selector_name: str) -> Optional[dict]:
        """Récupère un sélecteur par son nom"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM linkedin_selectors WHERE selector_name = ?
            """,
                (selector_name,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @retry_on_lock()
    def update_selector_validation(self, selector_name: str, is_valid: bool):
        """Met à jour le statut de validation d'un sélecteur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if is_valid:
                cursor.execute(
                    """
                    UPDATE linkedin_selectors
                    SET is_valid = 1,
                        last_validated = ?,
                        validation_count = validation_count + 1
                    WHERE selector_name = ?
                """,
                    (datetime.now().isoformat(), selector_name),
                )
            else:
                cursor.execute(
                    """
                    UPDATE linkedin_selectors
                    SET is_valid = 0,
                        last_validated = ?,
                        failure_count = failure_count + 1
                    WHERE selector_name = ?
                """,
                    (datetime.now().isoformat(), selector_name),
                )

    @retry_on_lock()
    def get_all_selectors(self) -> list[dict]:
        """Récupère tous les sélecteurs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM linkedin_selectors ORDER BY page_type, selector_name")
            return [dict(row) for row in cursor.fetchall()]

    # ==================== SCRAPED PROFILES ====================

    @retry_on_lock()
    def save_scraped_profile(
        self,
        profile_url: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        full_name: Optional[str] = None,
        headline: Optional[str] = None,
        summary: Optional[str] = None,
        relationship_level: Optional[str] = None,
        current_company: Optional[str] = None,
        education: Optional[str] = None,
        years_experience: Optional[int] = None,
        skills: Optional[list[str]] = None,
        certifications: Optional[list[str]] = None,
        fit_score: Optional[float] = None,
        campaign_id: Optional[int] = None,
        # Enhanced recruiter fields
        location: Optional[str] = None,
        languages: Optional[list[str]] = None,
        work_history: Optional[list[dict]] = None,
        connection_degree: Optional[str] = None,
        school: Optional[str] = None,
        degree: Optional[str] = None,
        job_title: Optional[str] = None,
        seniority_level: Optional[str] = None,
        endorsements_count: Optional[int] = None,
        profile_picture_url: Optional[str] = None,
        open_to_work: Optional[bool] = None,
    ) -> int:
        """
        Enregistre ou met à jour (UPSERT) les données scrapées d'un profil.
        Inclut toutes les données enrichies pour les recruteurs.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            scraped_at = datetime.now().isoformat()
            skills_json = json.dumps(skills) if skills else None
            certs_json = json.dumps(certifications) if certifications else None
            languages_json = json.dumps(languages) if languages else None
            work_history_json = json.dumps(work_history) if work_history else None
            open_to_work_int = 1 if open_to_work else (0 if open_to_work is False else None)

            # UPSERT: INSERT OR REPLACE avec toutes les colonnes enrichies
            sql = """
                INSERT INTO scraped_profiles
                (profile_url, first_name, last_name, full_name, headline, summary, relationship_level,
                 current_company, education, years_experience, skills, certifications, fit_score, scraped_at, campaign_id,
                 location, languages, work_history, connection_degree, school, degree, job_title, seniority_level,
                 endorsements_count, profile_picture_url, open_to_work)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_url) DO UPDATE SET
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    full_name = excluded.full_name,
                    headline = excluded.headline,
                    summary = excluded.summary,
                    relationship_level = excluded.relationship_level,
                    current_company = excluded.current_company,
                    education = excluded.education,
                    years_experience = excluded.years_experience,
                    skills = excluded.skills,
                    certifications = excluded.certifications,
                    fit_score = excluded.fit_score,
                    scraped_at = excluded.scraped_at,
                    location = excluded.location,
                    languages = excluded.languages,
                    work_history = excluded.work_history,
                    connection_degree = excluded.connection_degree,
                    school = excluded.school,
                    degree = excluded.degree,
                    job_title = excluded.job_title,
                    seniority_level = excluded.seniority_level,
                    endorsements_count = excluded.endorsements_count,
                    profile_picture_url = excluded.profile_picture_url,
                    open_to_work = excluded.open_to_work
            """

            params = [
                profile_url, first_name, last_name, full_name, headline, summary, relationship_level,
                current_company, education, years_experience, skills_json, certs_json, fit_score, scraped_at, campaign_id,
                location, languages_json, work_history_json, connection_degree, school, degree, job_title, seniority_level,
                endorsements_count, profile_picture_url, open_to_work_int
            ]

            if campaign_id is not None:
                sql += ", campaign_id = excluded.campaign_id"

            cursor.execute(sql, params)

            return cursor.lastrowid

    @retry_on_lock()
    def get_scraped_profile(self, profile_url: str) -> Optional[dict]:
        """
        Récupère les données scrapées d'un profil par son URL.

        Args:
            profile_url: URL du profil

        Returns:
            Dictionnaire avec les données du profil ou None si non trouvé
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM scraped_profiles WHERE profile_url = ?
            """,
                (profile_url,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @retry_on_lock()
    def get_all_scraped_profiles(self, limit: Optional[int] = None) -> list[dict]:
        """
        Récupère tous les profils scrapés.

        Args:
            limit: Nombre maximal de profils à retourner (None = tous)

        Returns:
            Liste de dictionnaires avec les données des profils
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if limit:
                cursor.execute(
                    """
                    SELECT * FROM scraped_profiles
                    ORDER BY scraped_at DESC
                    LIMIT ?
                """,
                    (limit,),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM scraped_profiles
                    ORDER BY scraped_at DESC
                """
                )

            return [dict(row) for row in cursor.fetchall()]

    @retry_on_lock()
    def export_scraped_data_to_csv(self, output_path: str) -> str:
        """
        Exporte les données scrapées vers un fichier CSV.

        Args:
            output_path: Chemin du fichier CSV de sortie

        Returns:
            Chemin du fichier créé

        Raises:
            Exception: Si l'export échoue
        """
        import csv

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT profile_url, first_name, last_name, full_name,
                       relationship_level, current_company, education,
                       years_experience, scraped_at
                FROM scraped_profiles
                ORDER BY scraped_at DESC
            """
            )

            rows = cursor.fetchall()

            if not rows:
                logger.warning("No scraped profiles found to export")
                # Créer un fichier vide avec headers
                with open(output_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f, delimiter=",")
                    writer.writerow(
                        [
                            "profile_url",
                            "first_name",
                            "last_name",
                            "full_name",
                            "relationship_level",
                            "current_company",
                            "education",
                            "years_experience",
                            "scraped_at",
                        ]
                    )
                return output_path

            # Écrire le CSV
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter=",")

                # Header
                writer.writerow(
                    [
                        "profile_url",
                        "first_name",
                        "last_name",
                        "full_name",
                        "relationship_level",
                        "current_company",
                        "education",
                        "years_experience",
                        "scraped_at",
                    ]
                )

                # Data rows
                for row in rows:
                    writer.writerow(
                        [
                            row["profile_url"],
                            row["first_name"] or "",
                            row["last_name"] or "",
                            row["full_name"] or "",
                            row["relationship_level"] or "",
                            row["current_company"] or "",
                            row["education"] or "",
                            row["years_experience"] if row["years_experience"] is not None else "",
                            row["scraped_at"],
                        ]
                    )

            logger.info(f"Exported {len(rows)} scraped profiles to {output_path}")
            return output_path

    # ==================== BOT EXECUTIONS & VISITOR INSIGHTS ====================

    @retry_on_lock()
    def log_bot_execution(
        self,
        bot_name: str,
        start_time: float,
        items_processed: int,
        items_ignored: int,
        errors: int,
        status: str = "success"
    ) -> int:
        """Enregistre une exécution de bot."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            end_time = datetime.now().isoformat()
            start_iso = datetime.fromtimestamp(start_time).isoformat()

            cursor.execute(
                """
                INSERT INTO bot_executions
                (bot_name, start_time, end_time, items_processed, items_ignored, errors, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (bot_name, start_iso, end_time, items_processed, items_ignored, errors, status),
            )
            return cursor.lastrowid

    @retry_on_lock()
    def get_latest_execution_stats(self, bot_name: Optional[str] = None) -> dict:
        """Récupère les stats de la dernière exécution."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM bot_executions"
            params = []

            if bot_name:
                query += " WHERE bot_name = ?"
                params.append(bot_name)

            query += " ORDER BY start_time DESC LIMIT 1"
            cursor.execute(query, tuple(params))

            row = cursor.fetchone()
            if row:
                return dict(row)
            return {"items_processed": 0, "items_ignored": 0, "errors": 0}

    @retry_on_lock()
    def get_visitor_insights(self, days: int = 30) -> dict[str, Any]:
        """
        Récupère les métriques qualitatives du Visitor Bot.
        - Avg Fit Score
        - Top 5 Skills
        - Funnel stats
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            # 1. Avg Fit Score & Open To Work
            cursor.execute(
                """
                SELECT
                    AVG(fit_score) as avg_score,
                    COUNT(*) as total_scraped,
                    SUM(CASE WHEN fit_score > 70 THEN 1 ELSE 0 END) as qualified_profiles,
                    SUM(CASE WHEN headline LIKE '%Open to Work%' OR headline LIKE '%recherche%' OR headline LIKE '%looking for%' THEN 1 ELSE 0 END) as open_to_work
                FROM scraped_profiles
                WHERE scraped_at >= ?
            """,
                (cutoff_date,),
            )
            stats = dict(cursor.fetchone())

            # 2. Top Skills (Parsing JSON en Python - Optimisé)
            cursor.execute(
                """
                SELECT skills FROM scraped_profiles
                WHERE scraped_at >= ? AND skills IS NOT NULL
                ORDER BY scraped_at DESC LIMIT 200
            """,
                (cutoff_date,)
            )

            skill_counter = Counter()
            for row in cursor.fetchall():
                try:
                    skills_list = json.loads(row["skills"])
                    if isinstance(skills_list, list):
                        skill_counter.update(skills_list)
                except: continue

            top_skills = [{"name": s, "count": c} for s, c in skill_counter.most_common(5)]

            # 3. Funnel Data (Requires data from different tables)
            # Found (Search results estimate - hard to get precise, using visits attempted)
            # Visited (profile_visits)
            # Scraped (scraped_profiles)
            # Qualified (fit_score > 70)

            cursor.execute("SELECT COUNT(*) as count FROM profile_visits WHERE visited_at >= ?", (cutoff_date,))
            visits_count = cursor.fetchone()["count"]

            return {
                "avg_fit_score": round(stats["avg_score"] or 0, 1),
                "open_to_work_count": stats["open_to_work"] or 0,
                "top_skills": top_skills,
                "funnel": {
                    "visited": visits_count,
                    "scraped": stats["total_scraped"] or 0,
                    "qualified": stats["qualified_profiles"] or 0
                }
            }

    # ==================== STATISTICS ====================

    @retry_on_lock()
    def get_statistics(self, days: int = 30) -> dict[str, Any]:
        """
        Récupère les statistiques d'activité

        Args:
            days: Nombre de jours à analyser

        Returns:
            Dictionnaire avec les statistiques
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            # Messages envoyés
            cursor.execute(
                """
                SELECT COUNT(*) as total,
                       COALESCE(SUM(CASE WHEN is_late = 1 THEN 1 ELSE 0 END), 0) as late_messages
                FROM birthday_messages
                WHERE sent_at >= ?
            """,
                (cutoff_date,),
            )
            messages_stats = dict(cursor.fetchone())

            # Profils visités
            cursor.execute(
                """
                SELECT COUNT(*) as total,
                       COALESCE(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END), 0) as successful
                FROM profile_visits
                WHERE visited_at >= ?
            """,
                (cutoff_date,),
            )
            visits_stats = dict(cursor.fetchone())

            # Erreurs
            cursor.execute(
                """
                SELECT COUNT(*) as total,
                       COUNT(DISTINCT error_type) as unique_types
                FROM errors
                WHERE occurred_at >= ?
            """,
                (cutoff_date,),
            )
            errors_stats = dict(cursor.fetchone())

            # Contacts uniques contactés
            cursor.execute(
                """
                SELECT COUNT(DISTINCT contact_name) as unique_contacts
                FROM birthday_messages
                WHERE sent_at >= ?
            """,
                (cutoff_date,),
            )
            unique_contacts = cursor.fetchone()["unique_contacts"]

            return {
                "period_days": days,
                "messages": {
                    "total": messages_stats["total"],
                    "on_time": messages_stats["total"] - messages_stats["late_messages"],
                    "late": messages_stats["late_messages"],
                },
                "contacts": {"unique": unique_contacts},
                "profile_visits": {
                    "total": visits_stats["total"],
                    "successful": visits_stats["successful"],
                    "failed": visits_stats["total"] - visits_stats["successful"],
                },
                "errors": {
                    "total": errors_stats["total"],
                    "unique_types": errors_stats["unique_types"],
                },
            }

    @retry_on_lock()
    def get_today_statistics(self) -> dict[str, int]:
        """
        Récupère les statistiques d'aujourd'hui uniquement

        Returns:
            Dictionnaire avec les statistiques du jour:
            - wishes_sent_total: Total des messages envoyés (all time)
            - wishes_sent_today: Messages envoyés aujourd'hui
            - wishes_sent_week: Messages envoyés cette semaine
            - profiles_visited_total: Total des profils visités (all time)
            - profiles_visited_today: Profils visités aujourd'hui
            - profiles_ignored_today: Profils ignorés aujourd'hui (NEW)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            today_start = (
                datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            )
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()

            # Messages envoyés aujourd'hui
            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM birthday_messages
                WHERE sent_at >= ?
            """,
                (today_start,),
            )
            wishes_sent_today = cursor.fetchone()["count"]

            # Messages envoyés cette semaine
            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM birthday_messages
                WHERE sent_at >= ?
            """,
                (week_ago,),
            )
            wishes_sent_week = cursor.fetchone()["count"]

            # Total des messages envoyés (all time)
            cursor.execute("SELECT COUNT(*) as count FROM birthday_messages")
            wishes_sent_total = cursor.fetchone()["count"]

            # Profils visités aujourd'hui
            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM profile_visits
                WHERE visited_at >= ?
            """,
                (today_start,),
            )
            profiles_visited_today = cursor.fetchone()["count"]

            # Total des profils visités (all time)
            cursor.execute("SELECT COUNT(*) as count FROM profile_visits")
            profiles_visited_total = cursor.fetchone()["count"]

            # Profils ignorés (Basé sur la dernière exécution d'aujourd'hui)
            # C'est une approximation, mais suffisante pour le dashboard
            cursor.execute(
                """
                SELECT SUM(items_ignored) as count
                FROM bot_executions
                WHERE start_time >= ? AND bot_name = 'VisitorBot'
                """,
                (today_start,)
            )
            row = cursor.fetchone()
            profiles_ignored_today = row["count"] if row and row["count"] else 0

            return {
                "wishes_sent_total": wishes_sent_total,
                "wishes_sent_today": wishes_sent_today,
                "wishes_sent_week": wishes_sent_week,
                "profiles_visited_total": profiles_visited_total,
                "profiles_visited_today": profiles_visited_today,
                "profiles_ignored_today": profiles_ignored_today
            }

    @retry_on_lock()
    def get_daily_activity(self, days: int = 30) -> list[dict]:
        """
        Récupère l'activité quotidienne

        Args:
            days: Nombre de jours à analyser

        Returns:
            Liste des activités par jour
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=days)).date().isoformat()

            cursor.execute(
                """
                SELECT
                    DATE(sent_at) as date,
                    COUNT(*) as messages_count,
                    SUM(CASE WHEN is_late = 1 THEN 1 ELSE 0 END) as late_messages
                FROM birthday_messages
                WHERE sent_at >= ?
                GROUP BY DATE(sent_at)
                ORDER BY date DESC
            """,
                (cutoff_date,),
            )

            messages_by_day = {row["date"]: dict(row) for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT
                    DATE(visited_at) as date,
                    COUNT(*) as visits_count
                FROM profile_visits
                WHERE visited_at >= ?
                GROUP BY DATE(visited_at)
                ORDER BY date DESC
            """,
                (cutoff_date,),
            )

            visits_by_day = {row["date"]: dict(row) for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as contacts_count
                FROM contacts
                WHERE created_at >= ?
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """,
                (cutoff_date,),
            )

            contacts_by_day = {row["date"]: dict(row) for row in cursor.fetchall()}

            # Combiner les données
            all_dates = (
                set(messages_by_day.keys())
                | set(visits_by_day.keys())
                | set(contacts_by_day.keys())
            )

            result = []
            for date in sorted(all_dates, reverse=True):
                messages = messages_by_day.get(date, {})
                visits = visits_by_day.get(date, {})
                contacts = contacts_by_day.get(date, {})

                result.append(
                    {
                        "date": date,
                        "messages": messages.get("messages_count", 0),
                        "late_messages": messages.get("late_messages", 0),
                        "visits": visits.get("visits_count", 0),
                        "contacts": contacts.get("contacts_count", 0),
                    }
                )

            return result

    @retry_on_lock()
    def get_top_contacts(self, limit: int = 10) -> list[dict]:
        """Récupère les contacts les plus contactés"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    bm.contact_name as name,
                    c.linkedin_url,
                    COUNT(bm.id) as message_count,
                    MAX(bm.sent_at) as last_message
                FROM birthday_messages bm
                LEFT JOIN contacts c ON bm.contact_id = c.id
                GROUP BY bm.contact_name
                ORDER BY message_count DESC, last_message DESC
                LIMIT ?
            """,
                (limit,),
            )

            return [dict(row) for row in cursor.fetchall()]

    # ==================== CAMPAIGNS ====================

    @retry_on_lock()
    def create_campaign(self, name: str, search_url: str, filters: dict) -> int:
        """Crée une nouvelle campagne de recherche"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            filters_json = json.dumps(filters)

            cursor.execute(
                """
                INSERT INTO campaigns (name, search_url, filters, status, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', ?, ?)
            """,
                (name, search_url, filters_json, now, now),
            )
            return cursor.lastrowid

    @retry_on_lock()
    def get_campaigns(self) -> list[dict]:
        """Récupère toutes les campagnes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    # ==================== MAINTENANCE ====================

    @retry_on_lock()
    def cleanup_old_data(self, days_to_keep: int = 365):
        """
        Supprime les anciennes données

        Args:
            days_to_keep: Nombre de jours de données à conserver
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

            # Supprimer les anciennes erreurs
            cursor.execute("DELETE FROM errors WHERE occurred_at < ?", (cutoff_date,))
            errors_deleted = cursor.rowcount

            # Supprimer les anciennes visites de profils
            cursor.execute("DELETE FROM profile_visits WHERE visited_at < ?", (cutoff_date,))
            visits_deleted = cursor.rowcount

            return {"errors_deleted": errors_deleted, "visits_deleted": visits_deleted}

    @retry_on_lock()
    def export_to_json(self, output_path: str):
        """Exporte toute la base de données en JSON"""
        data = {
            "contacts": [],
            "birthday_messages": [],
            "profile_visits": [],
            "errors": [],
            "linkedin_selectors": [],
        }

        # Whitelist stricte des tables exportables (protection SQL injection)
        ALLOWED_TABLES = {
            "contacts",
            "birthday_messages",
            "profile_visits",
            "errors",
            "linkedin_selectors"
        }

        with self.get_connection() as conn:
            cursor = conn.cursor()

            for table in data.keys():
                # Validation stricte du nom de table
                if table not in ALLOWED_TABLES:
                    logger.error(f"SECURITY: Tentative d'export table non autorisée: {table}")
                    continue

                # Sécurisé car table est validé contre whitelist
                cursor.execute(f"SELECT * FROM {table}")
                data[table] = [dict(row) for row in cursor.fetchall()]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return output_path

    @retry_on_lock()
    def vacuum(self) -> dict[str, Any]:
        """
        Exécute VACUUM pour optimiser la base de données.

        VACUUM défragmente la base SQLite et récupère l'espace disque.
        Particulièrement important sur Raspberry Pi 4 avec SD card.

        Returns:
            Dict avec les statistiques du vacuum

        Note:
            VACUUM peut prendre du temps sur de grandes bases.
            Il est recommandé de l'exécuter pendant les heures creuses.
        """
        logger.info("Starting database VACUUM...")
        start_time = time.time()

        # Get database size before vacuum
        db_size_before = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

        # Define internal function to apply decorator
        @retry_on_lock()
        def _execute_vacuum():
            # Pour VACUUM, on a besoin d'une connexion isolée (pas de transaction)
            # On ne peut pas utiliser get_connection() standard car il est dans un bloc transactionnel
            conn = sqlite3.connect(self.db_path, timeout=60.0)
            try:
                conn.isolation_level = None
                conn.execute("VACUUM")
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)") # Force WAL flush
            finally:
                conn.close()

        try:
            _execute_vacuum()

            # Get database size after vacuum
            db_size_after = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            space_saved = db_size_before - db_size_after
            duration = time.time() - start_time

            result = {
                "success": True,
                "duration_seconds": round(duration, 2),
                "size_before_bytes": db_size_before,
                "size_after_bytes": db_size_after,
                "space_saved_bytes": space_saved,
                "space_saved_mb": round(space_saved / (1024 * 1024), 2),
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                f"✅ VACUUM completed in {duration:.2f}s, "
                f"saved {space_saved / (1024 * 1024):.2f} MB"
            )

            return result

        except Exception as e:
            logger.error(f"❌ VACUUM failed: {e}", exc_info=True)
            return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

    def should_vacuum(self, days_since_last_vacuum: int = 7) -> bool:
        """
        Détermine si un VACUUM est nécessaire.

        Args:
            days_since_last_vacuum: Nombre de jours depuis le dernier VACUUM

        Returns:
            True si VACUUM recommandé, False sinon
        """
        # Vérifier la taille de la base
        if not os.path.exists(self.db_path):
            return False

        db_size = os.path.getsize(self.db_path)

        # VACUUM recommandé si > 10 MB sur Pi4 (économie SD card)
        if db_size > 10 * 1024 * 1024:
            logger.info(f"VACUUM recommended: database size is {db_size / (1024 * 1024):.2f} MB")
            return True

        # Vérifier la fragmentation via page count
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]

                cursor.execute("PRAGMA freelist_count")
                freelist_count = cursor.fetchone()[0]

                # Si plus de 20% de pages libres, VACUUM recommandé
                if page_count > 0:
                    fragmentation_ratio = freelist_count / page_count
                    if fragmentation_ratio > 0.2:
                        logger.info(
                            f"VACUUM recommended: {fragmentation_ratio * 100:.1f}% fragmentation"
                        )
                        return True

        except Exception as e:
            logger.warning(f"Could not check fragmentation: {e}", exc_info=True)

        return False

    def auto_vacuum_if_needed(self) -> Optional[dict[str, Any]]:
        """
        Exécute automatiquement VACUUM si nécessaire.

        Returns:
            Résultat du VACUUM ou None si non nécessaire
        """
        if self.should_vacuum():
            logger.info("Auto-vacuum triggered")
            return self.vacuum()
        else:
            logger.debug("Auto-vacuum skipped: not needed")
            return None

    # ==================== BLACKLIST ====================

    @retry_on_lock()
    def add_to_blacklist(
        self,
        contact_name: str,
        linkedin_url: Optional[str] = None,
        reason: Optional[str] = None,
        added_by: str = "user"
    ) -> int:
        """
        Ajoute un contact à la blacklist.

        Args:
            contact_name: Nom du contact à bloquer
            linkedin_url: URL du profil LinkedIn (optionnel)
            reason: Raison du blocage (optionnel)
            added_by: Qui a ajouté (user, system, import)

        Returns:
            ID de l'entrée créée
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            # Vérifier si déjà dans la blacklist
            cursor.execute(
                """
                SELECT id FROM blacklist
                WHERE contact_name = ? OR (linkedin_url IS NOT NULL AND linkedin_url = ?)
                """,
                (contact_name, linkedin_url)
            )
            existing = cursor.fetchone()

            if existing:
                # Réactiver si désactivé
                cursor.execute(
                    "UPDATE blacklist SET is_active = 1, reason = ?, added_at = ? WHERE id = ?",
                    (reason, now, existing["id"])
                )
                logger.info(f"Blacklist entry reactivated for: {contact_name}")
                return existing["id"]

            cursor.execute(
                """
                INSERT INTO blacklist (contact_name, linkedin_url, reason, added_at, added_by, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (contact_name, linkedin_url, reason, now, added_by)
            )
            logger.info(f"Contact added to blacklist: {contact_name}")
            return cursor.lastrowid

    @retry_on_lock()
    def remove_from_blacklist(self, blacklist_id: int) -> bool:
        """
        Supprime (désactive) une entrée de la blacklist.

        Args:
            blacklist_id: ID de l'entrée à supprimer

        Returns:
            True si supprimé avec succès
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE blacklist SET is_active = 0 WHERE id = ?",
                (blacklist_id,)
            )
            success = cursor.rowcount > 0
            if success:
                logger.info(f"Blacklist entry {blacklist_id} deactivated")
            return success

    @retry_on_lock()
    def is_blacklisted(self, contact_name: str, linkedin_url: Optional[str] = None) -> bool:
        """
        Vérifie si un contact est dans la blacklist.

        Args:
            contact_name: Nom du contact à vérifier
            linkedin_url: URL du profil LinkedIn (optionnel, pour vérification supplémentaire)

        Returns:
            True si le contact est blacklisté
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Vérification par nom (case-insensitive) ou URL
            if linkedin_url:
                cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM blacklist
                    WHERE is_active = 1 AND (
                        LOWER(contact_name) = LOWER(?)
                        OR (linkedin_url IS NOT NULL AND linkedin_url = ?)
                    )
                    """,
                    (contact_name, linkedin_url)
                )
            else:
                cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM blacklist
                    WHERE is_active = 1 AND LOWER(contact_name) = LOWER(?)
                    """,
                    (contact_name,)
                )

            return cursor.fetchone()["count"] > 0

    @retry_on_lock()
    def get_blacklist(self, include_inactive: bool = False) -> list[dict]:
        """
        Récupère la liste complète des contacts blacklistés.

        Args:
            include_inactive: Inclure les entrées désactivées

        Returns:
            Liste des entrées de la blacklist
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if include_inactive:
                cursor.execute(
                    """
                    SELECT id, contact_name, linkedin_url, reason, added_at, added_by, is_active
                    FROM blacklist
                    ORDER BY added_at DESC
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT id, contact_name, linkedin_url, reason, added_at, added_by, is_active
                    FROM blacklist
                    WHERE is_active = 1
                    ORDER BY added_at DESC
                    """
                )

            return [dict(row) for row in cursor.fetchall()]

    @retry_on_lock()
    def get_blacklist_count(self) -> int:
        """Retourne le nombre de contacts blacklistés actifs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM blacklist WHERE is_active = 1")
            return cursor.fetchone()["count"]

    @retry_on_lock()
    def update_blacklist_entry(
        self,
        blacklist_id: int,
        contact_name: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """
        Met à jour une entrée de la blacklist.

        Args:
            blacklist_id: ID de l'entrée à modifier
            contact_name: Nouveau nom (optionnel)
            linkedin_url: Nouvelle URL (optionnel)
            reason: Nouvelle raison (optionnel)

        Returns:
            True si mis à jour avec succès
        """
        updates = []
        params = []

        if contact_name is not None:
            updates.append("contact_name = ?")
            params.append(contact_name)
        if linkedin_url is not None:
            updates.append("linkedin_url = ?")
            params.append(linkedin_url)
        if reason is not None:
            updates.append("reason = ?")
            params.append(reason)

        if not updates:
            return False

        params.append(blacklist_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE blacklist SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )
            return cursor.rowcount > 0


# Fonction utilitaire pour obtenir l'instance de base de données (thread-safe)
_db_instance = None
_db_lock = threading.Lock()


def get_database(db_path: str = "linkedin_automation.db") -> Database:
    """Retourne l'instance singleton de la base de données (thread-safe)"""
    global _db_instance

    # Double-checked locking pattern
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = Database(db_path)
                logger.info(f"Database initialized: {db_path} (schema v{Database.SCHEMA_VERSION})")

    return _db_instance


if __name__ == "__main__":
    # Configuration du logging pour les tests
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Test de la base de données
    db = Database("test_linkedin.db")

    print("✓ Base de données créée avec succès")

    # Test d'ajout de contact
    contact_id = db.add_contact("Jean Dupont", "https://linkedin.com/in/jeandupont", 75.0)
    print(f"✓ Contact créé avec ID: {contact_id}")

    # Test d'ajout de message
    msg_id = db.add_birthday_message("Jean Dupont", "Joyeux anniversaire Jean !", False, 0)
    print(f"✓ Message créé avec ID: {msg_id}")

    # Test de statistiques
    stats = db.get_statistics(30)
    print(f"✓ Statistiques: {stats}")

    # Test d'export
    db.export_to_json("test_export.json")
    print("✓ Export JSON créé")

    # Clean up test DB
    if os.path.exists("test_linkedin.db"):
        os.remove("test_linkedin.db")
    if os.path.exists("test_linkedin.db-shm"):
        os.remove("test_linkedin.db-shm")
    if os.path.exists("test_linkedin.db-wal"):
        os.remove("test_linkedin.db-wal")

    print("\n✓ Tous les tests sont passés avec succès !")
