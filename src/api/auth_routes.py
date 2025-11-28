import json
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from playwright.async_api import (
    TimeoutError as PlaywrightTimeoutError,
)
from playwright.async_api import (
    async_playwright,
)
from pydantic import BaseModel

from ..core.auth_manager import AuthManager
from ..monitoring.tracing import TemporaryTracing
from ..utils.logging import get_logger
from .security import verify_api_key

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════

MAX_2FA_RETRIES = 3  # Maximum number of 2FA code attempts
SESSION_TIMEOUT_SECONDS = 300  # 5 minutes session timeout

# ═══════════════════════════════════════════════════════════════════
# GLOBAL STATE & ROUTER
# ═══════════════════════════════════════════════════════════════════

# A simple in-memory dictionary to hold the browser session.
# This is suitable for a single-admin dashboard but would need a more robust
# solution (like Redis-based session management) for a multi-user system.
auth_session: dict[str, Any] = {
    "browser": None,
    "page": None,
    "context": None,
    "playwright": None,  # BUGFIX: Store Playwright instance to close properly
    "retry_count": 0,  # BUGFIX: Track 2FA retry attempts
    "created_at": None,  # BUGFIX: Track session creation time
}

router = APIRouter(prefix="/auth", tags=["Authentication"], dependencies=[Depends(verify_api_key)])

# ═══════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════


class StartAuthRequest(BaseModel):
    email: str
    password: str


class Verify2FARequest(BaseModel):
    code: str


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════


async def close_browser_session():
    """Safely closes any active Playwright browser session."""
    logger.info("Closing browser session.")

    # Close browser first
    if auth_session.get("browser"):
        try:
            await auth_session["browser"].close()
        except Exception as e:
            logger.error(f"Error closing browser: {e}", exc_info=True)

    # BUGFIX: Close Playwright instance to prevent resource leak
    if auth_session.get("playwright"):
        try:
            await auth_session["playwright"].stop()
            logger.debug("Playwright instance stopped")
        except Exception as e:
            logger.error(f"Error stopping Playwright: {e}", exc_info=True)

    # Reset session state
    auth_session.update(
        {
            "browser": None,
            "page": None,
            "context": None,
            "playwright": None,
            "retry_count": 0,
            "created_at": None,
        }
    )


# ═══════════════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════════════


