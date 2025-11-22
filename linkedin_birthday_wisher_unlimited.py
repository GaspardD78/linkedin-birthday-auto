import os
import random
import time
import logging
import base64
import json
import re
import pytz
from datetime import datetime, timedelta
from typing import Optional
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

# Import debug utilities (si disponibles)
try:
    from debug_utils import (
        DebugScreenshotManager,
        DOMStructureValidator,
        LinkedInPolicyDetector,
        EnhancedLogger,
        AlertSystem,
        retry_with_fallbacks,
        quick_debug_check
    )
    DEBUG_UTILS_AVAILABLE = True
except ImportError:
    DEBUG_UTILS_AVAILABLE = False
    logging.warning("Debug utilities not available - continuing without advanced debugging")

# Import database utilities (si disponibles)
try:
    from database import get_database
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logging.warning("Database utilities not available - continuing without message history tracking")

# Import selector validator (si disponible)
try:
    from selector_validator import validate_birthday_feed_selectors, validate_messaging_selectors
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False
    logging.warning("Selector validator not available - continuing without selector validation")

# Import proxy manager (si disponible)
try:
    from proxy_manager import ProxyManager
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False
    logging.warning("Proxy manager not available - continuing without proxy rotation")

# --- Configuration ---
# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Secure authentication using an auth state from GitHub Secrets
LINKEDIN_AUTH_STATE = os.getenv('LINKEDIN_AUTH_STATE')
AUTH_FILE_PATH = "auth_state.json"

# General settings
HEADLESS_BROWSER = True  # Set to False for debugging to see the browser UI
DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'  # Enables test mode

# Advanced debugging settings
ENABLE_ADVANCED_DEBUG = os.getenv('ENABLE_ADVANCED_DEBUG', 'false').lower() == 'true'
ENABLE_EMAIL_ALERTS = os.getenv('ENABLE_EMAIL_ALERTS', 'false').lower() == 'true'

# ═══════════════════════════════════════════════════════════════════════════
# VERSION ANNIVERSAIRES DU JOUR UNIQUEMENT
# ═══════════════════════════════════════════════════════════════════════════
# Cette version traite UNIQUEMENT les anniversaires du jour
# - Les anniversaires en retard sont ignorés
# - Parfait pour usage quotidien automatisé
# - Évite de surcharger avec des centaines d'anniversaires en retard
# - Peut être lancé tous les jours sans limite

# Délais entre les messages (toujours nécessaire pour éviter la détection)
MIN_DELAY_SECONDS = 120  # 2 minutes minimum entre chaque message
MAX_DELAY_SECONDS = 300  # 5 minutes maximum entre chaque message

# Randomized User-Agents (updated versions)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

# Randomized viewport sizes
VIEWPORT_SIZES = [
    {'width': 1920, 'height': 1080},
    {'width': 1366, 'height': 768},
    {'width': 1440, 'height': 900},
    {'width': 1536, 'height': 864}
]

