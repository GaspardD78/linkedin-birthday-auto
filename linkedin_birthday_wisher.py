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

# Import debug utilities
from debug_utils import (
    DebugScreenshotManager,
    DOMStructureValidator,
    LinkedInPolicyDetector,
    EnhancedLogger,
    AlertSystem,
    retry_with_fallbacks,
    quick_debug_check
)

# Import database utilities
from database import get_database

# Import selector validator
from selector_validator import validate_birthday_feed_selectors, validate_messaging_selectors

# Import proxy manager
from proxy_manager import ProxyManager

# --- Configuration ---
# Logging setup
# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/birthday_wisher.log"),
        logging.StreamHandler()
    ]
)

# Secure authentication using an auth state from GitHub Secrets
LINKEDIN_AUTH_STATE = os.getenv('LINKEDIN_AUTH_STATE')
AUTH_FILE_PATH = "auth_state.json"

# General settings
HEADLESS_BROWSER = True # Set to False for debugging to see the browser UI
DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true' # Enables test mode

# Advanced debugging settings
ENABLE_ADVANCED_DEBUG = os.getenv('ENABLE_ADVANCED_DEBUG', 'false').lower() == 'true'
ENABLE_EMAIL_ALERTS = os.getenv('ENABLE_EMAIL_ALERTS', 'false').lower() == 'true'

# Anti-detection limits
MAX_MESSAGES_PER_RUN = None  # Pas de limite - tous les anniversaires du jour doivent être fêtés
WEEKLY_MESSAGE_LIMIT = 80  # Limite hebdomadaire (sous la limite LinkedIn de 100)
WEEKLY_TRACKER_FILE = "weekly_messages.json"

# Planification des messages entre 7h et 19h
DAILY_START_HOUR = 7  # Début d'envoi des messages (7h du matin)
DAILY_END_HOUR = 19   # Fin d'envoi des messages (19h le soir)
DAILY_WINDOW_SECONDS = (DAILY_END_HOUR - DAILY_START_HOUR) * 3600  # 12 heures = 43200 secondes

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

# --- Timezone Check for Automatic Schedule ---

def check_paris_timezone_window(target_hour_start: int, target_hour_end: int) -> bool:
    """
    Vérifie si l'heure actuelle à Paris est dans la fenêtre horaire souhaitée.
    Cette fonction permet d'avoir des cron jobs doubles (été/hiver) qui s'adaptent
    automatiquement aux changements d'heure sans intervention manuelle.

    Args:
        target_hour_start: Heure de début de la fenêtre (ex: 7 pour 7h)
        target_hour_end: Heure de fin de la fenêtre (ex: 9 pour 9h)

    Returns:
        True si l'heure actuelle à Paris est dans la fenêtre, False sinon
    """
    paris_tz = pytz.timezone('Europe/Paris')
    paris_time = datetime.now(paris_tz)
    current_hour = paris_time.hour

    logging.info(f"⏰ Heure actuelle à Paris: {paris_time.strftime('%H:%M:%S')} (timezone: {paris_tz})")
    logging.info(f"📅 Fenêtre d'exécution autorisée: {target_hour_start}h - {target_hour_end}h")

    if target_hour_start <= current_hour < target_hour_end:
        logging.info(f"✅ Heure valide ({current_hour}h) - Le script va s'exécuter")
        return True
    else:
        logging.info(f"⏸️  Heure invalide ({current_hour}h) - Script arrêté (mauvaise fenêtre horaire)")
        logging.info(f"ℹ️  Ce comportement est normal : les doubles crons (été/hiver) garantissent")
        logging.info(f"   qu'un seul s'exécute dans la bonne fenêtre horaire, sans ajustement manuel.")
        return False

# --- Weekly Message Tracking ---

def load_weekly_count():
    """Charge le compteur de messages de la semaine."""
    try:
        with open(WEEKLY_TRACKER_FILE, 'r') as f:
            data = json.load(f)
            # Réinitialiser si plus d'une semaine
            last_reset = datetime.fromisoformat(data['last_reset'])
            if datetime.now() - last_reset > timedelta(days=7):
                return {'count': 0, 'last_reset': datetime.now().isoformat()}
            return data
    except (FileNotFoundError, KeyError, ValueError):
        return {'count': 0, 'last_reset': datetime.now().isoformat()}

def save_weekly_count(count):
    """Sauvegarde le compteur de messages hebdomadaires."""
    data = load_weekly_count()
    data['count'] = count
    with open(WEEKLY_TRACKER_FILE, 'w') as f:
        json.dump(data, f)

def can_send_more_messages(messages_to_send):
    """Vérifie si on peut envoyer plus de messages cette semaine."""
    data = load_weekly_count()

    if data['count'] + messages_to_send > WEEKLY_MESSAGE_LIMIT:
        logging.warning(f"⚠️ Limite hebdomadaire atteinte ({data['count']}/{WEEKLY_MESSAGE_LIMIT})")
        return False, WEEKLY_MESSAGE_LIMIT - data['count']
    return True, messages_to_send

