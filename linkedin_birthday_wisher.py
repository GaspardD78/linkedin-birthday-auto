import os
import random
import time
import logging
import base64
import json
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

# --- Configuration ---
# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Secure authentication using a Base64 encoded auth state from GitHub Secrets
LINKEDIN_AUTH_STATE_B64 = os.getenv('LINKEDIN_AUTH_STATE')
AUTH_FILE_PATH = "auth_state.json"

# General settings
HEADLESS_BROWSER = True # Set to False for debugging to see the browser UI
DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true' # Enables test mode

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

# --- Human Behavior Simulation ---

def random_delay(min_seconds: float = 0.5, max_seconds: float = 1.5):
    """Waits for a random duration within a specified range to mimic human latency."""
    time.sleep(random.uniform(min_seconds, max_seconds))

def type_like_a_human(page: Page, selector: str, text: str):
    """Simulates typing text into an element char by char with small random delays."""
    logging.info(f"Typing message: '{text}'")
    page.click(selector, delay=random.uniform(50, 100))
    for char in text:
        page.press(selector, char, delay=random.uniform(70, 200))

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

def get_birthday_contacts(page: Page) -> list:
    """Navigates to the birthdays page and extracts a list of contacts."""
    logging.info("Navigating to the birthdays page.")
    page.goto("https://www.linkedin.com/notifications/birthdays", timeout=60000)

    # Wait for the page to load
    random_delay(3, 5)

    # Take a screenshot for debugging
    page.screenshot(path='birthdays_page.png')
    logging.info("Screenshot saved as 'birthdays_page.png' for debugging.")

    # Try multiple possible selectors for birthday cards
    possible_selectors = [
        ".scaffold-finite-scroll__content > ul > li",  # Original selector
        "li.birthday-card",  # Alternative: direct birthday card selector
        "div[data-view-name='birthday-card']",  # Alternative: by data attribute
        ".artdeco-list__item",  # Alternative: artdeco list item
        "ul.birthday-notifications-list > li",  # Alternative: specific list
        "[class*='birthday']",  # Any element with 'birthday' in class
    ]

    contacts = []
    for selector in possible_selectors:
        logging.info(f"Trying selector: {selector}")
        try:
            page.wait_for_selector(selector, timeout=5000)
            contacts = page.query_selector_all(selector)
            if len(contacts) > 0:
                logging.info(f"Found {len(contacts)} contact(s) with selector '{selector}'")
                return contacts
        except PlaywrightTimeoutError:
            logging.info(f"Selector '{selector}' not found, trying next...")
            continue

    # If no selector worked, try to find any list items on the page
    logging.warning("All specific selectors failed. Searching for any list items...")
    all_list_items = page.query_selector_all("li")
    logging.info(f"Found {len(all_list_items)} total <li> elements on the page.")

    # Save page HTML for analysis
    html_content = page.content()
    with open('birthdays_page.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    logging.info("Page HTML saved as 'birthdays_page.html' for analysis.")

    logging.info("No birthday notifications found today.")
    return []

def send_birthday_message(page: Page, contact_element):
    """Opens the messaging modal and sends a personalized birthday wish."""
    # Extract the first name from the card's title (e.g., "Say happy birthday to John Doe")
    name_text = contact_element.query_selector("h3").inner_text()
    first_name = name_text.split()[-2] # A simple way to get the first name.

    logging.info(f"--- Processing birthday for {first_name} ---")

    # Click the "Message" button on the birthday card to open the composer.
    message_button = contact_element.query_selector("button:has-text('Message')")
    if not message_button:
        logging.warning(f"Could not find a 'Message' button for {first_name}. Skipping.")
        return

    message_button.click()

    message_box_selector = "div.msg-form__contenteditable[role='textbox']"
    page.wait_for_selector(message_box_selector, state="visible", timeout=30000)

    message = random.choice(BIRTHDAY_MESSAGES).format(name=first_name)

    if DRY_RUN:
        logging.info(f"[DRY RUN] Would send message to {first_name}: '{message}'")
        # In dry run, we must close the modal to proceed to the next contact.
        close_button = page.locator("button[data-control-name='overlay.close_conversation_window']")
        if close_button.is_visible():
            close_button.click()
        return

    type_like_a_human(page, message_box_selector, message)
    random_delay(1, 2)

    submit_button = page.locator("button.msg-form__send-button")
    if submit_button.is_enabled():
        submit_button.click()
        logging.info("Message sent successfully.")
    else:
        logging.warning("Send button is not enabled. Skipping.")

    # Always close the modal after processing.
    close_button = page.locator("button[data-control-name='overlay.close_conversation_window']")
    if close_button.is_visible():
        close_button.click()


# --- Main Execution ---

def main():
    """Main function to run the LinkedIn birthday wisher bot."""
    if DRY_RUN:
        logging.info("=== SCRIPT RUNNING IN DRY RUN MODE ===")

    # Add a random startup delay.
    # In normal mode, this is long to simulate a user logging in between 8h-10h UTC.
    # In DRY RUN mode, this is short for quick testing.
    if DRY_RUN:
        startup_delay = random.randint(1, 10) # 1 to 10 seconds for testing
    else:
        startup_delay = random.randint(0, 7200) # 0 to 120 minutes for normal operation

    logging.info(f"Startup delay: waiting for {startup_delay // 60}m {startup_delay % 60}s to start.")
    time.sleep(startup_delay)

    if not BIRTHDAY_MESSAGES:
        logging.error("Message list is empty. Please check messages.txt. Exiting.")
        return

    # Decode and save the auth state from the environment variable
    if not LINKEDIN_AUTH_STATE_B64:
        logging.error("LINKEDIN_AUTH_STATE environment variable is not set. Please generate it first.")
        return

    try:
        auth_state_bytes = base64.b64decode(LINKEDIN_AUTH_STATE_B64)
        with open(AUTH_FILE_PATH, "wb") as f:
            f.write(auth_state_bytes)
    except Exception as e:
        logging.error(f"Failed to decode or save the auth state: {e}")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS_BROWSER,
            slow_mo=100
        )
        context = browser.new_context(
            storage_state=AUTH_FILE_PATH,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = context.new_page()

        try:
            if not check_login_status(page):
                return # Stop execution if login verification fails.

            random_delay(2, 4)

            contacts = get_birthday_contacts(page)

            for i, contact in enumerate(contacts):
                send_birthday_message(page, contact)

                # If it's not the last contact, pause.
                # In normal mode, this is a long, random duration to simulate human behavior.
                # In DRY RUN mode, this is short for quick testing.
                if i < len(contacts) - 1:
                    if DRY_RUN:
                        delay = random.randint(1, 5) # 1 to 5 seconds for testing
                    else:
                        delay = random.randint(120, 300) # 2 to 5 minutes for normal operation
                    logging.info(f"Pausing for {delay // 60}m {delay % 60}s.")
                    time.sleep(delay)

            logging.info("Script finished successfully.")

        except PlaywrightTimeoutError as e:
            logging.error(f"A timeout error occurred: {e}")
            page.screenshot(path='error_timeout.png')
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            page.screenshot(path='error_unexpected.png')
        finally:
            logging.info("Closing browser.")
            browser.close()
            # Clean up the local auth file for security
            if os.path.exists(AUTH_FILE_PATH):
                os.remove(AUTH_FILE_PATH)

if __name__ == "__main__":
    main()
