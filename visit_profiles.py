import os
import random
import time
import logging
import base64
import json
import urllib.parse
import pytz
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Authentication
LINKEDIN_AUTH_STATE = os.getenv('LINKEDIN_AUTH_STATE')
AUTH_FILE_PATH = "auth_state.json"

# Visited profiles file
VISITED_PROFILES_FILE = "visited_profiles.txt"

# General settings
# En mode GitHub Actions, forcer headless. Sinon, utiliser headless=False pour réduire la détection
IS_GITHUB_ACTIONS = os.getenv('GITHUB_ACTIONS', 'false').lower() == 'true'
HEADLESS_BROWSER = IS_GITHUB_ACTIONS  # Headless uniquement sur GitHub Actions
DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'
PROFILES_TO_VISIT_PER_RUN = 15  # Réduit à 15 pour éviter la détection (max 20 recommandé)
MAX_PAGES_TO_SCRAPE = int(os.getenv('MAX_PAGES_TO_SCRAPE', '100'))  # Maximum number of pages to scrape per run (default: 100)

# User-Agents réalistes pour randomisation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
]

# --- Helper Functions ---

def load_config():
    """Loads search configuration from config.json."""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            # Validate required keys
            if 'keywords' not in config or 'location' not in config:
                logging.error("config.json must contain 'keywords' and 'location' keys.")
                return None
            if not isinstance(config['keywords'], list) or len(config['keywords']) == 0:
                logging.error("'keywords' must be a non-empty list in config.json.")
                return None
            if not isinstance(config['location'], str) or not config['location'].strip():
                logging.error("'location' must be a non-empty string in config.json.")
                return None
            return config
    except FileNotFoundError:
        logging.error("config.json not found. Please create it.")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding config.json: {e}. Please check its format.")
        return None

def load_visited_profiles():
    """Loads the set of already visited profile URLs. Creates the file if it doesn't exist."""
    if not os.path.exists(VISITED_PROFILES_FILE):
        # Create the file so it can be committed by the workflow even if no new profiles are visited.
        with open(VISITED_PROFILES_FILE, "w", encoding="utf-8") as f:
            pass # Create an empty file
        return set()

    try:
        with open(VISITED_PROFILES_FILE, "r", encoding="utf-8") as f:
            profiles = set()
            for line in f:
                line = line.strip()
                if line and (line.startswith('http://') or line.startswith('https://')):
                    profiles.add(line)
                elif line:
                    logging.warning(f"Invalid URL found in {VISITED_PROFILES_FILE}: {line}")
            return profiles
    except Exception as e:
        logging.error(f"Error reading {VISITED_PROFILES_FILE}: {e}")
        return set()

def save_visited_profile(profile_url):
    """Appends a new visited profile URL to the file."""
    with open(VISITED_PROFILES_FILE, "a", encoding="utf-8") as f:
        f.write(profile_url + "\n")

def random_delay(min_seconds: float = 8, max_seconds: float = 20):
    """Waits for a random duration to mimic human latency with occasional longer pauses."""
    delay = random.uniform(min_seconds, max_seconds)
    # Ajouter occasionnellement des pauses plus longues (10% du temps)
    if random.random() < 0.1:
        delay += random.uniform(30, 60)
        logging.info(f"Pause prolongée: {delay:.1f}s")
    time.sleep(delay)

def simulate_human_interactions(page: Page):
    """Simule des interactions humaines naturelles (scroll, mouvements de souris)."""
    try:
        # Scroll aléatoire
        for _ in range(random.randint(2, 5)):
            scroll_amount = random.randint(200, 600)
            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            time.sleep(random.uniform(0.8, 2.5))

        # Mouvements de souris aléatoires
        for _ in range(random.randint(3, 7)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            # Utiliser move avec steps pour rendre le mouvement plus naturel
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.3, 1.2))

        # Temps de lecture variable
        reading_time = random.uniform(5, 15)
        logging.debug(f"Simulation lecture: {reading_time:.1f}s")
        time.sleep(reading_time)
    except Exception as e:
        logging.debug(f"Erreur lors de la simulation d'interactions (non critique): {e}")

