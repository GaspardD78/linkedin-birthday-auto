import os
import random
import time
import logging
import base64
import json
from typing import Optional
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

# --- Configuration ---
# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Secure authentication using an auth state from GitHub Secrets
LINKEDIN_AUTH_STATE = os.getenv('LINKEDIN_AUTH_STATE')
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
LATE_BIRTHDAY_MESSAGES = load_birthday_messages("late_messages.txt")

# --- Human Behavior Simulation ---

def random_delay(min_seconds: float = 0.5, max_seconds: float = 1.5):
    """Waits for a random duration within a specified range to mimic human latency."""
    time.sleep(random.uniform(min_seconds, max_seconds))

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
    into 'today' and 'late' birthdays.
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

    # Categorize birthdays
    birthdays = {'today': [], 'late': []}
    ignored_count = 0
    for contact in all_contacts:
        birthday_type, days_late = get_birthday_type(contact)
        if birthday_type == 'today':
            birthdays['today'].append(contact)
        elif birthday_type == 'late':
            birthdays['late'].append((contact, days_late))
        else: # birthday_type == 'ignore'
            ignored_count += 1

    logging.info(f"Ignored {ignored_count} birthdays older than 4 days.")

    logging.info(f"Found {len(birthdays['today'])} birthdays for today.")
    logging.info(f"Found {len(birthdays['late'])} late birthdays.")

    # Save page HTML for analysis, especially if something goes wrong
    if not all_contacts:
        html_content = page.content()
        with open('birthdays_page_analysis.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        logging.info("Page HTML saved as 'birthdays_page_analysis.html' for analysis.")

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

def get_birthday_type(contact_element) -> tuple[str, int]:
    """
    Determines if a birthday is 'today', 'late' (within 4 days), or 'ignore'.
    Returns a tuple of (type, days_late).
    """
    card_text = contact_element.inner_text().lower()

    # Priority 1: Check for today's birthdays explicitly
    if 'aujourd\'hui' in card_text or 'today' in card_text:
        return 'today', 0

    # Priority 2: Check for yesterday
    if 'hier' in card_text or 'yesterday' in card_text:
        return 'late', 1

    # Priority 3: Check for "il y a X jours"
    import re
    match = re.search(r'il y a (\d+) jours', card_text)
    if match:
        days_late = int(match.group(1))
        if 1 <= days_late <= 4:
            return 'late', days_late
        else:
            # It's a late birthday, but too old to process
            return 'ignore', days_late

    # Priority 4: If any other late keywords are present, we can't quantify, so ignore.
    late_keywords = ['avec un peu de retard', 'avec du retard', 'en retard', 'belated']
    if any(keyword in card_text for keyword in late_keywords):
        return 'ignore', 0

    # Default case: If no late keywords are found, it's today's birthday.
    return 'today', 0

def send_birthday_message(page: Page, contact_element, is_late: bool = False, days_late: int = 0):
    """Opens the messaging modal and sends a personalized birthday wish."""
    full_name = extract_contact_name(contact_element)
    if not full_name:
        logging.warning("Skipping contact because name could not be extracted.")
        return

    first_name = full_name.split()[0]

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

    message_button.click()

    message_box_selector = "div.msg-form__contenteditable[role='textbox']"
    page.wait_for_selector(message_box_selector, state="visible", timeout=30000)

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

            birthdays = get_birthday_contacts(page)

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
                        if i < len(contacts) - 1:
                            if DRY_RUN:
                                delay = random.randint(2, 5) # Short delay for testing
                            else:
                                delay = random.randint(120, 300) # 2-5 minutes for normal operation
                            logging.info(f"Pausing for {delay // 60}m {delay % 60}s.")
                            time.sleep(delay)
                else:
                    for i, contact in enumerate(contacts):
                        send_birthday_message(page, contact, is_late=is_late)

                        # Add a pause between messages
                        if i < len(contacts) - 1:
                            if DRY_RUN:
                                delay = random.randint(2, 5) # Short delay for testing
                            else:
                                delay = random.randint(120, 300) # 2-5 minutes for normal operation
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
