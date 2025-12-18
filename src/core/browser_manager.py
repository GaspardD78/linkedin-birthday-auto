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

            # Arguments de lancement (optimisé pour Raspberry Pi 4)
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--mute-audio",

                # 🚀 OPTIMISATIONS RASPBERRY PI 4 (MEMORY-SAFE)
                # Removed --single-process (causes instability and crashes)
                # Using multi-process with limits instead for better stability
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-sync",
                "--disable-translate",
                "--disable-plugins",
                "--disable-default-apps",
                "--no-first-run",
                # ✅ RETIRÉ: --memory-pressure-off (causait OOM après 30min)
                "--renderer-process-limit=2",  # Increased from 1 to 2 for better stability
                "--max-old-space-size=512",  # ✅ Réduit de 1024MB à 512MB (RPi4 safe)
                "--disable-features=AudioServiceOutOfProcess",  # Prevent audio process spawn
                "--disable-background-timer-throttling",  # Prevent tab suspension issues
                "--disable-backgrounding-occluded-windows",
                "--disable-breakpad",  # Disable crash reporter (saves memory)
                "--disable-component-extensions-with-background-pages",
                "--js-flags=--max-old-space-size=512",  # ✅ Cohérent avec ci-dessus
                # ✅ AJOUT: Forcer garbage collection agressif
                "--js-flags=--expose-gc",
                "--enable-aggressive-domstorage-flushing"
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
                timeout=120000, # Increased launch timeout to 120s for Pi4 stability
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
                    # Load and sanitize auth state
                    with open(auth_state_path, "r") as f:
                        auth_state = json.load(f)

                    # Sanitize cookies to ensure sameSite compatibility
                    if "cookies" in auth_state and isinstance(auth_state["cookies"], list):
                        from ..core.auth_manager import sanitize_cookies
                        auth_state["cookies"] = sanitize_cookies(auth_state["cookies"])
                        logger.debug(f"Sanitized {len(auth_state['cookies'])} cookies for Playwright compatibility")

                    # Pass sanitized auth state as a dict instead of file path
                    context_options["storage_state"] = auth_state
                    logger.info(f"Loaded and sanitized auth state from: {auth_state_path}")
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
            # Increased default timeouts for Pi4 stability
            timeout = getattr(self.config, "timeout", 120000)  # Increased from 60s to 120s
            self.page.set_default_timeout(timeout)
            self.page.set_default_navigation_timeout(timeout)
            logger.debug(f"Page timeouts set to {timeout}ms")

            logger.info("Browser session created successfully")
            return self.browser, self.context, self.page

        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}", exc_info=True)
            self.close()
            raise BrowserInitError(f"Failed to initialize browser: {e}")

    def close(self) -> None:
        """
        Ferme TOUTES les ressources du navigateur avec garantie de nettoyage.

        Ordre important pour éviter les fuites mémoire :
        1. Pages individuelles (with hard timeout)
        2. Contexte browser
        3. Browser process (with SIGKILL fallback)
        4. Playwright

        Note: Utilise SIGKILL comme dernier recours si timeout dépassé.
        """
        import signal
        import time
        import subprocess
        import threading

        logger.info("Closing browser resources...")
        errors = []

        def force_close_with_timeout(close_fn, resource_name: str, timeout_sec: int = 5):
            """Exécute close_fn avec timeout. Si timeout, retourne False."""
            result = {"success": False, "error": None}

            def target():
                try:
                    close_fn()
                    result["success"] = True
                except Exception as e:
                    result["error"] = str(e)

            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            thread.join(timeout=timeout_sec)

            if thread.is_alive():
                logger.warning(f"{resource_name} close timed out after {timeout_sec}s")
                return False

            if result["error"] and "has been closed" not in result["error"]:
                errors.append(f"{resource_name}: {result['error']}")

            return result["success"]

        # Étape 1: Fermer toutes les pages (timeout 3s par page)
        if self.context:
            try:
                pages = self.context.pages
                for i, page in enumerate(pages):
                    logger.debug(f"Closing page {i+1}/{len(pages)}...")
                    force_close_with_timeout(page.close, f"Page {i+1}", timeout_sec=3)
            except Exception as e:
                errors.append(f"Pages enumeration: {e}")

        # Étape 2: Fermer le contexte (timeout 5s)
        if self.context:
            force_close_with_timeout(self.context.close, "Context", timeout_sec=5)
            self.context = None

        # Étape 3: Fermer le browser (timeout 5s, puis SIGKILL)
        if self.browser:
            success = force_close_with_timeout(self.browser.close, "Browser", timeout_sec=5)

            if not success:
                # ✅ Dernier recours : SIGKILL du process Chromium
                logger.warning("Browser did not close gracefully. Attempting SIGKILL...")
                try:
                    # Trouver tous les process chromium
                    result = subprocess.run(
                        ["pgrep", "-f", "chromium"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )

                    if result.returncode == 0:
                        pids = result.stdout.strip().split("\n")
                        for pid in pids:
                            if pid:
                                try:
                                    os.kill(int(pid), signal.SIGKILL)
                                    logger.info(f"Killed chromium process PID {pid}")
                                except ProcessLookupError:
                                    pass  # Already dead
                                except Exception as e:
                                    logger.warning(f"Failed to kill PID {pid}: {e}")
                except Exception as e:
                    logger.error(f"Failed to SIGKILL chromium: {e}")

            self.browser = None

        # Étape 4: Arrêter Playwright (timeout 5s)
        if self.playwright:
            force_close_with_timeout(self.playwright.stop, "Playwright", timeout_sec=5)
            self.playwright = None

        # Logger les erreurs APRÈS le nettoyage complet
        if errors:
            logger.warning(f"Cleanup completed with warnings: {', '.join(errors)}")
        else:
            logger.info("✅ Browser resources closed successfully")

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
