"""
Module de gestion de la base de données SQLite pour LinkedIn Birthday Auto
Gère les contacts, messages, visites de profils, erreurs et sélecteurs LinkedIn
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
import json
from contextlib import contextmanager


class Database:
    """Classe de gestion de la base de données SQLite"""

    def __init__(self, db_path: str = "linkedin_automation.db"):
        """
        Initialise la connexion à la base de données

        Args:
            db_path: Chemin vers le fichier de base de données
        """
        self.db_path = db_path
        self.init_database()

    @contextmanager
    def get_connection(self):
        """Context manager pour la connexion à la base de données"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Permet l'accès par nom de colonne
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_database(self):
        """Crée les tables si elles n'existent pas"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

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
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_birthday_messages_sent_at
                ON birthday_messages(sent_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_birthday_messages_contact_name
                ON birthday_messages(contact_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_profile_visits_visited_at
                ON profile_visits(visited_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_errors_occurred_at
                ON errors(occurred_at)
            """)

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

    def add_contact(self, name: str, linkedin_url: Optional[str] = None,
                   relationship_score: float = 0.0, notes: Optional[str] = None) -> int:
        """
        Ajoute un nouveau contact

        Args:
            name: Nom du contact
            linkedin_url: URL du profil LinkedIn
            relationship_score: Score de relation (0-100)
            notes: Notes sur le contact

        Returns:
            ID du contact créé
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO contacts (name, linkedin_url, relationship_score, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, linkedin_url, relationship_score, notes, now, now))

            return cursor.lastrowid

    def get_contact_by_name(self, name: str) -> Optional[Dict]:
        """Récupère un contact par son nom"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contacts WHERE name = ?", (name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_contact_last_message(self, name: str, message_date: str):
        """Met à jour la date du dernier message et incrémente le compteur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE contacts
                SET last_message_date = ?,
                    message_count = message_count + 1,
                    updated_at = ?
                WHERE name = ?
            """, (message_date, datetime.now().isoformat(), name))

    # ==================== BIRTHDAY MESSAGES ====================

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

            # Récupérer ou créer le contact
            contact = self.get_contact_by_name(contact_name)
            contact_id = contact['id'] if contact else self.add_contact(contact_name)

            # Enregistrer le message
            sent_at = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO birthday_messages
                (contact_id, contact_name, message_text, sent_at, is_late, days_late, script_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (contact_id, contact_name, message_text, sent_at, is_late, days_late, script_mode))

            # Mettre à jour le contact
            self.update_contact_last_message(contact_name, sent_at)

            return cursor.lastrowid

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

    def get_selector(self, selector_name: str) -> Optional[Dict]:
        """Récupère un sélecteur par son nom"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM linkedin_selectors WHERE selector_name = ?
            """, (selector_name,))
            row = cursor.fetchone()
            return dict(row) if row else None

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

    def get_all_selectors(self) -> List[Dict]:
        """Récupère tous les sélecteurs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM linkedin_selectors ORDER BY page_type, selector_name")
            return [dict(row) for row in cursor.fetchall()]

    # ==================== STATISTICS ====================

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
                       SUM(CASE WHEN is_late = 1 THEN 1 ELSE 0 END) as late_messages
                FROM birthday_messages
                WHERE sent_at >= ?
            """, (cutoff_date,))
            messages_stats = dict(cursor.fetchone())

            # Profils visités
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
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
                    "late": messages_stats['late_messages'],
                    "unique_contacts": unique_contacts
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

            # Combiner les données
            all_dates = set(messages_by_day.keys()) | set(visits_by_day.keys())

            result = []
            for date in sorted(all_dates, reverse=True):
                messages = messages_by_day.get(date, {})
                visits = visits_by_day.get(date, {})

                result.append({
                    "date": date,
                    "messages_count": messages.get('messages_count', 0),
                    "late_messages": messages.get('late_messages', 0),
                    "visits_count": visits.get('visits_count', 0)
                })

            return result

    def get_top_contacts(self, limit: int = 10) -> List[Dict]:
        """Récupère les contacts les plus contactés"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT contact_name, COUNT(*) as message_count, MAX(sent_at) as last_message
                FROM birthday_messages
                GROUP BY contact_name
                ORDER BY message_count DESC, last_message DESC
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    # ==================== MAINTENANCE ====================

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


# Fonction utilitaire pour obtenir l'instance de base de données
_db_instance = None

def get_database() -> Database:
    """Retourne l'instance singleton de la base de données"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


if __name__ == "__main__":
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