# Load birthday messages from the external file.
def load_birthday_messages(file_path="messages.txt"):
    """Loads birthday messages from a text file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            # Read lines, strip whitespace, and filter out empty lines.
            messages = [line.strip() for line in f if line.strip()]
        if not messages:
            logging.error(f"'{file_path}' is empty. Please add at least one message.")
            return []
        logging.info(f"Loaded {len(messages)} messages from '{file_path}'.")
        return messages
    except FileNotFoundError:
        logging.error(f"Error: The message file '{file_path}' was not found.")
        return []

BIRTHDAY_MESSAGES = load_birthday_messages()
LATE_BIRTHDAY_MESSAGES = load_birthday_messages("late_messages.txt")

# --- Human Behavior Simulation ---

def random_delay(min_seconds: float = 0.5, max_seconds: float = 1.5):
    """Waits for a random duration within a specified range to mimic human latency."""
    time.sleep(random.uniform(min_seconds, max_seconds))

def simulate_human_activity(page: Page):
    """
    Simulates random human-like activity to avoid detection.
    Performs random actions like scrolling, mouse movements, and brief pauses.
    """
    actions = [
        # Random scroll
        lambda: page.mouse.wheel(0, random.randint(100, 400)),
        # Brief reading pause
        lambda: time.sleep(random.uniform(1.5, 4.0)),
        # Random mouse movement
        lambda: page.mouse.move(
            random.randint(300, 800),
            random.randint(200, 600)
        ),
    ]

    # Execute 1-3 random actions
    num_actions = random.randint(1, 3)
    for _ in range(num_actions):
        action = random.choice(actions)
        try:
            action()
            time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            # Silently ignore errors in activity simulation
            logging.debug(f"Activity simulation error (non-critical): {e}")
            pass

def scroll_and_collect_contacts(page: Page, card_selector: str, max_scrolls: int = 20) -> list:
    """Scrolls the page by bringing the last element into view until no new cards are loaded."""
    logging.info("Starting robust scroll to load all birthday cards...")

    last_card_count = 0
    scroll_attempts = 0

    while scroll_attempts < max_scrolls:
        current_contacts = page.query_selector_all(card_selector)
        current_card_count = len(current_contacts)

        logging.info(f"Scroll attempt {scroll_attempts + 1}: Found {current_card_count} cards.")

        # If the number of cards hasn't changed after a scroll, we're done.
        if scroll_attempts > 0 and current_card_count == last_card_count:
            logging.info("No new cards loaded. Concluding scroll.")
            break

        last_card_count = current_card_count

        # Scroll the last found element into view to trigger loading more.
        if current_contacts:
            current_contacts[-1].scroll_into_view_if_needed()
            # Wait for a moment to let new content load
            time.sleep(3)

        scroll_attempts += 1

    if scroll_attempts >= max_scrolls:
        logging.warning(f"Reached max scroll attempts ({max_scrolls}).")

    final_contacts = page.query_selector_all(card_selector)
    logging.info(f"Finished scrolling. Total cards found: {len(final_contacts)}")
    return final_contacts

def close_all_message_modals(page: Page):
    """Ferme toutes les modales de message ouvertes pour éviter les conflits."""
    try:
        # Trouver tous les boutons de fermeture de modale
        close_buttons = page.locator("button[data-control-name='overlay.close_conversation_window']")
        initial_count = close_buttons.count()

        if initial_count > 0:
            logging.info(f"🧹 Fermeture de {initial_count} modale(s) ouverte(s)...")
            # Fermer toutes les modales une par une en re-vérifiant à chaque fois
            closed_count = 0
            max_attempts = initial_count + 2  # Protection contre boucle infinie
            attempt = 0

            while attempt < max_attempts:
                try:
                    current_count = page.locator("button[data-control-name='overlay.close_conversation_window']").count()
                    if current_count == 0:
                        break

                    page.locator("button[data-control-name='overlay.close_conversation_window']").first.click(timeout=2000)
                    closed_count += 1
                    random_delay(0.3, 0.6)  # Petit délai entre chaque fermeture
                except Exception as e:
                    logging.debug(f"Impossible de fermer une modale (déjà fermée?): {e}")
                    break

                attempt += 1

            logging.info(f"✅ {closed_count} modale(s) fermée(s)")
    except Exception as e:
        logging.debug(f"Erreur lors de la fermeture des modales (non critique): {e}")

# --- Core Automation Functions ---

def check_login_status(page: Page):
    """Checks if the user is logged in by verifying the presence of the feed."""
    page.goto("https://www.linkedin.com/feed/", timeout=60000)
    try:
        # A reliable indicator of being logged in is the presence of the profile avatar dropdown.
        profile_avatar_selector = "img.global-nav__me-photo"
        page.wait_for_selector(profile_avatar_selector, timeout=15000)
        logging.info("Successfully logged in and on the main feed.")
        return True
    except PlaywrightTimeoutError:
        logging.error("Failed to verify login. The feed page doesn't seem to be loaded correctly.")
        page.screenshot(path='error_login_verification_failed.png')
        return False

def get_birthday_contacts(page: Page) -> dict:
    """
    Navigates to the birthdays page, extracts contacts, and categorizes them
    into 'today' and 'late' birthdays with detailed statistics.
    """
    logging.info("Navigating to the birthdays page.")
    page.goto("https://www.linkedin.com/mynetwork/catch-up/birthday/", timeout=60000)

    # Use a robust selector for birthday cards and wait for them to be visible
    card_selector = "div[role='listitem']"
    try:
        logging.info(f"Waiting for birthday cards with selector: '{card_selector}'")
        page.wait_for_selector(card_selector, state="visible", timeout=15000)
    except PlaywrightTimeoutError:
        logging.info("No birthday cards found on the page.")
        page.screenshot(path='birthdays_page_no_cards.png')
        return {'today': [], 'late': []}

    # Take a screenshot for debugging
    page.screenshot(path='birthdays_page_loaded.png')
    logging.info("Screenshot saved as 'birthdays_page_loaded.png' for debugging.")

    all_contacts = scroll_and_collect_contacts(page, card_selector)

    # Categorize birthdays avec compteurs de debug
    birthdays = {'today': [], 'late': []}
    classification_stats = {
        'today': 0,
        'late_1d': 0,
        'late_2d': 0,
        'late_3d': 0,
        'late_4d': 0,
        'late_5d': 0,
        'late_6d': 0,
        'late_7d': 0,
        'late_8d': 0,
        'late_9d': 0,
        'late_10d': 0,
        'ignored': 0,
        'errors': 0
    }

    for i, contact in enumerate(all_contacts):
        try:
            birthday_type, days_late = get_birthday_type(contact)

            if birthday_type == 'today':
                birthdays['today'].append(contact)
                classification_stats['today'] += 1

            elif birthday_type == 'late':
                birthdays['late'].append((contact, days_late))
                # Statistiques détaillées par jour de retard
                if 1 <= days_late <= 10:
                    classification_stats[f'late_{days_late}d'] += 1

            else:  # 'ignore'
                classification_stats['ignored'] += 1

        except Exception as e:
            logging.error(f"Erreur lors de la classification de la carte {i+1}: {e}")
            classification_stats['errors'] += 1
            # Sauvegarder la carte problématique pour analyse
            try:
                contact.screenshot(path=f'error_card_classification_{i+1}.png')
            except Exception as screenshot_error:
                logging.debug(f"Cannot save error screenshot: {screenshot_error}")

    # Afficher les statistiques détaillées
    logging.info("═══════════════════════════════════════════════════")
    logging.info("📊 STATISTIQUES DE CLASSIFICATION DES ANNIVERSAIRES")
    logging.info("═══════════════════════════════════════════════════")
    logging.info(f"Total de cartes analysées: {len(all_contacts)}")
    logging.info(f"")
    logging.info(f"✅ Aujourd'hui:           {classification_stats['today']}")
    logging.info(f"⏰ En retard (1 jour):    {classification_stats['late_1d']}")
    logging.info(f"⏰ En retard (2 jours):   {classification_stats['late_2d']}")
    logging.info(f"⏰ En retard (3 jours):   {classification_stats['late_3d']}")
    logging.info(f"⏰ En retard (4 jours):   {classification_stats['late_4d']}")
    logging.info(f"⏰ En retard (5 jours):   {classification_stats['late_5d']}")
    logging.info(f"⏰ En retard (6 jours):   {classification_stats['late_6d']}")
    logging.info(f"⏰ En retard (7 jours):   {classification_stats['late_7d']}")
    logging.info(f"⏰ En retard (8 jours):   {classification_stats['late_8d']}")
    logging.info(f"⏰ En retard (9 jours):   {classification_stats['late_9d']}")
    logging.info(f"⏰ En retard (10 jours):  {classification_stats['late_10d']}")
    logging.info(f"❌ Ignorés (>10 jours):   {classification_stats['ignored']}")
    logging.info(f"⚠️  Erreurs:               {classification_stats['errors']}")
    logging.info("═══════════════════════════════════════════════════")

    total_late = sum([classification_stats[f'late_{i}d'] for i in range(1, 11)])
    logging.info(f"")
    logging.info(f"TOTAL À TRAITER: {classification_stats['today'] + total_late}")
    logging.info(f"  - Aujourd'hui: {classification_stats['today']}")
    logging.info(f"  - En retard:   {total_late}")
    logging.info("")

    # Sauvegarder le HTML pour analyse si des erreurs ou classifications ambiguës
    if classification_stats['errors'] > 0 or classification_stats['ignored'] > len(all_contacts) * 0.3:
        html_content = page.content()
        with open('birthdays_page_analysis.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        logging.warning("⚠️ Nombre élevé d'erreurs/ignorés - HTML sauvegardé pour analyse")

    return birthdays

def extract_contact_name(contact_element) -> Optional[str]:
    """
    Extracts the contact's name from a birthday card element using a robust, multi-step process.
    """
    # Iterate through all paragraphs, which is a robust method
    paragraphs = contact_element.query_selector_all("p")

    # Keywords to filter out paragraphs that are not names
    non_name_keywords = [
        'Célébrez', 'anniversaire', 'Aujourd\'hui', 'Il y a',
        'avec un peu de retard', 'avec du retard', 'Message', 'Say happy birthday'
    ]

    for p in paragraphs:
        text = p.inner_text().strip()
        # A name is unlikely to be very short or very long, and it shouldn't contain keywords.
        if text and 2 < len(text) < 100 and not any(keyword.lower() in text.lower() for keyword in non_name_keywords):
            logging.info(f"Found potential name from paragraph: '{text}'")
            return text

    logging.warning("Could not extract a valid name for the contact.")
    return None

def extract_days_from_date(card_text: str) -> Optional[int]:
    """
    Extrait le nombre de jours entre une date mentionnée dans le texte et aujourd'hui.
    """
    # Pattern pour capturer "le X mois" (ex: "le 10 nov.")
    pattern = r'le (\d{1,2}) (janv?\.?|févr?\.?|mars?\.?|avr\.?|mai\.?|juin?\.?|juil\.?|août?\.?|sept?\.?|oct\.?|nov\.?|déc\.?|january?|february?|march?|april?|may|june?|july?|august?|september?|october?|november?|december?)'

    match = re.search(pattern, card_text, re.IGNORECASE)

    if not match:
        return None

    day = int(match.group(1))
    month_str = match.group(2).lower()

    # Mapping mois français → numéro
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

    # Retirer les points et trouver le mois
    month_key = month_str.rstrip('.')
    month = None

    for key, value in month_mapping.items():
        if month_key.startswith(key):
            month = value
            break

    if month is None:
        logging.warning(f"⚠️ Mois non reconnu: '{month_str}'")
        return None

    # Construire la date de l'anniversaire
    current_year = datetime.now().year
    try:
        birthday_date = datetime(current_year, month, day)
    except ValueError:
        logging.error(f"⚠️ Date invalide: jour={day}, mois={month}")
        return None

    # Si la date est dans le futur, c'était l'année dernière
    if birthday_date > datetime.now():
        birthday_date = datetime(current_year - 1, month, day)

    # Calculer la différence en jours
    delta = datetime.now() - birthday_date
    days_diff = delta.days

    logging.debug(f"📅 Date extraite: {day}/{month} → {days_diff} jour(s) de différence")

    return days_diff


def get_birthday_type(contact_element) -> tuple[str, int]:
    """
    Détermine si un anniversaire est 'today', 'late' (1-10 jours), ou 'ignore' (>10 jours).
    """
    card_text = contact_element.inner_text().lower()

    # Debug: afficher le texte complet de la carte en mode debug avancé
    logging.debug(f"Analyzing card text: {card_text[:200]}...")

    # MÉTHODE 1 : Analyser le texte du bouton
    button_text_today = "je vous souhaite un très joyeux anniversaire"
    button_text_late = "joyeux anniversaire avec un peu de retard"

    if button_text_today in card_text:
        logging.info(f"✓ Anniversaire du jour détecté (bouton standard)")
        return 'today', 0

    if button_text_late in card_text:
        logging.info(f"✓ Anniversaire en retard détecté (bouton retard)")
        days = extract_days_from_date(card_text)
        if days is not None:
            if 1 <= days <= 10:
                logging.info(f"→ {days} jour(s) de retard - Classé comme 'late'")
                return 'late', days
            else:
                logging.info(f"→ {days} jour(s) de retard - Trop ancien, classé comme 'ignore'")
                return 'ignore', days
        else:
            logging.warning("⚠️ Retard détecté mais date non parsable, estimation à 2 jours")
            return 'late', 2

    # MÉTHODE 2 : Détection explicite "aujourd'hui"
    today_keywords = [
        'aujourd\'hui', 'aujourdhui', 'c\'est aujourd\'hui',
        'de [nom] aujourd\'hui', 'today', 'is today', '\'s birthday is today'
    ]

    for keyword in today_keywords:
        if keyword in card_text:
            logging.info(f"✓ Anniversaire du jour détecté (mot-clé: '{keyword}')")
            return 'today', 0

    # MÉTHODE 3 : Parser la date explicite
    days = extract_days_from_date(card_text)
    if days is not None:
        if days == 0:
            logging.info(f"✓ Date parsée = aujourd'hui")
            return 'today', 0
        elif 1 <= days <= 10:
            logging.info(f"✓ Date parsée = {days} jour(s) de retard")
            return 'late', days
        else:
            logging.info(f"→ Date parsée = {days} jour(s) - Trop ancien")
            return 'ignore', days

    # MÉTHODE 4 : Regex classique "il y a X jours"
    match_fr = re.search(r'il y a (\d+) jours?', card_text)
    match_en = re.search(r'(\d+) days? ago', card_text)

    if match_fr or match_en:
        days_late = int(match_fr.group(1) if match_fr else match_en.group(1))
        if 1 <= days_late <= 10:
            logging.info(f"✓ Regex détectée: {days_late} jour(s) de retard")
            return 'late', days_late
        else:
            logging.info(f"→ Regex: {days_late} jours - Trop ancien")
            return 'ignore', days_late

    # CAS PAR DÉFAUT
    logging.warning(f"⚠️ Aucun pattern reconnu dans la carte")
    logging.warning(f"Texte complet:\n{card_text}")

    time_keywords = ['retard', 'il y a', 'ago', 'récent']
    has_time_keyword = any(kw in card_text for kw in time_keywords)

    if not has_time_keyword:
        logging.info("→ Aucun indicateur de retard, classification: 'today'")
        return 'today', 0
    else:
        logging.warning("→ Indicateurs temporels ambigus, classification: 'ignore'")
        try:
            contact_element.screenshot(path=f'debug_unknown_pattern_{int(time.time())}.png')
        except Exception as e:
            logging.debug(f"Cannot save debug screenshot: {e}")
        return 'ignore', 0

def standardize_first_name(name: str) -> str:
    """
    Standardizes a first name by removing emojis and special characters,
    capitalizing properly, and handling compound names.
    """
    if not name:
        return ""

    # Remove emojis and special characters
    cleaned_chars = []
    for char in name:
        if char.isalpha() or char == '-' or char == ' ':
            cleaned_chars.append(char)

    cleaned_name = ''.join(cleaned_chars)

    # Normalize spaces
    while '  ' in cleaned_name:
        cleaned_name = cleaned_name.replace('  ', ' ')

    # Normalize hyphens
    cleaned_name = cleaned_name.replace(' - ', '-')
    cleaned_name = cleaned_name.replace('- ', '-')
    cleaned_name = cleaned_name.replace(' -', '-')

    cleaned_name = cleaned_name.strip()

    if not cleaned_name:
        return ""

    # Check if it's just an initial
    if len(cleaned_name) == 1:
        return ""

    # Handle compound names
    space_parts = cleaned_name.split(' ')

    processed_parts = []
    for space_part in space_parts:
        if not space_part:
            continue

        if '-' in space_part:
            hyphen_parts = space_part.split('-')
            capitalized_hyphen_parts = [part.capitalize() for part in hyphen_parts if part]
            processed_parts.append('-'.join(capitalized_hyphen_parts))
        else:
            processed_parts.append(space_part.capitalize())

    return ' '.join(processed_parts)

def send_birthday_message(page: Page, contact_element, is_late: bool = False, days_late: int = 0):
    """Opens the messaging modal and sends a personalized birthday wish."""

    # STEP 1: Fermer toutes les modales existantes AVANT d'en ouvrir une nouvelle
    close_all_message_modals(page)

    full_name = extract_contact_name(contact_element)
    if not full_name:
        logging.warning("Skipping contact because name could not be extracted.")
        return

    # Extract and standardize the first name
    first_name = full_name.split()[0]
    first_name = standardize_first_name(first_name)

    # Skip if the first name is just an initial
    if not first_name:
        logging.warning(f"Skipping contact '{full_name}' because first name is just an initial.")
        return

    if is_late:
        logging.info(f"--- Processing late birthday ({days_late} days ago) for {full_name} ---")
    else:
        logging.info(f"--- Processing current birthday for {full_name} ---")

    # Flag pour savoir si une modale a été ouverte (pour éviter les délais inutiles)
    modal_opened = False

    # Utiliser un try-finally pour garantir la fermeture de la modale même en cas d'erreur
    try:
        # Trouver et cliquer sur le bouton de message en utilisant un locator pour éviter les problèmes de détachement
        message_button_selector = 'a[aria-label*="Envoyer un message"], a[href*="/messaging/compose"], button:has-text("Message")'

        # Chercher le bouton Message avec gestion d'erreur pour élément détaché
        try:
            message_buttons_in_contact = contact_element.query_selector_all(message_button_selector)
        except Exception as e:
            logging.error(f"❌ Erreur lors de la recherche du bouton Message: {e}")
            logging.error(f"   contact_element est peut-être déjà détaché du DOM")
            return

        if not message_buttons_in_contact:
            logging.warning(f"Could not find a 'Message' button for {full_name}. Skipping.")
            return  # Pas de modale ouverte, pas de délai nécessaire

        # Cliquer sur le premier bouton trouvé avec gestion d'erreur
        try:
            message_buttons_in_contact[0].click()
            random_delay(1, 2)  # Délai augmenté pour laisser le temps à la modale de s'ouvrir
        except Exception as e:
            logging.error(f"❌ Erreur lors du clic initial sur le bouton Message: {e}")
            logging.error(f"   Type d'erreur: {type(e).__name__}")
            page.screenshot(path=f'error_initial_click_{first_name.replace(" ", "_")}.png')
            return

        message_box_selector = "div.msg-form__contenteditable[role='textbox']"
        page.wait_for_selector(message_box_selector, state="visible", timeout=30000)
        
        # Modale ouverte avec succès
        modal_opened = True

        # STEP 2: Vérifier combien de modales sont ouvertes
        modal_count = page.locator(message_box_selector).count()
        if modal_count > 1:
            logging.warning(f"⚠️ ATTENTION: {modal_count} modales détectées simultanément!")
            page.screenshot(path=f'warning_multiple_modals_{first_name.replace(" ", "_")}.png')
            
            # Fermer toutes les modales
            close_all_message_modals(page)
            random_delay(1, 2)  # Délai augmenté après fermeture
            
            # Re-trouver le bouton de message (l'ancien est détaché du DOM)
            logging.info("Re-opening message modal after cleanup...")

            # Attendre que le DOM se stabilise
            random_delay(1, 1.5)

            # Chercher directement dans les cartes d'anniversaire au lieu de parcourir tous les boutons
            message_button_found = None
            try:
                # Chercher toutes les cartes d'anniversaire
                all_cards = page.query_selector_all("div[role='listitem']")
                logging.info(f"   Recherche parmi {len(all_cards)} cartes...")

                # Trouver la carte qui contient le nom du contact
                for card in all_cards:
                    try:
                        card_text = card.inner_text()
                        if full_name in card_text or first_name in card_text:
                            # Trouver le bouton Message dans cette carte
                            message_button_found = card.query_selector(message_button_selector)
                            if message_button_found:
                                logging.info(f"   ✅ Bouton Message retrouvé dans la carte de {first_name}")
                                message_button_found.click()
                                random_delay(1, 2)
                                page.wait_for_selector(message_box_selector, state="visible", timeout=30000)
                                logging.info(f"   ✅ Modale ré-ouverte avec succès")
                                break
                    except Exception as e:
                        logging.debug(f"   Carte ignorée lors de la recherche: {e}")
                        continue

                if not message_button_found:
                    logging.error(f"   ❌ Impossible de retrouver le bouton Message après fermeture. Skip.")
                    return

            except Exception as e:
                logging.error(f"Failed to re-open modal for {full_name}: {e}")
                return

        # Toujours utiliser .last pour cibler la modale la plus récente
        message_box_locator = page.locator(message_box_selector).last

        logging.info(f"Message modal opened. Current viewport: {page.viewport_size}")
        page.screenshot(path=f'debug_message_modal_{first_name.replace(" ", "_")}.png')

        # Select the appropriate message list
        if is_late:
            message_list = LATE_BIRTHDAY_MESSAGES
            if not message_list:
                logging.warning("Late birthday message list is empty. Using default messages.")
                message_list = BIRTHDAY_MESSAGES
        else:
            message_list = BIRTHDAY_MESSAGES

        if not message_list:
            logging.error("No birthday messages are available. Skipping message sending.")
            return

        message = random.choice(message_list).format(name=first_name)

        # Check message history if database available
        previous_messages = []
        db = None
        if DATABASE_AVAILABLE:
            try:
                db = get_database()
                previous_messages = db.get_messages_sent_to_contact(full_name, years=2)
            except Exception as e:
                logging.warning(f"Could not access database: {e}")
                db = None

        if previous_messages:
            used_messages = {msg['message_text'] for msg in previous_messages}
            available_messages = [msg for msg in message_list if msg.format(name=first_name) not in used_messages]

            if available_messages:
                message = random.choice(available_messages).format(name=first_name)
                logging.info(f"Selected unused message from {len(available_messages)} available")
            else:
                message = random.choice(message_list).format(name=first_name)
                logging.warning(f"All messages used for {full_name}, reusing from pool")

        if DRY_RUN:
            logging.info(f"[DRY RUN] Would send message to {first_name}: '{message}'")
            if db:
                try:
                    db.add_birthday_message(full_name, message, is_late, days_late, "routine_dry_run")
                except Exception as e:
                    logging.warning(f"Could not record to database: {e}")
            return

        # Effacer et taper le message
        logging.info(f"Typing message: '{message}'")
        message_box_locator.clear()
        random_delay(0.3, 0.5)
        message_box_locator.fill(message)
        random_delay(1, 2)

        # Send button
        submit_button = page.locator("button.msg-form__send-button").last

        try:
            message_box_locator.scroll_into_view_if_needed(timeout=5000)
            random_delay(0.3, 0.5)
            submit_button.scroll_into_view_if_needed(timeout=5000)
            random_delay(0.5, 1)

            if submit_button.is_enabled():
                submit_button.click()
                logging.info("Message sent successfully.")
                if db:
                    try:
                        db.add_birthday_message(full_name, message, is_late, days_late, "routine")
                    except Exception as e:
                        logging.warning(f"Could not record to database: {e}")
            else:
                logging.warning("Send button is not enabled. Skipping.")
        except Exception as e:
            logging.warning(f"Could not send message normally ({type(e).__name__}), attempting force click...")
            page.screenshot(path=f'warning_send_issue_{first_name.replace(" ", "_")}.png')
            try:
                submit_button.click(force=True, timeout=10000)
                logging.info("Message sent successfully (force click).")
                if db:
                    try:
                        db.add_birthday_message(full_name, message, is_late, days_late, "routine")
                    except Exception as e:
                        logging.warning(f"Could not record to database: {e}")
            except Exception as e2:
                error_msg = f"Failed to click send button: {e2}"
                logging.error(error_msg)
                page.screenshot(path=f'error_send_button_{first_name.replace(" ", "_")}.png')
                if db and DATABASE_AVAILABLE:
                    try:
                        db.log_error("linkedin_birthday_wisher", "SendButtonError", error_msg, str(e2), f'error_send_button_{first_name.replace(" ", "_")}.png')
                    except Exception:
                        pass
                raise

    finally:
        # STEP 3: Fermer la modale UNIQUEMENT si elle a été ouverte
        if modal_opened:
            random_delay(0.5, 1)
            close_all_message_modals(page)
        # Si pas de modale ouverte (bouton Message non trouvé), pas de délai ni fermeture


# --- Main Execution ---

def main():
    """Main function to run the LinkedIn birthday wisher bot - VERSION ANNIVERSAIRES DU JOUR UNIQUEMENT."""
    
    logging.info("╔════════════════════════════════════════════════════════════════╗")
    logging.info("║    LinkedIn Birthday Wisher - ANNIVERSAIRES DU JOUR SEULS    ║")
    logging.info("╚════════════════════════════════════════════════════════════════╝")
    
    if DRY_RUN:
        logging.info("🧪 SCRIPT RUNNING IN DRY RUN MODE")
    else:
        logging.info("🚀 SCRIPT RUNNING IN PRODUCTION MODE")
        logging.info("🎂 Traitement des anniversaires du jour uniquement")
        logging.info("⏭️  Les anniversaires en retard sont ignorés")
    
    logging.info("")

    # ═══════════════════════════════════════════════════════════════════════════
    # VERSION ANNIVERSAIRES DU JOUR UNIQUEMENT
    # - Traite seulement les anniversaires d'aujourd'hui
    # - Ignore les anniversaires en retard
    # - Parfait pour usage quotidien automatisé
    # ═══════════════════════════════════════════════════════════════════════════

    if not BIRTHDAY_MESSAGES:
        logging.error("❌ Message list is empty. Please check messages.txt. Exiting.")
        return

    # --- Authentication Setup ---
    if LINKEDIN_AUTH_STATE and LINKEDIN_AUTH_STATE.strip():
        try:
            # Try to load as JSON
            json.loads(LINKEDIN_AUTH_STATE)
            logging.info("Auth state is valid JSON. Writing to file.")
            with open(AUTH_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(LINKEDIN_AUTH_STATE)
        except json.JSONDecodeError:
            # Try Base64
            logging.info("Auth state is Base64, decoding...")
            try:
                padding = '=' * (-len(LINKEDIN_AUTH_STATE) % 4)
                auth_state_padded = LINKEDIN_AUTH_STATE + padding
                auth_state_bytes = base64.b64decode(auth_state_padded)
                with open(AUTH_FILE_PATH, "wb") as f:
                    f.write(auth_state_bytes)
            except (base64.binascii.Error, TypeError) as e:
                logging.error(f"Failed to decode Base64 auth state: {e}")
                return
        except Exception as e:
            logging.error(f"Unexpected error during auth state setup: {e}")
            return
    else:
        logging.info("Using existing auth_state.json file")

    # Check if auth file exists
    if not os.path.exists(AUTH_FILE_PATH):
        logging.error(f"❌ {AUTH_FILE_PATH} not found. Please run generate_linkedin_auth.py first.")
        return

    with sync_playwright() as p:
        # Initialize proxy manager if available
        proxy_manager = None
        proxy_config = None
        proxy_start_time = None

        if PROXY_AVAILABLE:
            try:
                proxy_manager = ProxyManager()
                if proxy_manager.is_enabled():
                    proxy_config = proxy_manager.get_playwright_proxy_config()
                    proxy_start_time = time.time()
                    if proxy_config:
                        logging.info(f"🌐 Proxy enabled")
            except Exception as e:
                logging.warning(f"Proxy initialization failed: {e}")

        # Randomize browser parameters
        selected_user_agent = random.choice(USER_AGENTS)
        selected_viewport = random.choice(VIEWPORT_SIZES)

        logging.info(f"🔧 User-Agent: {selected_user_agent[:50]}...")
        logging.info(f"🔧 Viewport: {selected_viewport}")

        browser = p.chromium.launch(
            headless=HEADLESS_BROWSER,
            slow_mo=random.randint(80, 150),
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                f'--window-size={selected_viewport["width"]},{selected_viewport["height"]}'
            ]
        )

        # Build context options
        context_options = {
            'storage_state': AUTH_FILE_PATH,
            'user_agent': selected_user_agent,
            'viewport': selected_viewport,
            'locale': 'fr-FR',
            'timezone_id': 'Europe/Paris'
        }

        if proxy_config:
            context_options['proxy'] = proxy_config

        context = browser.new_context(**context_options)

        # Apply stealth mode if available
        try:
            from playwright_stealth import Stealth
            stealth = Stealth()
            stealth.apply_stealth_sync(context)
            logging.info("✅ Stealth mode activated")
        except ImportError:
            logging.warning("⚠️ playwright-stealth not installed")

        page = context.new_page()

        # Initialize debugging managers if enabled
        screenshot_mgr = None
        enhanced_logger = None
        policy_detector = None
        alert_system = None

        if ENABLE_ADVANCED_DEBUG and DEBUG_UTILS_AVAILABLE:
            logging.info("🔧 Advanced debugging enabled")
            try:
                screenshot_mgr = DebugScreenshotManager()
                enhanced_logger = EnhancedLogger()
                policy_detector = LinkedInPolicyDetector(page)
                if ENABLE_EMAIL_ALERTS:
                    alert_system = AlertSystem()
                    logging.info("📧 Email alerts enabled")
            except Exception as e:
                logging.warning(f"Could not initialize debug tools: {e}")

        try:
            # Capture initial state
            if screenshot_mgr:
                screenshot_mgr.capture(page, "01_browser_start")

            if not check_login_status(page):
                logging.error("❌ Login verification failed")
                if screenshot_mgr:
                    screenshot_mgr.capture(page, "login_failed", error=True)
                if alert_system:
                    alert_system.send_alert("Login Failed", f"Failed to verify login at {page.url}")
                return

            # Navigate to birthdays page
            page.goto("https://www.linkedin.com/feed/", timeout=60000)
            random_delay(1, 2)

            # Validate selectors if available
            if VALIDATOR_AVAILABLE:
                logging.info("🔍 Validating selectors...")
                validate_birthday_feed_selectors(page)

            random_delay(2, 4)

            birthdays = get_birthday_contacts(page)

            # Capture state
            if screenshot_mgr:
                screenshot_mgr.capture(page, "03_birthdays_page_loaded")

            # ═══════════════════════════════════════════════════════════════
            # VERSION SANS LIMITATIONS:
            # - Tous les anniversaires sont traités
            # - Aucune limite hebdomadaire
            # - Délais fixes entre messages pour éviter la détection
            # ═══════════════════════════════════════════════════════════════

            total_today = len(birthdays['today'])
            total_late = len(birthdays['late'])

            logging.info(f"📊 Total birthdays detected: today={total_today}, late={total_late}")
            
            # ═══════════════════════════════════════════════════════════════════════════
            # VERSION LIMITÉE AUX ANNIVERSAIRES DU JOUR
            # Les anniversaires en retard sont IGNORÉS
            # ═══════════════════════════════════════════════════════════════════════════
            
            if total_late > 0:
                logging.info(f"⏭️  Ignoring {total_late} late birthdays (script configured for today only)")
            
            logging.info(f"✅ {total_today} birthdays from today will be processed")
            logging.info(f"⏱️  Delay between messages: {MIN_DELAY_SECONDS//60}-{MAX_DELAY_SECONDS//60} minutes")
            logging.info("")

            # Track total messages sent
            total_messages_sent = 0

            # Process ONLY today's birthdays
            if birthdays['today']:
                logging.info(f"🎂 Processing {len(birthdays['today'])} birthdays from today...")
                for i, contact in enumerate(birthdays['today']):
                    send_birthday_message(page, contact, is_late=False)
                    total_messages_sent += 1

                    # Simulate human activity occasionally
                    if random.random() < 0.3:
                        simulate_human_activity(page)

                    # Pause between messages (except for last one)
                    if i < len(birthdays['today']) - 1:
                        if not DRY_RUN:
                            delay = random.randint(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                            minutes = delay // 60
                            seconds = delay % 60
                            logging.info(f"⏸️  Pause: {minutes}m {seconds}s")
                            time.sleep(delay)
                        else:
                            delay = random.randint(2, 5)
                            logging.info(f"⏸️  Pause (DRY RUN): {delay}s")
                            time.sleep(delay)
            else:
                logging.info("ℹ️  No birthdays today - nothing to do")

            logging.info("")
            logging.info("╔════════════════════════════════════════════════════════════════╗")
            logging.info(f"║  ✅ Script finished successfully - {total_messages_sent} messages sent  ║")
            logging.info("╚════════════════════════════════════════════════════════════════╝")

            # Final screenshot
            if screenshot_mgr:
                screenshot_mgr.capture(page, "99_execution_completed")

        except PlaywrightTimeoutError as e:
            logging.error(f"❌ Timeout error: {e}")
            if proxy_config and proxy_start_time and proxy_manager:
                proxy_manager.record_proxy_result(
                    proxy_config.get('server', 'unknown'),
                    success=False,
                    response_time=time.time() - proxy_start_time,
                    error_message=str(e)
                )
            if screenshot_mgr:
                screenshot_mgr.capture(page, "error_timeout", error=True)
            else:
                page.screenshot(path='error_timeout.png')

        except Exception as e:
            logging.error(f"❌ Unexpected error: {e}")
            if proxy_config and proxy_start_time and proxy_manager:
                proxy_manager.record_proxy_result(
                    proxy_config.get('server', 'unknown'),
                    success=False,
                    response_time=time.time() - proxy_start_time,
                    error_message=str(e)
                )
            if screenshot_mgr:
                screenshot_mgr.capture(page, "error_unexpected", error=True)
            else:
                page.screenshot(path='error_unexpected.png')

        finally:
            # Record proxy success if used
            if proxy_config and proxy_start_time and proxy_manager:
                proxy_manager.record_proxy_result(
                    proxy_config.get('server', 'unknown'),
                    success=True,
                    response_time=time.time() - proxy_start_time
                )

            logging.info("🔒 Closing browser...")
            browser.close()
            
            # Clean up auth file for security
            if os.path.exists(AUTH_FILE_PATH) and LINKEDIN_AUTH_STATE:
                os.remove(AUTH_FILE_PATH)

            if ENABLE_ADVANCED_DEBUG:
                logging.info("🔧 Check debug_screenshots/ for details")

if __name__ == "__main__":
    main()
