"""
Tests End-to-End pour le workflow complet du bot.

Ces tests simulent un workflow complet d'exécution du bot,
incluant la configuration, l'authentification, et l'exécution.

IMPORTANT:
- Ces tests s'exécutent en mode dry-run par défaut
- Ils ne nécessitent PAS de vraies credentials LinkedIn
- Ils simulent le comportement avec des mocks
- Pour tester avec de vraies credentials, définir LINKEDIN_AUTH_STATE

Pour exécuter:
    pytest tests/e2e/ -v -m e2e
    pytest tests/e2e/test_full_workflow.py::TestFullBotWorkflow -v
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.config_manager import ConfigManager
from src.bots.birthday_bot import BirthdayBot
from src.bots.unlimited_bot import UnlimitedBirthdayBot


@pytest.mark.e2e
class TestFullBotWorkflow:
    """Tests E2E du workflow complet du bot."""

    @pytest.fixture
    def temp_config_file(self):
        """Crée un fichier de config temporaire pour les tests E2E."""
        config_content = """
version: "2.0.0"
dry_run: true
bot_mode: "standard"

browser:
  headless: true
  locale: "fr-FR"

messaging_limits:
  weekly_message_limit: 80
  daily_message_limit: null
  max_messages_per_run: 10

birthday_filter:
  process_today: true
  process_late: false

database:
  enabled: false