@router.post("/start")
async def start_authentication(request: StartAuthRequest):
    """
    Starts the LinkedIn authentication process.
    It launches a headless browser, navigates to the login page, and
    submits the provided credentials. It then determines if a 2FA code
    is required or if the login was successful.
    """
    if auth_session.get("browser"):
        await close_browser_session()

    logger.info("Starting LinkedIn authentication process.")

    # Activer le tracing temporairement pour déboguer le processus d'authentification
    with TemporaryTracing(service_name="linkedin-auth-start") as tracer:
        with tracer.start_as_current_span("authentication_start") as span:
            try:
                span.set_attribute("email", request.email[:3] + "***")  # Log partiel pour sécurité

                p = await async_playwright().start()
                # Optimized browser launch for Raspberry Pi 4
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-software-rasterizer",
                        "--disable-extensions",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                    ],
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                # BUGFIX: Store Playwright instance and session metadata
                import time as time_module

                auth_session.update(
                    {
                        "browser": browser,
                        "page": page,
                        "context": context,
                        "playwright": p,
                        "retry_count": 0,
                        "created_at": time_module.time(),
                    }
                )

                # Increased timeouts for Raspberry Pi 4
                logger.info("Navigating to LinkedIn login page...")
                span.add_event("navigate_to_login")
                await page.goto("https://www.linkedin.com/login", timeout=120000)

                logger.info("Filling credentials...")
                span.add_event("fill_credentials")
                await page.fill("#username", request.email)
                await page.fill("#password", request.password)

                logger.info("Submitting login form...")
                span.add_event("submit_login_form")
                await page.click("button[type='submit']")

                # Wait for one of the possible outcomes after login attempt
                pin_input_selector = (
                    "#input__phone_verification_pin, input[name='pin'], #id_verification_pin"
                )
                feed_selector = "div.feed-identity-module, .feed-shared-update-v2, #global-nav"
                error_selector = ".login__form_action_container .error, .alert-content"
                captcha_selector = "#captcha-internal, iframe[src*='captcha']"

                logger.info("Waiting for login response...")
                span.add_event("wait_for_response")

                # Increased timeout for Raspberry Pi 4 (from 90s to 180s)
                try:
                    await page.wait_for_selector(
                        f"{pin_input_selector}, {feed_selector}, {error_selector}, {captcha_selector}",
                        timeout=180000,
                    )
                except PlaywrightTimeoutError:
                    # Capture current page state for debugging
                    current_url = page.url
                    page_title = await page.title()
                    logger.error(
                        f"Timeout waiting for login response. Current URL: {current_url}, Title: {page_title}"
                    )

                    # Take screenshot for debugging
                    try:
                        screenshot_path = "/app/logs/auth_timeout.png"
                        await page.screenshot(path=screenshot_path)
                        logger.info(f"Screenshot saved to: {screenshot_path}")
                    except Exception as e:
                        logger.warning(f"Failed to capture screenshot: {e}")

                    raise

                if await page.is_visible(captcha_selector):
                    logger.warning("Captcha detected! Automated login blocked.")
                    span.set_attribute("result", "captcha")
                    await close_browser_session()
                    raise HTTPException(
                        status_code=403, detail="Captcha detected. Please use manual cookie export."
                    )

                if await page.is_visible(pin_input_selector):
                    logger.info("2FA required.")
                    span.set_attribute("result", "2fa_required")
                    return {"status": "2fa_required"}

                if await page.is_visible(error_selector):
                    error_message = await page.text_content(error_selector)
                    logger.warning(f"Login failed: {error_message}")
                    span.set_attribute("result", "error")
                    span.set_attribute("error_message", error_message or "Unknown")
                    await close_browser_session()
                    raise HTTPException(
                        status_code=401, detail=error_message or "Invalid credentials."
                    )

                if await page.is_visible(feed_selector):
                    logger.info("Login successful, saving session.")
                    span.set_attribute("result", "success")
                    auth_manager = AuthManager()
                    # Save to writable /app/data directory instead of read-only mounted file
                    writable_auth_path = "/app/data/auth_state.json"
                    await auth_manager.save_cookies_from_context(
                        context, output_path=writable_auth_path
                    )
                    await close_browser_session()
                    return {"status": "success"}

                await close_browser_session()
                span.set_attribute("result", "unknown_state")
                raise HTTPException(status_code=500, detail="Unknown page state after login.")

            except PlaywrightTimeoutError:
                logger.error("Timeout during login process.")
                span.set_attribute("error", "timeout")
                await close_browser_session()
                raise HTTPException(
                    status_code=408, detail="Timeout: LinkedIn took too long to respond."
                )
            except Exception as e:
                logger.error(f"An unexpected error occurred during login: {e}", exc_info=True)
                span.set_attribute("error", str(e))
                await close_browser_session()
                raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e!s}")


