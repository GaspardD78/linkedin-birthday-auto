"""
Gestionnaire de navigateur Playwright.

Ce module encapsule la logique de gestion du cycle de vie du navigateur
(lancement, contexte, fermeture) et les configurations spécifiques
(proxy, user-agent, viewport).
"""

import json
import logging
import random
from typing import Optional, Tuple, Dict, Any

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright

from ..config.config_schema import BrowserConfig
from ..utils.exceptions import BrowserInitError

logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Gère le cycle de vie du navigateur Playwright.

    Responsabilités :
    - Initialisation du navigateur (Chromium)
    - Configuration du contexte (User-Agent, Viewport, Locale, Timezone)
    - Gestion de l'état d'authentification (cookies)
    - Nettoyage des ressources

    Exemples:
        >>> config = BrowserConfig()
        >>> manager = BrowserManager(config)
        >>> browser, context, page = manager.create_browser("auth.json")
        >>> # ... actions ...
        >>> manager.close()
    """

    def __init__(self, config: BrowserConfig):
        """
        Initialise le gestionnaire.

        Args:
            config: Configuration du navigateur
        """
        self.config = config
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        logger.info("BrowserManager initialized")

    def create_browser(
        self,
        auth_state_path: Optional[str] = None,
        proxy_config: Optional[Dict[str, str]] = None,
    ) -> Tuple[Browser, BrowserContext, Page]:
        """
        Crée une nouvelle instance de navigateur complète.

        Args:
            auth_state_path: Chemin vers le fichier d'état d'authentification (optionnel)
            proxy_config: Configuration du proxy (optionnel)

        Returns:
            Tuple (Browser, BrowserContext, Page)

        Raises:
            BrowserInitError: Si l'initialisation échoue
        """
        try:
            logger.info("Starting Playwright...")
            self.playwright = sync_playwright().start()

            # Arguments de lancement
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",  # Often needed for Pi4
                "--disable-software-rasterizer",
                "--mute-audio",
            ]

            # Custom args from config
            if self.config.args:
                launch_args.extend(self.config.args)

            logger.info(f"Launching browser (headless={self.config.headless})...")

            # Gestion du slow_mo aléatoire (Option B)
            slow_mo = self.config.slow_mo
            if isinstance(slow_mo, (tuple, list)) and len(slow_mo) == 2:
                slow_mo = random.randint(slow_mo[0], slow_mo[1])
                logger.debug(f"Randomized slow_mo: {slow_mo}ms")

            self.browser = self.playwright.chromium.launch(
                headless=self.config.headless,
                args=launch_args,
                slow_mo=slow_mo,
                timeout=60000, # Increased launch timeout
                proxy=proxy_config,
            )

            # Configuration du contexte
            context_options = self._get_context_options()

            # LOCALE-LOCK: Force English (US)
            context_options["locale"] = "en-US"
            context_options["timezone_id"] = "UTC" # Or Europe/Paris, but UTC matches standardized logs

            # Load auth state if provided
            if auth_state_path:
                try:
                    # Validate JSON first
                    with open(auth_state_path, "r") as f:
                        json.load(f)
                    context_options["storage_state"] = auth_state_path
                    logger.info(f"Loaded auth state from: {auth_state_path}")
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    logger.warning(f"Could not load auth state (starting fresh): {e}")

            logger.info("Creating browser context...")
            self.context = self.browser.new_context(**context_options)

            # Création de la page
            self.page = self.context.new_page()

            # Scripts anti-détection (Applied AFTER page creation)
            self._apply_stealth_scripts(self.page)

            # Timeout par défaut pour la page (HARDWARE REALISM)
            # Fix: Use constant or safe access as 'timeout' is not in BrowserConfig
            timeout = getattr(self.config, "timeout", 60000)
            self.page.set_default_timeout(timeout)
            self.page.set_default_navigation_timeout(timeout)

            logger.info("Browser session created successfully")
            return self.browser, self.context, self.page

        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}", exc_info=True)
            self.close()
            raise BrowserInitError(f"Failed to initialize browser: {e}")

    def close(self) -> None:
        """Ferme toutes les ressources du navigateur."""
        logger.info("Closing browser resources...")
        if self.context:
            try:
                self.context.close()
            except Exception as e:
                logger.debug(f"Error closing context: {e}", exc_info=True)
            self.context = None

        if self.browser:
            try:
                self.browser.close()
            except Exception as e:
                logger.debug(f"Error closing browser: {e}", exc_info=True)
            self.browser = None

        if self.playwright:
            try:
                self.playwright.stop()
            except Exception as e:
                logger.debug(f"Error stopping playwright: {e}", exc_info=True)
            self.playwright = None

    def take_screenshot(self, name: str) -> None:
        """Prend une capture d'écran de la page active."""
        if not self.page:
            return

        try:
            path = f"/app/logs/{name}"
            self.page.screenshot(path=path)
            logger.info(f"Screenshot saved: {path}")
        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}", exc_info=True)

    def _get_context_options(self) -> Dict[str, Any]:
        """Génère les options du contexte navigateur."""

        # User Agent (Fix: Random selection from list)
        if hasattr(self.config, "user_agent") and self.config.user_agent:
            user_agent = self.config.user_agent
        elif hasattr(self.config, "user_agents") and self.config.user_agents:
            user_agent = random.choice(self.config.user_agents)
        else:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        # Viewport (Fix: Random selection from list)
        viewport = {"width": 1280, "height": 720}

        if hasattr(self.config, "viewport_width") and hasattr(self.config, "viewport_height") and self.config.viewport_width and self.config.viewport_height:
            viewport = {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            }
        elif hasattr(self.config, "viewport_sizes") and self.config.viewport_sizes:
            viewport = random.choice(self.config.viewport_sizes)

        logger.debug(f"Context Config - UA: {user_agent[:50]}... Viewport: {viewport}")

        return {
            "user_agent": user_agent,
            "viewport": viewport,
            "accept_downloads": False,
            "java_script_enabled": True,
            "bypass_csp": True, # Helpful for scraping
        }

    def _apply_stealth_scripts(self, page: Page) -> None:
        """Applique les scripts de dissimulation (stealth)."""
        try:
            # Try to use playwright-stealth if installed
            from playwright_stealth import stealth_sync
            stealth_sync(page)
            logger.debug("Playwright-Stealth applied successfully")
        except ImportError:
            logger.warning("Playwright-Stealth not found, applying basic manual override")

        # Basic manual stealth overrides via init_script
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
