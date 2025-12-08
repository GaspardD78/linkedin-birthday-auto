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
from typing import Any, Optional, List, Union, Callable, Generator, Tuple
from dataclasses import dataclass

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

@dataclass
class ContactData:
    """Structure de données pour un contact d'anniversaire."""
    name: str
    birthday_type: str  # "today", "late", "ignore"
    days_late: int
    profile_url: Optional[str] = None
    text_snippet: Optional[str] = None

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
        """
        if isinstance(selectors, str):
            selectors = [selectors]

        combined_selector = ", ".join(selectors)

        try:
            if hasattr(parent, "query_selector"):
                return parent.query_selector(combined_selector)
            elif isinstance(parent, Locator):
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
        try:
            card_text = contact_element.inner_text()

            # Utilisation du service optimisé
            days_diff = DateParsingService.parse_days_diff(card_text, locale='en')

            if days_diff is not None:
                if days_diff == 0:
                    logger.debug(f"✓ Today detected: {card_text.strip()[:30]}...")
                    return "today", 0
                elif days_diff > 0:
                    max_days = self.config.birthday_filter.max_days_late
                    if days_diff <= max_days:
                        logger.debug(f"✓ Late detected: {days_diff} days ({card_text.strip()[:30]}...)")
                        return "late", days_diff

            return "ignore", 0

        except Exception as e:
            logger.debug(f"Date extraction failed: {e}")
            return "ignore", 0

    # ═══════════════════════════════════════════════════════════════
    #  EXTRACTION ET NAVIGATION (PROCESS-AS-YOU-GO GENERATOR)
    # ═══════════════════════════════════════════════════════════════

    def _safe_scroll_to_element(self, element: Locator):
        """
        Scroll l'élément au centre du viewport pour éviter l'occlusion par le Header (Sticky).
        Utilise evaluate() pour un alignement précis 'center'.
        """
        try:
            element.evaluate("el => el.scrollIntoView({ behavior: 'auto', block: 'center', inline: 'center' })")
            time.sleep(0.3)
        except Exception as e:
            logger.debug(f"Safe scroll fallback: {e}")
            element.scroll_into_view_if_needed()

    def yield_birthday_contacts(self) -> Generator[Tuple[ContactData, Locator], None, None]:
        """
        Générateur "Process-As-You-Go" qui parcourt la liste des anniversaires.

        Yields:
            Tuple[ContactData, Locator]: Données extraites et Locator frais.

        Avantages:
        1. Evite de stocker des Locators périmés (stale).
        2. Permet au bot de filtrer/agir élément par élément.
        3. Gère le scroll automatiquement.
        """
        with self.tracer.start_as_current_span("yield_birthday_contacts"):
            logger.info("Navigating to birthdays page...")
            self.page.goto("https://www.linkedin.com/mynetwork/catch-up/birthday/", timeout=60000, wait_until="domcontentloaded")

            card_selector = self.selector_manager.get_combined_selector("birthday.card") or "div[role='listitem']"
            try:
                self.page.wait_for_selector(card_selector, state="visible", timeout=30000)
            except PlaywrightTimeoutError:
                logger.info("No birthday cards found (timeout).")
                return

            processed_ids = set()
            no_new_items_count = 0
            max_scrolls = 60
            consecutive_empty_scrolls_limit = 3

            for scroll_idx in range(max_scrolls):
                visible_cards = self.page.locator(card_selector).all()
                new_items_in_pass = 0

                logger.debug(f"Scroll pass {scroll_idx+1}: {len(visible_cards)} visible cards detected.")

                for card in visible_cards:
                    try:
                        # 1. Identification Unique
                        name = self.extract_contact_name(card)
                        if not name: continue

                        if name in processed_ids: continue

                        # 2. Safe Scroll (Center Alignment)
                        self._safe_scroll_to_element(card)

                        # 3. Data Extraction
                        b_type, days_diff = self._get_birthday_type(card)

                        # Extract URL if possible (for fallback robustness)
                        profile_url = self._extract_profile_url(card)

                        contact_data = ContactData(
                            name=name,
                            birthday_type=b_type,
                            days_late=days_diff,
                            profile_url=profile_url,
                            text_snippet=card.inner_text()[:50]
                        )

                        # 4. Yield control to caller
                        yield contact_data, card

                        processed_ids.add(name)
                        new_items_in_pass += 1

                    except Exception as e:
                        logger.warning(f"Error processing card in stream: {e}")
                        continue

                # 5. Scroll Logic
                if new_items_in_pass == 0:
                    no_new_items_count += 1
                else:
                    no_new_items_count = 0

                if no_new_items_count >= consecutive_empty_scrolls_limit:
                    logger.info("End of list reached.")
                    break

                try:
                    self.page.keyboard.press("PageDown")
                    time.sleep(1.5)
                except Exception:
                    break

    def process_birthday_contact(self, data: ContactData, locator: Optional[Locator] = None) -> bool:
        """
        Méthode robuste pour traiter un contact, capable de gérer les éléments périmés.

        Stratégie:
        1. Si un Locator est fourni et valide, l'utiliser (Fast Path).
        2. Si Locator invalide/manquant, tenter de retrouver par nom dans le viewport.
        3. Si échec, naviguer vers l'URL du profil (Robust Fallback).
        """
        logger.info(f"Processing contact: {data.name}")

        # Strategy 1: Fast Path (Locator provided via Generator)
        if locator:
            try:
                # Simple check if attached
                if locator.is_visible():
                    self._safe_scroll_to_element(locator)
                    return self.send_birthday_message(locator, is_late=(data.birthday_type == "late"), days_late=data.days_late)
            except Exception:
                logger.warning(f"Locator for {data.name} is stale/invalid. Trying fallback.")

        # Strategy 2: Re-acquire by text in current viewport
        # Note: This only works if we haven't scrolled away too far
        try:
            logger.info("Attempting re-acquisition by text...")
            # More specific locator strategies could be added here
            fallback_locator = self.page.locator(f"div[role='listitem']:has-text('{data.name}')").first
            if fallback_locator.count() > 0 and fallback_locator.is_visible():
                self._safe_scroll_to_element(fallback_locator)
                return self.send_birthday_message(fallback_locator, is_late=(data.birthday_type == "late"), days_late=data.days_late)
        except Exception:
            pass

        # Strategy 3: Hard Navigation (Slow but Robust)
        if data.profile_url:
            logger.info(f"Fallback: Navigating to profile URL {data.profile_url}")
            try:
                self.page.goto(data.profile_url, timeout=60000, wait_until="domcontentloaded")
                # On profile page, the "Message" button is different
                # We need to adapt send_birthday_message or call a profile-specific method
                # For now, let's try to reuse send_birthday_message logic which looks for 'messaging.open_button'
                # But 'messaging.open_button' selectors might be list-specific.

                # We need profile-specific selectors here.
                # Assuming SelectorManager has them or we use generic text
                msg_btn = self.page.locator("button:has-text('Message')").first
                if msg_btn.is_visible():
                     # Construct a temporary "element" that contains the button (the page body or a wrapper)
                     # Actually send_birthday_message expects a container with the button.
                     # If we pass page.locator("body"), it might work if the selector finds the button inside.
                     return self.send_birthday_message(self.page.locator("body"), is_late=(data.birthday_type == "late"), days_late=data.days_late)
            except Exception as e:
                logger.error(f"Failed profile navigation fallback: {e}")

        return False

    def _extract_profile_url(self, element: Locator) -> Optional[str]:
        try:
            # Look for the main link (often the name)
            link = element.locator("a[href*='/in/']").first
            if link.count() > 0:
                url = link.get_attribute("href")
                if url: return url.split("?")[0] # Clean URL
        except Exception:
            pass
        return None

    def extract_contact_name(self, contact_element: Union[Locator, Any]) -> Optional[str]:
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
        if not self.db:
            return False
        try:
            today = datetime.now().date().isoformat()
            messages = self.db.get_messages_sent_to_contact(contact_name, years=1)
            for msg in messages:
                msg_date = msg.get("sent_at", "")
                if msg_date.startswith(today):
                    return True
            return False
        except Exception as e:
            logger.warning(f"Could not check contact history: {e}")
            return False

    def send_birthday_message(self, contact_element, is_late: bool = False, days_late: int = 0) -> bool:
        full_name = self.extract_contact_name(contact_element)
        if not full_name:
            # Try getting name from page title if on profile page
            try:
                title = self.page.title()
                if "|" in title: full_name = title.split("|")[0].strip()
                elif ")" in title: full_name = title.split(")")[1].strip() # "(1) Name | LinkedIn"
            except: pass

        if not full_name:
            logger.warning("Could not extract name from contact element/page")
            return False

        if self._was_contacted_today(full_name):
            logger.info(f"⏭️  Skipping {full_name} - already contacted today")
            return False

        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                result = self._send_birthday_message_internal(contact_element, is_late, days_late, full_name_override=full_name)

                if result and self.db and not self.config.dry_run:
                    try:
                        message_list = self.late_birthday_messages if is_late else self.birthday_messages
                        first_name = self.standardize_first_name(full_name.split()[0])
                        message_text = random.choice(message_list).format(name=first_name) if message_list else ""

                        self.db.add_birthday_message(
                            contact_name=full_name,
                            message_text=message_text,
                            is_late=is_late,
                            days_late=days_late,
                            script_mode=self.config.bot_mode
                        )
                    except Exception: pass

                return result

            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    logger.info("🩹 Self-healing: Closing all modals and retrying...")
                    self.browser_manager.take_screenshot(f"error_retry_{attempt}.png")
                    self._close_all_message_modals()
                    self.random_delay(2, 3)
                else:
                    return False

    def _send_birthday_message_internal(self, contact_element, is_late: bool, days_late: int, full_name_override: str = None) -> bool:
        self._close_all_message_modals()

        full_name = full_name_override or self.extract_contact_name(contact_element)
        if not full_name: return False
        first_name = self.standardize_first_name(full_name.split()[0])

        logger.info(f"--- Processing birthday for {full_name} ---")

        # 1. Open Modal
        # Try finding button in container
        msg_btn_locator = self.selector_manager.find_element(contact_element, "messaging.open_button")

        # If not found, maybe we are on profile page and contact_element is body?
        # Try generic profile button selector
        if not msg_btn_locator:
            try:
                 msg_btn_locator = self.page.locator("main button.message-anywhere-button, main button:has-text('Message')").first
                 if not msg_btn_locator.count(): msg_btn_locator = None
            except: pass

        if not msg_btn_locator:
            logger.warning("Configuration error: 'messaging.open_button' selector not found")
            return False

        try:
            # 1. Try generic click on first match
            # Note: locator.first refers to the first matching element in DOM order.
            # If the first element is hidden, click() waits for it to be visible.
            # To handle cases where multiple buttons exist but only one is visible/correct,
            # we try to narrow it down if the simple click fails.

            # Simple attempt first
            msg_btn_locator.first.click(timeout=3000)
        except Exception:
            # 2. Retry with Visibility Filter
            # Sometimes there are hidden buttons (e.g. mobile vs desktop) matched by generic selectors.
            try:
                logger.debug("First click failed, searching for visible button...")

                # Note: We rely on manual iteration to find the visible one among matches
                count = msg_btn_locator.count()
                found = False
                for i in range(count):
                    loc = msg_btn_locator.nth(i)
                    if loc.is_visible():
                        loc.click(timeout=3000)
                        found = True
                        break
                if not found:
                     raise Exception("No visible button found")
            except Exception:
                logger.warning("Could not find/click 'Message' button (timeout)")
                return False

        # 2. Wait for Modal
        try:
            box_selector = self.selector_manager.get_combined_selector("messaging.modal_textarea")
            self.page.wait_for_selector(box_selector, state="visible", timeout=20000)
        except Exception:
            logger.error("Message modal not found (timeout)")
            return False

        # Get the textarea
        message_box_locator = self.selector_manager.find_element(self.page, "messaging.modal_textarea")
        if message_box_locator:
             message_box = message_box_locator.last
        else:
             return False

        # 3. Message Selection
        message_list = self.late_birthday_messages if is_late else self.birthday_messages
        if not message_list:
            logger.warning("No messages loaded")
            return False

        message = random.choice(message_list).format(name=first_name)

        if self.config.dry_run:
            logger.info(f"[DRY RUN] Would send: '{message}'")
            return True

        # 4. Fill & Send
        try:
            message_box.click()
            self.random_delay(0.5, 1)
            message_box.fill(message)
        except Exception as e:
            raise Exception(f"Failed to fill message box: {e}")

        submit_btn_locator = self.selector_manager.find_element(self.page, "messaging.send_button")

        if submit_btn_locator:
            try:
                submit_btn_locator.last.click(timeout=5000)
                logger.info("✅ Message sent successfully")
                MESSAGES_SENT_TOTAL.labels(status="success", type="late" if is_late else "today").inc()
                return True
            except Exception as e:
                 logger.warning(f"Send button click failed: {e}")
                 return False
        else:
            logger.warning("Send button selector not found")
            return False

        self._close_all_message_modals()

    def _close_all_message_modals(self) -> None:
        try:
            close_buttons = self.selector_manager.find_all(self.page, "messaging.close_overlay")
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
        """Simule une activité humaine aléatoire."""
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
            except Exception: pass

    def random_delay(self, min_seconds: float = 0.5, max_seconds: float = 1.5) -> None:
        time.sleep(random.uniform(min_seconds, max_seconds))

    def _get_proxy_config(self) -> Optional[dict[str, str]]:
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