def calculate_optimal_delay(total_messages: int, start_hour: int = DAILY_START_HOUR, end_hour: int = DAILY_END_HOUR) -> tuple[int, int]:
    """
    Calcule le délai optimal entre les messages pour les répartir dans la journée.
    Tient compte de l'heure actuelle pour répartir les messages jusqu'à end_hour.

    Args:
        total_messages: Nombre total de messages à envoyer
        start_hour: Heure de début (défaut: 7h) - utilisé pour les logs
        end_hour: Heure de fin (défaut: 19h)

    Returns:
        tuple[int, int]: (délai_minimum_secondes, délai_maximum_secondes)
    """
    if total_messages <= 0:
        return (0, 0)

    # Obtenir l'heure actuelle
    now = datetime.now()
    current_hour = now.hour + now.minute / 60.0  # Heure avec décimales

    # Calculer le temps restant jusqu'à end_hour
    if current_hour >= end_hour:
        # Si on est déjà passé l'heure de fin, utiliser un délai minimal
        logging.warning(f"⚠️ Heure actuelle ({now.hour}h{now.minute:02d}) dépasse l'heure de fin ({end_hour}h)")
        logging.warning(f"   Les messages seront envoyés avec un délai minimal de 3 minutes")
        return (180, 300)  # 3-5 minutes

    # Temps restant en heures
    remaining_hours = end_hour - current_hour
    window_seconds = remaining_hours * 3600

    # Calculer le délai moyen entre les messages
    average_delay = window_seconds / total_messages

    # Ajouter une variation de ±20% pour rendre les envois plus naturels
    min_delay = int(average_delay * 0.8)
    max_delay = int(average_delay * 1.2)

    # S'assurer qu'on a au moins 60 secondes entre les messages
    min_delay = max(60, min_delay)

    # Calculer l'heure de fin estimée
    end_time = now.hour + (window_seconds / 3600)
    end_hour_estimated = int(end_time)
    end_minute_estimated = int((end_time % 1) * 60)

    logging.info(f"📅 Planification: {total_messages} messages à répartir jusqu'à {end_hour}h")
    logging.info(f"⏰ Heure actuelle: {now.hour}h{now.minute:02d} - Temps disponible: {remaining_hours:.1f}h")
    logging.info(f"⏱️  Délai moyen: {average_delay/60:.1f} minutes (variation: {min_delay/60:.1f}m - {max_delay/60:.1f}m)")
    logging.info(f"🏁 Fin estimée: ~{end_hour_estimated}h{end_minute_estimated:02d}")

    return (min_delay, max_delay)

# --- Human Behavior Simulation ---

def random_delay(min_seconds: float = 0.5, max_seconds: float = 1.5):
    """Waits for a random duration within a specified range to mimic human latency."""
    time.sleep(random.uniform(min_seconds, max_seconds))

