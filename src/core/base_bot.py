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
            logger.warning(f"Connectivity check failed: {e}")
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
        Détermine le type d'anniversaire avec approche "Locale-Lock".

        Stratégie prioritaire :
        1. Extraction de date numérique (ex: "Nov 23")
        2. Comparaison mathématique avec aujourd'hui
        3. Fallback sur regex textuelles (Today/Yesterday)
        """
        # Handle Locator vs ElementHandle transparently
        if isinstance(contact_element, Locator):
             card_text = contact_element.inner_text()
        else:
             card_text = contact_element.inner_text()

        # 1. Extraction numérique (Locale-Lock: Assume English due to Browser Config)
        try:
            days_diff = self._extract_days_from_date(card_text)
            if days_diff is not None:
                if days_diff == 0:
                    logger.debug("✓ Today detected (date calc)")
                    return "today", 0
                elif days_diff > 0:
                     # Only return late if within max limit
                    max_days = self.config.birthday_filter.max_days_late
                    if days_diff <= max_days:
                        logger.debug(f"✓ Late detected: {days_diff} days (date calc)")
                        return "late", days_diff
                    else:
                        return "ignore", days_diff
        except Exception as e:
            logger.debug(f"Date extraction failed: {e}")

        # 2. Fallback Regex (Textual Safety Net)
        # Note: Since we force 'en-US', we prioritize English, but keep French just in case.
        card_text_lower = card_text.lower()

        today_pattern = r"(today|aujourd'hui|joyeux anniversaire|happy birthday)"
        if re.search(today_pattern, card_text_lower):
            logger.debug("✓ Today detected (regex match)")
            return "today", 0

        if re.search(r"(yesterday|hier)", card_text_lower):
             return "late", 1

        # 3. Regex Relative Days (ex: "5 days ago")
        days_pattern = r"(\d+)\s*(days?|jours?)"
        match = re.search(days_pattern, card_text_lower)
        if match:
            days_late = int(match.group(1))
            max_days = self.config.birthday_filter.max_days_late
            if 1 <= days_late <= max_days:
                logger.debug(f"✓ Late detected: {days_late} days")
                return "late", days_late

        return "ignore", 0

    def _extract_days_from_date(self, card_text: str) -> Optional[int]:
        """
        Extracts date from text and returns days passed since that date.
        Handles: "November 23", "Nov 23", "23 Nov", etc.
        """
        # Improved Regex for EN/FR months
        # Matches: Day Month or Month Day
        # Groups: 1=Day, 2=Month OR 3=Month, 4=Day
        pattern = r"(?:(?:le\s+)?(\d{1,2})\s+(janv?\.?|févr?\.?|mars?\.?|avr\.?|mai\.?|juin?\.?|juil\.?|août?\.?|sept?\.?|oct\.?|nov\.?|déc\.?|january?|february?|march?|april?|may|june?|july?|august?|september?|october?|november?|december?))|(?:(janv?\.?|févr?\.?|mars?\.?|avr\.?|mai\.?|juin?\.?|juil\.?|août?\.?|sept?\.?|oct\.?|nov\.?|déc\.?|january?|february?|march?|april?|may|june?|july?|august?|september?|october?|november?|december?)\s+(\d{1,2}))"

        match = re.search(pattern, card_text, re.IGNORECASE)

        if not match:
            return None

        # Determine which group matched
        if match.group(1): # Day Month
            day = int(match.group(1))
            month_str = match.group(2).lower()
        else: # Month Day
            day = int(match.group(4))
            month_str = match.group(3).lower()

        month_mapping = {
            "jan": 1, "fév": 2, "fev": 2, "mar": 3, "apr": 4, "avr": 4, "may": 5, "mai": 5,
            "jun": 6, "jui": 7, "jul": 7, "aug": 8, "aoû": 8, "aou": 8,
            "sep": 9, "oct": 10, "nov": 11, "dec": 12, "déc": 12
        }

        # Helper to match partial months
        month = None
        for key, value in month_mapping.items():
            if key in month_str:
                month = value
                break

        if month is None:
            # Fallback for full names if not caught by 3-letter prefix
            full_mapping = {
                "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
                "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
            }
            if month_str in full_mapping:
                month = full_mapping[month_str]
            else:
                return None

        current_year = datetime.now().year
        try:
            birthday_date = datetime(current_year, month, day)
        except ValueError:
            return None

        # Logic to handle year wrap-around (e.g. in Jan, looking at a Dec birthday?
        # But birthdays are usually 'upcoming' or 'recent'.
        # If today is Jan 1, and birthday is Dec 31, it's late (1 day).
        # If today is Dec 31, and birthday is Jan 1, it's upcoming (ignore).

        now = datetime.now()

        # If birthday is in the future this year, it might be from last year (late)
        # But LinkedIn usually shows "Birthday was on..." or just the date.
        # If it shows the date without year, we assume current year.

        # Calculate delta
        delta = now - birthday_date

        # If delta is negative (birthday in future), assume it refers to last year ONLY if we are looking for late birthdays?
        # Actually LinkedIn list usually has "Recent" and "Upcoming".
        # We only care about Today or Past (Late).

        if delta.days < 0:
             # Check if it was actually last year (e.g. Today Jan 2, Birthday Dec 31)
             last_year_date = datetime(current_year - 1, month, day)
             delta_last = now - last_year_date
             if delta_last.days > 0 and delta_last.days < 360: # Reasonable late window
                 return delta_last.days
             else:
                 # It's truly in the future (Upcoming)
                 return None # Ignore

        return delta.days

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
        last_card_count = 0
        scroll_attempts = 0
        while scroll_attempts < max_scrolls:
            # Upgrade to Locators
            current_contacts = self.page.locator(card_selector).all()
            if len(current_contacts) == last_card_count and scroll_attempts > 0:
                break
            last_card_count = len(current_contacts)
            if current_contacts:
                # Scroll the last one into view
                current_contacts[-1].scroll_into_view_if_needed()
                # HARDWARE REALISM: Slow down scroll
                time.sleep(3)
            scroll_attempts += 1

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
