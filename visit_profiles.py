import os
import random
import time
import logging
import base64
import binascii
import json
import urllib.parse
import math
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError, BrowserContext, Browser
from playwright_stealth import Stealth

# Import database utilities
from database import get_database

# Import selector validator
from selector_validator import validate_search_selectors

# Import proxy manager
from proxy_manager import ProxyManager

# --- Configuration ---
# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/visit_profiles.log"),
        logging.StreamHandler()
    ]
)

# Authentication
LINKEDIN_AUTH_STATE = os.getenv('LINKEDIN_AUTH_STATE')
AUTH_FILE_PATH = "auth_state.json"

# General settings
# En mode GitHub Actions, forcer headless. Sinon, utiliser headless=False pour réduire la détection
IS_GITHUB_ACTIONS = os.getenv('GITHUB_ACTIONS', 'false').lower() == 'true'
HEADLESS_BROWSER = IS_GITHUB_ACTIONS  # Headless uniquement sur GitHub Actions
DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'

# User-Agents réalistes et à jour (2025)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15"
]

# --- Metrics tracking ---
class ExecutionMetrics:
    """Track execution metrics for observability"""
    def __init__(self):
        self.start_time = datetime.now()
        self.profiles_attempted = 0
        self.profiles_succeeded = 0
        self.profiles_failed = 0
        self.pages_scraped = 0
        self.errors = []

    def record_profile_attempt(self, success: bool):
        """Record a profile visit attempt"""
        self.profiles_attempted += 1
        if success:
            self.profiles_succeeded += 1
        else:
            self.profiles_failed += 1

    def record_error(self, error_msg: str):
        """Record an error"""
        self.errors.append({
            'timestamp': datetime.now().isoformat(),
            'message': error_msg
        })

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        duration = (datetime.now() - self.start_time).total_seconds()
        return {
            'duration_seconds': duration,
            'profiles_attempted': self.profiles_attempted,
            'profiles_succeeded': self.profiles_succeeded,
            'profiles_failed': self.profiles_failed,
            'success_rate': (self.profiles_succeeded / self.profiles_attempted * 100) if self.profiles_attempted > 0 else 0,
            'pages_scraped': self.pages_scraped,
            'avg_time_per_profile': duration / self.profiles_attempted if self.profiles_attempted > 0 else 0,
            'errors_count': len(self.errors)
        }

# --- Helper Functions ---

def load_config() -> Optional[Dict[str, Any]]:
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

            # Set defaults for optional settings
            if 'limits' not in config:
                config['limits'] = {}
            config['limits'].setdefault('profiles_per_run', 15)
            config['limits'].setdefault('max_pages_to_scrape', 100)
            config['limits'].setdefault('max_pages_without_new', 3)

            if 'delays' not in config:
                config['delays'] = {}
            config['delays'].setdefault('min_seconds', 8)
            config['delays'].setdefault('max_seconds', 20)
            config['delays'].setdefault('profile_visit_min', 15)
            config['delays'].setdefault('profile_visit_max', 35)
            config['delays'].setdefault('page_navigation_min', 3)
            config['delays'].setdefault('page_navigation_max', 6)

            if 'timezone' not in config:
                config['timezone'] = {}
            config['timezone'].setdefault('start_hour', 7)
            config['timezone'].setdefault('end_hour', 20)

            if 'retry' not in config:
                config['retry'] = {}
            config['retry'].setdefault('max_attempts', 3)
            config['retry'].setdefault('backoff_factor', 2)

            return config
    except FileNotFoundError:
        logging.error("config.json not found. Please create it.")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding config.json: {e}. Please check its format.")
        return None

