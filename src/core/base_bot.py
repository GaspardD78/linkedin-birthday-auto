"""
Classe abstraite de base pour tous les bots LinkedIn.

Ce module définit BaseLinkedInBot qui encapsule toute la logique commune
entre les différents types de bots (birthday, unlimited, etc.).
"""

from abc import ABC, abstractmethod
import random
import time
import re
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from ..config.config_manager import get_config
from ..config.config_schema import LinkedInBotConfig
from ..core.browser_manager import BrowserManager
from ..core.auth_manager import AuthManager
from ..utils.exceptions import (
    LinkedInBotError,
    SessionExpiredError,
    ElementNotFoundError,
    PageLoadTimeoutError,
    MessageSendError
)
from ..monitoring.metrics import (
    MESSAGES_SENT_TOTAL,
    BIRTHDAYS_PROCESSED,
    RUN_DURATION_SECONDS
)
from ..monitoring.prometheus import PrometheusClient
from ..monitoring.tracing import setup_tracing
from opentelemetry import trace
from ..utils.logging import get_logger

logger = get_logger(__name__)


class BaseLinkedInBot(ABC):
    """
    Classe abstraite de base pour les bots LinkedIn.

    Cette classe fournit toute l'infrastructure commune :
    - Gestion du browser et de l'authentification
    - Navigation LinkedIn
    - Extraction et traitement des anniversaires
    - Envoi de messages
    - Simulation de comportement humain

    Les sous-classes doivent implémenter :
    - run() : Logique principale d'exécution
    - get_message_strategy() : Stratégie d'envoi des messages

    Exemples:
        >>> class MyBot(BaseLinkedInBot):
        >>>     def run(self):
        >>>         # Logique spécifique
        >>>         pass
        >>>
        >>>     def get_message_strategy(self):
        >>>         return MessageStrategy.UNLIMITED
    """

    def __init__(self, config: Optional[LinkedInBotConfig] = None):
        """
        Initialise le bot.

        Args:
            config: Configuration du bot (ou None pour config par défaut)
        """
        self.config = config or get_config()

        # Managers
        self.browser_manager: Optional[BrowserManager] = None
        self.auth_manager: Optional[AuthManager] = None

        # Monitoring
        self.prometheus_client = PrometheusClient(metrics_dir=self.config.paths.logs_dir)

        # Tracing
        self.tracer = trace.get_tracer(__name__)
        # Note: Tracing provider should be initialized globally (e.g. in main.py or worker)
        # but we can ensure it's used here

        # Page Playwright
        self.page: Optional[Page] = None

        # Messages
        self.birthday_messages: List[str] = []
        self.late_birthday_messages: List[str] = []

        # Stats d'exécution
        self.stats = {
            'messages_sent': 0,
            'errors': 0,
            'contacts_processed': 0,
            'start_time': None,
            'end_time': None
        }

        logger.info(
            f"{self.__class__.__name__} initialized",
            mode=self.config.bot_mode,
            dry_run=self.config.dry_run
        )

    # ═══════════════════════════════════════════════════════════════
    # MÉTHODES ABSTRAITES (à implémenter par les sous-classes)
    # ═══════════════════════════════════════════════════════════════

    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """
        Exécute la logique principale du bot.

        Cette méthode doit être implémentée par chaque sous-classe
        pour définir le comportement spécifique du bot.

        Returns:
            Dict contenant les statistiques d'exécution

        Raises:
            LinkedInBotError: En cas d'erreur durant l'exécution
        """
        with self.tracer.start_as_current_span("bot_run"):
            return self._run_internal()

    @abstractmethod
    def _run_internal(self) -> Dict[str, Any]:
        """Internal abstract run method to be implemented by subclasses."""
        pass

    # ═══════════════════════════════════════════════════════════════
    # GESTION DU BROWSER ET AUTHENTIFICATION
    # ═══════════════════════════════════════════════════════════════

    def setup(self) -> None:
        """
        Initialise le browser et l'authentification.

        Cette méthode doit être appelée avant run().

        Raises:
            AuthenticationError: Si l'authentification échoue
            BrowserError: Si le browser ne démarre pas
        """
        logger.info("Setting up bot...")
        self.stats['start_time'] = datetime.now().isoformat()

        # Charger les messages
        self._load_messages()

        # Setup authentification
        self.auth_manager = AuthManager(config=self.config.auth)
        auth_path = self.auth_manager.prepare_auth_state()

        # Setup browser
        self.browser_manager = BrowserManager(config=self.config.browser)

        # Obtenir la config proxy si activée
        proxy_config = None
        if self.config.proxy.enabled:
            proxy_config = self._get_proxy_config()

        # Créer le browser
        browser, context, page = self.browser_manager.create_browser(
            auth_state_path=auth_path,
            proxy_config=proxy_config
        )

        self.page = page
        logger.info("✅ Bot setup completed")

    def teardown(self) -> None:
        """
        Nettoie les ressources (browser, auth, etc.).

        Cette méthode devrait toujours être appelée après run(),
        idéalement dans un try/finally block.
        """
        logger.info("Tearing down bot...")
        self.stats['end_time'] = datetime.now().isoformat()

        # Fermer le browser
        if self.browser_manager:
            self.browser_manager.close()

        # Nettoyer l'auth
        if self.auth_manager:
            # Garder le fichier si env var (peut être réutilisé)
            keep_file = self.auth_manager.get_auth_source() == "env"
            self.auth_manager.cleanup(keep_file=keep_file)

        # Write metrics to file
        if self.prometheus_client:
            self.prometheus_client.write_metrics()

        logger.info("✅ Bot teardown completed")

    def check_login_status(self) -> bool:
        """
        Vérifie que l'utilisateur est bien connecté à LinkedIn.

        Returns:
            True si connecté, False sinon

        Raises:
            SessionExpiredError: Si la session a expiré
        """
        logger.info("Checking login status...")

        try:
            self.page.goto("https://www.linkedin.com/feed/", timeout=60000)

            # Indicateur de connexion : avatar de profil
            profile_avatar_selector = "img.global-nav__me-photo"
            self.page.wait_for_selector(profile_avatar_selector, timeout=15000)

            logger.info("✅ Successfully logged in")
            return True

        except PlaywrightTimeoutError:
            logger.error("❌ Login verification failed")
            self.browser_manager.take_screenshot("error_login_verification_failed.png")
            raise SessionExpiredError("Failed to verify login - session may have expired")

    # ═══════════════════════════════════════════════════════════════
    # NAVIGATION ET EXTRACTION DES ANNIVERSAIRES
    # ═══════════════════════════════════════════════════════════════

    def get_birthday_contacts(self) -> Dict[str, List]:
        """
        Navigue vers la page anniversaires et extrait tous les contacts.

        Returns:
            Dict avec clés 'today' et 'late', contenant les éléments de contact

        Raises:
            PageLoadTimeoutError: Si la page ne charge pas
        """
        with self.tracer.start_as_current_span("get_birthday_contacts"):
            logger.info("Navigating to birthdays page...")
            self.page.goto("https://www.linkedin.com/mynetwork/catch-up/birthday/", timeout=60000)

            # Sélecteur des cartes d'anniversaire
            card_selector = "div[role='listitem']"

            try:
                logger.info(f"Waiting for birthday cards: '{card_selector}'")
                self.page.wait_for_selector(card_selector, state="visible", timeout=15000)
            except PlaywrightTimeoutError:
                logger.info("No birthday cards found on the page")
                self.browser_manager.take_screenshot("birthdays_page_no_cards.png")
                return {'today': [], 'late': []}

            # Screenshot pour debug
            self.browser_manager.take_screenshot("birthdays_page_loaded.png")

            # Scroller pour charger toutes les cartes
            all_contacts = self._scroll_and_collect_contacts(card_selector)

            # Catégoriser les anniversaires
            return self._categorize_birthdays(all_contacts)

    def _scroll_and_collect_contacts(
        self,
        card_selector: str,
        max_scrolls: int = 20
    ) -> List:
        """
        Scrolle la page pour charger toutes les cartes d'anniversaire.

        Args:
            card_selector: Sélecteur CSS des cartes
            max_scrolls: Nombre maximum de scrolls

        Returns:
            Liste de tous les éléments de contact trouvés
        """
        logger.info("Scrolling to load all birthday cards...")

        last_card_count = 0
        scroll_attempts = 0

        while scroll_attempts < max_scrolls:
            current_contacts = self.page.query_selector_all(card_selector)
            current_card_count = len(current_contacts)

            logger.info(f"Scroll attempt {scroll_attempts + 1}: {current_card_count} cards")

            # Plus de nouvelles cartes
            if scroll_attempts > 0 and current_card_count == last_card_count:
                logger.info("No new cards loaded, stopping scroll")
                break

            last_card_count = current_card_count

            # Scroller le dernier élément dans la vue
            if current_contacts:
                current_contacts[-1].scroll_into_view_if_needed()
                time.sleep(3)  # Laisser le temps de charger

            scroll_attempts += 1

        if scroll_attempts >= max_scrolls:
            logger.warning(f"Reached max scroll attempts ({max_scrolls})")

        final_contacts = self.page.query_selector_all(card_selector)
        logger.info(f"Finished scrolling: {len(final_contacts)} total cards")

        return final_contacts

    def _categorize_birthdays(self, contacts: List) -> Dict[str, List]:
        """
        Catégorise les contacts en anniversaires du jour et en retard.

        Args:
            contacts: Liste d'éléments Playwright

        Returns:
            Dict {'today': [...], 'late': [(contact, days_late), ...]}
        """
        birthdays = {'today': [], 'late': []}

        # Statistiques de classification
        stats = {
            'today': 0,
            'late_1d': 0, 'late_2d': 0, 'late_3d': 0, 'late_4d': 0,
            'late_5d': 0, 'late_6d': 0, 'late_7d': 0, 'late_8d': 0,
            'late_9d': 0, 'late_10d': 0,
            'ignored': 0,
            'errors': 0
        }

        for i, contact in enumerate(contacts):
            try:
                birthday_type, days_late = self._get_birthday_type(contact)

                if birthday_type == 'today':
                    birthdays['today'].append(contact)
                    stats['today'] += 1

                elif birthday_type == 'late':
                    birthdays['late'].append((contact, days_late))
                    if 1 <= days_late <= 10:
                        stats[f'late_{days_late}d'] += 1

                else:  # 'ignore'
                    stats['ignored'] += 1

            except Exception as e:
                logger.error(f"Error classifying card {i+1}: {e}")
                stats['errors'] += 1

        # Afficher les statistiques
        self._log_birthday_stats(stats, len(contacts))

        # Update metrics
        BIRTHDAYS_PROCESSED.labels(type='today').set(stats['today'])
        total_late = sum(stats[f'late_{i}d'] for i in range(1, 11))
        BIRTHDAYS_PROCESSED.labels(type='late').set(total_late)
        BIRTHDAYS_PROCESSED.labels(type='ignored').set(stats['ignored'])

        return birthdays

    def _log_birthday_stats(self, stats: Dict, total: int) -> None:
        """Affiche les statistiques de classification des anniversaires."""
        logger.info("═" * 50)
        logger.info("📊 BIRTHDAY CLASSIFICATION STATISTICS")
        logger.info("═" * 50)
        logger.info(f"Total cards analyzed: {total}")
        logger.info("")
        logger.info(f"✅ Today:              {stats['today']}")

        for i in range(1, 11):
            logger.info(f"⏰ Late ({i} day{'s' if i > 1 else ''}):    {stats[f'late_{i}d']}")

        logger.info(f"❌ Ignored (>10 days): {stats['ignored']}")
        logger.info(f"⚠️  Errors:             {stats['errors']}")
        logger.info("═" * 50)

        total_late = sum(stats[f'late_{i}d'] for i in range(1, 11))
        logger.info(f"\nTOTAL TO PROCESS: {stats['today'] + total_late}")
        logger.info(f"  - Today:  {stats['today']}")
        logger.info(f"  - Late:   {total_late}\n")

    def _get_birthday_type(self, contact_element) -> Tuple[str, int]:
        """
        Détermine le type d'anniversaire (today, late, ignore).

        Args:
            contact_element: Élément Playwright du contact

        Returns:
            Tuple (type: str, days_late: int)
                type: 'today', 'late', ou 'ignore'
                days_late: nombre de jours de retard (0 pour today)
        """
        card_text = contact_element.inner_text().lower()

        # Méthode 1 : Analyser le texte du bouton
        button_text_today = "je vous souhaite un très joyeux anniversaire"
        button_text_late = "joyeux anniversaire avec un peu de retard"

        if button_text_today in card_text:
            logger.debug("✓ Today's birthday detected (standard button)")
            return 'today', 0

        if button_text_late in card_text:
            logger.debug("✓ Late birthday detected (late button)")
            days = self._extract_days_from_date(card_text)
            if days is not None:
                max_days = self.config.birthday_filter.max_days_late
                if 1 <= days <= max_days:
                    logger.debug(f"→ {days} day(s) late - classified as 'late'")
                    return 'late', days
                else:
                    logger.debug(f"→ {days} day(s) late - too old, classified as 'ignore'")
                    return 'ignore', days
            else:
                logger.warning("⚠️ Late detected but date unparseable, estimating 2 days")
                return 'late', 2

        # Méthode 2 : Mots-clés "aujourd'hui"
        today_keywords = [
            "aujourd'hui", "aujourdhui", "c'est aujourd'hui",
            "today", "is today", "'s birthday is today"
        ]

        for keyword in today_keywords:
            if keyword in card_text:
                logger.debug(f"✓ Today detected (keyword: '{keyword}')")
                return 'today', 0

        # Méthode 3 : Parser la date explicite
        days = self._extract_days_from_date(card_text)
        if days is not None:
            max_days = self.config.birthday_filter.max_days_late

            if days == 0:
                logger.debug("✓ Parsed date = today")
                return 'today', 0
            elif 1 <= days <= max_days:
                logger.debug(f"✓ Parsed date = {days} day(s) late")
                return 'late', days
            else:
                logger.debug(f"→ Parsed date = {days} days - too old")
                return 'ignore', days

        # Méthode 4 : Regex "il y a X jours"
        match_fr = re.search(r'il y a (\d+) jours?', card_text)
        match_en = re.search(r'(\d+) days? ago', card_text)

        if match_fr or match_en:
            days_late = int(match_fr.group(1) if match_fr else match_en.group(1))
            max_days = self.config.birthday_filter.max_days_late

            if 1 <= days_late <= max_days:
                logger.debug(f"✓ Regex detected: {days_late} day(s) late")
                return 'late', days_late
            else:
                logger.debug(f"→ Regex: {days_late} days - too old")
                return 'ignore', days_late

        # Cas par défaut
        logger.warning("⚠️ No pattern recognized in card")
        logger.debug(f"Card text: {card_text[:200]}")

        time_keywords = ['retard', 'il y a', 'ago', 'récent']
        has_time_keyword = any(kw in card_text for kw in time_keywords)

        if not has_time_keyword:
            logger.debug("→ No delay indicator, classifying as 'today'")
            return 'today', 0
        else:
            logger.warning("→ Ambiguous time indicators, classifying as 'ignore'")
            return 'ignore', 0

    def _extract_days_from_date(self, card_text: str) -> Optional[int]:
        """
        Extrait le nombre de jours depuis une date mentionnée dans le texte.

        Args:
            card_text: Texte de la carte d'anniversaire

        Returns:
            Nombre de jours de différence ou None si non parsable

        Exemples:
            "le 10 nov." avec date actuelle 18 nov → 8 jours
        """
        # Pattern: "le 10 nov." ou "le 10 novembre"
        pattern = r'le (\d{1,2}) (janv?\.?|févr?\.?|mars?\.?|avr\.?|mai\.?|juin?\.?|juil\.?|août?\.?|sept?\.?|oct\.?|nov\.?|déc\.?|january?|february?|march?|april?|may|june?|july?|august?|september?|october?|november?|december?)'

        match = re.search(pattern, card_text, re.IGNORECASE)

        if not match:
            return None

        day = int(match.group(1))
        month_str = match.group(2).lower()

        # Mapping mois → numéro
        month_mapping = {
            'janv': 1, 'janvier': 1, 'january': 1,
            'févr': 2, 'fev': 2, 'février': 2, 'february': 2,
            'mars': 3, 'march': 3,
            'avr': 4, 'avril': 4, 'april': 4,
            'mai': 5, 'may': 5,
            'juin': 6, 'june': 6,
            'juil': 7, 'juillet': 7, 'july': 7,
            'août': 8, 'aout': 8, 'august': 8,
            'sept': 9, 'septembre': 9, 'september': 9,
            'oct': 10, 'octobre': 10, 'october': 10,
            'nov': 11, 'novembre': 11, 'november': 11,
            'déc': 12, 'dec': 12, 'décembre': 12, 'december': 12
        }

        month_key = month_str.rstrip('.')
        month = None

        for key, value in month_mapping.items():
            if month_key.startswith(key):
                month = value
                break

        if month is None:
            logger.warning(f"⚠️ Unrecognized month: '{month_str}'")
            return None

        # Construire la date
        current_year = datetime.now().year
        try:
            birthday_date = datetime(current_year, month, day)
        except ValueError:
            logger.error(f"⚠️ Invalid date: day={day}, month={month}")
            return None

        # Si dans le futur, c'était l'année dernière
        if birthday_date > datetime.now():
            birthday_date = datetime(current_year - 1, month, day)

        # Calculer la différence
        delta = datetime.now() - birthday_date
        days_diff = delta.days

        logger.debug(f"📅 Extracted date: {day}/{month} → {days_diff} day(s) difference")

        return days_diff

    # ═══════════════════════════════════════════════════════════════
    # EXTRACTION DE NOMS
    # ═══════════════════════════════════════════════════════════════

    def extract_contact_name(self, contact_element) -> Optional[str]:
        """
        Extrait le nom d'un contact depuis une carte d'anniversaire.

        Args:
            contact_element: Élément Playwright du contact

        Returns:
            Nom du contact ou None si non trouvé
        """
        paragraphs = contact_element.query_selector_all("p")

        # Mots-clés à exclure
        non_name_keywords = [
            'Célébrez', 'anniversaire', "Aujourd'hui", 'Il y a',
            'avec un peu de retard', 'avec du retard', 'Message',
            'Say happy birthday'
        ]

        for p in paragraphs:
            text = p.inner_text().strip()
            # Un nom est entre 3 et 100 caractères et ne contient pas de keywords
            is_valid_length = text and 2 < len(text) < 100
            has_no_keywords = not any(
                keyword.lower() in text.lower()
                for keyword in non_name_keywords
            )

            if is_valid_length and has_no_keywords:
                logger.debug(f"Found potential name: '{text}'")
                return text

        logger.warning("Could not extract valid name for contact")
        return None

    def standardize_first_name(self, name: str) -> str:
        """
        Standardise un prénom en retirant emojis et en capitalisant correctement.

        Args:
            name: Prénom brut

        Returns:
            Prénom standardisé ou string vide si invalide

        Exemples:
            "jean" → "Jean"
            "marie-claude" → "Marie-Claude"
            "C" → "" (initial seul)
        """
        if not name:
            return ""

        # Garder seulement lettres, hyphens et espaces
        cleaned_chars = []
        for char in name:
            if char.isalpha() or char == '-' or char == ' ':
                cleaned_chars.append(char)

        cleaned_name = ''.join(cleaned_chars)

        # Normaliser les espaces
        while '  ' in cleaned_name:
            cleaned_name = cleaned_name.replace('  ', ' ')

        # Normaliser les tirets
        cleaned_name = cleaned_name.replace(' - ', '-')
        cleaned_name = cleaned_name.replace('- ', '-')
        cleaned_name = cleaned_name.replace(' -', '-')

        cleaned_name = cleaned_name.strip()

        if not cleaned_name or len(cleaned_name) == 1:
            return ""  # Initial seul, on ignore

        # Capitaliser les parties (gérer tirets et espaces)
        space_parts = cleaned_name.split(' ')
        processed_parts = []

        for space_part in space_parts:
            if not space_part:
                continue

            if '-' in space_part:
                hyphen_parts = space_part.split('-')
                capitalized_hyphen_parts = [
                    part.capitalize() for part in hyphen_parts if part
                ]
                processed_parts.append('-'.join(capitalized_hyphen_parts))
            else:
                processed_parts.append(space_part.capitalize())

        return ' '.join(processed_parts)

    # ═══════════════════════════════════════════════════════════════
    # ENVOI DE MESSAGES
    # ═══════════════════════════════════════════════════════════════

    def send_birthday_message(
        self,
        contact_element,
        is_late: bool = False,
        days_late: int = 0
    ) -> bool:
        """
        Envoie un message d'anniversaire à un contact.

        Args:
            contact_element: Élément Playwright du contact
            is_late: Si True, le message est en retard
            days_late: Nombre de jours de retard

        Returns:
            True si le message a été envoyé avec succès, False sinon

        Raises:
            MessageSendError: Si l'envoi échoue
        """
        with self.tracer.start_as_current_span("send_birthday_message"):
            return self._send_birthday_message_internal(contact_element, is_late, days_late)

    def _send_birthday_message_internal(
        self,
        contact_element,
        is_late: bool,
        days_late: int
    ) -> bool:
        """Logique interne d'envoi de message."""
        # Fermer toutes les modales ouvertes
        self._close_all_message_modals()

        # Extraire le nom
        full_name = self.extract_contact_name(contact_element)
        if not full_name:
            logger.warning("Skipping contact - name extraction failed")
            return False

        # Standardiser le prénom
        first_name = full_name.split()[0]
        first_name = self.standardize_first_name(first_name)

        if not first_name:
            logger.warning(f"Skipping '{full_name}' - first name is just an initial")
            return False

        log_msg = f"late ({days_late}d)" if is_late else "today"
        logger.info(f"--- Processing birthday ({log_msg}) for {full_name} ---", contact=full_name)

        # Sélecteur du bouton Message
        message_button_selector = 'a[aria-label*="Envoyer un message"], a[href*="/messaging/compose"], button:has-text("Message")'

        try:
            # Chercher le bouton Message
            message_buttons = contact_element.query_selector_all(message_button_selector)
        except Exception as e:
            logger.error(f"❌ Error finding message button: {e}")
            return False

        if not message_buttons:
            logger.warning(f"Could not find 'Message' button for {full_name}. Skipping.")
            return False

        # Cliquer sur le bouton Message
        try:
            message_buttons[0].click()
            self.random_delay(1, 2)
        except Exception as e:
            logger.error(f"❌ Error clicking message button: {e}")
            self.browser_manager.take_screenshot(f"error_click_{first_name.replace(' ', '_')}.png")
            return False

        # Attendre la modale de message
        message_box_selector = "div.msg-form__contenteditable[role='textbox']"
        try:
            self.page.wait_for_selector(message_box_selector, state="visible", timeout=30000)
        except Exception as e:
            logger.error(f"❌ Message modal not found: {e}")
            return False

        # Vérifier s'il y a plusieurs modales (bug)
        modal_count = self.page.locator(message_box_selector).count()
        if modal_count > 1:
            logger.warning(f"⚠️ Multiple modals detected ({modal_count}), cleaning up...")
            self._close_all_message_modals()
            self.random_delay(1, 2)

            # Re-ouvrir la modale
            try:
                all_cards = self.page.query_selector_all("div[role='listitem']")
                for card in all_cards:
                    try:
                        card_text = card.inner_text()
                        if full_name in card_text or first_name in card_text:
                            button = card.query_selector(message_button_selector)
                            if button:
                                button.click()
                                self.random_delay(1, 2)
                                self.page.wait_for_selector(message_box_selector, state="visible", timeout=30000)
                                break
                    except Exception:
                        continue
            except Exception as e:
                logger.error(f"❌ Failed to re-open modal: {e}")
                return False

        # Toujours utiliser .last pour la modale la plus récente
        message_box = self.page.locator(message_box_selector).last
        logger.debug(f"Message modal opened for {first_name}")

        # Sélectionner le message approprié
        if is_late:
            message_list = self.late_birthday_messages if self.late_birthday_messages else self.birthday_messages
        else:
            message_list = self.birthday_messages

        if not message_list:
            logger.error("No birthday messages available!")
            return False

        message = random.choice(message_list).format(name=first_name)

        # Vérifier l'historique des messages si database disponible
        if self.config.database.enabled and hasattr(self, 'db') and self.db:
            try:
                previous_messages = self.db.get_messages_sent_to_contact(
                    full_name,
                    years=self.config.messages.avoid_repetition_years
                )

                if previous_messages:
                    used_messages = {msg['message_text'] for msg in previous_messages}
                    available_messages = [
                        msg for msg in message_list
                        if msg.format(name=first_name) not in used_messages
                    ]

                    if available_messages:
                        message = random.choice(available_messages).format(name=first_name)
                        logger.debug(f"Selected unused message from {len(available_messages)} available")
                    else:
                        logger.warning(f"All messages used for {full_name}, reusing from pool")
            except Exception as e:
                logger.warning(f"Could not check message history: {e}")

        # Mode dry-run
        if self.config.dry_run:
            logger.info(f"[DRY RUN] Would send to {first_name}: '{message}'")
            if self.config.database.enabled and hasattr(self, 'db') and self.db:
                try:
                    self.db.add_birthday_message(full_name, message, is_late, days_late, "dry_run")
                except Exception as e:
                    logger.warning(f"Could not record dry-run to database: {e}")
            return True

        # Taper le message
        try:
            logger.info(f"Typing message: '{message}'")
            message_box.clear()
            self.random_delay(0.3, 0.5)
            message_box.fill(message)
            self.random_delay(1, 2)
        except Exception as e:
            logger.error(f"❌ Error typing message: {e}")
            return False

        # Bouton d'envoi
        submit_button = self.page.locator("button.msg-form__send-button").last

        try:
            # Scroller pour rendre visible
            message_box.scroll_into_view_if_needed(timeout=5000)
            self.random_delay(0.3, 0.5)
            submit_button.scroll_into_view_if_needed(timeout=5000)
            self.random_delay(0.5, 1)

            # Envoyer
            if submit_button.is_enabled():
                submit_button.click()
                logger.info("✅ Message sent successfully", contact=full_name)
                MESSAGES_SENT_TOTAL.labels(status='success', type='late' if is_late else 'today').inc()

                # Enregistrer en DB
                if self.config.database.enabled and hasattr(self, 'db') and self.db:
                    try:
                        self.db.add_birthday_message(full_name, message, is_late, days_late, "production")
                    except Exception as e:
                        logger.warning(f"Could not record to database: {e}")

                return True
            else:
                logger.warning("⚠️ Send button is not enabled")
                return False

        except Exception as e:
            logger.warning(f"Could not send normally ({type(e).__name__}), trying force click...")
            self.browser_manager.take_screenshot(f"warning_send_{first_name.replace(' ', '_')}.png")

            try:
                submit_button.click(force=True, timeout=10000)
                logger.info("✅ Message sent (force click)")

                if self.config.database.enabled and hasattr(self, 'db') and self.db:
                    try:
                        self.db.add_birthday_message(full_name, message, is_late, days_late, "production")
                    except Exception as e:
                        logger.warning(f"Could not record to database: {e}")

                return True

            except Exception as e2:
                logger.error(f"❌ Failed to send message: {e2}")
                self.browser_manager.take_screenshot(f"error_send_{first_name.replace(' ', '_')}.png")
                return False

        finally:
            # Fermer la modale
            self.random_delay(0.5, 1)
            self._close_all_message_modals()

    def _close_all_message_modals(self) -> None:
        """Ferme toutes les modales de message ouvertes."""
        try:
            close_buttons = self.page.locator(
                "button[data-control-name='overlay.close_conversation_window']"
            )
            initial_count = close_buttons.count()

            if initial_count > 0:
                logger.debug(f"🧹 Closing {initial_count} modal(s)...")
                closed_count = 0
                max_attempts = initial_count + 2

                for attempt in range(max_attempts):
                    current_count = self.page.locator(
                        "button[data-control-name='overlay.close_conversation_window']"
                    ).count()

                    if current_count == 0:
                        break

                    try:
                        self.page.locator(
                            "button[data-control-name='overlay.close_conversation_window']"
                        ).first.click(timeout=2000)
                        closed_count += 1
                        self.random_delay(0.3, 0.6)
                    except Exception:
                        break

                logger.debug(f"✅ {closed_count} modal(s) closed")

        except Exception as e:
            logger.debug(f"Error closing modals (non-critical): {e}")

    # ═══════════════════════════════════════════════════════════════
    # SIMULATION COMPORTEMENT HUMAIN
    # ═══════════════════════════════════════════════════════════════

    def random_delay(self, min_seconds: float = 0.5, max_seconds: float = 1.5) -> None:
        """
        Pause aléatoire pour simuler le comportement humain.

        Args:
            min_seconds: Durée minimale en secondes
            max_seconds: Durée maximale en secondes
        """
        time.sleep(random.uniform(min_seconds, max_seconds))

    def simulate_human_activity(self) -> None:
        """Simule une activité humaine aléatoire (scroll, mouvement souris)."""
        actions = [
            # Scroll aléatoire
            lambda: self.page.mouse.wheel(0, random.randint(100, 400)),
            # Pause de lecture
            lambda: time.sleep(random.uniform(1.5, 4.0)),
            # Mouvement de souris
            lambda: self.page.mouse.move(
                random.randint(300, 800),
                random.randint(200, 600)
            ),
        ]

        num_actions = random.randint(1, 3)
        for _ in range(num_actions):
            try:
                action = random.choice(actions)
                action()
                time.sleep(random.uniform(0.5, 1.5))
            except Exception as e:
                logger.debug(f"Activity simulation error (non-critical): {e}")

    # ═══════════════════════════════════════════════════════════════
    # UTILITAIRES
    # ═══════════════════════════════════════════════════════════════

    def _load_messages(self) -> None:
        """Charge les messages d'anniversaire depuis les fichiers."""
        self.birthday_messages = self._load_messages_from_file(
            self.config.messages.messages_file
        )
        self.late_birthday_messages = self._load_messages_from_file(
            self.config.messages.late_messages_file
        )

    def _load_messages_from_file(self, file_path: str) -> List[str]:
        """Charge des messages depuis un fichier texte."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                messages = [line.strip() for line in f if line.strip()]

            if not messages:
                logger.warning(f"'{file_path}' is empty")
                return []

            logger.info(f"Loaded {len(messages)} messages from '{file_path}'")
            return messages

        except FileNotFoundError:
            logger.warning(f"Message file not found: '{file_path}'")
            return []

    def _get_proxy_config(self) -> Optional[Dict[str, str]]:
        """Obtient la configuration proxy si activée."""
        if not self.config.proxy.enabled:
            return None

        try:
            # Import du ProxyManager (si disponible)
            from proxy_manager import ProxyManager

            proxy_manager = ProxyManager()
            if proxy_manager.is_enabled():
                return proxy_manager.get_playwright_proxy_config()

        except ImportError:
            logger.warning("ProxyManager not available")

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'exécution."""
        return self.stats.copy()

    def __enter__(self):
        """Context manager entry."""
        self.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.teardown()

    def __repr__(self) -> str:
        """Représentation string du bot."""
        return (
            f"<{self.__class__.__name__}("
            f"mode={self.config.bot_mode}, "
            f"dry_run={self.config.dry_run})>"
        )