def gaussian_delay(min_seconds: int, max_seconds: int):
    """
    Waits for a random duration using a Gaussian (normal) distribution.
    This is more human-like than uniform distribution as humans tend to cluster
    around average times with occasional faster/slower actions.

    Args:
        min_seconds: Minimum delay in seconds
        max_seconds: Maximum delay in seconds
    """
    mean = (min_seconds + max_seconds) / 2
    # Standard deviation: ~99.7% of values fall within 3 std devs
    # So (max - min) = 6*std, therefore std = (max - min) / 6
    std_dev = (max_seconds - min_seconds) / 6

    # Generate delay with normal distribution
    delay = random.gauss(mean, std_dev)

    # Clamp to ensure we stay within bounds
    delay = max(min_seconds, min(max_seconds, delay))

    minutes = int(delay // 60)
    seconds = int(delay % 60)
    logging.info(f"Pausing for {minutes}m {seconds}s (Gaussian delay).")
    time.sleep(delay)

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

def long_break_if_needed(message_count: int, break_intervals: list = None) -> tuple[bool, list]:
    """
    Determines if a long break should be taken and executes it.
    Takes a 20-45 minute break every 10-15 messages to simulate natural human behavior.

    Args:
        message_count: Current count of messages sent
        break_intervals: List of message counts where breaks should occur.
                        If None, a new list will be generated.

    Returns:
        Tuple of (break_taken: bool, updated_break_intervals: list)
    """
    # Initialize break intervals if not provided
    if break_intervals is None:
        break_intervals = []

    # Generate next break point if needed
    if not break_intervals or (break_intervals and message_count >= break_intervals[-1]):
        # Set the next break to occur in 10-15 messages
        next_break = message_count + random.randint(10, 15)
        break_intervals.append(next_break)

    # Check if it's time for a break
    if message_count in break_intervals and message_count > 0:
        long_pause = random.randint(20 * 60, 45 * 60)  # 20-45 minutes
        minutes = long_pause // 60
        logging.info(f"🚽 Taking a natural break: {minutes} minute pause (simulating coffee/meeting/bathroom)")
        time.sleep(long_pause)
        return True, break_intervals

    return False, break_intervals

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

# Fonction supprimée car non utilisée - voir send_birthday_message() qui fait le typage directement

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
    Inspired by the logic from content.js.
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

def debug_birthday_card(contact_element, card_index: int = 0):
    """
    Fonction de debug pour analyser une carte d'anniversaire en détail.
    Utile pour diagnostiquer les problèmes de classification.
    """
    logging.info(f"═══════════════════════════════════════════════════")
    logging.info(f"🔍 DEBUG - Carte #{card_index}")
    logging.info(f"═══════════════════════════════════════════════════")

    # Extraire le texte complet
    full_text = contact_element.inner_text()
    logging.info(f"Texte complet:\n{full_text}")
    logging.info(f"")

    # Analyser chaque paragraphe
    paragraphs = contact_element.query_selector_all("p")
    logging.info(f"Nombre de paragraphes trouvés: {len(paragraphs)}")

    for i, p in enumerate(paragraphs):
        p_text = p.inner_text().strip()
        logging.info(f"  Paragraphe {i+1}: '{p_text}'")

    # Tester la classification
    birthday_type, days_late = get_birthday_type(contact_element)
    logging.info(f"")
    logging.info(f"Résultat de classification:")
    logging.info(f"  Type: {birthday_type}")
    logging.info(f"  Jours de retard: {days_late}")

    # Screenshot de la carte
    screenshot_path = f'debug_card_{card_index}_{birthday_type}.png'
    try:
        contact_element.screenshot(path=screenshot_path)
        logging.info(f"Screenshot sauvegardée: {screenshot_path}")
    except Exception as e:
        logging.warning(f"Impossible de sauvegarder la screenshot: {e}")
    logging.info(f"═══════════════════════════════════════════════════")

def extract_days_from_date(card_text: str) -> Optional[int]:
    """
    Extrait le nombre de jours entre une date mentionnée dans le texte et aujourd'hui.

    Exemple: "Célébrez l'anniversaire récent de Frédéric le 10 nov."
    Si on est le 18 nov → retourne 8 jours

    Returns:
        int: Nombre de jours de différence (0 = aujourd'hui, positif = passé)
        None: Si aucune date n'a pu être extraite
    """
    # Pattern pour capturer "le X mois" (ex: "le 10 nov.")
    # Supporte : nov, nov., novembre, dec, déc, décembre, etc.
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

    Logique de détection améliorée basée sur l'analyse des screenshots réels LinkedIn.
    Utilise une approche multi-méthodes pour une classification robuste.

    Returns:
        tuple[str, int]: (type, days_late)
            - type: 'today', 'late', ou 'ignore'
            - days_late: nombre de jours de retard (0 pour aujourd'hui)
    """
    card_text = contact_element.inner_text().lower()

    # Debug: afficher le texte complet de la carte en mode debug avancé
    logging.debug(f"Analyzing card text: {card_text[:200]}...")

    # ═══════════════════════════════════════════════════════════
    # MÉTHODE 1 (La plus fiable) : Analyser le texte du bouton
    # ═══════════════════════════════════════════════════════════

    # LinkedIn utilise des boutons différents selon la date:
    # - Aujourd'hui : "Je vous souhaite un très joyeux anniversaire."
    # - En retard :   "Joyeux anniversaire avec un peu de retard !"

    button_text_today = "je vous souhaite un très joyeux anniversaire"
    button_text_late = "joyeux anniversaire avec un peu de retard"

    if button_text_today in card_text:
        logging.info(f"✓ Anniversaire du jour détecté (bouton standard)")
        return 'today', 0

    if button_text_late in card_text:
        logging.info(f"✓ Anniversaire en retard détecté (bouton retard)")
        # Maintenant on doit déterminer COMBIEN de jours de retard
        # On va parser la date dans le texte
        days = extract_days_from_date(card_text)
        if days is not None:
            if 1 <= days <= 10:
                logging.info(f"→ {days} jour(s) de retard - Classé comme 'late'")
                return 'late', days
            else:
                logging.info(f"→ {days} jour(s) de retard - Trop ancien, classé comme 'ignore'")
                return 'ignore', days
        else:
            # Si on ne peut pas extraire le nombre exact de jours,
            # on suppose un retard de 1-3 jours basé sur le fait que LinkedIn affiche ce bouton
            logging.warning("⚠️ Retard détecté mais date non parsable, estimation à 2 jours")
            return 'late', 2  # Valeur par défaut conservatrice

    # ═══════════════════════════════════════════════════════════
    # MÉTHODE 2 : Détection explicite "aujourd'hui"
    # ═══════════════════════════════════════════════════════════

    today_keywords = [
        'aujourd\'hui',
        'aujourdhui',
        'c\'est aujourd\'hui',
        'de [nom] aujourd\'hui',
        'today',
        'is today',
        '\'s birthday is today'
    ]

    for keyword in today_keywords:
        if keyword in card_text:
            logging.info(f"✓ Anniversaire du jour détecté (mot-clé: '{keyword}')")
            return 'today', 0

    # ═══════════════════════════════════════════════════════════
    # MÉTHODE 3 : Parser la date explicite (ex: "le 10 nov.")
    # ═══════════════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════════════
    # MÉTHODE 4 : Regex classique "il y a X jours"
    # ═══════════════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════════════
    # CAS PAR DÉFAUT : Classification conservatrice
    # ═══════════════════════════════════════════════════════════

    logging.warning(f"⚠️ Aucun pattern reconnu dans la carte")
    logging.warning(f"Texte complet:\n{card_text}")

    # Si aucun indicateur de retard, on suppose que c'est aujourd'hui
    # (LinkedIn affiche généralement les anniversaires du jour en premier)
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
    Standardizes a first name by:
    - Removing emojis and special characters (except accents and hyphens)
    - Capitalizing the first letter of each part in compound names (e.g., Marie-Claude, Jean Marie)
    - Converting the rest to lowercase
    - Returning empty string if the name is just an initial (e.g., "C" or "C.")

    Args:
        name: The first name to standardize

    Returns:
        The standardized first name, or empty string if invalid

    Examples:
        "jean" -> "Jean"
        "MARIE" -> "Marie"
        "marie-claude" -> "Marie-Claude"
        "jean marie" -> "Jean Marie"
        "Jean🎉" -> "Jean"
        "françois" -> "François"
        "C" -> ""
        "C." -> ""
    """
    if not name:
        return ""

    # Remove emojis and special characters (including periods)
    # Keep only: letters (including accented), hyphens, and spaces
    cleaned_chars = []
    for char in name:
        # Keep alphabetic characters, hyphens, and spaces
        if char.isalpha() or char == '-' or char == ' ':
            cleaned_chars.append(char)

    cleaned_name = ''.join(cleaned_chars)

    # Normalize spaces: replace multiple spaces with single space
    while '  ' in cleaned_name:
        cleaned_name = cleaned_name.replace('  ', ' ')

    # Normalize spaces around hyphens: "marie - claude" -> "marie-claude"
    cleaned_name = cleaned_name.replace(' - ', '-')
    cleaned_name = cleaned_name.replace('- ', '-')
    cleaned_name = cleaned_name.replace(' -', '-')

    cleaned_name = cleaned_name.strip()

    if not cleaned_name:
        return ""  # Return empty if nothing left after cleaning

    # Check if it's just an initial (single letter)
    if len(cleaned_name) == 1:
        return ""  # Ignore single letter initials

    # Handle names with multiple parts (spaces or hyphens)
    # Split by spaces first to handle "Jean Marie" type names
    space_parts = cleaned_name.split(' ')

    # Process each space-separated part
    processed_parts = []
    for space_part in space_parts:
        if not space_part:
            continue

        # Check if this part has hyphens (e.g., "Marie-Claude")
        if '-' in space_part:
            hyphen_parts = space_part.split('-')
            capitalized_hyphen_parts = [part.capitalize() for part in hyphen_parts if part]
            processed_parts.append('-'.join(capitalized_hyphen_parts))
        else:
            # Simple part, just capitalize
            processed_parts.append(space_part.capitalize())

    return ' '.join(processed_parts)

def send_birthday_message(page: Page, contact_element, is_late: bool = False, days_late: int = 0) -> bool:
    """
    Opens the messaging modal and sends a personalized birthday wish.

    Returns:
        True if message was sent successfully, False otherwise
    """

    # STEP 1: Fermer toutes les modales existantes AVANT d'en ouvrir une nouvelle
    close_all_message_modals(page)

    full_name = extract_contact_name(contact_element)
    if not full_name:
        logging.warning("Skipping contact because name could not be extracted.")
        return False

    # Extract and standardize the first name
    first_name = full_name.split()[0]
    first_name = standardize_first_name(first_name)

    # Skip if the first name is just an initial (returns empty string)
    if not first_name:
        logging.warning(f"Skipping contact '{full_name}' because first name is just an initial.")
        return False

    if is_late:
        logging.info(f"--- Processing late birthday ({days_late} days ago) for {full_name} ---")
    else:
        logging.info(f"--- Processing current birthday for {full_name} ---")

    # Use a robust selector for the message button
    message_button = contact_element.query_selector(
        'a[aria-label*="Envoyer un message"], a[href*="/messaging/compose"], button:has-text("Message")'
    )
    if not message_button:
        logging.warning(f"Message button not found for {full_name}. Skipping.")
        return False

    # Utiliser un try-finally pour garantir la fermeture de la modale même en cas d'erreur
    try:
        message_button.click()
        random_delay(0.5, 1)  # Petit délai après le clic

        message_box_selector = "div.msg-form__contenteditable[role='textbox']"
        page.wait_for_selector(message_box_selector, state="visible", timeout=30000)

        # STEP 2: Vérifier combien de modales sont ouvertes et utiliser .last pour la plus récente
        modal_count = page.locator(message_box_selector).count()
        if modal_count > 1:
            logging.warning(f"⚠️ ATTENTION: {modal_count} modales détectées simultanément!")
            logging.warning(f"   Fermeture automatique de toutes les modales...")
            page.screenshot(path=f'warning_multiple_modals_{first_name.replace(" ", "_")}.png')

            # Fermer toutes les modales
            close_all_message_modals(page)
            random_delay(0.5, 1)

            # Attendre que toutes les modales soient fermées
            try:
                page.wait_for_selector(message_box_selector, state="hidden", timeout=5000)
            except:
                pass  # Continue même si timeout

            random_delay(0.3, 0.6)

            # RE-CHERCHER le bouton Message (évite "Element is not attached to the DOM")
            logging.info(f"   Re-recherche du bouton Message pour {first_name}...")
            message_button = contact_element.query_selector(
                'a[aria-label*="Envoyer un message"], a[href*="/messaging/compose"], button:has-text("Message")'
            )

            if not message_button:
                logging.error(f"   ❌ Impossible de retrouver le bouton Message après fermeture des modales. Skip.")
                return False

            # Rouvrir la modale proprement
            logging.info(f"   Ré-ouverture de la modale pour {first_name}...")
            message_button.click()
            random_delay(0.5, 1)

            # Vérifier que la modale s'est ouverte
            try:
                page.wait_for_selector(message_box_selector, state="visible", timeout=10000)
                logging.info(f"   ✅ Modale ré-ouverte avec succès")
            except Exception as e:
                logging.error(f"   ❌ Échec de ré-ouverture de la modale : {e}")
                return False

        # Toujours utiliser .last pour cibler la modale la plus récemment ouverte
        message_box_locator = page.locator(message_box_selector).last

        # Debug logging for troubleshooting viewport issues
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
            return False

        message = random.choice(message_list).format(name=first_name)

        # Check message history to avoid repetition (with fallback)
        previous_messages = []
        db = None
        try:
            db = get_database()
            previous_messages = db.get_messages_sent_to_contact(full_name, years=2)
        except Exception as e:
            logging.warning(f"Could not access database for message history: {e}. Proceeding with random selection.")
            db = None  # Reset db to None to avoid using it later

        if previous_messages:
            # Filter out messages already used for this contact
            used_messages = {msg['message_text'] for msg in previous_messages}
            available_messages = [msg for msg in message_list if msg.format(name=first_name) not in used_messages]

            if available_messages:
                message = random.choice(available_messages).format(name=first_name)
                logging.info(f"Selected unused message from {len(available_messages)} available options (avoiding {len(used_messages)} used)")
            else:
                # All messages have been used, reset and pick any
                message = random.choice(message_list).format(name=first_name)
                logging.warning(f"All {len(message_list)} messages have been used for {full_name}, reusing from pool")

        if DRY_RUN:
            logging.info(f"[DRY RUN] Would send message to {first_name}: '{message}'")
            # Record message in database even in dry run mode for testing (if db available)
            if db:
                try:
                    db.add_birthday_message(full_name, message, is_late, days_late, "routine_dry_run")
                except Exception as e:
                    logging.warning(f"Could not record message to database: {e}")
            return True  # Succès en mode DRY_RUN

        # Effacer le texte automatique que LinkedIn pré-remplit (ex: "Je vous souhaite un très joyeux anniversaire.")
        # puis ajouter notre message personnalisé
        logging.info(f"Typing message: '{message}'")
        message_box_locator.clear()  # Effacer le texte pré-rempli
        random_delay(0.3, 0.5)  # Petit délai pour simuler le comportement humain
        message_box_locator.fill(message)
        random_delay(1, 2)

        # Use .last to target the most recently opened message form's send button
        # This avoids strict mode violations when multiple message forms are present on the page
        submit_button = page.locator("button.msg-form__send-button").last

        # Ensure the button is in viewport before clicking to avoid timeout errors
        try:
            # First try to scroll the message box (modal) into view
            message_box_locator.scroll_into_view_if_needed(timeout=5000)
            random_delay(0.3, 0.5)

            # Then scroll the send button into view
            submit_button.scroll_into_view_if_needed(timeout=5000)
            random_delay(0.5, 1)  # Small delay to let UI settle after scrolling

            if submit_button.is_enabled():
                submit_button.click()
                logging.info("Message sent successfully.")
                # Record message in database (with fallback)
                if db:
                    try:
                        db.add_birthday_message(full_name, message, is_late, days_late, "routine")
                    except Exception as db_err:
                        logging.warning(f"Could not record message to database: {db_err}")
                return True  # Message envoyé avec succès
            else:
                logging.warning("Send button is not enabled. Skipping.")
                return False
        except Exception as e:
            # Catch all exceptions (timeout, viewport issues, etc.)
            logging.warning(f"Could not send message normally ({type(e).__name__}: {e}), attempting force click...")
            page.screenshot(path=f'warning_send_issue_{first_name.replace(" ", "_")}.png')
            # Fallback: try force click if normal click fails
            try:
                submit_button.click(force=True, timeout=10000)
                logging.info("Message sent successfully (force click).")
                # Record message in database (with fallback)
                if db:
                    try:
                        db.add_birthday_message(full_name, message, is_late, days_late, "routine")
                    except Exception as db_err:
                        logging.warning(f"Could not record message to database: {db_err}")
                return True  # Message envoyé avec force click
            except Exception as e2:
                error_msg = f"Failed to click send button even with force ({type(e2).__name__}): {e2}"
                logging.error(error_msg)
                screenshot_path = f'error_send_button_{first_name.replace(" ", "_")}.png'
                page.screenshot(path=screenshot_path)
                # Log error to database (with fallback)
                if db:
                    try:
                        db.log_error("linkedin_birthday_wisher", "SendButtonError", error_msg, str(e2), screenshot_path)
                    except Exception as db_err:
                        logging.warning(f"Could not log error to database: {db_err}")
                return False  # Échec de l'envoi du message

    finally:
        # STEP 3: Fermer SYSTÉMATIQUEMENT la modale après traitement, même en cas d'erreur
        random_delay(0.5, 1)  # Petit délai pour laisser l'UI se stabiliser
        close_all_message_modals(page)


# --- Main Execution ---

def main():
    """Main function to run the LinkedIn birthday wisher bot."""
    if DRY_RUN:
        logging.info("=== SCRIPT RUNNING IN DRY RUN MODE ===")

    # Vérification du fuseau horaire - arrêt automatique si hors fenêtre (7h-9h Paris)
    # Cela permet aux doubles crons (6h et 7h UTC) de s'adapter automatiquement été/hiver
    if not check_paris_timezone_window(target_hour_start=7, target_hour_end=9):
        logging.info("Script terminé (hors fenêtre horaire).")
        return

    # Add a random startup delay.
    # In normal mode, this is set to 3-15 minutes to simulate realistic human behavior
    # while avoiding bot detection (never start at 0 seconds).
    # In DRY RUN mode, this is short for quick testing.
    if DRY_RUN:
        startup_delay = random.randint(1, 10) # 1 to 10 seconds for testing
    else:
        startup_delay = random.randint(180, 900) # 3 to 15 minutes for normal operation

    logging.info(f"Startup delay: waiting for {startup_delay // 60}m {startup_delay % 60}s to start.")
    time.sleep(startup_delay)

    if not BIRTHDAY_MESSAGES:
        logging.error("Message list is empty. Please check messages.txt. Exiting.")
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
        # Initialize proxy manager
        proxy_manager = ProxyManager()
        proxy_config = None
        proxy_start_time = None

        if proxy_manager.is_enabled():
            proxy_config = proxy_manager.get_playwright_proxy_config()
            proxy_start_time = time.time()
            if proxy_config:
                logging.info(f"🌐 Proxy rotation enabled - using proxy")
            else:
                logging.warning("⚠️ Proxy rotation enabled but no proxy available, continuing without proxy")

        # Randomize browser parameters for anti-detection
        selected_user_agent = random.choice(USER_AGENTS)
        selected_viewport = random.choice(VIEWPORT_SIZES)

        logging.info(f"🔧 Using User-Agent: {selected_user_agent[:50]}...")
        logging.info(f"🔧 Using Viewport: {selected_viewport}")

        browser = p.chromium.launch(
            headless=HEADLESS_BROWSER,
            slow_mo=random.randint(80, 150),  # Randomize slow_mo
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

        # Add proxy configuration if available
        if proxy_config:
            context_options['proxy'] = proxy_config

        context = browser.new_context(**context_options)

        # Apply stealth mode to avoid bot detection
        try:
            from playwright_stealth import Stealth
            stealth = Stealth()
            stealth.apply_stealth_sync(context)
            logging.info("✅ Playwright stealth mode activated")
        except ImportError:
            logging.warning("⚠️ playwright-stealth not installed, skipping stealth mode")

        page = context.new_page()

        # Initialize debugging managers if advanced debug is enabled
        screenshot_mgr = None
        enhanced_logger = None
        policy_detector = None
        alert_system = None

        if ENABLE_ADVANCED_DEBUG:
            logging.info("🔧 Advanced debugging enabled - initializing debug managers...")
            screenshot_mgr = DebugScreenshotManager()
            enhanced_logger = EnhancedLogger()
            policy_detector = LinkedInPolicyDetector(page)
            if ENABLE_EMAIL_ALERTS:
                alert_system = AlertSystem()
                logging.info("📧 Email alerts enabled")

        try:
            # Capture initial state
            if screenshot_mgr:
                screenshot_mgr.capture(page, "01_browser_start")

            if not check_login_status(page):
                if screenshot_mgr:
                    screenshot_mgr.capture(page, "login_failed", error=True)
                if alert_system:
                    alert_system.send_alert(
                        "Login Failed",
                        f"Failed to verify login at {page.url}"
                    )
                return # Stop execution if login verification fails.

            # Navigate to birthdays page first to validate selectors
            page.goto("https://www.linkedin.com/feed/", timeout=60000)
            random_delay(1, 2)

            # Validate birthday feed selectors
            logging.info("🔍 Validating birthday feed selectors...")
            selectors_valid = validate_birthday_feed_selectors(page)
            if not selectors_valid:
                logging.warning("⚠️ Some birthday feed selectors are invalid - LinkedIn may have changed")

            # Validate DOM structure after login
            if ENABLE_ADVANCED_DEBUG:
                dom_validator = DOMStructureValidator(page)
                if screenshot_mgr:
                    screenshot_mgr.capture(page, "02_after_login")

                if not dom_validator.validate_all_selectors(screenshot_mgr):
                    logging.warning("⚠️ Some DOM selectors failed validation - check logs")
                    dom_validator.export_validation_report()
                    if alert_system:
                        alert_system.send_alert(
                            "DOM Structure Validation Failed",
                            "Some LinkedIn selectors failed validation. Site structure may have changed."
                        )

                # Check for policy restrictions
                is_ok, issues = policy_detector.check_for_restrictions(screenshot_mgr)
                if not is_ok:
                    logging.critical("🚨 Policy violation detected - stopping execution")
                    if alert_system:
                        screenshot_path = screenshot_mgr.capture(page, "policy_violation_critical", error=True)
                        alert_system.alert_policy_violation(issues, screenshot_path)
                    return

            random_delay(2, 4)

            birthdays = get_birthday_contacts(page)

            # Capture birthdays page state
            if screenshot_mgr:
                screenshot_mgr.capture(page, "03_birthdays_page_loaded")
            if enhanced_logger:
                enhanced_logger.log_page_state(page, "Birthdays page loaded")

            # --- PLANIFICATION: Tous les anniversaires du jour doivent être fêtés ---
            total_today = len(birthdays['today'])
            total_late = len(birthdays['late'])
            logging.info(f"📊 Total birthdays detected: today={total_today}, late={total_late}")

            # IMPORTANT: Tous les anniversaires du jour doivent être traités
            # On ne limite PAS les anniversaires du jour
            messages_to_send_today = total_today

            # Check weekly limit pour les messages en retard uniquement
            if not DRY_RUN:
                can_send, allowed_messages = can_send_more_messages(total_today + total_late)
                if not can_send:
                    logging.warning(f"⚠️ Weekly limit reached. Can only send {allowed_messages} more messages this week.")
                    # Prioriser les anniversaires du jour
                    if allowed_messages < total_today:
                        logging.error(f"⚠️ ATTENTION: Pas assez de quota pour tous les anniversaires du jour!")
                        logging.error(f"   Anniversaires du jour: {total_today}, Quota restant: {allowed_messages}")
                        # On envoie quand même tous les anniversaires du jour (c'est une priorité)
                        messages_to_send_today = total_today
                        birthdays['late'] = []  # On supprime les retards
                    else:
                        # On a assez pour les anniversaires du jour
                        messages_to_send_today = total_today
                        remaining_quota = allowed_messages - total_today
                        birthdays['late'] = birthdays['late'][:remaining_quota]
                        logging.info(f"✂️ Limited late birthdays to {len(birthdays['late'])} (quota: {remaining_quota})")

            logging.info(f"✅ Traitement prévu: {messages_to_send_today} anniversaires du jour + {len(birthdays['late'])} en retard")

            # --- PLANIFICATION AVEC PRIORITÉ : Anniversaires du jour AVANT 12h ---
            # Phase 1 : Anniversaires du jour répartis jusqu'à 12h maximum
            # Phase 2 : Anniversaires en retard répartis de 12h à 19h
            from datetime import datetime
            import pytz

            paris_tz = pytz.timezone('Europe/Paris')
            current_time = datetime.now(paris_tz)
            current_hour = current_time.hour + current_time.minute / 60.0

            if not DRY_RUN:
                # Phase 1 : Anniversaires du jour (priorité absolue avant 12h)
                if len(birthdays['today']) > 0:
                    if current_hour < 12:
                        # On a encore du temps avant 12h
                        min_delay_today, max_delay_today = calculate_optimal_delay(
                            len(birthdays['today']),
                            end_hour=12
                        )
                        logging.info(f"🎂 PRIORITÉ: {len(birthdays['today'])} anniversaires du jour seront traités AVANT 12h")
                    else:
                        # Déjà après 12h - on envoie quand même en priorité avec délai minimal
                        min_delay_today, max_delay_today = (60, 120)  # 1-2 minutes
                        logging.warning(f"⚠️ Déjà {current_hour:.1f}h - Anniversaires du jour envoyés en priorité avec délai minimal")
                else:
                    min_delay_today, max_delay_today = (0, 0)

                # Phase 2 : Anniversaires en retard (après les anniversaires du jour)
                if len(birthdays['late']) > 0:
                    # Ces messages seront envoyés après les anniversaires du jour
                    # On les répartit entre l'heure actuelle (ou 12h) et 19h
                    late_start_hour = max(current_hour, 12)
                    if late_start_hour < 19:
                        min_delay_late, max_delay_late = calculate_optimal_delay(
                            len(birthdays['late']),
                            end_hour=19
                        )
                        logging.info(f"⏰ {len(birthdays['late'])} anniversaires en retard seront traités après (jusqu'à 19h)")
                    else:
                        # Déjà après 19h - délai minimal
                        min_delay_late, max_delay_late = (60, 120)
                        logging.warning(f"⚠️ Déjà {current_hour:.1f}h - Anniversaires en retard avec délai minimal")
                else:
                    min_delay_late, max_delay_late = (0, 0)
            else:
                # En mode DRY_RUN, utiliser des délais courts
                min_delay_today, max_delay_today = (2, 5)
                min_delay_late, max_delay_late = (2, 5)

            # Track total messages sent for implementing periodic long breaks
            total_messages_sent = 0
            break_intervals = []  # Track when to take long breaks

            # Process today's birthdays first, then late ones.
            # This structure allows for easy expansion or prioritization.
            for birthday_type, contacts in birthdays.items():
                is_late = (birthday_type == 'late')

                # We won't send messages to late birthdays in DRY_RUN to keep tests fast and focused.
                if is_late and DRY_RUN:
                    logging.info("Skipping late birthdays in DRY RUN mode.")
                    continue

                if not contacts:
                    logging.info(f"No {birthday_type} birthdays to process.")
                    continue

                logging.info(f"--- Starting to process {len(contacts)} {birthday_type} birthdays ---")

                if is_late:
                    for i, (contact, days_late) in enumerate(contacts):
                        # Envoyer le message et vérifier si ça a réussi
                        message_sent = send_birthday_message(page, contact, is_late=True, days_late=days_late)

                        # N'incrémenter et faire une pause QUE si le message a été envoyé
                        if message_sent:
                            total_messages_sent += 1

                            # Check for policy restrictions every 5 messages
                            if ENABLE_ADVANCED_DEBUG and policy_detector and total_messages_sent % 5 == 0:
                                is_ok, issues = policy_detector.check_for_restrictions(screenshot_mgr)
                                if not is_ok:
                                    logging.critical("🚨 Policy violation detected during execution - stopping")
                                    if alert_system:
                                        screenshot_path = screenshot_mgr.capture(page, "policy_violation_during_run", error=True)
                                        alert_system.alert_policy_violation(issues, screenshot_path)
                                    return

                            # Simulate occasional human activity
                            if random.random() < 0.3:  # 30% chance
                                simulate_human_activity(page)

                            # Pause UNIQUEMENT si le message a été envoyé et qu'il reste des contacts
                            if i < len(contacts) - 1:
                                # Utiliser le délai calculé selon le type d'anniversaire
                                if not DRY_RUN:
                                    delay = random.randint(min_delay_late, max_delay_late)
                                    minutes = delay // 60
                                    seconds = delay % 60
                                    logging.info(f"⏸️ Pause planifiée (retard): {minutes}m {seconds}s")
                                    time.sleep(delay)
                                else:
                                    # Short delay for testing
                                    delay = random.randint(2, 5)
                                    logging.info(f"Pausing for {delay}s (DRY RUN).")
                                    time.sleep(delay)
                        else:
                            # Si le message n'a pas été envoyé, pause minimale avant le prochain
                            logging.info("⏭️ Contact skippé, passage immédiat au suivant")
                            random_delay(1, 3)  # Pause minimale de 1-3 secondes
                else:
                    for i, contact in enumerate(contacts):
                        # Envoyer le message et vérifier si ça a réussi
                        message_sent = send_birthday_message(page, contact, is_late=is_late)

                        # N'incrémenter et faire une pause QUE si le message a été envoyé
                        if message_sent:
                            total_messages_sent += 1

                            # Check for policy restrictions every 5 messages
                            if ENABLE_ADVANCED_DEBUG and policy_detector and total_messages_sent % 5 == 0:
                                is_ok, issues = policy_detector.check_for_restrictions(screenshot_mgr)
                                if not is_ok:
                                    logging.critical("🚨 Policy violation detected during execution - stopping")
                                    if alert_system:
                                        screenshot_path = screenshot_mgr.capture(page, "policy_violation_during_run", error=True)
                                        alert_system.alert_policy_violation(issues, screenshot_path)
                                    return

                            # Simulate occasional human activity
                            if random.random() < 0.3:  # 30% chance
                                simulate_human_activity(page)

                            # Pause UNIQUEMENT si le message a été envoyé et qu'il reste des contacts
                            if i < len(contacts) - 1:
                                # Utiliser le délai calculé selon le type d'anniversaire (priorité avant 12h pour aujourd'hui)
                                if not DRY_RUN:
                                    delay = random.randint(min_delay_today, max_delay_today)
                                    minutes = delay // 60
                                    seconds = delay % 60
                                    logging.info(f"⏸️ Pause planifiée (aujourd'hui): {minutes}m {seconds}s")
                                    time.sleep(delay)
                                else:
                                    # Short delay for testing
                                    delay = random.randint(2, 5)
                                    logging.info(f"Pausing for {delay}s (DRY RUN).")
                                    time.sleep(delay)
                        else:
                            # Si le message n'a pas été envoyé, pause minimale avant le prochain
                            logging.info("⏭️ Contact skippé, passage immédiat au suivant")
                            random_delay(1, 3)  # Pause minimale de 1-3 secondes

            # Save weekly message count
            if not DRY_RUN and total_messages_sent > 0:
                weekly_data = load_weekly_count()
                new_count = weekly_data['count'] + total_messages_sent
                save_weekly_count(new_count)
                logging.info(f"📊 Weekly message count updated: {new_count}/{WEEKLY_MESSAGE_LIMIT}")

            logging.info("Script finished successfully.")

            # Final screenshot if debugging enabled
            if screenshot_mgr:
                screenshot_mgr.capture(page, "99_execution_completed")

        except PlaywrightTimeoutError as e:
            logging.error(f"A timeout error occurred: {e}")

            # Record proxy failure if proxy was used
            if proxy_config and proxy_start_time:
                response_time = time.time() - proxy_start_time
                proxy_manager.record_proxy_result(
                    proxy_config.get('server', 'unknown'),
                    success=False,
                    response_time=response_time,
                    error_message=f"Timeout error: {str(e)}"
                )

            # Enhanced error handling
            if screenshot_mgr:
                screenshot_mgr.capture(page, "error_timeout", error=True)
            else:
                page.screenshot(path='error_timeout.png')

            if alert_system:
                alert_system.send_alert(
                    "Timeout Error",
                    f"Script encountered a timeout error:\n\n{str(e)}\n\nCheck debug screenshots for details.",
                    attach_files=['error_timeout.png'] if not screenshot_mgr else None
                )

        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

            # Record proxy failure if proxy was used
            if proxy_config and proxy_start_time:
                response_time = time.time() - proxy_start_time
                proxy_manager.record_proxy_result(
                    proxy_config.get('server', 'unknown'),
                    success=False,
                    response_time=response_time,
                    error_message=f"Unexpected error: {str(e)}"
                )

            # Enhanced error handling
            if screenshot_mgr:
                screenshot_mgr.capture(page, "error_unexpected", error=True)
            else:
                page.screenshot(path='error_unexpected.png')

            if alert_system:
                alert_system.send_alert(
                    "Unexpected Error",
                    f"Script crashed with unexpected error:\n\n{str(e)}\n\nCheck debug screenshots and logs for details.",
                    attach_files=['error_unexpected.png'] if not screenshot_mgr else None
                )

        finally:
            # Record proxy success if proxy was used and no exceptions occurred
            if proxy_config and proxy_start_time:
                response_time = time.time() - proxy_start_time
                proxy_manager.record_proxy_result(
                    proxy_config.get('server', 'unknown'),
                    success=True,
                    response_time=response_time
                )
                logging.info(f"✅ Proxy completed successfully (response time: {response_time:.2f}s)")

            logging.info("Closing browser.")
            browser.close()
            # Clean up the local auth file for security
            if os.path.exists(AUTH_FILE_PATH):
                os.remove(AUTH_FILE_PATH)

            # Log debugging summary if enabled
            if ENABLE_ADVANCED_DEBUG:
                logging.info("🔧 Advanced debugging session completed - check debug_screenshots/ folder for details")

if __name__ == "__main__":
    main()