def extract_profile_name_from_url(url: str) -> str:
    """
    Extracts profile name from LinkedIn URL with error handling.

    Args:
        url: LinkedIn profile URL

    Returns:
        Extracted profile name or 'Unknown' if extraction fails
    """
    try:
        if '/in/' not in url:
            return 'Unknown'

        # Extract the part after /in/
        parts = url.split('/in/')
        if len(parts) < 2:
            return 'Unknown'

        # Get the identifier
        identifier = parts[1].split('/')[0].split('?')[0]

        # Convert hyphens to spaces and title case
        name = identifier.replace('-', ' ').title()

        # Validate the name (should contain at least one letter)
        if not any(c.isalpha() for c in name):
            return 'Unknown'

        return name
    except Exception as e:
        logging.warning(f"Error extracting profile name from URL {url}: {e}")
        return 'Unknown'

def random_delay(min_seconds: float = 8, max_seconds: float = 20):
    """
    Waits for a random duration to mimic human latency with occasional longer pauses.
    Uses normal distribution for more realistic timing.
    """
    # Use normal distribution instead of uniform for more realistic delays
    mean = (min_seconds + max_seconds) / 2
    std_dev = (max_seconds - min_seconds) / 6  # ~99% within range
    delay = random.gauss(mean, std_dev)

    # Clamp to min/max range
    delay = max(min_seconds, min(max_seconds, delay))

    # Ajouter occasionnellement des pauses plus longues (10% du temps)
    if random.random() < 0.1:
        extra_delay = random.uniform(30, 60)
        delay += extra_delay
        logging.info(f"Pause prolongée: {delay:.1f}s")

    time.sleep(delay)

def bezier_curve(start: Tuple[int, int], end: Tuple[int, int], control_points: int = 3) -> List[Tuple[int, int]]:
    """
    Generate a smooth Bézier curve for mouse movement.

    Args:
        start: Starting point (x, y)
        end: Ending point (x, y)
        control_points: Number of control points for the curve

    Returns:
        List of points along the curve
    """
    # Generate random control points
    points = [start]
    for _ in range(control_points):
        x = random.randint(min(start[0], end[0]), max(start[0], end[0]))
        y = random.randint(min(start[1], end[1]), max(start[1], end[1]))
        points.append((x, y))
    points.append(end)

    # Calculate points along the Bézier curve
    curve_points = []
    steps = 20  # Number of steps along the curve

    for t in range(steps + 1):
        t_normalized = t / steps
        # De Casteljau's algorithm for Bézier curves
        temp_points = points[:]
        while len(temp_points) > 1:
            new_points = []
            for i in range(len(temp_points) - 1):
                x = (1 - t_normalized) * temp_points[i][0] + t_normalized * temp_points[i + 1][0]
                y = (1 - t_normalized) * temp_points[i][1] + t_normalized * temp_points[i + 1][1]
                new_points.append((int(x), int(y)))
            temp_points = new_points
        curve_points.append(temp_points[0])

    return curve_points

def simulate_human_interactions(page: Page):
    """Simule des interactions humaines naturelles (scroll, mouvements de souris)."""
    try:
        # Scroll aléatoire avec accélération/décélération naturelle
        total_scrolls = random.randint(3, 6)
        for i in range(total_scrolls):
            # Variation de la vitesse de scroll (accélération au début, décélération à la fin)
            progress = i / total_scrolls
            if progress < 0.3:  # Accélération
                scroll_amount = int(200 + (progress / 0.3) * 400)
            elif progress > 0.7:  # Décélération
                scroll_amount = int(600 - ((progress - 0.7) / 0.3) * 400)
            else:  # Vitesse constante
                scroll_amount = random.randint(400, 600)

            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            time.sleep(random.gauss(1.5, 0.4))  # Normal distribution for scroll delays

        # Mouvements de souris avec courbes de Bézier
        mouse_movements = random.randint(2, 4)
        current_pos = (random.randint(100, 400), random.randint(100, 300))

        for _ in range(mouse_movements):
            # Nouvelle position cible
            target_pos = (random.randint(100, 1200), random.randint(100, 800))

            # Générer une courbe de Bézier
            curve = bezier_curve(current_pos, target_pos, control_points=2)

            # Suivre la courbe
            for point in curve:
                page.mouse.move(point[0], point[1])
                time.sleep(random.uniform(0.01, 0.03))  # Très court délai pour mouvement fluide

            current_pos = target_pos
            time.sleep(random.gauss(0.8, 0.2))

        # Temps de lecture variable (distribution normale)
        reading_time = random.gauss(10, 3)  # Mean 10s, std dev 3s
        reading_time = max(5, min(15, reading_time))  # Clamp between 5-15s
        logging.debug(f"Simulation lecture: {reading_time:.1f}s")
        time.sleep(reading_time)
    except Exception as e:
        logging.debug(f"Erreur lors de la simulation d'interactions (non critique): {e}")

