import os
import random
import time
import logging
import base64
import json
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

# --- Configuration ---
# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Secure authentication using an auth state from GitHub Secrets
LINKEDIN_AUTH_STATE = os.getenv('LINKEDIN_AUTH_STATE')
AUTH_FILE_PATH = "auth_state.json"

# General settings
HEADLESS_BROWSER = True # Set to False for debugging to see the browser UI
DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true' # Enables test mode

# Advanced debugging settings
ENABLE_ADVANCED_DEBUG = os.getenv('ENABLE_ADVANCED_DEBUG', 'false').lower() == 'true'
ENABLE_EMAIL_ALERTS = os.getenv('ENABLE_EMAIL_ALERTS', 'false').lower() == 'true'

# Anti-detection limits - UNLIMITED MODE (utilisation unique)
MAX_MESSAGES_PER_RUN = None  # Pas de limite pour le mode unlimited
WEEKLY_MESSAGE_LIMIT = None  # Pas de limite hebdomadaire pour le mode unlimited
WEEKLY_TRACKER_FILE = "weekly_messages_unlimited.json"  # Fichier séparé pour ne pas impacter le routine

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

# --- Weekly Message Tracking ---

def load_weekly_count():
    """Charge le compteur de messages de la semaine."""
    try:
        with open(WEEKLY_TRACKER_FILE, 'r') as f:
            data = json.load(f)
            # Réinitialiser si plus d'une semaine
            from datetime import datetime, timedelta
            last_reset = datetime.fromisoformat(data['last_reset'])
            if datetime.now() - last_reset > timedelta(days=7):
                return {'count': 0, 'last_reset': datetime.now().isoformat()}
            return data
    except (FileNotFoundError, KeyError, ValueError):
        from datetime import datetime
        return {'count': 0, 'last_reset': datetime.now().isoformat()}

def save_weekly_count(count):
    """Sauvegarde le compteur de messages hebdomadaires."""
    data = load_weekly_count()
    data['count'] = count
    with open(WEEKLY_TRACKER_FILE, 'w') as f:
        json.dump(data, f)

def can_send_more_messages(messages_to_send):
    """Vérifie si on peut envoyer plus de messages cette semaine."""
    # MODE UNLIMITED : Pas de limite
    if WEEKLY_MESSAGE_LIMIT is None:
        logging.info(f"🚀 MODE UNLIMITED : Aucune limite - {messages_to_send} messages peuvent être envoyés")
        return True, messages_to_send

    data = load_weekly_count()

    if data['count'] + messages_to_send > WEEKLY_MESSAGE_LIMIT:
        logging.warning(f"⚠️ Limite hebdomadaire atteinte ({data['count']}/{WEEKLY_MESSAGE_LIMIT})")
        return False, WEEKLY_MESSAGE_LIMIT - data['count']
    return True, messages_to_send

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

def type_like_a_human(page: Page, selector: str, text: str):
    """Fills the element with the given text."""
    logging.info(f"Typing message: '{text}'")
    page.locator(selector).fill(text)