# --- Timezone Check for Automatic Schedule ---

def check_paris_timezone_window(target_hour_start: int, target_hour_end: int) -> bool:
    """
    Vérifie si l'heure actuelle à Paris est dans la fenêtre horaire souhaitée.
    Cette fonction permet d'avoir des cron jobs doubles (été/hiver) qui s'adaptent
    automatiquement aux changements d'heure sans intervention manuelle.

    Args:
        target_hour_start: Heure de début de la fenêtre (ex: 9 pour 9h)
        target_hour_end: Heure de fin de la fenêtre (ex: 11 pour 11h)

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

# --- Core Automation Functions ---

def check_login_status(page: Page):
    """Checks if the user is logged in."""
    page.goto("https://www.linkedin.com/feed/", timeout=60000)
    try:
        page.wait_for_selector("img.global-nav__me-photo", timeout=15000)
        logging.info("Successfully logged in.")
        return True
    except PlaywrightTimeoutError:
        logging.error("Failed to verify login.")
        page.screenshot(path='error_login_verification_failed.png')
        return False

def search_profiles(page: Page, keywords: list, location: str, page_number: int = 1):
    """Performs a search on LinkedIn and returns profile URLs."""
    keyword_str = " ".join(keywords)
    # Use the location text directly in the search query, which is more flexible.
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(keyword_str)}&location={urllib.parse.quote(location)}&origin=GLOBAL_SEARCH_HEADER&page={page_number}"

    logging.info(f"Navigating to search URL (page {page_number}): {search_url}")
    page.goto(search_url, timeout=90000)
    random_delay()

    page.screenshot(path='search_results_page.png')

    profile_links = []
    # The new selector for the container of each search result.
    result_container_selector = 'div[data-view-name="people-search-result"]'

    try:
        # Wait for the first result container to appear.
        page.wait_for_selector(result_container_selector, timeout=20000)

        # Scroll to load more results
        for _ in range(5): # Scroll a few times
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            random_delay()

        result_containers = page.query_selector_all(result_container_selector)
        logging.info(f"Found {len(result_containers)} result containers on the page.")

        for container in result_containers:
            # The link is in an 'a' tag with a specific data-view-name attribute
            link_element = container.query_selector('a[data-view-name="search-result-lockup-title"]')
            if link_element:
                href = link_element.get_attribute("href")
                if href and "linkedin.com/in/" in href:
                    # Clean up the URL to remove tracking parameters
                    clean_url = href.split('?')[0]
                    profile_links.append(clean_url)

        logging.info(f"Extracted {len(profile_links)} potential profiles from containers.")
    except PlaywrightTimeoutError:
        logging.warning("Could not find profile result containers on the search results page.")
        page.screenshot(path='error_search_no_results.png')

    return list(dict.fromkeys(profile_links)) # Return unique links

# --- Main Execution ---

def main():
    """Main function to run the profile visiting bot."""
    if DRY_RUN:
        logging.info("=== SCRIPT RUNNING IN DRY RUN MODE ===")

    # Vérification du fuseau horaire - arrêt automatique si hors fenêtre (9h-11h Paris)
    # Cela permet aux doubles crons (8h et 9h UTC) de s'adapter automatiquement été/hiver
    if not check_paris_timezone_window(target_hour_start=9, target_hour_end=11):
        logging.info("Script terminé (hors fenêtre horaire).")
        return

    config = load_config()
    if not config:
        return

    # Authentication setup
    if not LINKEDIN_AUTH_STATE:
        logging.error("LINKEDIN_AUTH_STATE environment variable is not set. Exiting.")
        return

    try:
        auth_state_decoded = base64.b64decode(LINKEDIN_AUTH_STATE)
        with open(AUTH_FILE_PATH, "wb") as f:
            f.write(auth_state_decoded)
    except Exception as e:
        logging.error(f"Failed to decode or write auth state: {e}")
        return

    visited_profiles = load_visited_profiles()
    logging.info(f"Loaded {len(visited_profiles)} visited profiles.")

    profiles_visited_this_run = 0

    with sync_playwright() as p:
        # Lancement du browser avec arguments anti-détection
        browser = p.chromium.launch(
            headless=HEADLESS_BROWSER,  # Non-headless localement, headless sur GitHub Actions
            slow_mo=random.randint(100, 300),  # Ralentissement aléatoire
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )

        # Création du contexte avec User-Agent et empreinte aléatoires
        context = browser.new_context(
            storage_state=AUTH_FILE_PATH,
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': random.randint(1280, 1920), 'height': random.randint(720, 1080)},
            locale='fr-FR',
            timezone_id='Europe/Paris'
        )

        # Application de playwright-stealth pour masquer l'automatisation
        stealth = Stealth()
        stealth.apply_stealth_sync(context)

        page = context.new_page()

        try:
            if not check_login_status(page):
                return

            # Iterate through multiple pages
            current_page = 1
            pages_without_new_profiles = 0  # Safety counter to prevent infinite loops
            MAX_PAGES_WITHOUT_NEW = 3  # Stop after 3 consecutive pages with no new profiles

            while current_page <= MAX_PAGES_TO_SCRAPE and profiles_visited_this_run < PROFILES_TO_VISIT_PER_RUN:
                logging.info(f"Scraping page {current_page}/{MAX_PAGES_TO_SCRAPE}")

                profile_urls = search_profiles(page, config['keywords'], config['location'], current_page)

                if not profile_urls:
                    logging.info(f"No more profiles found on page {current_page}. Stopping pagination.")
                    break

                # Track if we found new profiles on this page
                found_new_profiles = False

                for url in profile_urls:
                    if profiles_visited_this_run >= PROFILES_TO_VISIT_PER_RUN:
                        logging.info(f"Reached visit limit for this run ({PROFILES_TO_VISIT_PER_RUN}).")
                        break

                    if url in visited_profiles:
                        logging.info(f"Skipping already visited profile: {url}")
                        continue

                    found_new_profiles = True
                    logging.info(f"Visiting profile: {url}")
                    if not DRY_RUN:
                        try:
                            page.goto(url, timeout=60000)
                            # Simuler des interactions humaines (scroll, mouvements de souris)
                            simulate_human_interactions(page)
                            random_delay(15, 35)  # Délai plus naturel (15-35s au lieu de 5-10s)
                            save_visited_profile(url)
                            visited_profiles.add(url)
                        except Exception as e:
                            logging.error(f"Error visiting profile {url}: {e}")
                            # Continue to next profile instead of crashing
                            continue
                    else:
                        logging.info(f"[DRY RUN] Would have visited {url}")

                    profiles_visited_this_run += 1
                    logging.info(f"Profiles visited in this run: {profiles_visited_this_run}/{PROFILES_TO_VISIT_PER_RUN}")
                    random_delay()

                # Safety check: if we didn't find new profiles, increment counter
                if not found_new_profiles:
                    pages_without_new_profiles += 1
                    logging.info(f"No new profiles on page {current_page} ({pages_without_new_profiles}/{MAX_PAGES_WITHOUT_NEW} pages without new)")
                    if pages_without_new_profiles >= MAX_PAGES_WITHOUT_NEW:
                        logging.info(f"Stopping: {MAX_PAGES_WITHOUT_NEW} consecutive pages with no new profiles.")
                        break
                else:
                    pages_without_new_profiles = 0  # Reset counter

                # If we've reached the visit limit, stop pagination
                if profiles_visited_this_run >= PROFILES_TO_VISIT_PER_RUN:
                    break

                current_page += 1
                random_delay(3, 6)  # Delay between page navigation

            logging.info(f"Script finished successfully. Scraped {current_page} page(s).")

        except PlaywrightTimeoutError as e:
            logging.error(f"A timeout error occurred: {e}")
            page.screenshot(path='error_timeout.png')
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}", exc_info=True)
            page.screenshot(path='error_unexpected.png')
        finally:
            logging.info("Closing browser.")
            browser.close()
            if os.path.exists(AUTH_FILE_PATH):
                os.remove(AUTH_FILE_PATH)

if __name__ == "__main__":
    main()
