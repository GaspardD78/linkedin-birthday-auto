import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

from cryptography.fernet import Fernet, InvalidToken
from playwright.async_api import Page

from app_v2.core.config import Settings

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.auth_file = Path("data/auth_state.json")
        try:
            # Initialize Fernet with the key from settings
            # Note: get_secret_value() returns the string, which we need to encode to bytes for Fernet
            key = settings.auth_encryption_key.get_secret_value()
            self.cipher = Fernet(key.encode())
        except Exception as e:
            logger.error(f"Failed to initialize Fernet cipher: {e}")
            raise

    async def load_auth_state(self) -> Optional[Dict[str, Any]]:
        """
        Loads and decrypts the authentication state from the file.
        Returns the storage state dict or None if invalid/missing.
        """
        if not self.auth_file.exists():
            logger.warning(f"Auth file not found at {self.auth_file}")
            return None

        try:
            encrypted_data = self.auth_file.read_bytes()
            decrypted_data = self.cipher.decrypt(encrypted_data)
            auth_state = json.loads(decrypted_data)
            logger.info("✓ Auth state loaded and decrypted successfully")
            return auth_state
        except InvalidToken:
            logger.error("Failed to decrypt auth state: Invalid Token (wrong key?)")
            return None
        except json.JSONDecodeError:
            logger.error("Failed to parse auth state JSON")
            return None
        except Exception as e:
            logger.error(f"Error loading auth state: {e}")
            return None

    async def save_auth_state(self, storage_state: Dict[str, Any]) -> None:
        """
        Encrypts and saves the authentication state to the file.
        """
        try:
            # Ensure data directory exists
            self.auth_file.parent.mkdir(parents=True, exist_ok=True)

            json_data = json.dumps(storage_state)
            encrypted_data = self.cipher.encrypt(json_data.encode())

            self.auth_file.write_bytes(encrypted_data)
            logger.info("✓ Session sauvegardée")
        except Exception as e:
            logger.error(f"Error saving auth state: {e}")
            raise

    async def validate_session(self, page: Page) -> bool:
        """
        Validates the current session by navigating to LinkedIn feed.
        """
        try:
            logger.info("Validating session...")
            # Navigation vers le feed avec timeout court (10s)
            try:
                await page.goto("https://www.linkedin.com/feed/", timeout=10000, wait_until="domcontentloaded")
            except Exception as e:
                logger.warning(f"Navigation timeout or error: {e}")
                # Continue checking just in case we landed somewhere or partial load

            # Indicateur 1: Avatar
            try:
                # On attend un peu que ça s'affiche
                avatar = page.locator('img[alt*="photo"]').first
                if await avatar.count() > 0:
                     await avatar.wait_for(state="visible", timeout=5000)
                     logger.info("✓ Session valide (Avatar détecté)")
                     return True
                else:
                    # Try waiting for it even if count is 0, wait_for handles it
                    await avatar.wait_for(state="visible", timeout=2000)
                    logger.info("✓ Session valide (Avatar détecté)")
                    return True
            except Exception:
                pass # Continue to check 2

            # Indicateur 2: Pas de redirect login
            current_url = page.url
            if "/login" in current_url or "uas/authenticate" in current_url:
                logger.warning(f"Session invalide: Redirection vers {current_url}")
                await self._take_screenshot(page, "session_invalid.png")
                return False

            # Si on est sur le feed sans voir l'avatar (ex: layout différent, lent)
            if "feed" in current_url:
                logger.info("✓ Session valide (URL feed détectée)")
                return True

            logger.warning(f"Session état inconnu: {current_url}")
            await self._take_screenshot(page, "session_invalid.png")
            return False

        except Exception as e:
            logger.error(f"Erreur lors de la validation de session: {e}")
            await self._take_screenshot(page, "session_error.png")
            return False

    async def is_session_expired(self) -> bool:
        """
        Checks if the 'li_at' cookie is expired based on the loaded auth state.
        """
        state = await self.load_auth_state()
        if not state:
            return True # No state = expired/invalid

        cookies = state.get("cookies", [])
        li_at = next((c for c in cookies if c["name"] == "li_at"), None)

        if not li_at:
            logger.warning("'li_at' cookie not found in auth state")
            return True

        expires = li_at.get("expires", -1)
        if expires == -1:
            # Session cookie, expires when browser closes? Or invalid.
            return False

        # Check expiration
        if time.time() > expires:
            logger.warning("Session cookie 'li_at' has expired")
            return True

        return False

    async def _take_screenshot(self, page: Page, name: str):
        try:
            screenshot_path = Path("data/screenshots") / name
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(screenshot_path))
            logger.info(f"Screenshot saved to {screenshot_path}")
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
