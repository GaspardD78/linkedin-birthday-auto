"""
Module de gestion de la base de données SQLite pour LinkedIn Birthday Auto
Gère les contacts, messages, visites de profils, erreurs et sélecteurs LinkedIn

Version 2.1.0 - Corrections audit:
- Mode WAL pour performances
- Thread-safe singleton
- Résolution des connexions nested
- Retry logic pour locks
- Timeout configuré
"""

import sqlite3
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from functools import wraps
import json
from contextlib import contextmanager
import logging

# Configure logging
logger = logging.getLogger(__name__)


def retry_on_lock(max_retries=3, delay=0.5):
    """Decorator pour retry automatique en cas de database lock"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "locked" in str(e) and attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Database locked, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Database operation failed after {max_retries} attempts: {e}")
                        raise
            return None
        return wrapper
    return decorator


class Database:
    """Classe de gestion de la base de données SQLite (thread-safe)"""

    # Version du schéma de BDD pour migrations futures
    SCHEMA_VERSION = "2.1.0"

    def __init__(self, db_path: str = "linkedin_automation.db"):
        """
        Initialise la connexion à la base de données

        Args:
            db_path: Chemin vers le fichier de base de données
        """
        self.db_path = db_path
        self._configure_sqlite()
        self.init_database()

    def _configure_sqlite(self):
        """Configure SQLite pour de meilleures performances et gestion de la concurrence"""
        # Connexion temporaire pour configuration globale
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            # Mode WAL pour better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            # Timeout pour éviter locks immédiats
            conn.execute("PRAGMA busy_timeout=30000")  # 30 secondes
            # Synchronisation NORMAL pour meilleures performances (safe avec WAL)
            conn.execute("PRAGMA synchronous=NORMAL")
            # Cache size (en KB)
            conn.execute("PRAGMA cache_size=-10000")  # 10MB
            logger.info("SQLite configured: WAL mode, 30s timeout, optimized cache")
        finally:
            conn.close()

    @contextmanager
    def get_connection(self):
        """Context manager pour la connexion à la base de données"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Permet l'accès par nom de colonne
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise e
        finally:
            conn.close()

    def init_database(self):
        """Crée les tables si elles n'existent pas"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Table de versioning du schéma
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)

            # Vérifier et enregistrer la version
            cursor.execute("SELECT version FROM schema_version LIMIT 1")
            existing_version = cursor.fetchone()
            if not existing_version:
                cursor.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (self.SCHEMA_VERSION, datetime.now().isoformat())
                )

            # Table contacts
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

            # Table birthday_messages
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

            # Table profile_visits
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

            # Table errors
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

            # Table linkedin_selectors
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

            # Index pour améliorer les performances
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_birthday_messages_sent_at ON birthday_messages(sent_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_birthday_messages_contact_name ON birthday_messages(contact_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_profile_visits_visited_at ON profile_visits(visited_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_profile_visits_url ON profile_visits(profile_url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_occurred_at ON errors(occurred_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name)")

            # Initialiser les sélecteurs par défaut
            self._init_default_selectors(cursor)

    def _init_default_selectors(self, cursor):
        """Initialise les sélecteurs LinkedIn par défaut"""
        default_selectors = [
            {
                "name": "birthday_card",
                "value": "div.occludable-update",
                "page_type": "birthday_feed",
                "description": "Carte d'anniversaire dans le fil"
            },
            {
                "name": "birthday_name",
                "value": "span.update-components-actor__name > span > span > span:first-child",
                "page_type": "birthday_feed",
                "description": "Nom du contact dans la carte d'anniversaire"
            },
            {
                "name": "birthday_date",
                "value": "span.update-components-actor__supplementary-actor-info",
                "page_type": "birthday_feed",
                "description": "Date d'anniversaire affichée"
            },
            {
                "name": "message_button",
                "value": "button.message-anywhere-button",
                "page_type": "birthday_feed",
                "description": "Bouton pour envoyer un message"
            },
            {
                "name": "message_textarea",
                "value": "div.msg-form__contenteditable",
                "page_type": "messaging",
                "description": "Zone de texte pour écrire le message"
            },
            {
                "name": "send_button",
                "value": "button.msg-form__send-button",
                "page_type": "messaging",
                "description": "Bouton d'envoi du message"
            },
            {
                "name": "profile_card",
                "value": "li.reusable-search__result-container",
                "page_type": "search",
                "description": "Carte de profil dans les résultats de recherche"
            }
        ]

        for selector in default_selectors:
            cursor.execute("""
                INSERT OR IGNORE INTO linkedin_selectors
                (selector_name, selector_value, page_type, description, last_validated, is_valid)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                selector["name"],
                selector["value"],
                selector["page_type"],
                selector["description"],
                datetime.now().isoformat(),
                True
            ))

    # ==================== CONTACTS ====================

    @retry_on_lock(max_retries=3)
    def add_contact(self, name: str, linkedin_url: Optional[str] = None,
                   relationship_score: float = 0.0, notes: Optional[str] = None,
                   conn=None) -> int:
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
            cursor.execute("""
                INSERT INTO contacts (name, linkedin_url, relationship_score, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, linkedin_url, relationship_score, notes, now, now))
            return cursor.lastrowid

        if conn:
            return _add(conn.cursor())
        else:
            with self.get_connection() as conn:
                return _add(conn.cursor())

    @retry_on_lock(max_retries=3)
    def get_contact_by_name(self, name: str, conn=None) -> Optional[Dict]:
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

    @retry_on_lock(max_retries=3)
    def update_contact_last_message(self, name: str, message_date: str, conn=None):
        """Met à jour la date du dernier message et incrémente le compteur"""
        def _update(cursor):
            cursor.execute("""
                UPDATE contacts
                SET last_message_date = ?,
                    message_count = message_count + 1,
                    updated_at = ?
                WHERE name = ?
            """, (message_date, datetime.now().isoformat(), name))

        if conn:
            _update(conn.cursor())
        else:
            with self.get_connection() as conn:
                _update(conn.cursor())

    # ==================== BIRTHDAY MESSAGES ====================

    @retry_on_lock(max_retries=3)
    def add_birthday_message(self, contact_name: str, message_text: str,
                            is_late: bool = False, days_late: int = 0,
                            script_mode: str = "routine") -> int:
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
            contact_id = contact['id'] if contact else self.add_contact(contact_name, conn=conn)

            # Enregistrer le message
            sent_at = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO birthday_messages
                (contact_id, contact_name, message_text, sent_at, is_late, days_late, script_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (contact_id, contact_name, message_text, sent_at, is_late, days_late, script_mode))

            # Mettre à jour le contact (en passant la connexion!)
            self.update_contact_last_message(contact_name, sent_at, conn=conn)

            return cursor.lastrowid

    @retry_on_lock(max_retries=3)
    def get_messages_sent_to_contact(self, contact_name: str, years: int = 3) -> List[Dict]:
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
            cutoff_date = (datetime.now() - timedelta(days=365*years)).isoformat()

            cursor.execute("""
                SELECT * FROM birthday_messages
                WHERE contact_name = ? AND sent_at >= ?
                ORDER BY sent_at DESC
            """, (contact_name, cutoff_date))

            return [dict(row) for row in cursor.fetchall()]

    @retry_on_lock(max_retries=3)
    def get_weekly_message_count(self) -> int:
        """Retourne le nombre de messages envoyés cette semaine"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()

            cursor.execute("""
                SELECT COUNT(*) as count FROM birthday_messages
                WHERE sent_at >= ?
            """, (week_ago,))

            return cursor.fetchone()['count']

    @retry_on_lock(max_retries=3)
    def get_daily_message_count(self, date: Optional[str] = None) -> int:
        """Retourne le nombre de messages envoyés pour une date donnée"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if date is None:
                date = datetime.now().date().isoformat()

            cursor.execute("""
                SELECT COUNT(*) as count FROM birthday_messages
                WHERE DATE(sent_at) = ?
            """, (date,))

            return cursor.fetchone()['count']

    # ==================== PROFILE VISITS ====================

    @retry_on_lock(max_retries=3)
    def add_profile_visit(self, profile_name: str, profile_url: Optional[str] = None,
                         source_search: Optional[str] = None, keywords: Optional[List[str]] = None,
                         location: Optional[str] = None, success: bool = True,
                         error_message: Optional[str] = None) -> int:
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

            cursor.execute("""
                INSERT INTO profile_visits
                (profile_name, profile_url, visited_at, source_search, keywords, location, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile_name,
                profile_url,
                datetime.now().isoformat(),
                source_search,
                keywords_json,
                location,
                success,
                error_message
            ))

            return cursor.lastrowid

    @retry_on_lock(max_retries=3)
    def get_daily_visits_count(self, date: Optional[str] = None) -> int:
        """Retourne le nombre de profils visités pour une date donnée"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if date is None:
                date = datetime.now().date().isoformat()

            cursor.execute("""
                SELECT COUNT(*) as count FROM profile_visits
                WHERE DATE(visited_at) = ?
            """, (date,))

            return cursor.fetchone()['count']

    @retry_on_lock(max_retries=3)
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

            cursor.execute("""
                SELECT COUNT(*) as count FROM profile_visits
                WHERE profile_url = ? AND visited_at >= ?
            """, (profile_url, cutoff_date))

            return cursor.fetchone()['count'] > 0

    # ==================== ERRORS ====================

    @retry_on_lock(max_retries=3)
    def log_error(self, script_name: str, error_type: str, error_message: str,
                 error_details: Optional[str] = None, screenshot_path: Optional[str] = None) -> int:
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

            cursor.execute("""
                INSERT INTO errors
                (script_name, error_type, error_message, error_details, screenshot_path, occurred_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                script_name,
                error_type,
                error_message,
                error_details,
                screenshot_path,
                datetime.now().isoformat()
            ))

            return cursor.lastrowid

    @retry_on_lock(max_retries=3)
    def get_recent_errors(self, limit: int = 50) -> List[Dict]:
        """Récupère les erreurs récentes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM errors
                ORDER BY occurred_at DESC
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    # ==================== LINKEDIN SELECTORS ====================

    @retry_on_lock(max_retries=3)
    def get_selector(self, selector_name: str) -> Optional[Dict]:
        """Récupère un sélecteur par son nom"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM linkedin_selectors WHERE selector_name = ?
            """, (selector_name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @retry_on_lock(max_retries=3)
    def update_selector_validation(self, selector_name: str, is_valid: bool):
        """Met à jour le statut de validation d'un sélecteur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if is_valid:
                cursor.execute("""
                    UPDATE linkedin_selectors
                    SET is_valid = 1,
                        last_validated = ?,
                        validation_count = validation_count + 1
                    WHERE selector_name = ?
                """, (datetime.now().isoformat(), selector_name))
            else:
                cursor.execute("""
                    UPDATE linkedin_selectors
                    SET is_valid = 0,
                        last_validated = ?,
                        failure_count = failure_count + 1
                    WHERE selector_name = ?
                """, (datetime.now().isoformat(), selector_name))

    @retry_on_lock(max_retries=3)
    def get_all_selectors(self) -> List[Dict]:
        """Récupère tous les sélecteurs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM linkedin_selectors ORDER BY page_type, selector_name")
            return [dict(row) for row in cursor.fetchall()]

    # ==================== STATISTICS ====================

    @retry_on_lock(max_retries=3)
    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
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
            cursor.execute("""
                SELECT COUNT(*) as total,
                       COALESCE(SUM(CASE WHEN is_late = 1 THEN 1 ELSE 0 END), 0) as late_messages
                FROM birthday_messages
                WHERE sent_at >= ?
            """, (cutoff_date,))
            messages_stats = dict(cursor.fetchone())

            # Profils visités
            cursor.execute("""
                SELECT COUNT(*) as total,
                       COALESCE(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END), 0) as successful
                FROM profile_visits
                WHERE visited_at >= ?
            """, (cutoff_date,))
            visits_stats = dict(cursor.fetchone())

            # Erreurs
            cursor.execute("""
                SELECT COUNT(*) as total,
                       COUNT(DISTINCT error_type) as unique_types
                FROM errors
                WHERE occurred_at >= ?
            """, (cutoff_date,))
            errors_stats = dict(cursor.fetchone())

            # Contacts uniques contactés
            cursor.execute("""
                SELECT COUNT(DISTINCT contact_name) as unique_contacts
                FROM birthday_messages
                WHERE sent_at >= ?
            """, (cutoff_date,))
            unique_contacts = cursor.fetchone()['unique_contacts']

            return {
                "period_days": days,
                "messages": {
                    "total": messages_stats['total'],
                    "on_time": messages_stats['total'] - messages_stats['late_messages'],
                    "late": messages_stats['late_messages']
                },
                "contacts": {
                    "unique": unique_contacts
                },
                "profile_visits": {
                    "total": visits_stats['total'],
                    "successful": visits_stats['successful'],
                    "failed": visits_stats['total'] - visits_stats['successful']
                },
                "errors": {
                    "total": errors_stats['total'],
                    "unique_types": errors_stats['unique_types']
                }
            }

    @retry_on_lock(max_retries=3)
    def get_today_statistics(self) -> Dict[str, int]:
        """
        Récupère les statistiques d'aujourd'hui uniquement

        Returns:
            Dictionnaire avec les statistiques du jour:
            - wishes_sent_total: Total des messages envoyés (all time)
            - wishes_sent_today: Messages envoyés aujourd'hui
            - wishes_sent_week: Messages envoyés cette semaine
            - profiles_visited_total: Total des profils visités (all time)
            - profiles_visited_today: Profils visités aujourd'hui
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()

            # Messages envoyés aujourd'hui
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM birthday_messages
                WHERE sent_at >= ?
            """, (today_start,))
            wishes_sent_today = cursor.fetchone()['count']

            # Messages envoyés cette semaine
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM birthday_messages
                WHERE sent_at >= ?
            """, (week_ago,))
            wishes_sent_week = cursor.fetchone()['count']

            # Total des messages envoyés (all time)
            cursor.execute("SELECT COUNT(*) as count FROM birthday_messages")
            wishes_sent_total = cursor.fetchone()['count']

            # Profils visités aujourd'hui
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM profile_visits
                WHERE visited_at >= ?
            """, (today_start,))
            profiles_visited_today = cursor.fetchone()['count']

            # Total des profils visités (all time)
            cursor.execute("SELECT COUNT(*) as count FROM profile_visits")
            profiles_visited_total = cursor.fetchone()['count']

            return {
                "wishes_sent_total": wishes_sent_total,
                "wishes_sent_today": wishes_sent_today,
                "wishes_sent_week": wishes_sent_week,
                "profiles_visited_total": profiles_visited_total,
                "profiles_visited_today": profiles_visited_today
            }

    @retry_on_lock(max_retries=3)
    def get_daily_activity(self, days: int = 30) -> List[Dict]:
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

            cursor.execute("""
                SELECT
                    DATE(sent_at) as date,
                    COUNT(*) as messages_count,
                    SUM(CASE WHEN is_late = 1 THEN 1 ELSE 0 END) as late_messages
                FROM birthday_messages
                WHERE DATE(sent_at) >= ?
                GROUP BY DATE(sent_at)
                ORDER BY date DESC
            """, (cutoff_date,))

            messages_by_day = {row['date']: dict(row) for row in cursor.fetchall()}

            cursor.execute("""
                SELECT
                    DATE(visited_at) as date,
                    COUNT(*) as visits_count
                FROM profile_visits
                WHERE DATE(visited_at) >= ?
                GROUP BY DATE(visited_at)
                ORDER BY date DESC
            """, (cutoff_date,))

            visits_by_day = {row['date']: dict(row) for row in cursor.fetchall()}

            cursor.execute("""
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as contacts_count
                FROM contacts
                WHERE DATE(created_at) >= ?
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """, (cutoff_date,))

            contacts_by_day = {row['date']: dict(row) for row in cursor.fetchall()}

            # Combiner les données
            all_dates = set(messages_by_day.keys()) | set(visits_by_day.keys()) | set(contacts_by_day.keys())

            result = []
            for date in sorted(all_dates, reverse=True):
                messages = messages_by_day.get(date, {})
                visits = visits_by_day.get(date, {})
                contacts = contacts_by_day.get(date, {})

                result.append({
                    "date": date,
                    "messages": messages.get('messages_count', 0),
                    "late_messages": messages.get('late_messages', 0),
                    "visits": visits.get('visits_count', 0),
                    "contacts": contacts.get('contacts_count', 0)
                })

            return result

    @retry_on_lock(max_retries=3)
    def get_top_contacts(self, limit: int = 10) -> List[Dict]:
        """Récupère les contacts les plus contactés"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
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
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    # ==================== MAINTENANCE ====================

    @retry_on_lock(max_retries=3)
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

            return {
                "errors_deleted": errors_deleted,
                "visits_deleted": visits_deleted
            }

    @retry_on_lock(max_retries=3)
    def export_to_json(self, output_path: str):
        """Exporte toute la base de données en JSON"""
        data = {
            "contacts": [],
            "birthday_messages": [],
            "profile_visits": [],
            "errors": [],
            "linkedin_selectors": []
        }

        with self.get_connection() as conn:
            cursor = conn.cursor()

            for table in data.keys():
                cursor.execute(f"SELECT * FROM {table}")
                data[table] = [dict(row) for row in cursor.fetchall()]

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return output_path

    @retry_on_lock(max_retries=3)
    def vacuum(self) -> Dict[str, Any]:
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

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # VACUUM ne peut pas être exécuté dans une transaction
                conn.isolation_level = None
                cursor.execute("VACUUM")
                conn.isolation_level = ''

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
                "timestamp": datetime.now().isoformat()
            }

            logger.info(
                f"✅ VACUUM completed in {duration:.2f}s, "
                f"saved {space_saved / (1024 * 1024):.2f} MB"
            )

            return result

        except Exception as e:
            logger.error(f"❌ VACUUM failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

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
            logger.warning(f"Could not check fragmentation: {e}")

        return False

    def auto_vacuum_if_needed(self) -> Optional[Dict[str, Any]]:
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
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

    print("\n✓ Tous les tests sont passés avec succès !")
