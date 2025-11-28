"""
Tests d'intégration pour l'exécution complète des bots.

Ces tests vérifient le flow complet d'exécution avec des mocks
pour les composants externes (Playwright, LinkedIn).
"""

import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock, patch

import pytest

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.bots.birthday_bot import BirthdayBot
from src.bots.unlimited_bot import UnlimitedBirthdayBot
from src.config.config_schema import LinkedInBotConfig


class TestBirthdayBotIntegration:
    """Tests d'intégration pour BirthdayBot."""

    @pytest.fixture
    def integration_config(self):
        """Configuration pour tests d'intégration."""
        config = LinkedInBotConfig()
        config.dry_run = True
        config.bot_mode = "standard"
        config.birthday_filter.process_today = True
        config.birthday_filter.process_late = False
        config.database.enabled = False
        config.browser.headless = True
        return config

    @pytest.fixture
    def mock_playwright_page(self):
        """Page Playwright mockée avec comportements réalistes."""
        page = Mock()

        # Mock navigation
        page.goto = Mock()
        page.wait_for_selector = Mock()
        page.wait_for_load_state = Mock()

        # Mock query selectors
        page.query_selector = Mock()
        page.query_selector_all = Mock(return_value=[])

        # Mock locator
        locator_mock = Mock()
        locator_mock.count = Mock(return_value=0)
        locator_mock.last = Mock()
        page.locator = Mock(return_value=locator_mock)

        # Mock screenshot
        page.screenshot = Mock()

        return page

    @pytest.fixture
    def mock_auth_state(self):
        """Fichier d'auth mocké."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            auth_data = {
                "cookies": [{"name": "li_at", "value": "fake_token", "domain": ".linkedin.com"}],
                "origins": [],
            }
            json.dump(auth_data, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    @patch("src.core.base_bot.BrowserManager")
    @patch("src.core.auth_manager.validate_auth", return_value=True)
    def test_bot_run_with_no_birthdays(
        self,
        mock_validate_auth,
        mock_browser_manager_class,
        integration_config,
        mock_playwright_page,
    ):
        """Test run() quand il n'y a aucun anniversaire."""
        # Setup browser manager mock
        mock_browser_manager = Mock()
        mock_browser_manager.page = mock_playwright_page
        mock_browser_manager.browser = Mock()
        mock_browser_manager.context = Mock()
        mock_browser_manager_class.return_value = mock_browser_manager

        # Mock login check
        mock_playwright_page.url = "https://www.linkedin.com/feed/"

        with BirthdayBot(config=integration_config) as bot:
            # Override get_birthday_contacts pour retourner zéro anniversaire
            bot.get_birthday_contacts = Mock(return_value={"today": [], "late": []})

            result = bot.run()

        # Vérifications
        assert result["success"] is True
        assert result["messages_sent"] == 0
        assert result["contacts_processed"] == 0
        assert result["birthdays_today"] == 0

    @patch("src.core.base_bot.BrowserManager")
    @patch("src.core.auth_manager.validate_auth", return_value=True)
    def test_bot_run_with_birthdays_dry_run(
        self,
        mock_validate_auth,
        mock_browser_manager_class,
        integration_config,
        mock_playwright_page,
    ):
        """Test run() avec des anniversaires en mode dry-run."""
        # Setup browser manager mock
        mock_browser_manager = Mock()
        mock_browser_manager.page = mock_playwright_page
        mock_browser_manager.browser = Mock()
        mock_browser_manager.context = Mock()
        mock_browser_manager_class.return_value = mock_browser_manager

        # Mock login check
        mock_playwright_page.url = "https://www.linkedin.com/feed/"

        # Mock contacts
        mock_contact = Mock()
        mock_contact.inner_text = Mock(return_value="John Doe\nSoftware Engineer")

        with BirthdayBot(config=integration_config) as bot:
            # Override methods
            bot.get_birthday_contacts = Mock(
                return_value={"today": [mock_contact, mock_contact, mock_contact], "late": []}
            )

            bot.send_birthday_message = Mock(return_value=True)

            result = bot.run()

        # Vérifications
        assert result["success"] is True
        assert result["messages_sent"] == 3
        assert result["contacts_processed"] == 3
        assert result["birthdays_today"] == 3
        assert result["dry_run"] is True

        # Vérifier que send_birthday_message a été appelé 3 fois
        assert bot.send_birthday_message.call_count == 3

    @patch("src.core.base_bot.BrowserManager")
    @patch("src.core.auth_manager.validate_auth", return_value=True)
    @patch("src.bots.birthday_bot.get_database")
    def test_bot_respects_weekly_limit(
        self,
        mock_get_db,
        mock_validate_auth,
        mock_browser_manager_class,
        integration_config,
        mock_playwright_page,
    ):
        """Test que le bot respecte la limite hebdomadaire."""
        # Enable database
        integration_config.database.enabled = True
        integration_config.messaging_limits.weekly_message_limit = 80

        # Setup browser manager mock
        mock_browser_manager = Mock()
        mock_browser_manager.page = mock_playwright_page
        mock_browser_manager.browser = Mock()
        mock_browser_manager.context = Mock()
        mock_browser_manager_class.return_value = mock_browser_manager

        # Mock database : 78 messages cette semaine
        mock_db = Mock()
        mock_db.get_weekly_message_count = Mock(return_value=78)
        mock_db.get_daily_message_count = Mock(return_value=0)
        mock_get_db.return_value = mock_db

        # Mock login check
        mock_playwright_page.url = "https://www.linkedin.com/feed/"

        # Mock 5 contacts
        mock_contact = Mock()
        mock_contact.inner_text = Mock(return_value="John Doe\nSoftware Engineer")
        contacts = [mock_contact] * 5

        with BirthdayBot(config=integration_config) as bot:
            bot.db = mock_db

            # Override methods
            bot.get_birthday_contacts = Mock(return_value={"today": contacts, "late": []})

            bot.send_birthday_message = Mock(return_value=True)

            result = bot.run()

        # Vérifications : avec 78/80, on ne peut envoyer que 2 messages
        assert result["success"] is True
        assert result["messages_sent"] == 2
        assert result["contacts_processed"] == 2
        assert bot.send_birthday_message.call_count == 2


