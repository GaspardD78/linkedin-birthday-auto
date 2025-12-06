"""
Classe abstraite de base pour tous les bots LinkedIn.

Ce module définit BaseLinkedInBot qui encapsule toute la logique commune
entre les différents types de bots (birthday, unlimited, etc.).
"""

from abc import ABC, abstractmethod
from datetime import datetime
import random
import re
import time
from typing import Any, Optional, List, Union

from opentelemetry import trace
from playwright.sync_api import Page, Locator
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ..config.config_manager import get_config
from ..core.selector_manager import SelectorManager
from ..config.config_schema import LinkedInBotConfig
from ..core.auth_manager import AuthManager
from ..core.browser_manager import BrowserManager
from ..monitoring.metrics import BIRTHDAYS_PROCESSED, MESSAGES_SENT_TOTAL
from ..monitoring.prometheus import PrometheusClient
from ..utils.exceptions import (
    SessionExpiredError,
)
from ..utils.logging import get_logger
from ..utils.date_parser import DateParsingService

logger = get_logger(__name__)


class BaseLinkedInBot(ABC):
    """
    Classe abstraite de base pour les bots LinkedIn.
    """

    def __init__(self, config: Optional[LinkedInBotConfig] = None):
        """Initialise le bot."""
        self.config = config or get_config()

        # Managers
        self.selector_manager = SelectorManager()
        self.browser_manager: Optional[BrowserManager] = None
        self.auth_manager: Optional[AuthManager] = None

        # Monitoring
        self.prometheus_client = PrometheusClient(metrics_dir=self.config.paths.logs_dir)
        self.tracer = trace.get_tracer(__name__)

        # Page Playwright
        self.page: Optional[Page] = None

        # Messages
        self.birthday_messages: list[str] = []
        self.late_birthday_messages: list[str] = []

        # Stats d'exécution
        self.stats = {
            "messages_sent": 0,
            "errors": 0,
            "contacts_processed": 0,
            "start_time": None,
            "end_time": None,
        }

        logger.info(
            f"{self.__class__.__name__} initialized",
            mode=self.config.bot_mode,
            dry_run=self.config.dry_run,
        )

    # ═══════════════════════════════════════════════════════════════
    # MÉTHODES ABSTRAITES
    # ═══════════════════════════════════════════════════════════════

    @abstractmethod
    def run(self) -> dict[str, Any]:
        """Exécute la logique principale du bot."""
        with self.tracer.start_as_current_span("bot_run"):
            return self._run_internal()

    @abstractmethod
    def _run_internal(self) -> dict[str, Any]:
        pass

    # ═══════════════════════════════════════════════════════════════
    # SETUP & TEARDOWN
    # ═══════════════════════════════════════════════════════════════

    def setup(self) -> None:
        logger.info("Setting up bot...")
        self.stats["start_time"] = datetime.now().isoformat()
        self._load_messages()
        self.auth_manager = AuthManager(config=self.config.auth)
        auth_path = self.auth_manager.prepare_auth_state()
        self.browser_manager = BrowserManager(config=self.config.browser)
        proxy_config = self._get_proxy_config() if self.config.proxy.enabled else None

        # LOCALE-LOCK: Force English (US) to ensure reliable text scraping
        browser, context, page = self.browser_manager.create_browser(
            auth_state_path=auth_path, proxy_config=proxy_config
        )

        self.page = page
        logger.info("✅ Bot setup completed")

    def teardown(self) -> None:
        logger.info("Tearing down bot...")
        self.stats["end_time"] = datetime.now().isoformat()
        if self.browser_manager:
            self.browser_manager.close()
        if self.auth_manager:
            keep_file = self.auth_manager.get_auth_source() == "env"
            self.auth_manager.cleanup(keep_file=keep_file)
        if self.prometheus_client:
            self.prometheus_client.write_metrics()
        logger.info("✅ Bot teardown completed")

    def _check_connectivity(self) -> bool:
        try:
            logger.debug("Checking internet connectivity...")
            self.page.goto("https://www.google.com", timeout=30000)
            return True
        except Exception as e:
            logger.warning(f"Connectivity check failed: {e}", exc_info=True)
            return False

    def check_login_status(self) -> bool:
        logger.info("Checking login status...")
        if not self._check_connectivity():
            raise SessionExpiredError("No internet connectivity")

        try:
            # HARDWARE REALISM: Increased timeout to 60s for Pi4
            self.page.goto("https://www.linkedin.com/feed/", timeout=60000, wait_until="domcontentloaded")

            # Use combined selector to wait for ANY login indicator
            combined_selector = self.selector_manager.get_combined_selector("login.indicators")
            try:
                self.page.wait_for_selector(combined_selector, timeout=60000)
                logger.info(f"✅ Successfully logged in")
                return True
            except PlaywrightTimeoutError:
                pass # Continue to check URL

            if "/feed" in self.page.url or "/mynetwork" in self.page.url:
                 return True

            raise PlaywrightTimeoutError("No login indicators found")

        except PlaywrightTimeoutError:
            self.browser_manager.take_screenshot("error_login_verification_failed.png")
            raise SessionExpiredError("Failed to verify login")

    # ═══════════════════════════════════════════════════════════════
    #  STRATEGIE ANTI-FRAGILE (Sélecteurs & Dates)
    # ═══════════════════════════════════════════════════════════════

    def _find_element_by_cascade(self, parent: Any, selectors: Union[List[str], str]) -> Optional[Any]:
        """
        Legacy support for finding an element using a list of selectors.
        Uses Playwright's combined selector syntax (OR) for efficiency.

        Returns:
            ElementHandle (if using query_selector) or None.
            Kept compatible with VisitorBot which expects a handle/truthy return if found, or None.
        """
        if isinstance(selectors, str):
            selectors = [selectors]

        combined_selector = ", ".join(selectors)

        try:
            # Use query_selector to return an ElementHandle immediately (or None)
            # This maintains compatibility with VisitorBot logic which checks 'if element:'
            if hasattr(parent, "query_selector"):
                return parent.query_selector(combined_selector)
            elif isinstance(parent, Locator):
                 # For Locator, we can't easily get an ElementHandle without evaluating
                 # But usually VisitorBot passes ElementHandles from query_selector_all
                 # If we must return a Locator, we must ensure it 'exists'
                 loc = parent.locator(combined_selector).first
                 if loc.count() > 0:
                     return loc
        except Exception:
            pass

        return None

    def _get_birthday_type(self, contact_element: Union[Locator, Any]) -> tuple[str, int]:
        """
        Détermine le type d'anniversaire via DateParsingService.
        Compatible EN (prioritaire) et FR (fallback).
        """
        if isinstance(contact_element, Locator):
             card_text = contact_element.inner_text()
        else:
             card_text = contact_element.inner_text()

        # Utilisation du service optimisé
        try:
            # Tente de parser avec la locale par défaut (EN) puis fallback automatique
            days_diff = DateParsingService.parse_days_diff(card_text, locale='en')

            if days_diff is not None:
                if days_diff == 0:
                    logger.debug(f"✓ Today detected: {card_text.strip()}")
                    return "today", 0
                elif days_diff > 0:
                    max_days = self.config.birthday_filter.max_days_late
                    if days_diff <= max_days:
                        logger.debug(f"✓ Late detected: {days_diff} days ({card_text.strip()})")
                        return "late", days_diff

            return "ignore", 0

        except Exception as e:
            logger.debug(f"Date extraction failed for '{card_text[:20]}...': {e}", exc_info=True)
            return "ignore", 0

    # ═══════════════════════════════════════════════════════════════
    #  EXTRACTION ET NAVIGATION
    # ═══════════════════════════════════════════════════════════════

    def get_birthday_contacts(self) -> dict[str, list]:
        """Navigue vers la page anniversaires et extrait tous les contacts."""
        with self.tracer.start_as_current_span("get_birthday_contacts"):
            logger.info("Navigating to birthdays page...")
            # HARDWARE REALISM: 60s timeout
            self.page.goto("https://www.linkedin.com/mynetwork/catch-up/birthday/", timeout=60000, wait_until="domcontentloaded")

            # Use selector manager combined selector
            card_selector = self.selector_manager.get_combined_selector("birthday.card") or "div[role='listitem']"

            try:
                self.page.wait_for_selector(card_selector, state="visible", timeout=30000)
            except PlaywrightTimeoutError:
                return {"today": [], "late": []}

            all_contacts = self._scroll_and_collect_contacts(card_selector)
            return self._categorize_birthdays(all_contacts)

    def _scroll_and_collect_contacts(self, card_selector: str, max_scrolls: int = 20) -> List[Locator]:
        """
        Scroll la page et collecte tous les contacts d'anniversaire.

        FIX: Extrait les données HTML PENDANT le scroll pour éviter la perte
        d'éléments si LinkedIn décharge le DOM (pagination virtuelle).
        """
        seen_contacts_html = set()  # Track unique contacts by HTML signature
        last_unique_count = 0
        scroll_attempts = 0
        min_scrolls = 10  # Force au moins 10 scrolls pour voir tous les anniversaires

        while scroll_attempts < max_scrolls:
            # Get all current contacts
            current_contacts = self.page.locator(card_selector).all()

            # Store HTML signatures to track uniqueness across scrolls
            for contact in current_contacts:
                try:
                    # Use inner_html as unique signature (contains name, date, etc.)
                    html_sig = contact.inner_html()[:200]  # First 200 chars is enough
                    seen_contacts_html.add(html_sig)
                except:
                    pass  # Skip if element is stale

            current_unique_count = len(seen_contacts_html)

            # Stop if no new contacts found AND we've scrolled at least min_scrolls times
            if current_unique_count == last_unique_count and scroll_attempts >= min_scrolls:
                logger.debug(f"No new contacts after {scroll_attempts} scrolls, stopping")
                break

            last_unique_count = current_unique_count

            # Scroll to load more
            if current_contacts:
                try:
                    # 1. Force scroll to bottom using Keyboard (triggers lazy loading better than element scroll)
                    self.page.keyboard.press("End")
                    time.sleep(1.5)

                    # 2. Also scroll specific element just in case
                    current_contacts[-1].scroll_into_view_if_needed()

                    # HARDWARE REALISM: Slow down scroll
                    time.sleep(2)
                except:
                    break  # Last element might be stale

            scroll_attempts += 1

        logger.info(f"Collected {len(seen_contacts_html)} unique contacts after {scroll_attempts} scrolls")

        # Return fresh locators from final page state
        return self.page.locator(card_selector).all()

    def _categorize_birthdays(self, contacts: list) -> dict[str, list]:
        birthdays = {"today": [], "late": []}
        for contact in contacts:
            try:
                b_type, days = self._get_birthday_type(contact)
                if b_type == "today": birthdays["today"].append(contact)
                elif b_type == "late": birthdays["late"].append((contact, days))
            except Exception: continue
        return birthdays

    def extract_contact_name(self, contact_element: Union[Locator, Any]) -> Optional[str]:
        # Handle Locator vs ElementHandle transparently
        if isinstance(contact_element, Locator):
            paragraphs = contact_element.locator("p").all()
        else:
            paragraphs = contact_element.query_selector_all("p")

        non_name_keywords = ["Célébrez", "anniversaire", "Aujourd'hui", "Message", "Say", "Happy", "Birthday"]
        for p in paragraphs:
            text = p.inner_text().strip()
            if text and 2 < len(text) < 100 and not any(k.lower() in text.lower() for k in non_name_keywords):
                return text
        return None

    def standardize_first_name(self, name: str) -> str:
        if not name: return ""
        return name.split()[0].capitalize()

    # ═══════════════════════════════════════════════════════════════
    #  ENVOI AVEC AUTO-GUÉRISON (Self-Healing)
    # ═══════════════════════════════════════════════════════════════

    def _was_contacted_today(self, contact_name: str) -> bool:
        """
        Vérifie si un contact a déjà été contacté aujourd'hui.

        Args:
            contact_name: Nom du contact

        Returns:
            True si déjà contacté aujourd'hui, False sinon
        """
        if not self.db:
            return False

        try:
            today = datetime.now().date().isoformat()
            daily_count = self.db.get_daily_message_count(date=today)

            # Vérifier si ce contact spécifique a été contacté aujourd'hui
            messages = self.db.get_messages_sent_to_contact(contact_name, years=1)
            for msg in messages:
                msg_date = msg.get("sent_at", "")
                if msg_date.startswith(today):
                    logger.debug(f"Contact {contact_name} already contacted today")
                    return True

            return False

        except Exception as e:
            logger.warning(f"Could not check contact history: {e}")
            return False

    def send_birthday_message(self, contact_element, is_late: bool = False, days_late: int = 0) -> bool:
        """Envoie un message avec stratégie de retry et nettoyage proactif (Self-Healing)."""
        # FIX: Vérifier l'historique AVANT d'essayer d'envoyer
        full_name = self.extract_contact_name(contact_element)
        if not full_name:
            logger.warning("Could not extract name from contact element")
            return False

        if self._was_contacted_today(full_name):
            logger.info(f"⏭️  Skipping {full_name} - already contacted today")
            return False

        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                result = self._send_birthday_message_internal(contact_element, is_late, days_late)

                # FIX: Enregistrer en DB si envoi réussi
                if result and self.db and not self.config.dry_run:
                    try:
                        first_name = self.standardize_first_name(full_name.split()[0])
                        message_list = self.late_birthday_messages if is_late else self.birthday_messages
                        message_text = random.choice(message_list).format(name=first_name) if message_list else ""

                        self.db.add_birthday_message(
                            contact_name=full_name,
                            message_text=message_text,
                            is_late=is_late,
                            days_late=days_late,
                            script_mode=self.config.bot_mode
                        )
                        logger.debug(f"✅ Message recorded in database for {full_name}")
                    except Exception as e:
                        logger.warning(f"Failed to record message in database: {e}")

                return result

            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    logger.info("🩹 Self-healing: Closing all modals and retrying...")
                    self.browser_manager.take_screenshot(f"error_retry_{attempt}.png")
                    self._close_all_message_modals()
                    self.random_delay(2, 3)
                else:
                    logger.error("❌ All attempts failed")
                    return False

    def _send_birthday_message_internal(self, contact_element, is_late: bool, days_late: int) -> bool:
        self._close_all_message_modals() # Cleanup préventif

        # FIX: Le nom est déjà extrait par send_birthday_message, mais on le re-extrait ici
        # car cette fonction peut être appelée directement dans certains cas
        full_name = self.extract_contact_name(contact_element)
        if not full_name:
            logger.warning("Could not extract name from contact element")
            return False
        first_name = self.standardize_first_name(full_name.split()[0])

        logger.info(f"--- Processing birthday for {full_name} ---")

        # CASCADE DE SÉLECTEURS (Priority: Data Attributes > Roles > CSS > Fallback)
        # Using SelectorManager
        msg_btn_locator = self.selector_manager.find_element(contact_element, "messaging.open_button")

        if not msg_btn_locator:
            logger.warning("Configuration error: 'messaging.open_button' selector not found")
            return False

        # Scoped to contact_element, so usually one button, but be safe with .first
        try:
            msg_btn_locator.first.click(timeout=5000)
        except Exception:
            logger.warning("Could not find/click 'Message' button (timeout)")
            # Log HTML context for debugging (without crashing)
            try:
                html_context = contact_element.inner_html()[:500] # Limit size
                logger.debug(f"Failed element context: {html_context}")
            except: pass
            return False

        # Attente modale (Increased Timeout)
        # Using SelectorManager
        try:
             # Wait for at least one text box to appear
            box_selector = self.selector_manager.get_combined_selector("messaging.modal_textarea")
            self.page.wait_for_selector(box_selector, state="visible", timeout=20000)
        except Exception:
            logger.error("Message modal not found (timeout)")
            return False

        # Get the textarea
        message_box_locator = self.selector_manager.find_element(self.page, "messaging.modal_textarea")
        if message_box_locator:
             # We want the LAST one (active modal)
             message_box = message_box_locator.last
        else:
             return False

        # Sélection message
        message_list = self.late_birthday_messages if is_late else self.birthday_messages
        if not message_list:
            logger.warning("No messages loaded")
            return False

        message = random.choice(message_list).format(name=first_name)

        if self.config.dry_run:
            logger.info(f"[DRY RUN] Would send: '{message}'")
            return True

        # 2. SAISIE SÉCURISÉE
        try:
            message_box.click() # Force focus
            self.random_delay(0.5, 1)
            # Use fill instead of press to avoid issues with emojis/special chars
            message_box.fill(message)
        except Exception as e:
            raise Exception(f"Failed to fill message box: {e}")

        # 3. ENVOI
        submit_btn_locator = self.selector_manager.find_element(self.page, "messaging.send_button")

        if submit_btn_locator:
            try:
                # Use click's native auto-wait logic instead of immediate is_enabled check
                submit_btn_locator.last.click(timeout=5000)
                logger.info("✅ Message sent successfully")
                MESSAGES_SENT_TOTAL.labels(status="success", type="late" if is_late else "today").inc()
                return True
            except Exception as e:
                 logger.warning(f"Send button click failed (disabled or timeout): {e}")
                 return False
        else:
            logger.warning("Send button selector not found")
            return False

        self._close_all_message_modals()

    def _close_all_message_modals(self) -> None:
        """Ferme toutes les modales de message ouvertes."""
        try:
            close_buttons = self.selector_manager.find_all(self.page, "messaging.close_overlay")
            # If find_all returns list of Locators, but typically it returns a single Locator matching multiple if we used .all()
            # My find_all implementation returns List[Locator] (result of locator.all())

            if close_buttons:
                for btn in close_buttons:
                    try:
                        btn.click(timeout=2000)
                        self.random_delay(0.2, 0.5)
                    except Exception: break
        except Exception: pass

    # ═══════════════════════════════════════════════════════════════
    #  UTILITAIRES RESTAURÉS (Anti-Bot & Proxy)
    # ═══════════════════════════════════════════════════════════════

    def simulate_human_activity(self) -> None:
        """[RESTAURÉ] Simule une activité humaine aléatoire."""
        actions = [
            lambda: self.page.mouse.wheel(0, random.randint(100, 400)),
            lambda: time.sleep(random.uniform(1.5, 4.0)),
            lambda: self.page.mouse.move(random.randint(300, 800), random.randint(200, 600)),
        ]
        num_actions = random.randint(1, 3)
        for _ in range(num_actions):
            try:
                action = random.choice(actions)
                action()
                time.sleep(random.uniform(0.5, 1.5))
            except Exception as e:
                logger.debug(f"Activity simulation error: {e}")

    def random_delay(self, min_seconds: float = 0.5, max_seconds: float = 1.5) -> None:
        time.sleep(random.uniform(min_seconds, max_seconds))

    def _get_proxy_config(self) -> Optional[dict[str, str]]:
        """[RESTAURÉ] Obtient la configuration proxy."""
        if not self.config.proxy.enabled:
            return None
        try:
            from proxy_manager import ProxyManager
            proxy_manager = ProxyManager()
            if proxy_manager.is_enabled():
                return proxy_manager.get_playwright_proxy_config()
        except ImportError:
            logger.warning("ProxyManager not available")
        return None

    def _load_messages(self) -> None:
        self.birthday_messages = self._load_messages_from_file(self.config.messages.messages_file)
        self.late_birthday_messages = self._load_messages_from_file(self.config.messages.late_messages_file)

    def _load_messages_from_file(self, file_path: str) -> list[str]:
        try:
            with open(file_path, encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError: return []

    def get_stats(self) -> dict: return self.stats.copy()
    def __enter__(self): self.setup(); return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.teardown()