delays:
  min_delay_seconds: 2
  max_delay_seconds: 5
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    @pytest.fixture
    def temp_auth_file(self):
        """Crée un fichier d'auth temporaire."""
        auth_data = {
            "cookies": [
                {
                    "name": "li_at",
                    "value": "fake_test_token_for_e2e",
                    "domain": ".linkedin.com",
                    "path": "/",
                    "expires": 9999999999,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "None"
                }
            ],
            "origins": []
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(auth_data, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    @pytest.fixture
    def mock_playwright_environment(self):
        """Mock complet de l'environnement Playwright."""
        # Mock Page
        mock_page = Mock()
        mock_page.goto = Mock()
        mock_page.wait_for_selector = Mock()
        mock_page.wait_for_load_state = Mock()
        mock_page.url = "https://www.linkedin.com/feed/"
        mock_page.screenshot = Mock()
        mock_page.query_selector = Mock()
        mock_page.query_selector_all = Mock(return_value=[])

        # Mock Locator
        mock_locator = Mock()
        mock_locator.count = Mock(return_value=0)
        mock_locator.last = Mock()
        mock_page.locator = Mock(return_value=mock_locator)

        # Mock Context
        mock_context = Mock()
        mock_context.new_page = Mock(return_value=mock_page)
        mock_context.close = Mock()

        # Mock Browser
        mock_browser = Mock()
        mock_browser.new_context = Mock(return_value=mock_context)
        mock_browser.close = Mock()

        # Mock BrowserManager
        mock_browser_manager = Mock()
        mock_browser_manager.browser = mock_browser
        mock_browser_manager.context = mock_context
        mock_browser_manager.page = mock_page
        mock_browser_manager.cleanup = Mock()
        mock_browser_manager.take_screenshot = Mock()

        return mock_browser_manager

    @patch('src.core.base_bot.BrowserManager')
    @patch('src.core.auth_manager.validate_auth', return_value=True)
    def test_standard_bot_complete_workflow_no_birthdays(
        self,
        mock_validate_auth,
        mock_browser_manager_class,
        temp_config_file,
        temp_auth_file,
        mock_playwright_environment
    ):
        """
        Test E2E complet : BirthdayBot sans anniversaires.

        Workflow:
        1. Charger configuration
        2. Initialiser le bot
        3. Vérifier login
        4. Récupérer contacts (aucun)
        5. Terminer sans envoyer de messages
        """
        # Setup
        mock_browser_manager_class.return_value = mock_playwright_environment

        # Force nouvelle instance de ConfigManager
        ConfigManager._instance = None
        config = ConfigManager.get_instance(config_path=temp_config_file).config
        config.auth.auth_file_path = temp_auth_file

        # Exécution
        with BirthdayBot(config=config) as bot:
            # Mock get_birthday_contacts
            bot.get_birthday_contacts = Mock(return_value={
                'today': [],
                'late': []
            })

            result = bot.run()

        # Assertions
        assert result['success'] is True
        assert result['bot_mode'] == 'standard'
        assert result['messages_sent'] == 0
        assert result['contacts_processed'] == 0
        assert result['dry_run'] is True
        assert 'timestamp' in result

        # Vérifier que cleanup a été appelé
        mock_playwright_environment.cleanup.assert_called_once()

    @patch('src.core.base_bot.BrowserManager')
    @patch('src.core.auth_manager.validate_auth', return_value=True)
    def test_standard_bot_complete_workflow_with_birthdays(
        self,
        mock_validate_auth,
        mock_browser_manager_class,
        temp_config_file,
        temp_auth_file,
        mock_playwright_environment
    ):
        """
        Test E2E complet : BirthdayBot avec 5 anniversaires.

        Workflow:
        1. Charger configuration
        2. Initialiser le bot
        3. Vérifier login
        4. Récupérer 5 contacts
        5. Envoyer 5 messages (dry-run)
        6. Nettoyer ressources
        """
        # Setup
        mock_browser_manager_class.return_value = mock_playwright_environment

        ConfigManager._instance = None
        config = ConfigManager.get_instance(config_path=temp_config_file).config
        config.auth.auth_file_path = temp_auth_file

        # Mock contacts
        mock_contacts = []
        for i in range(5):
            mock_contact = Mock()
            mock_contact.inner_text = Mock(return_value=f"Contact {i}\nJob Title")
            mock_contacts.append(mock_contact)

        # Exécution
        with BirthdayBot(config=config) as bot:
            bot.get_birthday_contacts = Mock(return_value={
                'today': mock_contacts,
                'late': []
            })

            bot.send_birthday_message = Mock(return_value=True)

            result = bot.run()

        # Assertions
        assert result['success'] is True
        assert result['messages_sent'] == 5
        assert result['contacts_processed'] == 5
        assert result['birthdays_today'] == 5
        assert result['birthdays_late_ignored'] == 0

        # Vérifier appels
        assert bot.send_birthday_message.call_count == 5
        mock_playwright_environment.cleanup.assert_called_once()

    @patch('src.core.base_bot.BrowserManager')
    @patch('src.core.auth_manager.validate_auth', return_value=True)
    def test_unlimited_bot_complete_workflow(
        self,
        mock_validate_auth,
        mock_browser_manager_class,
        temp_config_file,
        temp_auth_file,
        mock_playwright_environment
    ):
        """
        Test E2E complet : UnlimitedBot avec anniversaires du jour et en retard.

        Workflow:
        1. Charger configuration (mode unlimited)
        2. Initialiser le bot
        3. Vérifier login
        4. Récupérer contacts (today + late)
        5. Envoyer tous les messages
        6. Nettoyer ressources
        """
        # Setup
        mock_browser_manager_class.return_value = mock_playwright_environment

        ConfigManager._instance = None
        config = ConfigManager.get_instance(config_path=temp_config_file).config
        config.bot_mode = "unlimited"
        config.birthday_filter.process_late = True
        config.birthday_filter.max_days_late = 10
        config.auth.auth_file_path = temp_auth_file

        # Mock contacts
        mock_contact_today = Mock()
        mock_contact_today.inner_text = Mock(return_value="Alice Smith\nDesigner")

        mock_contact_late = Mock()
        mock_contact_late.inner_text = Mock(return_value="Bob Johnson\nDeveloper")

        # Exécution
        with UnlimitedBirthdayBot(config=config) as bot:
            bot.get_birthday_contacts = Mock(return_value={
                'today': [mock_contact_today, mock_contact_today],
                'late': [(mock_contact_late, 3), (mock_contact_late, 7)]
            })

            bot.send_birthday_message = Mock(return_value=True)

            result = bot.run()

        # Assertions
        assert result['success'] is True
        assert result['bot_mode'] == 'unlimited'
        assert result['messages_sent'] == 4  # 2 today + 2 late
        assert result['contacts_processed'] == 4
        assert result['birthdays_today'] == 2
        assert result['birthdays_late'] == 2

        # Vérifier que les messages en retard ont bien été appelés avec is_late=True
        calls = bot.send_birthday_message.call_args_list
        assert calls[0][1]['is_late'] is False  # Premier aujourd'hui
        assert calls[1][1]['is_late'] is False  # Deuxième aujourd'hui
        assert calls[2][1]['is_late'] is True   # Premier en retard
        assert calls[2][1]['days_late'] == 3
        assert calls[3][1]['is_late'] is True   # Deuxième en retard
        assert calls[3][1]['days_late'] == 7

        mock_playwright_environment.cleanup.assert_called_once()

    @patch('src.core.base_bot.BrowserManager')
    @patch('src.core.auth_manager.validate_auth', return_value=True)
    def test_bot_workflow_with_errors(
        self,
        mock_validate_auth,
        mock_browser_manager_class,
        temp_config_file,
        temp_auth_file,
        mock_playwright_environment
    ):
        """
        Test E2E : Gestion des erreurs lors de l'envoi.

        Workflow:
        1. Initialiser le bot
        2. Récupérer 3 contacts
        3. Le 2ème message échoue
        4. Vérifier que le bot continue et comptabilise l'erreur
        """
        # Setup
        mock_browser_manager_class.return_value = mock_playwright_environment

        ConfigManager._instance = None
        config = ConfigManager.get_instance(config_path=temp_config_file).config
        config.auth.auth_file_path = temp_auth_file

        # Mock contacts
        mock_contacts = [Mock() for _ in range(3)]
        for i, contact in enumerate(mock_contacts):
            contact.inner_text = Mock(return_value=f"Contact {i}\nJob")

        # Exécution
        with BirthdayBot(config=config) as bot:
            bot.get_birthday_contacts = Mock(return_value={
                'today': mock_contacts,
                'late': []
            })

            # Mock send_birthday_message : succès, échec, succès
            bot.send_birthday_message = Mock(side_effect=[True, False, True])

            result = bot.run()

        # Assertions
        assert result['success'] is True
        assert result['messages_sent'] == 2  # 2 succès sur 3
        assert result['contacts_processed'] == 3
        assert result['errors'] == 1

    @patch('src.core.base_bot.BrowserManager')
    @patch('src.core.auth_manager.validate_auth', return_value=False)
    def test_bot_workflow_authentication_failure(
        self,
        mock_validate_auth,
        mock_browser_manager_class,
        temp_config_file,
        mock_playwright_environment
    ):
        """
        Test E2E : Échec d'authentification.

        Workflow:
        1. Tentative d'initialisation
        2. Authentification échoue
        3. Bot retourne une erreur
        """
        # Setup
        mock_browser_manager_class.return_value = mock_playwright_environment

        ConfigManager._instance = None
        config = ConfigManager.get_instance(config_path=temp_config_file).config

        # Exécution
        with BirthdayBot(config=config) as bot:
            # Mock check_login_status pour retourner False
            bot.check_login_status = Mock(return_value=False)

            result = bot.run()

        # Assertions
        assert result['success'] is False
        assert 'error' in result or result['messages_sent'] == 0


@pytest.mark.e2e
class TestAPIWorkflow:
    """Tests E2E de l'API REST."""

    @pytest.fixture
    def api_client(self):
        """Client de test pour l'API FastAPI."""
        from fastapi.testclient import TestClient
        from src.api.app import app

        return TestClient(app)

    @patch('src.api.app.get_config')
    @patch('src.core.auth_manager.validate_auth', return_value=True)
    def test_health_endpoint(self, mock_validate_auth, mock_get_config, api_client):
        """Test E2E de l'endpoint /health."""
        # Mock config
        from src.config.config_schema import LinkedInBotConfig
        mock_config = LinkedInBotConfig()
        mock_get_config.return_value = mock_config

        # Requête
        response = api_client.get("/health")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
        assert 'version' in data
        assert data['version'] == "2.0.0"
        assert 'timestamp' in data

    def test_root_endpoint(self, api_client):
        """Test E2E de l'endpoint racine /."""
        response = api_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data['name'] == "LinkedIn Birthday Bot API"
        assert data['version'] == "2.0.0"
        assert data['docs'] == "/docs"


# Fixtures pytest communes

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset tous les singletons avant/après chaque test E2E."""
    from src.config.config_manager import ConfigManager

    # Before test
    ConfigManager._instance = None

    yield

    # After test
    ConfigManager._instance = None


# Pour exécuter les tests E2E :
# pytest tests/e2e/ -v -m e2e
# pytest tests/e2e/test_full_workflow.py -v
# pytest tests/e2e/test_full_workflow.py::TestFullBotWorkflow::test_standard_bot_complete_workflow_with_birthdays -v