class TestUnlimitedBotIntegration:
    """Tests d'intégration pour UnlimitedBirthdayBot."""

    @pytest.fixture
    def integration_config(self):
        """Configuration pour tests d'intégration."""
        config = LinkedInBotConfig()
        config.dry_run = True
        config.bot_mode = "unlimited"
        config.birthday_filter.process_today = True
        config.birthday_filter.process_late = True
        config.birthday_filter.max_days_late = 10
        config.database.enabled = False
        config.browser.headless = True
        return config

    @pytest.fixture
    def mock_playwright_page(self):
        """Page Playwright mockée."""
        page = Mock()
        page.goto = Mock()
        page.wait_for_selector = Mock()
        page.wait_for_load_state = Mock()
        page.query_selector = Mock()
        page.query_selector_all = Mock(return_value=[])
        page.url = "https://www.linkedin.com/feed/"

        locator_mock = Mock()
        locator_mock.count = Mock(return_value=0)
        locator_mock.last = Mock()
        page.locator = Mock(return_value=locator_mock)
        page.screenshot = Mock()

        return page

    @patch("src.core.base_bot.BrowserManager")
    @patch("src.core.auth_manager.validate_auth", return_value=True)
    def test_unlimited_bot_processes_late_birthdays(
        self,
        mock_validate_auth,
        mock_browser_manager_class,
        integration_config,
        mock_playwright_page,
    ):
        """Test que UnlimitedBot traite les anniversaires en retard."""
        # Setup browser manager mock
        mock_browser_manager = Mock()
        mock_browser_manager.page = mock_playwright_page
        mock_browser_manager.browser = Mock()
        mock_browser_manager.context = Mock()
        mock_browser_manager_class.return_value = mock_browser_manager

        # Mock contacts
        mock_contact_today = Mock()
        mock_contact_today.inner_text = Mock(return_value="Alice Smith\nDesigner")

        mock_contact_late = Mock()
        mock_contact_late.inner_text = Mock(return_value="Bob Johnson\nDeveloper")

        with UnlimitedBirthdayBot(config=integration_config) as bot:
            # Override methods
            bot.get_birthday_contacts = Mock(
                return_value={
                    "today": [mock_contact_today, mock_contact_today],
                    "late": [(mock_contact_late, 5), (mock_contact_late, 7)],
                }
            )

            bot.send_birthday_message = Mock(return_value=True)

            result = bot.run()

        # Vérifications : doit traiter les 2 du jour + 2 en retard = 4 total
        assert result["success"] is True
        assert result["messages_sent"] == 4
        assert result["contacts_processed"] == 4
        assert result["birthdays_today"] == 2
        assert result["birthdays_late"] == 2

        # Vérifier les appels à send_birthday_message
        assert bot.send_birthday_message.call_count == 4

        # Vérifier les paramètres des appels
        calls = bot.send_birthday_message.call_args_list

        # Les 2 premiers devraient être is_late=False
        assert calls[0][1]["is_late"] is False
        assert calls[1][1]["is_late"] is False

        # Les 2 suivants devraient être is_late=True
        assert calls[2][1]["is_late"] is True
        assert calls[2][1]["days_late"] == 5
        assert calls[3][1]["is_late"] is True
        assert calls[3][1]["days_late"] == 7

    @patch("src.core.base_bot.BrowserManager")
    @patch("src.core.auth_manager.validate_auth", return_value=True)
    def test_unlimited_bot_respects_max_days_late(
        self,
        mock_validate_auth,
        mock_browser_manager_class,
        integration_config,
        mock_playwright_page,
    ):
        """Test que UnlimitedBot respecte max_days_late."""
        # Limiter à 5 jours
        integration_config.birthday_filter.max_days_late = 5

        # Setup browser manager mock
        mock_browser_manager = Mock()
        mock_browser_manager.page = mock_playwright_page
        mock_browser_manager.browser = Mock()
        mock_browser_manager.context = Mock()
        mock_browser_manager_class.return_value = mock_browser_manager

        # Mock contacts
        mock_contact = Mock()
        mock_contact.inner_text = Mock(return_value="Charlie Brown\nManager")

        with UnlimitedBirthdayBot(config=integration_config) as bot:
            # Contacts en retard : 3j, 5j, 7j, 10j
            # Seulement 3j et 5j devraient être traités
            bot.get_birthday_contacts = Mock(
                return_value={
                    "today": [],
                    "late": [
                        (mock_contact, 3),
                        (mock_contact, 5),
                        (mock_contact, 7),  # Ignoré (> 5)
                        (mock_contact, 10),  # Ignoré (> 5)
                    ],
                }
            )

            bot.send_birthday_message = Mock(return_value=True)

            result = bot.run()

        # Vérifications : seulement 2 contacts (3j et 5j)
        assert result["success"] is True
        assert result["messages_sent"] == 2
        assert result["contacts_processed"] == 2
        assert bot.send_birthday_message.call_count == 2


