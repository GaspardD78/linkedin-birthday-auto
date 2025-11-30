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
from typing import Any, Optional, List

from opentelemetry import trace
from playwright.sync_api import Page, Locator
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ..config.config_manager import get_config
from ..config.config_schema import LinkedInBotConfig
from ..core.auth_manager import AuthManager
from ..core.browser_manager import BrowserManager
from ..monitoring.metrics import BIRTHDAYS_PROCESSED, MESSAGES_SENT_TOTAL
from ..monitoring.prometheus import PrometheusClient
from ..utils.exceptions import (
    SessionExpiredError,
)
from ..utils.logging import get_logger

logger = get_logger(__name__)


class BaseLinkedInBot(ABC):
    """
    Classe abstraite de base pour les bots LinkedIn.
    """

    def __init__(self, config: Optional[LinkedInBotConfig] = None):
        """Initialise le bot."""
        self.config = config or get_config()

        # Managers
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
            self.page.goto("https://www.google.com", timeout=15000)
            return True
        except Exception as e:
            logger.warning(f"Connectivity check failed: {e}")
            return False

    def check_login_status(self) -> bool:
        logger.info("Checking login status...")
        if not self._check_connectivity():
            raise SessionExpiredError("No internet connectivity")

        try:
            self.page.goto("https://www.linkedin.com/feed/", timeout=120000, wait_until="domcontentloaded")
            login_selectors = [
                "img.global-nav__me-photo",
                "button.global-nav__primary-link-me-menu-trigger",
                "div.feed-identity-module",
                "img[alt*='Photo']",
            ]
            for selector in login_selectors:
                try:
                    self.page.wait_for_selector(selector, timeout=30000)
                    logger.info(f"✅ Successfully logged in (via: {selector})")
                    return True
                except PlaywrightTimeoutError:
                    continue

            if "/feed" in self.page.url or "/mynetwork" in self.page.url:
                 return True

            raise PlaywrightTimeoutError("No login indicators found")

        except PlaywrightTimeoutError:
            self.browser_manager.take_screenshot("error_login_verification_failed.png")
            raise SessionExpiredError("Failed to verify login")

    # ═══════════════════════════════════════════════════════════════
    #  STRATEGIE ANTI-FRAGILE (Sélecteurs & Dates)
    # ═══════════════════════════════════════════════════════════════

    def _find_element_by_cascade(self, parent: Any, selectors: List[str]) -> Optional[Locator]:
        """Cherche un élément en essayant une liste de sélecteurs par ordre de priorité."""
        for selector in selectors:
            try:
                element = parent.query_selector(selector)
                if element:
                    logger.debug(f"✓ Element found using strategy: {selector}")
                    return element
            except Exception:
                continue
        return None

    def _get_birthday_type(self, contact_element) -> tuple[str, int]:
        """Détermine le type d'anniversaire avec support multi-langue (FR/EN) via Regex."""
        card_text = contact_element.inner_text().lower()

        # 1. Regex "Aujourd'hui" / "Today"
        today_pattern = r"(aujourd'hui|today|joyeux anniversaire|happy birthday)"
        if re.search(today_pattern, card_text):
            logger.debug("✓ Today detected (regex match)")
            return "today", 0

        # 2. Regex "Hier" / "Yesterday"
        if re.search(r"(hier|yesterday)", card_text):
            return "late", 1

        # 3. Regex Jours écoulés (ex: "il y a 5 jours", "5 days ago")
        days_pattern = r"(\d+)\s*(jours?|days?)"
        match = re.search(days_pattern, card_text)
        if match:
            days_late = int(match.group(1))
            max_days = self.config.birthday_filter.max_days_late
            if 1 <= days_late <= max_days:
                logger.debug(f"✓ Late detected: {days_late} days")
                return "late", days_late
            else:
                logger.debug(f"→ Too late ({days_late} days) - ignoring")
                return "ignore", days_late

        # 4. Fallback sur le parsing de date explicite (ex: "le 10 nov")
        days = self._extract_days_from_date(card_text)
        if days is not None:
            if days == 0: return "today", 0
            elif 1 <= days <= self.config.birthday_filter.max_days_late: return "late", days
            else: return "ignore", days

        return "ignore", 0

    def _extract_days_from_date(self, card_text: str) -> Optional[int]:
        """[RESTAURÉ] Logique complète d'extraction de date."""
        pattern = r"le (\d{1,2}) (janv?\.?|févr?\.?|mars?\.?|avr\.?|mai\.?|juin?\.?|juil\.?|août?\.?|sept?\.?|oct\.?|nov\.?|déc\.?|january?|february?|march?|april?|may|june?|july?|august?|september?|october?|november?|december?)"
        match = re.search(pattern, card_text, re.IGNORECASE)

        if not match:
            return None

        day = int(match.group(1))
        month_str = match.group(2).lower()

        month_mapping = {
            "janv": 1, "janvier": 1, "january": 1,
            "févr": 2, "fev": 2, "février": 2, "february": 2,
            "mars": 3, "march": 3,
            "avr": 4, "avril": 4, "april": 4,
            "mai": 5, "may": 5,
            "juin": 6, "june": 6,
            "juil": 7, "juillet": 7, "july": 7,
            "août": 8, "aout": 8, "august": 8,
            "sept": 9, "septembre": 9, "september": 9,
            "oct": 10, "octobre": 10, "october": 10,
            "nov": 11, "novembre": 11, "november": 11,
            "déc": 12, "dec": 12, "décembre": 12, "december": 12,
        }

        month_key = month_str.rstrip(".")
        month = None
        for key, value in month_mapping.items():
            if month_key.startswith(key):
                month = value
                break

        if month is None:
            return None

        current_year = datetime.now().year
        try:
            birthday_date = datetime(current_year, month, day)
        except ValueError:
            return None

        if birthday_date > datetime.now():
            birthday_date = datetime(current_year - 1, month, day)

        delta = datetime.now() - birthday_date
        return delta.days

    # ═══════════════════════════════════════════════════════════════
    #  EXTRACTION ET NAVIGATION
    # ═══════════════════════════════════════════════════════════════

    def get_birthday_contacts(self) -> dict[str, list]:
        """Navigue vers la page anniversaires et extrait tous les contacts."""
        with self.tracer.start_as_current_span("get_birthday_contacts"):
            logger.info("Navigating to birthdays page...")
            self.page.goto("https://www.linkedin.com/mynetwork/catch-up/birthday/", timeout=120000, wait_until="domcontentloaded")

            card_selector = "div[role='listitem']"
            try:
                self.page.wait_for_selector(card_selector, state="visible", timeout=15000)
            except PlaywrightTimeoutError:
                return {"today": [], "late": []}

            all_contacts = self._scroll_and_collect_contacts(card_selector)
            return self._categorize_birthdays(all_contacts)

    def _scroll_and_collect_contacts(self, card_selector: str, max_scrolls: int = 20) -> list:
        last_card_count = 0
        scroll_attempts = 0
        while scroll_attempts < max_scrolls:
            current_contacts = self.page.query_selector_all(card_selector)
            if len(current_contacts) == last_card_count and scroll_attempts > 0:
                break
            last_card_count = len(current_contacts)
            if current_contacts:
                current_contacts[-1].scroll_into_view_if_needed()
                time.sleep(3)
            scroll_attempts += 1
        return self.page.query_selector_all(card_selector)

    def _categorize_birthdays(self, contacts: list) -> dict[str, list]:
        birthdays = {"today": [], "late": []}
        for contact in contacts:
            try:
                b_type, days = self._get_birthday_type(contact)
                if b_type == "today": birthdays["today"].append(contact)
                elif b_type == "late": birthdays["late"].append((contact, days))
            except Exception: continue
        return birthdays

    def extract_contact_name(self, contact_element) -> Optional[str]:
        paragraphs = contact_element.query_selector_all("p")
        non_name_keywords = ["Célébrez", "anniversaire", "Aujourd'hui", "Message", "Say"]
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

    def send_birthday_message(self, contact_element, is_late: bool = False, days_late: int = 0) -> bool:
        """Envoie un message avec stratégie de retry et nettoyage proactif (Self-Healing)."""
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                return self._send_birthday_message_internal(contact_element, is_late, days_late)
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

        full_name = self.extract_contact_name(contact_element)
        if not full_name: return False
        first_name = self.standardize_first_name(full_name.split()[0])

        logger.info(f"--- Processing birthday for {full_name} ---")

        # 1. CASCADE DE SÉLECTEURS
        message_selectors = [
            '[data-control-name="message"]',
            '[data-control-name="compose_message"]',
            'button[aria-label*="Message"]',
            'a[href*="/messaging/compose"]',
            'button:has-text("Message")',  # EN
            'button:has-text("Envoyer")',  # FR
            '.artdeco-button--secondary'   # Legacy Fallback
        ]

        msg_btn = self._find_element_by_cascade(contact_element, message_selectors)
        if not msg_btn:
            logger.warning("Could not find 'Message' button using any selector strategy")
            return False

        msg_btn.click()

        # Attente modale
        message_box_selector = "div.msg-form__contenteditable[role='textbox']"
        try:
            self.page.wait_for_selector(message_box_selector, state="visible", timeout=10000)
        except Exception:
            logger.error("Message modal not found")
            return False

        message_box = self.page.locator(message_box_selector).last

        # Sélection message
        message_list = self.late_birthday_messages if is_late else self.birthday_messages
        if not message_list: return False
        message = random.choice(message_list).format(name=first_name)

        if self.config.dry_run:
            logger.info(f"[DRY RUN] Would send: '{message}'")
            return True

        # 2. SAISIE SÉCURISÉE
        try:
            message_box.click() # Force focus
            self.random_delay(0.5, 1)
            message_box.fill(message)
        except Exception as e:
            raise Exception(f"Failed to fill message box: {e}")

        # 3. ENVOI
        submit_btn = self.page.locator("button.msg-form__send-button").last
        if submit_btn.is_enabled():
            submit_btn.click()
            logger.info("✅ Message sent successfully")
            MESSAGES_SENT_TOTAL.labels(status="success", type="late" if is_late else "today").inc()
            return True
        else:
            logger.warning("Send button disabled")
            return False

        self._close_all_message_modals()

    def _close_all_message_modals(self) -> None:
        """Ferme toutes les modales de message ouvertes."""
        try:
            close_buttons = self.page.locator("button[data-control-name='overlay.close_conversation_window']")
            count = close_buttons.count()
            if count > 0:
                for _ in range(count):
                    try:
                        close_buttons.first.click(timeout=1000)
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