def close_all_message_modals(page: Page):
    """Ferme toutes les modales de message ouvertes pour éviter les conflits."""
    try:
        # Trouver tous les boutons de fermeture de modale
        close_buttons = page.locator("button[data-control-name='overlay.close_conversation_window']")
        count = close_buttons.count()

        if count > 0:
            logging.info(f"🧹 Fermeture de {count} modale(s) ouverte(s)...")
            # Fermer toutes les modales une par une
            for i in range(count):
                try:
                    close_buttons.first.click(timeout=2000)
                    random_delay(0.3, 0.6)  # Petit délai entre chaque fermeture
                except Exception as e:
                    logging.debug(f"Impossible de fermer une modale (déjà fermée?): {e}")
            logging.info("✅ Toutes les modales ont été fermées")
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
            except:
                pass

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
    import re
    from datetime import datetime

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
    import re

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
        except:
            pass
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

    # Skip if the first name is just an initial (returns empty string)
    if not first_name:
        logging.warning(f"Skipping contact '{full_name}' because first name is just an initial.")
        return

    if is_late:
        logging.info(f"--- Processing late birthday ({days_late} days ago) for {full_name} ---")
    else:
        logging.info(f"--- Processing current birthday for {full_name} ---")

    # Use a robust selector for the message button
    message_button = contact_element.query_selector(
        'a[aria-label*="Envoyer un message"], a[href*="/messaging/compose"], button:has-text("Message")'
    )
    if not message_button:
        logging.warning(f"Could not find a 'Message' button for {full_name}. Skipping.")
        return

    # Utiliser un try-finally pour garantir la fermeture de la modale même en cas d'erreur
    try:
        message_button.click()
        random_delay(0.5, 1)  # Petit délai après le clic

        message_box_selector = "div.msg-form__contenteditable[role='textbox']"
        page.wait_for_selector(message_box_selector, state="visible", timeout=30000)

        # STEP 2: Vérifier combien de modales sont ouvertes et utiliser .last pour la plus récente
        modal_count = page.locator(message_box_selector).count()
        if modal_count > 1:
            logging.warning(f"⚠️ ATTENTION: {modal_count} modales détectées simultanément! Utilisation de .last pour cibler la plus récente.")
            page.screenshot(path=f'warning_multiple_modals_{first_name.replace(" ", "_")}.png')

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
            return

        message = random.choice(message_list).format(name=first_name)

        if DRY_RUN:
            logging.info(f"[DRY RUN] Would send message to {first_name}: '{message}'")
            return  # La fermeture sera gérée par le finally

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
            submit_button.scroll_into_view_if_needed(timeout=5000)
            random_delay(0.5, 1)  # Small delay to let UI settle after scrolling

            if submit_button.is_enabled():
                submit_button.click()
                logging.info("Message sent successfully.")
            else:
                logging.warning("Send button is not enabled. Skipping.")
        except PlaywrightTimeoutError:
            logging.warning("Could not scroll send button into view, attempting force click...")
            # Fallback: try force click if scrolling fails
            try:
                submit_button.click(force=True, timeout=10000)
                logging.info("Message sent successfully (force click).")
            except PlaywrightTimeoutError as e:
                logging.error(f"Failed to click send button even with force: {e}")
                page.screenshot(path=f'error_send_button_{first_name}.png')
                raise

    finally:
        # STEP 3: Fermer SYSTÉMATIQUEMENT la modale après traitement, même en cas d'erreur
        random_delay(0.5, 1)  # Petit délai pour laisser l'UI se stabiliser
        close_all_message_modals(page)


# --- Main Execution ---

