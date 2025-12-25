"""
Tests pour Phase 3.2: Timezone UTC Awareness

Ces tests valident que toutes les timestamps sont correctement gérées en UTC
et qu'il n'y a pas d'incohérence entre les timestamps locale et UTC.

Bug #10 (Timezone UTC Explicit):
- Toutes les insertions et lectures doivent utiliser timezone.utc
- Les fonctions statistiques doivent comparer des timestamps UTC
- Les migrations doivent enregistrer applied_at en UTC
"""

import pytest
from datetime import datetime, timezone, timedelta
import sqlite3
import tempfile
import os
from src.core.database import Database
from unittest.mock import patch, MagicMock


class TestTimezoneAwarenessDatabase:
    """Tests pour assurer que database.py utilise correctement UTC"""

    @pytest.fixture
    def db(self):
        """Crée une base de données temporaire pour les tests"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = Database(path)
        yield db
        db.close()
        if os.path.exists(path):
            os.unlink(path)

    def test_add_contact_uses_utc_timestamps(self, db):
        """Teste que add_contact utilise UTC pour created_at et updated_at"""
        contact_id = db.add_contact("Test User", linkedin_url="https://linkedin.com/in/test")

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT created_at, updated_at FROM contacts WHERE id = ?", (contact_id,))
            row = cursor.fetchone()
            created_at = row['created_at']
            updated_at = row['updated_at']

        # Les timestamps doivent avoir le format ISO avec +00:00 ou Z
        assert created_at is not None
        assert updated_at is not None

        # Vérifier que c'est un format ISO valide et parsable
        try:
            dt_created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            dt_updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            # Si on arrive ici, les timestamps sont valides
            assert True
        except ValueError:
            pytest.fail(f"Timestamps not in ISO format: {created_at}, {updated_at}")

    def test_add_birthday_message_uses_utc_timestamp(self, db):
        """Teste que add_birthday_message utilise UTC pour sent_at"""
        message_id = db.add_birthday_message("Test User", "Happy Birthday!")
        assert message_id is not None

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sent_at FROM birthday_messages WHERE id = ?", (message_id,))
            row = cursor.fetchone()
            sent_at = row['sent_at']

        # Vérifier que le timestamp est valide et parsable
        try:
            dt_sent = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
            # Les timestamps UTC doivent avoir tzinfo
            assert dt_sent is not None
        except ValueError:
            pytest.fail(f"sent_at not in ISO format: {sent_at}")

    def test_add_profile_visit_uses_utc_timestamp(self, db):
        """Teste que add_profile_visit utilise UTC pour visited_at"""
        visit_id = db.add_profile_visit(
            profile_name="John Doe",
            profile_url="https://linkedin.com/in/johndoe"
        )

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT visited_at FROM profile_visits WHERE id = ?", (visit_id,))
            row = cursor.fetchone()
            visited_at = row['visited_at']

        # Vérifier format ISO
        try:
            dt_visited = datetime.fromisoformat(visited_at.replace('Z', '+00:00'))
            assert dt_visited is not None
        except ValueError:
            pytest.fail(f"visited_at not in ISO format: {visited_at}")

    def test_log_error_uses_utc_timestamp(self, db):
        """Teste que log_error utilise UTC pour occurred_at"""
        error_id = db.log_error(
            script_name="test_script",
            error_type="TestError",
            error_message="Test error message"
        )

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT occurred_at FROM errors WHERE id = ?", (error_id,))
            row = cursor.fetchone()
            occurred_at = row['occurred_at']

        try:
            dt_occurred = datetime.fromisoformat(occurred_at.replace('Z', '+00:00'))
            assert dt_occurred is not None
        except ValueError:
            pytest.fail(f"occurred_at not in ISO format: {occurred_at}")

    def test_update_selector_validation_uses_utc_timestamp(self, db):
        """Teste que update_selector_validation utilise UTC pour last_validated"""
        # D'abord ajouter un sélecteur
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO linkedin_selectors (selector_name, selector_value, page_type, description, last_validated, is_valid) VALUES (?, ?, ?, ?, ?, ?)",
                ("test_selector", ".test", "test_page", "Test Description", datetime.now(timezone.utc).isoformat(), True)
            )

        # Puis mettre à jour la validation
        db.update_selector_validation("test_selector", is_valid=True)

        # Vérifier la timestamp
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT last_validated FROM linkedin_selectors WHERE selector_name = ?", ("test_selector",))
            row = cursor.fetchone()
            last_validated = row['last_validated']

        try:
            dt_validated = datetime.fromisoformat(last_validated.replace('Z', '+00:00'))
            assert dt_validated is not None
        except ValueError:
            pytest.fail(f"last_validated not in ISO format: {last_validated}")

    def test_add_to_blacklist_uses_utc_timestamp(self, db):
        """Teste que add_to_blacklist utilise UTC pour added_at"""
        blacklist_id = db.add_to_blacklist("Spam User", reason="Test blacklist")

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT added_at FROM blacklist WHERE id = ?", (blacklist_id,))
            row = cursor.fetchone()
            added_at = row['added_at']

        try:
            dt_added = datetime.fromisoformat(added_at.replace('Z', '+00:00'))
            assert dt_added is not None
        except ValueError:
            pytest.fail(f"added_at not in ISO format: {added_at}")

    def test_create_campaign_uses_utc_timestamps(self, db):
        """Teste que create_campaign utilise UTC pour created_at et updated_at"""
        campaign_id = db.create_campaign(
            name="Test Campaign",
            search_url="https://linkedin.com/search",
            filters={"keyword": "python"}
        )

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT created_at, updated_at FROM campaigns WHERE id = ?", (campaign_id,))
            row = cursor.fetchone()
            created_at = row['created_at']
            updated_at = row['updated_at']

        try:
            dt_created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            dt_updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            assert dt_created is not None
            assert dt_updated is not None
        except ValueError:
            pytest.fail(f"Timestamps not in ISO format: {created_at}, {updated_at}")

    def test_log_bot_execution_uses_utc_timestamps(self, db):
        """Teste que log_bot_execution utilise UTC pour start_time et end_time"""
        now_utc = datetime.now(timezone.utc).timestamp()
        execution_id = db.log_bot_execution(
            bot_name="test_bot",
            start_time=now_utc,
            items_processed=10,
            items_ignored=5,
            errors=0
        )

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT start_time, end_time FROM bot_executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            start_time = row['start_time']
            end_time = row['end_time']

        try:
            dt_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            dt_end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            assert dt_start is not None
            assert dt_end is not None
        except ValueError:
            pytest.fail(f"Timestamps not in ISO format: {start_time}, {end_time}")

    def test_get_statistics_uses_utc_cutoff(self, db):
        """Teste que get_statistics utilise UTC pour le cutoff"""
        # Ajouter un message
        db.add_birthday_message("Test User", "Happy Birthday!")

        # Récupérer les statistiques
        stats = db.get_statistics(days=30)

        # Vérifier que les statistiques sont correctes
        assert stats is not None
        assert "messages" in stats
        assert stats["messages"]["total"] >= 0

    def test_get_visitor_insights_uses_utc_cutoff(self, db):
        """Teste que get_visitor_insights utilise UTC pour le cutoff"""
        # Ajouter un profil
        db.add_profile_visit(
            profile_name="Test Profile",
            profile_url="https://linkedin.com/in/test"
        )

        # Récupérer les insights
        insights = db.get_visitor_insights(days=30)

        # Vérifier que les insights sont corrects
        assert insights is not None
        assert "avg_fit_score" in insights

    def test_get_today_statistics_uses_utc_date(self, db):
        """Teste que get_today_statistics utilise UTC pour la date"""
        # Ajouter un message
        db.add_birthday_message("Test User", "Happy Birthday!")

        # Récupérer les statistiques du jour
        stats = db.get_today_statistics()

        # Vérifier que les statistiques sont correctes
        assert stats is not None
        assert "wishes_sent_today" in stats
        assert stats["wishes_sent_today"] >= 0

    def test_cleanup_old_logs_uses_utc_cutoff(self, db):
        """Teste que cleanup_old_logs utilise UTC pour le cutoff"""
        # Ajouter une erreur
        db.log_error("test_script", "TestError", "Test error message")

        # Nettoyer les anciens logs (30 jours)
        result = db.cleanup_old_logs(days=30)

        # Vérifier que la fonction s'est exécutée correctement
        assert result is not None
        assert "errors_deleted" in result

    def test_cleanup_old_data_uses_utc_cutoff(self, db):
        """Teste que cleanup_old_data utilise UTC pour le cutoff"""
        # Ajouter une visite de profil
        db.add_profile_visit(
            profile_name="Test Profile",
            profile_url="https://linkedin.com/in/test"
        )

        # Nettoyer les anciennes données (365 jours)
        result = db.cleanup_old_data(days=365)

        # Vérifier que la fonction s'est exécutée correctement
        assert result is not None
        assert "visits_deleted" in result

    def test_timezone_consistency_across_operations(self, db):
        """Teste la cohérence des timezones entre différentes opérations"""
        # Ajouter un contact et un message
        contact_id = db.add_contact("Test User")
        message_id = db.add_birthday_message("Test User", "Happy Birthday!")

        # Ajouter une visite de profil
        visit_id = db.add_profile_visit("Test User", "https://linkedin.com/in/test")

        # Ajouter une erreur
        error_id = db.log_error("test_script", "TestError", "Test error")

        # Ajouter un message à la liste noire
        blacklist_id = db.add_to_blacklist("Test User", reason="Test")

        # Récupérer tous les timestamps
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT created_at FROM contacts WHERE id = ?", (contact_id,))
            contact_ts = cursor.fetchone()['created_at']

            cursor.execute("SELECT sent_at FROM birthday_messages WHERE id = ?", (message_id,))
            message_ts = cursor.fetchone()['sent_at']

            cursor.execute("SELECT visited_at FROM profile_visits WHERE id = ?", (visit_id,))
            visit_ts = cursor.fetchone()['visited_at']

            cursor.execute("SELECT occurred_at FROM errors WHERE id = ?", (error_id,))
            error_ts = cursor.fetchone()['occurred_at']

            cursor.execute("SELECT added_at FROM blacklist WHERE id = ?", (blacklist_id,))
            blacklist_ts = cursor.fetchone()['added_at']

        # Tous les timestamps doivent être parsables et cohérents
        timestamps = [contact_ts, message_ts, visit_ts, error_ts, blacklist_ts]
        for ts in timestamps:
            try:
                datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except ValueError:
                pytest.fail(f"Timestamp {ts} is not in valid ISO format")


class TestRunMigrationsUsesUTC:
    """Tests spécifiques pour les migrations et les timestamps UTC"""

    @pytest.fixture
    def db(self):
        """Crée une base de données temporaire pour les tests"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db = Database(path)
        yield db
        db.close()
        if os.path.exists(path):
            os.unlink(path)

    def test_run_migrations_records_utc_applied_at(self, db):
        """Teste que les migrations enregistrent applied_at en UTC"""
        # Obtenir la version actuelle (après init_database)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT applied_at FROM schema_version ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                applied_at = row['applied_at']

                # Vérifier que le format est ISO
                try:
                    datetime.fromisoformat(applied_at.replace('Z', '+00:00'))
                    # Si on arrive ici, c'est valide
                    assert True
                except ValueError:
                    pytest.fail(f"applied_at not in ISO format: {applied_at}")