@router.post("/verify-2fa")
async def verify_2fa_code(request: Verify2FARequest):
    """
    Submits the 2FA code to complete the authentication.
    Uses the browser session started by /start.
    """
    page = auth_session.get("page")
    context = auth_session.get("context")
    retry_count = auth_session.get("retry_count", 0)
    created_at = auth_session.get("created_at")

    if not page or not context:
        raise HTTPException(status_code=400, detail="No active authentication session found.")

    # BUGFIX: Check session timeout
    import time as time_module

    if created_at and (time_module.time() - created_at) > SESSION_TIMEOUT_SECONDS:
        logger.warning("Session timeout exceeded")
        await close_browser_session()
        raise HTTPException(
            status_code=408, detail="Session timeout. Please restart authentication."
        )

    # BUGFIX: Check retry limit
    if retry_count >= MAX_2FA_RETRIES:
        logger.warning(f"Max 2FA retries exceeded ({MAX_2FA_RETRIES})")
        await close_browser_session()
        raise HTTPException(
            status_code=429, detail=f"Too many attempts. Maximum {MAX_2FA_RETRIES} retries allowed."
        )

    logger.info(f"Submitting 2FA code (attempt {retry_count + 1}/{MAX_2FA_RETRIES})")

    # Activer le tracing temporairement pour déboguer la vérification 2FA
    with TemporaryTracing(service_name="linkedin-auth-2fa") as tracer:
        with tracer.start_as_current_span("authentication_2fa_verify") as span:
            try:
                span.add_event("submit_2fa_code")
                await page.fill("#input__phone_verification_pin", request.code)
                await page.click("button[type='submit']")

                feed_selector = "div.feed-identity-module, .feed-shared-update-v2, #global-nav"
                error_selector = ".form__subtitle--error, .alert-content, .error-label"

                logger.info("Waiting for 2FA verification response...")
                span.add_event("wait_for_2fa_response")
                # Increased timeout for Raspberry Pi 4 (from 90s to 180s)
                await page.wait_for_selector(f"{feed_selector}, {error_selector}", timeout=180000)

                if await page.is_visible(error_selector):
                    error_message = await page.text_content(error_selector)
                    logger.warning(f"2FA verification failed: {error_message}")
                    span.set_attribute("result", "error")
                    span.set_attribute("error_message", error_message or "Unknown")

                    # BUGFIX: Increment retry count on failure
                    auth_session["retry_count"] = retry_count + 1
                    remaining = MAX_2FA_RETRIES - (retry_count + 1)

                    # DO NOT close browser session here to allow retry
                    detail = error_message or "Invalid 2FA code."
                    if remaining > 0:
                        detail += f" {remaining} attempt(s) remaining."
                    raise HTTPException(status_code=401, detail=detail)

                if await page.is_visible(feed_selector):
                    logger.info("2FA verification successful, saving session.")
                    span.set_attribute("result", "success")
                    auth_manager = AuthManager()
                    # Save to writable /app/data directory instead of read-only mounted file
                    writable_auth_path = "/app/data/auth_state.json"
                    await auth_manager.save_cookies_from_context(
                        context, output_path=writable_auth_path
                    )
                    await close_browser_session()
                    return {"status": "success"}

                await close_browser_session()
                span.set_attribute("result", "unknown_state")
                raise HTTPException(
                    status_code=500, detail="Unknown page state after 2FA submission."
                )

            except PlaywrightTimeoutError:
                logger.error("Timeout during 2FA verification.")
                span.set_attribute("error", "timeout")
                await close_browser_session()
                raise HTTPException(
                    status_code=408, detail="Timeout: Verification failed or took too long."
                )
            except Exception as e:
                logger.error(f"An unexpected error occurred during 2FA: {e}", exc_info=True)
                span.set_attribute("error", str(e))
                await close_browser_session()
                raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e!s}")


@router.post("/upload")
async def upload_auth_file(file: UploadFile = File(...)):
    """
    Allows uploading an auth_state.json file directly as a fallback.
    """
    if not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Please upload a .json file."
        )

    logger.info(f"Receiving uploaded auth file: {file.filename}")
    try:
        content = await file.read()
        # The content might be inside a "cookies" key or be the list itself
        parsed_json = json.loads(content)
        cookies = parsed_json.get("cookies", parsed_json)

        if not isinstance(cookies, list):
            raise ValueError(
                "JSON content must be a list of cookies or an object with a 'cookies' key."
            )

        auth_manager = AuthManager()
        # Save to writable /app/data directory instead of read-only mounted file
        writable_auth_path = "/app/data/auth_state.json"
        auth_manager.save_cookies(cookies, output_path=writable_auth_path)
        logger.info(f"Successfully saved cookies from uploaded file to: {writable_auth_path}")
        return {"status": "success", "filename": file.filename, "saved_to": writable_auth_path}
    except json.JSONDecodeError:
        logger.error("Failed to decode uploaded JSON file.")
        raise HTTPException(status_code=400, detail="Invalid JSON format.")
    except Exception as e:
        logger.error(f"Failed to process uploaded auth file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process file: {e!s}")
