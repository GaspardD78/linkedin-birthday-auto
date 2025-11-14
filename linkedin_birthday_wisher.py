import os
import random
import time
import logging
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

# --- Configuration ---
# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Credentials and settings from environment variables
LINKEDIN_EMAIL = os.getenv('LINKEDIN_EMAIL')
LINKEDIN_PASSWORD = os.getenv('LINKEDIN_PASSWORD')
USER_DATA_DIR = './playwright_user_data' # Stores session cookies to avoid repeated logins
HEADLESS_BROWSER = True # Set to False for debugging to see the browser UI

# Customizable birthday messages. {name} will be replaced by the contact's first name.
BIRTHDAY_MESSAGES = [
    "Joyeux anniversaire, {name} !",
    "Bonjour {name}, je vous souhaite un excellent anniversaire !",
    "Je te souhaite un très joyeux anniversaire, {name} ! Profite bien de ta journée."
]

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

def login_to_linkedin(page: Page):
    """Handles the login process for LinkedIn."""
    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        raise ValueError("LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables must be set.")

    logging.info("Navigating to LinkedIn login page.")
    page.goto("https://www.linkedin.com/login", timeout=60000)

    # If already logged in (redirected to feed), skip login.
    if "feed" in page.url:
        logging.info("Already logged in.")
        return

    logging.info("Logging in with provided credentials.")
    page.fill("#username", LINKEDIN_EMAIL)
    random_delay()
    page.fill("#password", LINKEDIN_PASSWORD)
    random_delay()
    page.click("button[type='submit']")

    try:
        # Wait for the main feed to load to confirm successful login
        page.wait_for_url("**/feed/**", timeout=90000)
        logging.info("Login successful.")
    except PlaywrightTimeoutError:
        logging.error("Login failed. Could be due to incorrect credentials or a CAPTCHA.")
        page.screenshot(path='error_login_failed.png')
        raise

def get_birthday_contacts(page: Page) -> list:
    """Navigates to the birthdays page and extracts a list of contacts."""
    logging.info("Navigating to the birthdays page.")
    page.goto("https://www.linkedin.com/notifications/birthdays", timeout=60000)

    # This selector targets the list containing birthday cards.
    birthday_list_selector = ".scaffold-finite-scroll__content > ul > li"

    try:
        page.wait_for_selector(birthday_list_selector, timeout=30000)
        contacts = page.query_selector_all(birthday_list_selector)
        logging.info(f"Found {len(contacts)} contact(s) with a birthday today.")
        return contacts
    except PlaywrightTimeoutError:
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
    type_like_a_human(page, message_box_selector, message)
    random_delay(1, 2)

    submit_button = page.locator("button.msg-form__send-button")
    if submit_button.is_enabled():
        submit_button.click()
        logging.info("Message sent successfully.")
    else:
        logging.warning("Send button is not enabled. Skipping.")
        # Close the modal to continue
        page.locator("button[data-control-name='overlay.close_conversation_window']").click()


# --- Main Execution ---

def main():
    """Main function to run the LinkedIn birthday wisher bot."""
    # Add a random startup delay to run between 8h and 10h UTC.
    # The GitHub Action is scheduled for 8:00 UTC.
    startup_delay = random.randint(0, 7200) # 0 to 120 minutes (2 hours)
    logging.info(f"Startup delay: waiting for {startup_delay // 60}m {startup_delay % 60}s to start.")
    time.sleep(startup_delay)
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=HEADLESS_BROWSER,
            slow_mo=100,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = browser.new_page()

        try:
            login_to_linkedin(page)
            random_delay(2, 4)

            contacts = get_birthday_contacts(page)

            for i, contact in enumerate(contacts):
                send_birthday_message(page, contact)

                # If it's not the last contact, pause for a long, random duration
                if i < len(contacts) - 1:
                    delay = random.randint(120, 300) # 2 to 5 minutes
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

if __name__ == "__main__":
    main()
