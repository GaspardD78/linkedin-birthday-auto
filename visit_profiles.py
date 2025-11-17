import os
import random
import time
import logging
import base64
import json
import urllib.parse
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Authentication
LINKEDIN_AUTH_STATE = os.getenv('LINKEDIN_AUTH_STATE')
AUTH_FILE_PATH = "auth_state.json"

# Visited profiles file
VISITED_PROFILES_FILE = "visited_profiles.txt"

# General settings
HEADLESS_BROWSER = True
DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'
PROFILES_TO_VISIT_PER_RUN = 50

# --- Helper Functions ---

def load_config():
    """Loads search configuration from config.json."""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error("config.json not found. Please create it.")
        return None
    except json.JSONDecodeError:
        logging.error("Error decoding config.json. Please check its format.")
        return None

def load_visited_profiles():
    """Loads the set of already visited profile URLs. Creates the file if it doesn't exist."""
    if not os.path.exists(VISITED_PROFILES_FILE):
        # Create the file so it can be committed by the workflow even if no new profiles are visited.
        with open(VISITED_PROFILES_FILE, "w", encoding="utf-8") as f:
            pass # Create an empty file
        return set()
    with open(VISITED_PROFILES_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}

def save_visited_profile(profile_url):
    """Appends a new visited profile URL to the file."""
    with open(VISITED_PROFILES_FILE, "a", encoding="utf-8") as f:
        f.write(profile_url + "\n")

def random_delay(min_seconds: float = 2.5, max_seconds: float = 5.5):
    """Waits for a random duration to mimic human latency."""
    time.sleep(random.uniform(min_seconds, max_seconds))

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

def search_profiles(page: Page, keywords: list, location: str):
    """Performs a search on LinkedIn and returns profile URLs."""
    keyword_str = " ".join(keywords)
    # Use the location text directly in the search query, which is more flexible.
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(keyword_str)}&location={urllib.parse.quote(location)}&origin=GLOBAL_SEARCH_HEADER"

    logging.info(f"Navigating to search URL: {search_url}")
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
        browser = p.chromium.launch(headless=HEADLESS_BROWSER, slow_mo=150)
        context = browser.new_context(storage_state=AUTH_FILE_PATH)
        page = context.new_page()

        try:
            if not check_login_status(page):
                return

            profile_urls = search_profiles(page, config['keywords'], config['location'])

            for url in profile_urls:
                if profiles_visited_this_run >= PROFILES_TO_VISIT_PER_RUN:
                    logging.info(f"Reached visit limit for this run ({PROFILES_TO_VISIT_PER_RUN}).")
                    break

                if url in visited_profiles:
                    logging.info(f"Skipping already visited profile: {url}")
                    continue

                logging.info(f"Visiting profile: {url}")
                if not DRY_RUN:
                    page.goto(url, timeout=60000)
                    random_delay(5, 10) # Stay on page for a bit
                    save_visited_profile(url)
                    visited_profiles.add(url)
                else:
                    logging.info(f"[DRY RUN] Would have visited {url}")

                profiles_visited_this_run += 1
                logging.info(f"Profiles visited in this run: {profiles_visited_this_run}/{PROFILES_TO_VISIT_PER_RUN}")
                random_delay()

            logging.info("Script finished successfully.")

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
