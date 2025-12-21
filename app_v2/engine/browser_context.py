from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from pathlib import Path
from datetime import datetime
import asyncio
import logging
from typing import Optional

from app_v2.core.config import Settings
from app_v2.engine.auth_manager import AuthManager

logger = logging.getLogger(__name__)

class LinkedInBrowserContext:
    def __init__(self, settings: Settings, auth_manager: AuthManager):
        self.settings = settings
        self.auth_manager = auth_manager
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def __aenter__(self) -> "LinkedInBrowserContext":
        try:
            self.playwright = await async_playwright().start()

            # Args OBLIGATOIRES (testés sur RPi 4)
            self.browser = await self.playwright.chromium.launch(
                headless=self.settings.headless,
                args=[
                    '--disable-gpu',
                    '--disable-dev-shm-usage',           # CRITIQUE : évite /dev/shm
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    '--no-sandbox',
                    '--single-process',                   # CRITIQUE : évite les forks zombies
                    '--disable-setuid-sandbox',
                    '--disable-web-security',             # Pour bloquer ressources
                    '--js-flags=--max-old-space-size=256', # RÉDUIT vs ancien (512)
                    '--no-first-run',
                    '--no-default-browser-check',
                ],
                timeout=self.settings.browser_timeout,
            )

            # Charge les cookies chiffrés
            storage_state = await self.auth_manager.load_auth_state()

            # Crée le contexte avec blocage ressources
            self.context = await self.browser.new_context(
                storage_state=storage_state,
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 Chrome/120.0.0.0',
                locale='fr-FR',
                timezone_id='Europe/Paris',
            )

            # CRITIQUE : Bloque images/fonts/videos pour économiser RAM
            await self.context.route(
                "**/*",
                lambda route: route.abort() if route.request.resource_type in ["image", "font", "media", "stylesheet"] else route.continue_()
            )

            return self

        except Exception as e:
            logger.error(f"Erreur initialisation browser : {e}")
            # Ensure cleanup if initialization fails partly
            if self.browser or self.playwright:
                 await self.__aexit__(type(e), e, None)
            raise e

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            # 1. Ferme toutes les pages d'abord
            if self.context:
                for page in self.context.pages:
                    try:
                        await page.close()
                    except Exception as e:
                        logger.warning(f"Erreur fermeture page: {e}")

            # 2. Ferme le contexte
            if self.context:
                try:
                    await self.context.close()
                except Exception as e:
                    logger.warning(f"Erreur fermeture contexte: {e}")

            # 3. Ferme le browser
            if self.browser:
                try:
                    await self.browser.close()
                except Exception as e:
                    logger.warning(f"Erreur fermeture browser: {e}")

            # 4. Stop Playwright
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception as e:
                    logger.warning(f"Erreur stop playwright: {e}")

            # 5. Attends que tout soit bien fermé
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Erreur fermeture browser : {e}")
        finally:
            # Force cleanup
            self.context = None
            self.browser = None
            self.playwright = None
            logger.info("✓ Browser context fermé proprement")

    async def take_screenshot(self, page: Page, name: str) -> Path:
        # Crée le dossier data/screenshots/ si inexistant
        screenshot_dir = Path("data/screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Nom du fichier : f"{datetime.now():%Y%m%d_%H%M%S}_{name}.png"
        filename = f"{datetime.now():%Y%m%d_%H%M%S}_{name}.png"
        filepath = screenshot_dir / filename

        # Sauvegarde avec page.screenshot(path=...)
        await page.screenshot(path=str(filepath))
        # Log : "📸 Screenshot : {filename}"
        logger.info(f"📸 Screenshot : {filename}")

        return filepath

    async def new_page(self) -> Page:
        if not self.context:
            raise RuntimeError("Browser context not initialized")

        # Crée une nouvelle page
        page = await self.context.new_page()
        # Configure timeout par défaut (30s)
        page.set_default_timeout(30000)

        return page