def main():
    """Main function to run the LinkedIn birthday wisher bot."""
    if DRY_RUN:
        logging.info("=== SCRIPT RUNNING IN DRY RUN MODE ===")

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

    # Decode and save the auth state from the environment variable
    # --- Authentication Setup ---
    if not LINKEDIN_AUTH_STATE:
        logging.error("LINKEDIN_AUTH_STATE environment variable is not set. Exiting.")
        return

    try:
        # Try to load the auth state as a JSON string directly
        json.loads(LINKEDIN_AUTH_STATE)
        logging.info("Auth state is a valid JSON string.")
        with open(AUTH_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(LINKEDIN_AUTH_STATE)
    except json.JSONDecodeError:
        # If it's not a JSON string, assume it's a Base64 encoded string
        logging.info("Auth state is not a JSON string, attempting to decode from Base64.")
    try:
        # Try to load the auth state as a JSON string directly
        json.loads(LINKEDIN_AUTH_STATE)
        logging.info("Auth state is a valid JSON string. Writing to file directly.")
        with open(AUTH_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(LINKEDIN_AUTH_STATE)
    except json.JSONDecodeError:
        # If it's not a JSON string, assume it's a Base64 encoded binary file
        logging.info("Auth state is not a JSON string, attempting to decode from Base64.")
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
        logging.error(f"An unexpected error occurred during auth state setup: {e}")
        return

    with sync_playwright() as p:
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
        context = browser.new_context(
            storage_state=AUTH_FILE_PATH,
            user_agent=selected_user_agent,
            viewport=selected_viewport,
            locale='fr-FR',
            timezone_id='Europe/Paris'
        )

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

            # --- MODE UNLIMITED: Pas de limite sur les messages ---
            total_birthdays = len(birthdays['today']) + len(birthdays['late'])
            logging.info(f"📊 Total birthdays detected: {total_birthdays} (today: {len(birthdays['today'])}, late: {len(birthdays['late'])})")
            logging.info(f"🚀 MODE UNLIMITED : Tous les anniversaires seront traités sans limite")

            # Pas de limite de messages en mode unlimited
            # Tous les anniversaires (aujourd'hui + en retard) seront traités

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
                        send_birthday_message(page, contact, is_late=True, days_late=days_late)
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

                        if i < len(contacts) - 1:
                            # ANTI-DETECTION: Extra pause every 5 messages
                            if not DRY_RUN and total_messages_sent % 5 == 0 and total_messages_sent > 0:
                                extra_pause = random.randint(600, 1200)  # 10-20 minutes
                                logging.info(f"⏸️ Extra pause after 5 messages: {extra_pause // 60} minutes")
                                time.sleep(extra_pause)

                            # Check if we need a long break (every 10-15 messages)
                            if not DRY_RUN:
                                break_taken, break_intervals = long_break_if_needed(total_messages_sent, break_intervals)
                                if not break_taken:
                                    # Normal delay between messages using Gaussian distribution
                                    gaussian_delay(180, 420)  # 3-7 minutes
                            elif DRY_RUN:
                                # Short delay for testing
                                delay = random.randint(2, 5)
                                logging.info(f"Pausing for {delay}s (DRY RUN).")
                                time.sleep(delay)
                else:
                    for i, contact in enumerate(contacts):
                        send_birthday_message(page, contact, is_late=is_late)
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

                        # Add a pause between messages
                        if i < len(contacts) - 1:
                            # ANTI-DETECTION: Extra pause every 5 messages
                            if not DRY_RUN and total_messages_sent % 5 == 0 and total_messages_sent > 0:
                                extra_pause = random.randint(600, 1200)  # 10-20 minutes
                                logging.info(f"⏸️ Extra pause after 5 messages: {extra_pause // 60} minutes")
                                time.sleep(extra_pause)

                            # Check if we need a long break (every 10-15 messages)
                            if not DRY_RUN:
                                break_taken, break_intervals = long_break_if_needed(total_messages_sent, break_intervals)
                                if not break_taken:
                                    # Normal delay between messages using Gaussian distribution
                                    gaussian_delay(180, 420)  # 3-7 minutes
                            elif DRY_RUN:
                                # Short delay for testing
                                delay = random.randint(2, 5)
                                logging.info(f"Pausing for {delay}s (DRY RUN).")
                                time.sleep(delay)

            # Save weekly message count (pas de sauvegarde en mode unlimited)
            if not DRY_RUN and total_messages_sent > 0:
                if WEEKLY_MESSAGE_LIMIT is not None:
                    weekly_data = load_weekly_count()
                    new_count = weekly_data['count'] + total_messages_sent
                    save_weekly_count(new_count)
                    logging.info(f"📊 Weekly message count updated: {new_count}/{WEEKLY_MESSAGE_LIMIT}")
                else:
                    logging.info(f"🚀 MODE UNLIMITED : {total_messages_sent} messages envoyés (pas de tracking hebdomadaire)")

            logging.info("Script finished successfully.")

            # Final screenshot if debugging enabled
            if screenshot_mgr:
                screenshot_mgr.capture(page, "99_execution_completed")

        except PlaywrightTimeoutError as e:
            logging.error(f"A timeout error occurred: {e}")

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