class TestBotContextManager:
    """Tests du protocol context manager."""

    @patch("src.core.base_bot.BrowserManager")
    @patch("src.core.auth_manager.validate_auth", return_value=True)
    def test_bot_context_manager_cleanup(self, mock_validate_auth, mock_browser_manager_class):
        """Test que le context manager nettoie correctement les ressources."""
        config = LinkedInBotConfig()
        config.dry_run = True

        # Setup browser manager mock
        mock_browser_manager = Mock()
        mock_browser_manager.page = Mock()
        mock_browser_manager.browser = Mock()
        mock_browser_manager.context = Mock()
        mock_browser_manager.cleanup = Mock()
        mock_browser_manager_class.return_value = mock_browser_manager

        with BirthdayBot(config=config) as bot:
            assert bot is not None

        # Vérifier que cleanup a été appelé
        mock_browser_manager.cleanup.assert_called_once()

    @patch("src.core.base_bot.BrowserManager")
    @patch("src.core.auth_manager.validate_auth", return_value=True)
    def test_bot_context_manager_cleanup_on_exception(
        self, mock_validate_auth, mock_browser_manager_class
    ):
        """Test que le cleanup est appelé même en cas d'exception."""
        config = LinkedInBotConfig()
        config.dry_run = True

        # Setup browser manager mock
        mock_browser_manager = Mock()
        mock_browser_manager.page = Mock()
        mock_browser_manager.browser = Mock()
        mock_browser_manager.context = Mock()
        mock_browser_manager.cleanup = Mock()
        mock_browser_manager_class.return_value = mock_browser_manager

        try:
            with BirthdayBot(config=config) as bot:
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Vérifier que cleanup a été appelé malgré l'exception
        mock_browser_manager.cleanup.assert_called_once()


# Fixtures pytest communes


@pytest.fixture
def clean_singletons():
    """Reset les singletons entre les tests."""
    from src.config.config_manager import ConfigManager

    ConfigManager._instance = None
    yield
    ConfigManager._instance = None


# Pour exécuter les tests :
# pytest tests/integration/test_bot_execution.py -v
# pytest tests/integration/test_bot_execution.py -v --cov=src.bots
# pytest tests/integration/test_bot_execution.py::TestBirthdayBotIntegration::test_bot_respects_weekly_limit -v