# --- Screenshot management ---

def cleanup_old_screenshots(max_age_days: int = 7):
    """
    Clean up old screenshot files.

    Args:
        max_age_days: Maximum age of screenshots to keep in days
    """
    try:
        current_time = time.time()
        max_age_seconds = max_age_days * 86400

        screenshot_patterns = ['error_', 'search_results_page.png']
        cleaned_count = 0

        for filename in os.listdir('.'):
            if any(filename.startswith(pattern) or filename == pattern for pattern in screenshot_patterns):
                if filename.endswith('.png'):
                    file_path = os.path.join('.', filename)
                    file_age = current_time - os.path.getmtime(file_path)

                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        cleaned_count += 1
                        logging.debug(f"Removed old screenshot: {filename}")

        if cleaned_count > 0:
            logging.info(f"Cleaned up {cleaned_count} old screenshot(s)")
    except Exception as e:
        logging.warning(f"Error during screenshot cleanup: {e}")

def take_error_screenshot(page: Page, error_type: str) -> Optional[str]:
    """
    Take a screenshot and return the path.

    Args:
        page: Playwright page object
        error_type: Type of error for filename

    Returns:
        Screenshot path or None if failed
    """
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = f'error_{error_type}_{timestamp}.png'
        page.screenshot(path=screenshot_path)
        logging.info(f"Screenshot saved: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        logging.warning(f"Failed to take screenshot: {e}")
        return None

# --- Error handling ---

def log_error_to_db(script_name: str, error_type: str, error_message: str,
                    error_details: Optional[str] = None, screenshot_path: Optional[str] = None):
    """
    Unified error logging to database.

    Args:
        script_name: Name of the script
        error_type: Type of error
        error_message: Error message
        error_details: Additional error details
        screenshot_path: Path to error screenshot
    """
    try:
        db = get_database()
        db.log_error(script_name, error_type, error_message, error_details, screenshot_path)
        logging.info(f"Error logged to database: {error_type}")
    except Exception as e:
        logging.error(f"Failed to log error to database: {e}")

# --- Core Automation Functions ---

def check_login_status(page: Page) -> bool:
    """Checks if the user is logged in."""
    try:
        page.goto("https://www.linkedin.com/feed/", timeout=60000)
        page.wait_for_selector("img.global-nav__me-photo", timeout=15000)
        logging.info("Successfully logged in.")
        return True
    except PlaywrightTimeoutError:
        logging.error("Failed to verify login.")
        screenshot_path = take_error_screenshot(page, 'login_verification_failed')
        log_error_to_db('visit_profiles', 'LoginVerificationError',
                       'Failed to verify login status', screenshot_path=screenshot_path)
        return False

def search_profiles(page: Page, keywords: List[str], location: str, page_number: int = 1) -> List[str]:
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
        for _ in range(5):  # Scroll a few times
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
        screenshot_path = take_error_screenshot(page, 'search_no_results')
        log_error_to_db('visit_profiles', 'SearchError',
                       'No search results found', screenshot_path=screenshot_path)

    return list(dict.fromkeys(profile_links))  # Return unique links

def record_profile_visit(profile_url: str, profile_name: str, config: Dict,
                        success: bool, error_message: Optional[str] = None):
    """
    Record a profile visit to the database (DRY - Don't Repeat Yourself).

    Args:
        profile_url: URL of the profile
        profile_name: Name extracted from profile
        config: Configuration dict with keywords and location
        success: Whether the visit was successful
        error_message: Error message if failed
    """
    try:
        db = get_database()
        source_search = "keyword_search" if not DRY_RUN else "keyword_search_dry_run"

        db.add_profile_visit(
            profile_name=profile_name,
            profile_url=profile_url,
            source_search=source_search,
            keywords=config['keywords'],
            location=config['location'],
            success=success,
            error_message=error_message
        )
    except Exception as e:
        logging.error(f"Failed to record profile visit to database: {e}")

def visit_profile_with_retry(page: Page, url: str, config: Dict,
                            max_attempts: int = 3, backoff_factor: int = 2) -> bool:
    """
    Visit a profile with retry logic and exponential backoff.

    Args:
        page: Playwright page object
        url: Profile URL to visit
        config: Configuration dict
        max_attempts: Maximum number of retry attempts
        backoff_factor: Factor for exponential backoff

    Returns:
        True if successful, False otherwise
    """
    delays = config.get('delays', {})

    for attempt in range(max_attempts):
        try:
            logging.info(f"Visiting profile (attempt {attempt + 1}/{max_attempts}): {url}")
            page.goto(url, timeout=60000)

            # Simuler des interactions humaines (scroll, mouvements de souris)
            simulate_human_interactions(page)

            # Délai plus naturel
            min_delay = delays.get('profile_visit_min', 15)
            max_delay = delays.get('profile_visit_max', 35)
            random_delay(min_delay, max_delay)

            return True

        except PlaywrightTimeoutError as e:
            wait_time = backoff_factor ** attempt
            logging.warning(f"Timeout visiting profile (attempt {attempt + 1}/{max_attempts}): {e}")

            if attempt < max_attempts - 1:
                logging.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logging.error(f"Failed to visit profile after {max_attempts} attempts")
                return False

        except Exception as e:
            logging.error(f"Unexpected error visiting profile: {e}")
            return False

    return False

def is_profile_already_visited(profile_url: str, days: int = 30) -> bool:
    """
    Check if a profile has been visited recently using the database.

    Args:
        profile_url: URL of the profile
        days: Number of days to look back

    Returns:
        True if already visited, False otherwise
    """
    try:
        db = get_database()
        return db.is_profile_visited(profile_url, days)
    except Exception as e:
        logging.error(f"Error checking if profile visited: {e}")
        # On error, assume not visited to avoid skipping profiles
        return False

def check_session_valid(page: Page) -> bool:
    """
    Check if the LinkedIn session is still valid.

    Args:
        page: Playwright page object

    Returns:
        True if session is valid, False otherwise
    """
    try:
        # Check if we're on a login page or can see the user menu
        current_url = page.url

        # If we're on a login/checkpoint page, session is invalid
        if 'login' in current_url or 'checkpoint' in current_url or 'authwall' in current_url:
            logging.warning(f"Session appears invalid - on auth page: {current_url}")
            return False

        # Try to find the user menu/photo with multiple selectors and longer timeout
        user_menu_selectors = [
            "img.global-nav__me-photo",
            "div.global-nav__me",
            "button[aria-label*='View profile']",
            "a[href*='/in/']"  # Fallback: any profile link
        ]

        for selector in user_menu_selectors:
            try:
                page.wait_for_selector(selector, timeout=10000)
                logging.debug(f"Session valid - found selector: {selector}")
                return True
            except PlaywrightTimeoutError:
                continue

        # If none of the selectors found, session might be invalid
        logging.warning("Session may be invalid - couldn't find any user menu indicators")
        logging.debug(f"Current URL: {current_url}")
        return False

    except Exception as e:
        logging.error(f"Error checking session validity: {e}")
        return False

# --- Setup Functions ---

def setup_authentication() -> bool:
    """
    Set up authentication from environment variable or local file.

    Returns:
        True if successful, False otherwise
    """
    # 1. Try Environment Variable first (Priority)
    if LINKEDIN_AUTH_STATE:
        try:
            # Try to load the auth state as a JSON string directly
            json.loads(LINKEDIN_AUTH_STATE)
            logging.info("Auth state is a valid JSON string. Writing to file directly.")
            with open(AUTH_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(LINKEDIN_AUTH_STATE)
            return True
        except json.JSONDecodeError:
            # If it's not a JSON string, assume it's a Base64 encoded binary file
            logging.info("Auth state is not a JSON string, attempting to decode from Base64.")
            try:
                padding = '=' * (-len(LINKEDIN_AUTH_STATE) % 4)
                auth_state_padded = LINKEDIN_AUTH_STATE + padding
                auth_state_bytes = base64.b64decode(auth_state_padded)
                with open(AUTH_FILE_PATH, "wb") as f:
                    f.write(auth_state_bytes)
                return True
            except (binascii.Error, TypeError) as e:
                logging.error(f"Failed to decode Base64 auth state: {e}")
                # Continue to fallback...
        except Exception as e:
            logging.error(f"An unexpected error occurred during auth state setup: {e}")
            # Continue to fallback...

    # 2. Fallback to existing 'auth_state.json' if it was manually placed
    if os.path.exists(AUTH_FILE_PATH):
        logging.info(f"Environment variable missing. Found existing '{AUTH_FILE_PATH}', using it.")
        return True

    logging.error("LINKEDIN_AUTH_STATE environment variable is not set and no valid local auth file found. Exiting.")
    return False

def setup_browser_context(p, proxy_manager: ProxyManager) -> Tuple[Optional[Browser], Optional[BrowserContext], Optional[Page], Optional[Dict], Optional[float]]:
    """
    Set up browser, context, and page with all anti-detection measures.

    Args:
        p: Playwright instance
        proxy_manager: ProxyManager instance

    Returns:
        Tuple of (browser, context, page, proxy_config, proxy_start_time)
    """
    proxy_config = None
    proxy_start_time = None

    if proxy_manager.is_enabled():
        proxy_config = proxy_manager.get_playwright_proxy_config()
        proxy_start_time = time.time()
        if proxy_config:
            logging.info(f"🌐 Proxy rotation enabled - using proxy")
        else:
            logging.warning("⚠️ Proxy rotation enabled but no proxy available, continuing without proxy")

    # Lancement du browser avec arguments anti-détection
    browser = p.chromium.launch(
        headless=HEADLESS_BROWSER,
        slow_mo=random.randint(100, 300),
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
    )

    # Build context options
    context_options = {
        'storage_state': AUTH_FILE_PATH,
        'user_agent': random.choice(USER_AGENTS),
        'viewport': {'width': random.randint(1280, 1920), 'height': random.randint(720, 1080)},
        'locale': 'fr-FR',
        'timezone_id': 'Europe/Paris'
    }

    # Add proxy configuration if available
    if proxy_config:
        context_options['proxy'] = proxy_config

    # Création du contexte avec User-Agent et empreinte aléatoires
    context = browser.new_context(**context_options)

    # Application de playwright-stealth pour masquer l'automatisation
    stealth = Stealth()
    stealth.apply_stealth_sync(context)

    page = context.new_page()

    return browser, context, page, proxy_config, proxy_start_time

def visit_profiles_loop(page: Page, config: Dict, metrics: ExecutionMetrics) -> int:
    """
    Main loop for visiting profiles.

    Args:
        page: Playwright page object
        config: Configuration dictionary
        metrics: Metrics tracker

    Returns:
        Number of profiles visited
    """
    profiles_visited = 0
    limits = config.get('limits', {})
    delays = config.get('delays', {})
    retry_config = config.get('retry', {})

    profiles_per_run = limits.get('profiles_per_run', 15)
    max_pages = limits.get('max_pages_to_scrape', 100)
    max_pages_without_new = limits.get('max_pages_without_new', 3)

    # Validate search selectors before starting
    logging.info("🔍 Validating search page selectors...")
    test_search_url = f"https://www.linkedin.com/search/results/people/?keywords={config['keywords'][0]}"
    page.goto(test_search_url, timeout=60000)
    random_delay(1, 2)

    selectors_valid = validate_search_selectors(page)
    if not selectors_valid:
        logging.warning("⚠️ Some search selectors are invalid - LinkedIn may have changed")

    # Iterate through multiple pages
    current_page = 1
    pages_without_new_profiles = 0

    while current_page <= max_pages and profiles_visited < profiles_per_run:
        logging.info(f"Scraping page {current_page}/{max_pages}")
        metrics.pages_scraped = current_page

        profile_urls = search_profiles(page, config['keywords'], config['location'], current_page)

        if not profile_urls:
            logging.info(f"No more profiles found on page {current_page}. Stopping pagination.")
            break

        # Track if we found new profiles on this page
        found_new_profiles = False

        for url in profile_urls:
            if profiles_visited >= profiles_per_run:
                logging.info(f"Reached visit limit for this run ({profiles_per_run}).")
                break

            # Check if already visited using database
            if is_profile_already_visited(url, days=30):
                logging.info(f"Skipping already visited profile: {url}")
                continue

            found_new_profiles = True
            logging.info(f"Visiting profile: {url}")

            # Extract profile name from URL
            profile_name = extract_profile_name_from_url(url)

            if not DRY_RUN:
                # Visit with retry logic
                max_attempts = retry_config.get('max_attempts', 3)
                backoff_factor = retry_config.get('backoff_factor', 2)

                success = visit_profile_with_retry(page, url, config, max_attempts, backoff_factor)

                # Record the visit
                record_profile_visit(url, profile_name, config, success,
                                   error_message=None if success else "Failed after retries")

                # Track metrics
                metrics.record_profile_attempt(success)

                if success:
                    profiles_visited += 1
                else:
                    metrics.record_error(f"Failed to visit {url}")

                # Check session validity periodically (every 5 profiles)
                if profiles_visited % 5 == 0:
                    if not check_session_valid(page):
                        logging.error("Session is no longer valid. Stopping.")
                        log_error_to_db('visit_profiles', 'SessionInvalidError',
                                      'LinkedIn session became invalid during execution')
                        break
            else:
                logging.info(f"[DRY RUN] Would have visited {url}")
                record_profile_visit(url, profile_name, config, success=True)
                profiles_visited += 1
                metrics.record_profile_attempt(True)

            logging.info(f"Profiles visited in this run: {profiles_visited}/{profiles_per_run}")
            random_delay()

        # Safety check: if we didn't find new profiles, increment counter
        if not found_new_profiles:
            pages_without_new_profiles += 1
            logging.info(f"No new profiles on page {current_page} ({pages_without_new_profiles}/{max_pages_without_new} pages without new)")
            if pages_without_new_profiles >= max_pages_without_new:
                logging.info(f"Stopping: {max_pages_without_new} consecutive pages with no new profiles.")
                break
        else:
            pages_without_new_profiles = 0  # Reset counter

        # If we've reached the visit limit, stop pagination
        if profiles_visited >= profiles_per_run:
            break

        current_page += 1

        # Delay between page navigation
        min_nav_delay = delays.get('page_navigation_min', 3)
        max_nav_delay = delays.get('page_navigation_max', 6)
        random_delay(min_nav_delay, max_nav_delay)

    logging.info(f"Script finished successfully. Scraped {current_page} page(s).")
    return profiles_visited

def cleanup_resources(browser: Browser, proxy_manager: ProxyManager, proxy_config: Optional[Dict],
                     proxy_start_time: Optional[float], script_successful: bool):
    """
    Clean up resources and record proxy results.

    Args:
        browser: Browser instance to close
        proxy_manager: ProxyManager instance
        proxy_config: Proxy configuration used
        proxy_start_time: When proxy usage started
        script_successful: Whether the script completed successfully
    """
    # Record proxy result if proxy was used
    if proxy_config and proxy_start_time:
        response_time = time.time() - proxy_start_time
        proxy_url = proxy_config.get('server', 'unknown')

        if script_successful:
            proxy_manager.record_proxy_result(proxy_url, success=True, response_time=response_time)
            logging.info(f"✅ Proxy completed successfully (response time: {response_time:.2f}s)")
        else:
            proxy_manager.record_proxy_result(proxy_url, success=False, response_time=response_time,
                                            error_message="Script execution failed")
            logging.warning(f"⚠️ Proxy recorded as failed due to script errors")

    logging.info("Closing browser.")
    try:
        browser.close()
    except Exception as e:
        # Browser might already be closed by playwright context manager
        logging.debug(f"Browser close skipped (already closed): {e}")

    if os.path.exists(AUTH_FILE_PATH):
        os.remove(AUTH_FILE_PATH)
        logging.debug("Auth file removed")

# --- Main Execution ---

def main():
    """Main function to run the profile visiting bot."""

    # ===== Configuration =====
    config = load_config()
    if not config:
        return

    # Clean up old screenshots
    cleanup_old_screenshots(max_age_days=7)

    if DRY_RUN:
        logging.info("=== SCRIPT RUNNING IN DRY RUN MODE ===")

    # Initialize metrics
    metrics = ExecutionMetrics()

    # Authentication setup
    if not setup_authentication():
        return

    # Track overall script success
    script_successful = False
    browser = None
    proxy_manager = None
    proxy_config = None
    proxy_start_time = None

    try:
        with sync_playwright() as p:
            # Initialize proxy manager
            proxy_manager = ProxyManager()

            # Setup browser
            browser, context, page, proxy_config, proxy_start_time = setup_browser_context(p, proxy_manager)

            if not browser or not page:
                logging.error("Failed to set up browser")
                return

            # Check login
            if not check_login_status(page):
                return

            # Visit profiles
            profiles_visited = visit_profiles_loop(page, config, metrics)

            # Mark as successful
            script_successful = True

            # Log metrics summary
            summary = metrics.get_summary()
            logging.info("=" * 60)
            logging.info("EXECUTION METRICS SUMMARY")
            logging.info("=" * 60)
            logging.info(f"Duration: {summary['duration_seconds']:.1f}s")
            logging.info(f"Profiles attempted: {summary['profiles_attempted']}")
            logging.info(f"Profiles succeeded: {summary['profiles_succeeded']}")
            logging.info(f"Profiles failed: {summary['profiles_failed']}")
            logging.info(f"Success rate: {summary['success_rate']:.1f}%")
            logging.info(f"Pages scraped: {summary['pages_scraped']}")
            logging.info(f"Avg time per profile: {summary['avg_time_per_profile']:.1f}s")
            logging.info(f"Errors encountered: {summary['errors_count']}")
            logging.info("=" * 60)

    except PlaywrightTimeoutError as e:
        logging.error(f"A timeout error occurred: {e}")
        error_msg = f"Playwright timeout: {str(e)}"

        if page:
            screenshot_path = take_error_screenshot(page, 'timeout')
            log_error_to_db('visit_profiles', 'PlaywrightTimeoutError', error_msg,
                          error_details=str(e), screenshot_path=screenshot_path)

        metrics.record_error(error_msg)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        error_msg = f"Unexpected error: {str(e)}"

        if page:
            screenshot_path = take_error_screenshot(page, 'unexpected')
            log_error_to_db('visit_profiles', 'UnexpectedError', error_msg,
                          error_details=str(e), screenshot_path=screenshot_path)

        metrics.record_error(error_msg)

    finally:
        # ===== P0: Fixed proxy recording (using flag instead of assuming success) =====
        if browser and proxy_manager:
            cleanup_resources(browser, proxy_manager, proxy_config, proxy_start_time, script_successful)

if __name__ == "__main__":
    main()
