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
    AccountRestrictedError,
    CaptchaRequiredError,
    LinkedInBotError,
    is_critical_error,
)
from ..utils.logging import get_logger
from ..utils.date_parser import DateParsingService

logger = get_logger(__name__)

# Import conditionnel pour éviter les erreurs d'import circulaire
def _get_notification_service(db_path: str = "/app/data/linkedin.db"):
    """Lazy import du service de notification pour éviter import circulaire."""
    try:
        from ..services.notification_sync import get_sync_notification_service
        return get_sync_notification_service(db_path)
    except Exception as e:
        logger.debug(f"Notification service not available: {e}")
        return None

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

        # Database reference (initialized by child classes)
        self.db = None

        # Stats d'exécution
        self.stats = {
            "messages_sent": 0,
            "errors": 0,
            "contacts_processed": 0,
            "start_time": None,
            "end_time": None,
        }

        # Service de notification (initialisé en lazy)
        self._notification_service = None
        self._critical_error_occurred = False
        self._critical_error_message = None

        logger.info(
            f"{self.__class__.__name__} initialized",
            mode=self.config.bot_mode,
            dry_run=self.config.dry_run,
        )

    def _get_notifier(self):
        """Retourne le service de notification (lazy init)."""
        if self._notification_service is None:
            db_path = self.config.database.db_path if self.config.database.enabled else "/app/data/linkedin.db"
            self._notification_service = _get_notification_service(db_path)
        return self._notification_service

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

        # Notification de démarrage
        notifier = self._get_notifier()
        if notifier:
            notifier.notify_bot_start()

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

        # Notifications de fin d'exécution
        notifier = self._get_notifier()
        if notifier:
            if self._critical_error_occurred:
                # Erreur critique détectée pendant l'exécution
                notifier.notify_error(
                    self._critical_error_message or "Une erreur critique s'est produite",
                    f"Bot: {self.__class__.__name__}, Errors: {self.stats['errors']}"
                )
            elif self.stats["errors"] == 0 and self.stats["messages_sent"] > 0:
                # Succès complet
                notifier.notify_success(self.stats["messages_sent"])

            # Notification d'arrêt
            notifier.notify_bot_stop()

        # 🚀 RASPBERRY PI 4 MEMORY CLEANUP
        # Force garbage collection to free memory immediately after browser close
        import gc
        gc.collect()
        logger.debug("Forced garbage collection completed")

        logger.info("✅ Bot teardown completed")

    def _handle_critical_error(self, error: Exception, context: str = "") -> None:
        """
        Gère une erreur critique et envoie une notification immédiate.

        Args:
            error: L'exception qui s'est produite
            context: Contexte additionnel sur l'erreur
        """
        self._critical_error_occurred = True
        error_type = type(error).__name__

        # Déterminer le type d'erreur pour le message
        if isinstance(error, SessionExpiredError):
            self._critical_error_message = "Session LinkedIn expirée - Reconnexion requise"
            notifier = self._get_notifier()
            if notifier:
                notifier.notify_cookies_expiry()
        elif isinstance(error, AccountRestrictedError):
            self._critical_error_message = "Compte LinkedIn restreint - Vérification manuelle requise"
            notifier = self._get_notifier()
            if notifier:
                notifier.notify_linkedin_blocked("Compte restreint")
        elif isinstance(error, CaptchaRequiredError):
            self._critical_error_message = "Captcha requis par LinkedIn - Vérification manuelle requise"
            notifier = self._get_notifier()
            if notifier:
                notifier.notify_linkedin_blocked("Captcha requis")
        else:
            self._critical_error_message = f"{error_type}: {str(error)}"
            if context:
                self._critical_error_message += f" ({context})"

        logger.error(f"Critical error handled: {self._critical_error_message}")

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

        # Verify browser is still alive before proceeding
        if not self.page or not self.browser_manager or not self.browser_manager.browser:
            logger.error("Browser not initialized or already closed")
            raise SessionExpiredError("Browser not available")

        # Check if browser context is still valid
        try:
            if not self.browser_manager.context or not self.browser_manager.browser.is_connected():
                logger.error("Browser context or connection lost")
                raise SessionExpiredError("Browser connection lost")
        except Exception as e:
            logger.error(f"Browser connection check failed: {e}")
            raise SessionExpiredError(f"Browser not accessible: {e}")

        # Retry mechanism for Pi 4 stability
        max_retries = 3
        timeout = 120000  # Increased to 120s for better stability

        for attempt in range(1, max_retries + 1):
            try:
                # HARDWARE REALISM: Increased timeout to 120s for Pi4
                logger.debug(f"Navigating to feed (Attempt {attempt}/{max_retries})...")

                # Check if page is still connected before navigating
                try:
                    # Try a simple operation to verify page is alive
                    current_url = self.page.url
                    logger.debug(f"Current page URL: {current_url}")
                except Exception as e:
                    logger.error(f"Page is not accessible: {e}")
                    raise SessionExpiredError(f"Browser page closed unexpectedly: {e}")

                logger.debug("Attempting navigation to LinkedIn feed...")
                # Use 'commit' instead of 'domcontentloaded' for better stability on slow systems
                # 'commit' is faster as it doesn't wait for DOM parsing, just network commit
                self.page.goto("https://www.linkedin.com/feed/", timeout=timeout, wait_until="commit")
                logger.debug("Navigation committed, waiting for page to stabilize...")
                # Give the page a moment to settle after commit
                time.sleep(2)

                # Use combined selector to wait for ANY login indicator
                combined_selector = self.selector_manager.get_combined_selector("login.indicators")
                try:
                    self.page.wait_for_selector(combined_selector, timeout=45000)
                    logger.info(f"✅ Successfully logged in")
                    return True
                except PlaywrightTimeoutError:
                    pass # Continue to check URL

                if "/feed" in self.page.url or "/mynetwork" in self.page.url:
                     return True

                if attempt < max_retries:
                    logger.warning(f"Login indicators not found (Attempt {attempt}). Retrying...")
                    time.sleep(5)
                    continue

                raise PlaywrightTimeoutError("No login indicators found")

            except PlaywrightTimeoutError as e:
                logger.warning(f"Login verification timed out (Attempt {attempt}/{max_retries}): {e}")
                if attempt == max_retries:
                    if self.browser_manager:
                        self.browser_manager.take_screenshot("error_login_verification_failed.png")
                    raise SessionExpiredError(f"Failed to verify login after {max_retries} attempts")
                time.sleep(5)
            except Exception as e:
                error_msg = str(e)
                # Check if this is a browser crash/closure error
                if "Target page, context or browser has been closed" in error_msg or "has been closed" in error_msg:
                    logger.error(f"Browser crashed or closed unexpectedly during login verification: {e}")

                    # Try to diagnose the issue
                    try:
                        if self.browser_manager and self.browser_manager.browser:
                            is_connected = self.browser_manager.browser.is_connected()
                            logger.error(f"Browser is_connected status: {is_connected}")
                        else:
                            logger.error("Browser manager or browser is None")
                    except Exception as diag_e:
                        logger.error(f"Failed to diagnose browser state: {diag_e}")

                    raise SessionExpiredError(f"Browser crashed during login verification: {e}")

                logger.error(f"Unexpected error during login verification: {e}", exc_info=True)
                raise SessionExpiredError(f"Login verification error: {e}")

        return False

    # ═══════════════════════════════════════════════════════════════
    #  STRATEGIE ANTI-FRAGILE (Sélecteurs & Dates & Clicks)
    # ═══════════════════════════════════════════════════════════════

    def _smart_click(self, locator: Locator, timeout: int = 5000) -> bool:
        """
        Tente de cliquer sur un élément avec plusieurs stratégies de fallback.
        1. Standard click
        2. Force click (bypass viewport/overlay checks)
        3. JS click (works even if element is outside viewport)
        4. Dispatch Event

        Capture une capture d'écran en cas d'échec total et retourne False sans crasher.
        """
        error_msg = ""

        try:
            # Strategy 1: Standard Click
            locator.click(timeout=timeout)
            return True
        except Exception as e1:
            error_msg = str(e1)
            logger.debug(f"SmartClick: Standard click failed ({e1}). Trying force click...")

        try:
            # Strategy 2: Force Click (bypasses actionability checks including viewport)
            locator.click(timeout=timeout, force=True)
            return True
        except Exception as e2:
            logger.debug(f"SmartClick: Force click failed ({e2}). Trying JS click...")

        try:
            # Strategy 3: JS Click (works even if element is outside viewport)
            # This is the most reliable for elements in scrollable containers
            locator.evaluate("el => el.click()")
            return True
        except Exception as e3:
            logger.debug(f"SmartClick: JS click failed ({e3}). Trying Dispatch Event...")

        try:
            # Strategy 4: Dispatch Event (most compatible with various frameworks)
            locator.evaluate("el => el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}))")
            return True
        except Exception as e4:
            # All failed
            logger.warning(f"SmartClick: All strategies failed. Last error: {e4}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Safe hint extraction
            try:
                hint = "unknown"
                # Try to get basic selector info safely
                # str(locator) usually gives 'Locator@selector'
                raw_str = str(locator)
                if "@" in raw_str:
                    hint = raw_str.split("@")[-1].strip().replace("/", "_").replace(":", "")[:30]
            except:
                pass

            if self.browser_manager:
                self.browser_manager.take_screenshot(f"smartclick_failed_{timestamp}_{hint}.png")

            return False

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
        Pour les éléments dans des modals scrollables (comme la messagerie LinkedIn),
        scroll aussi le conteneur parent du modal.
        """
        try:
            # First, try to scroll within the modal container if element is inside one
            # This handles LinkedIn's messaging modal which has its own scroll context
            element.evaluate("""el => {
                // Find scrollable parent container (modal, overlay, etc.)
                let parent = el.parentElement;
                while (parent) {
                    const style = window.getComputedStyle(parent);
                    const isScrollable = style.overflow === 'auto' || style.overflow === 'scroll' ||
                                        style.overflowY === 'auto' || style.overflowY === 'scroll';
                    if (isScrollable && parent.scrollHeight > parent.clientHeight) {
                        // Scroll element into view within the scrollable container
                        const rect = el.getBoundingClientRect();
                        const parentRect = parent.getBoundingClientRect();
                        const scrollNeeded = rect.bottom - parentRect.bottom + 50; // 50px margin
                        if (scrollNeeded > 0) {
                            parent.scrollTop += scrollNeeded;
                        }
                        break;
                    }
                    parent = parent.parentElement;
                }
                // Then scroll element into main viewport
                el.scrollIntoView({ behavior: 'auto', block: 'center', inline: 'center' });
            }""")
            time.sleep(0.3)
        except Exception as e:
            logger.debug(f"Safe scroll fallback: {e}")
            try:
                element.scroll_into_view_if_needed()
            except Exception:
                pass

    def yield_birthday_contacts(self) -> Generator[Tuple[ContactData, Locator], None, None]:
        """
        Générateur "Process-As-You-Go" qui parcourt la liste des anniversaires.
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
        Méthode robuste pour traiter un contact.
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
        try:
            logger.info("Attempting re-acquisition by text...")
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
                # Use find_element to leverage selector manager's heuristic if configured
                return self.send_birthday_message(self.page.locator("body"), is_late=(data.birthday_type == "late"), days_late=data.days_late)
            except Exception as e:
                logger.error(f"Failed profile navigation fallback: {e}")

        return False

    def _extract_profile_url(self, element: Locator) -> Optional[str]:
        try:
            link = element.locator("a[href*='/in/']").first
            if link.count() > 0:
                url = link.get_attribute("href")
                if url: return url.split("?")[0]
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

    def _is_blacklisted(self, contact_name: str, profile_url: Optional[str] = None) -> bool:
        """
        Vérifie si un contact est dans la blacklist.

        Args:
            contact_name: Nom du contact à vérifier
            profile_url: URL du profil LinkedIn (optionnel)

        Returns:
            True si le contact est blacklisté
        """
        if not self.db:
            return False
        try:
            return self.db.is_blacklisted(contact_name, profile_url)
        except Exception as e:
            logger.warning(f"Could not check blacklist: {e}")
            return False

    def send_birthday_message(self, contact_element, is_late: bool = False, days_late: int = 0) -> bool:
        full_name = self.extract_contact_name(contact_element)
        if not full_name:
            try:
                title = self.page.title()
                if "|" in title: full_name = title.split("|")[0].strip()
                elif ")" in title: full_name = title.split(")")[1].strip()
            except: pass

        if not full_name:
            logger.warning("Could not extract name from contact element/page")
            return False

        # Vérification blacklist
        if self._is_blacklisted(full_name):
            logger.info(f"🚫 Skipping {full_name} - contact is blacklisted")
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
                    if self.browser_manager:
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

        # --- NOUVEAU BLOC ANTI-CRASH ---
        # 1. Vérification prioritaire : Si c'est un bouton "Se connecter", on ignore immédiatement.
        connect_btn = self.selector_manager.find_element(contact_element, "messaging.connect_button_heuristic")
        if connect_btn and connect_btn.is_visible():
            logger.warning(f"⚠️  Bouton 'Se connecter/Suivre' détecté pour {full_name}. Relation hors réseau ? -> SKIP")
            return False
        # -------------------------------

        # 2. Recherche du bouton Message
        # IMPORTANT: La recherche doit être strictement scopée à l'élément contact (card)
        # pour éviter de cliquer sur le bouton d'un autre contact (ce qui causerait une erreur de destinataire).
        msg_btn_locator = self.selector_manager.find_element(contact_element, "messaging.open_button_heuristic")

        if not msg_btn_locator:
            logger.warning("Bouton Message introuvable DANS LA CARTE (Sélecteur non trouvé). Abandon pour éviter erreur de personne.")
            return False

        # 3. Clic avec Timeout réduit (5s au lieu de 30s/60s)
        # Si on ne peut pas cliquer en 5s, on considère que c'est un échec et on passe.
        if not self._smart_click(msg_btn_locator.first, timeout=5000):
             logger.warning("Impossible de cliquer sur le bouton 'Message' (Timeout 5s ou masqué)")
             return False

        # 2. Wait for Modal Container (New 2025 Architecture)
        # We wait for the DIALOG or OVERLAY explicitly before finding the textarea.
        try:
            # "div[role='dialog']" is the standard accessibility container for modals
            # ".msg-overlay-conversation-bubble" is the LinkedIn specific class
            modal_container_selector = "div[role='dialog'], aside.msg-overlay-conversation-bubble, .msg-overlay-list-bubble"
            self.page.wait_for_selector(modal_container_selector, state="visible", timeout=20000)

            # Additional safety: Wait specifically for the contenteditable area to be interactive
            box_selector = self.selector_manager.get_combined_selector("messaging.modal_textarea")
            self.page.wait_for_selector(box_selector, state="visible", timeout=10000)
        except Exception:
            logger.error("Message modal/textarea not found (timeout). Check selectors.")
            return False

        # Get the textarea using the updated selector
        message_box_locator = self.selector_manager.find_element(self.page, "messaging.modal_textarea")
        if message_box_locator:
             # Use the LAST one because multiple chat bubbles might exist (we want the active one)
             message_box = message_box_locator.last
        else:
             return False

        # 3. VERIFICATION ULTIME : Le nom dans le modal correspond-il ?
        # C'est la protection finale contre le bug "Christelle -> Benjamin"
        try:
            # Sélecteur pour le titre du modal (ex: "Nouveau message pour Benjamin")
            # LinkedIn utilise souvent: h2#message-overlay-title-... ou .msg-overlay-bubble-header__title
            modal_header_locator = self.page.locator(".msg-overlay-bubble-header__title, h2[id*='message-overlay-title'], .msg-entity-lockup__entity-title").last

            if modal_header_locator.is_visible(timeout=3000):
                modal_name = modal_header_locator.inner_text().strip()

                # Normalisation pour comparaison (minuscule, sans accents)
                def normalize(s):
                    return s.lower().replace('é', 'e').replace('è', 'e').split()[0] # Comparaison sur le prénom

                target_first = normalize(full_name)
                modal_first = normalize(modal_name)

                # On vérifie si le prénom cible est dans le titre du modal
                if target_first not in modal_name.lower().replace('é', 'e').replace('è', 'e'):
                     logger.error(f"⛔ SECURITY BLOCK: Name mismatch! Target: '{full_name}' vs Modal: '{modal_name}'. Aborting to prevent error.")
                     self._close_all_message_modals()
                     return False
                else:
                    logger.info(f"✅ Recipient verified: '{modal_name}' matches '{full_name}'")
            else:
                 logger.debug("⚠️ Modal header not found/visible, skipping name verification (risky but proceeding)")

        except Exception as e:
            logger.warning(f"Name verification failed (non-blocking): {e}")


        # 4. Message Selection
        message_list = self.late_birthday_messages if is_late else self.birthday_messages
        if not message_list:
            logger.warning("No messages loaded")
            return False

        message = random.choice(message_list).format(name=first_name)

        if self.config.dry_run:
            logger.info(f"[DRY RUN] Would send: '{message}'")
            return True

        # 5. Fill & Send
        try:
            # Use fill directly on the robust selector
            message_box.fill(message)
            self.random_delay(0.5, 1)
        except Exception as e:
            raise Exception(f"Failed to fill message box: {e}")

        # 5. Send Button: DIRECT HEURISTIC ACTION (Bypass)
        # Try heuristic FIRST and use the handle DIRECTLY if high confidence.
        heuristic_send_btn = self.selector_manager.find_heuristic(self.page, "messaging.send_button_heuristic")

        if heuristic_send_btn:
            logger.info("⚡ Direct Heuristic Action: Clicking Send button immediately.")
            # Scroll into view before clicking to avoid "element outside viewport" errors
            self._safe_scroll_to_element(heuristic_send_btn)
            # Use _smart_click for robust click with fallbacks (force, JS click, dispatch event)
            if self._smart_click(heuristic_send_btn, timeout=5000):
                logger.info("✅ Message sent successfully (Heuristic)")
                MESSAGES_SENT_TOTAL.labels(status="success", type="late" if is_late else "today").inc()
                self._close_all_message_modals()
                return True
            else:
                logger.warning("Heuristic click failed. Falling back to standard selectors.")

        # Fallback: Standard Selectors
        submit_btn_locator = self.selector_manager.find_element(self.page, "messaging.send_button")

        if submit_btn_locator:
            # Scroll into view before clicking to avoid "element outside viewport" errors
            self._safe_scroll_to_element(submit_btn_locator.last)
            if self._smart_click(submit_btn_locator.last, timeout=5000):
                logger.info("✅ Message sent successfully")
                MESSAGES_SENT_TOTAL.labels(status="success", type="late" if is_late else "today").inc()
                self._close_all_message_modals()
                return True
            else:
                 logger.warning("Send button click failed")
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
                        self._smart_click(btn, timeout=2000)
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
