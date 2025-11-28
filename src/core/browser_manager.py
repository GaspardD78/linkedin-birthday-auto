"""
Gestionnaire de navigateur avec factory pattern.

Ce module fournit une interface unifiée pour créer et configurer des
browsers Playwright avec anti-détection et gestion du proxy.
"""

import logging
import random
from typing import Any, Optional

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from ..config.config_manager import get_config
from ..config.config_schema import BrowserConfig
from ..utils.exceptions import BrowserError

logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Factory pour créer et gérer des browsers Playwright.

    Cette classe encapsule la logique de création du browser avec :
    - Anti-détection (User-Agent rotation, viewport randomization)
    - Configuration du proxy
    - Mode stealth (si playwright-stealth disponible)
    - Gestion du contexte et de l'auth state

    Exemples d'utilisation :
        >>> manager = BrowserManager()
        >>> browser, context, page = manager.create_browser()
        >>> # ... utiliser le browser
        >>> manager.close()
    """

    def __init__(self, config: Optional[BrowserConfig] = None):
        """
        Initialise le gestionnaire de navigateur.

        Args:
            config: Configuration du navigateur (ou None pour config par défaut)
        """
        self.config = config or get_config().browser
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Sélectionner des paramètres aléatoires pour anti-détection
        self.user_agent = random.choice(self.config.user_agents)
        self.viewport = random.choice(self.config.viewport_sizes)
        self.slow_mo = random.randint(*self.config.slow_mo)

        logger.info(
            f"BrowserManager initialized "
            f"(headless={self.config.headless}, "
            f"slow_mo={self.slow_mo}ms)"
        )

    def create_browser(
        self, auth_state_path: Optional[str] = None, proxy_config: Optional[dict[str, str]] = None
    ) -> tuple[Browser, BrowserContext, Page]:
        """
        Crée et configure un browser Playwright complet.

        Args:
            auth_state_path: Chemin vers auth_state.json (optionnel)
            proxy_config: Configuration proxy Playwright (optionnel)

        Returns:
            Tuple (Browser, BrowserContext, Page)

        Raises:
            BrowserError: Si la création du browser échoue

        Exemples:
            >>> manager = BrowserManager()
            >>> browser, context, page = manager.create_browser(
            ...     auth_state_path="auth_state.json"
            ... )
        """
        # BUGFIX: Fermer les instances existantes pour éviter les fuites mémoire
        if self.browser or self.context or self.page or self.playwright:
            logger.warning("Browser already exists, closing previous instance")
            self.close()

        try:
            # Lancer Playwright
            self.playwright = sync_playwright().start()

            # Configurer les arguments de lancement
            launch_args = self._get_launch_args()

            # Lancer le browser
            self.browser = self.playwright.chromium.launch(
                headless=self.config.headless, slow_mo=self.slow_mo, args=launch_args
            )

            logger.info(f"Browser launched (user_agent: {self.user_agent[:50]}...)")

            # Créer le contexte
            context_options = self._get_context_options(
                auth_state_path=auth_state_path, proxy_config=proxy_config
            )

            self.context = self.browser.new_context(**context_options)

            # Appliquer le mode stealth si disponible
            self._apply_stealth_mode()

            # Créer une page
            self.page = self.context.new_page()

            logger.info(
                f"Browser context created "
                f"(viewport: {self.viewport['width']}x{self.viewport['height']})"
            )

            return self.browser, self.context, self.page

        except Exception as e:
            logger.error(f"Failed to create browser: {e}")
            self.close()
            raise BrowserError(f"Failed to create browser: {e}")

    def _get_launch_args(self) -> list[str]:
        """
        Construit les arguments de lancement du browser.

        Returns:
            Liste d'arguments pour chromium.launch()
        """
        """Construit les arguments de lancement optimisés pour Pi 4."""
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            f'--window-size={self.viewport["width"]},{self.viewport["height"]}',
        ]

        # Optimisations RAM Spécifiques Pi 4 :
        pi4_args = [
            "--disable-gl-drawing-for-tests",
            "--mute-audio",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-component-extensions-with-background-pages",
        ]
        args.extend(pi4_args)

        return args

    def _get_context_options(
        self, auth_state_path: Optional[str] = None, proxy_config: Optional[dict[str, str]] = None
    ) -> dict[str, Any]:
        """
        Construit les options du contexte browser.

        Args:
            auth_state_path: Chemin vers auth_state.json
            proxy_config: Configuration proxy

        Returns:
            Dict d'options pour browser.new_context()
        """
        options: dict[str, Any] = {
            "user_agent": self.user_agent,
            "viewport": self.viewport,
            "locale": self.config.locale,
            "timezone_id": self.config.timezone,
        }

        # Ajouter l'auth state si fourni
        if auth_state_path:
            options["storage_state"] = auth_state_path

        # Ajouter le proxy si fourni
        if proxy_config:
            options["proxy"] = proxy_config

        return options

    def _apply_stealth_mode(self) -> None:
        """
        Applique le mode stealth au contexte si playwright-stealth est disponible.

        Le mode stealth masque les indicateurs que le browser est automatisé.
        """
        try:
            from playwright_stealth import Stealth

            stealth = Stealth()
            stealth.apply_stealth_sync(self.context)
            logger.info("✅ Stealth mode applied successfully")
        except ImportError:
            logger.warning(
                "⚠️ playwright-stealth not installed, "
                "skipping stealth mode. Install with: pip install playwright-stealth"
            )
        except Exception as e:
            logger.warning(f"Failed to apply stealth mode: {e}")

    def get_page(self) -> Page:
        """
        Retourne la page actuelle.

        Returns:
            Page Playwright

        Raises:
            BrowserError: Si aucune page n'est créée
        """
        if not self.page:
            raise BrowserError("No page created. Call create_browser() first.")
        return self.page

    def navigate_to(self, url: str, timeout: int = 60000) -> None:
        """
        Navigue vers une URL.

        Args:
            url: URL de destination
            timeout: Timeout en millisecondes

        Raises:
            BrowserError: Si la navigation échoue
        """
        if not self.page:
            raise BrowserError("No page created. Call create_browser() first.")

        try:
            self.page.goto(url, timeout=timeout)
            logger.info(f"Navigated to: {url}")
        except Exception as e:
            logger.error(f"Navigation failed to {url}: {e}")
            raise BrowserError(f"Failed to navigate to {url}: {e}")

    def save_auth_state(self, output_path: str) -> None:
        """
        Sauvegarde l'état d'authentification actuel.

        Args:
            output_path: Chemin du fichier de sortie

        Raises:
            BrowserError: Si la sauvegarde échoue
        """
        if not self.context:
            raise BrowserError("No context created. Call create_browser() first.")

        try:
            self.context.storage_state(path=output_path)
            logger.info(f"Auth state saved to: {output_path}")
        except Exception as e:
            logger.error(f"Failed to save auth state: {e}")
            raise BrowserError(f"Failed to save auth state: {e}")

    def take_screenshot(self, path: str, full_page: bool = False, timeout: int = 10000) -> None:
        """
        Prend une capture d'écran (non-bloquant pour le debug).

        Args:
            path: Chemin du fichier de sortie
            full_page: Capturer la page entière ou seulement le viewport
            timeout: Timeout en millisecondes (défaut: 10000ms = 10s)

        Note:
            Les erreurs de screenshot sont loguées mais ne lèvent pas d'exception
            car les screenshots sont principalement utilisés pour le debug.
        """
        if not self.page:
            logger.warning(f"Cannot take screenshot '{path}': No page created")
            return

        try:
            # Petit délai pour stabiliser la page avant screenshot
            self.page.wait_for_timeout(500)
            self.page.screenshot(path=path, full_page=full_page, timeout=timeout)
            logger.debug(f"Screenshot saved to: {path}")
        except Exception as e:
            # Screenshots sont pour debug uniquement - ne pas bloquer l'exécution
            logger.warning(f"Failed to take screenshot '{path}': {e}")

    def close(self) -> None:
        """Ferme proprement le browser et Playwright avec timeout protection."""
        # BUGFIX: Amélioration de la robustesse du nettoyage avec timeout
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Browser cleanup timeout")

        # Set 10 second timeout for cleanup
        if hasattr(signal, "SIGALRM"):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)

        try:
            if self.page:
                try:
                    self.page.close()
                    logger.debug("Page closed")
                except Exception as e:
                    logger.warning(f"Error closing page: {e}")
                finally:
                    self.page = None

            if self.context:
                try:
                    self.context.close()
                    logger.debug("Context closed")
                except Exception as e:
                    logger.warning(f"Error closing context: {e}")
                finally:
                    self.context = None

            if self.browser:
                try:
                    self.browser.close()
                    logger.debug("Browser closed")
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
                finally:
                    self.browser = None

            if self.playwright:
                try:
                    self.playwright.stop()
                    logger.debug("Playwright stopped")
                except Exception as e:
                    logger.warning(f"Error stopping Playwright: {e}")
                finally:
                    self.playwright = None

            logger.info("✅ Browser cleanup completed")

        except TimeoutError:
            logger.error("⚠️ Browser cleanup timeout - forcing cleanup")
            # Force cleanup
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}")
            # Force cleanup même en cas d'erreur
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
        finally:
            # Cancel alarm
            if hasattr(signal, "SIGALRM"):
                signal.alarm(0)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        """Représentation string du manager."""
        return (
            f"<BrowserManager(headless={self.config.headless}, "
            f"viewport={self.viewport['width']}x{self.viewport['height']})>"
        )


def create_browser_with_auth(
    auth_state_path: str, proxy_config: Optional[dict[str, str]] = None
) -> tuple[BrowserManager, Browser, BrowserContext, Page]:
    """
    Fonction helper pour créer rapidement un browser avec authentification.

    Args:
        auth_state_path: Chemin vers auth_state.json
        proxy_config: Configuration proxy (optionnel)

    Returns:
        Tuple (BrowserManager, Browser, BrowserContext, Page)

    Exemples:
        >>> manager, browser, context, page = create_browser_with_auth(
        ...     "auth_state.json"
        ... )
        >>> # ... utiliser le browser
        >>> manager.close()
    """
    manager = BrowserManager()
    browser, context, page = manager.create_browser(
        auth_state_path=auth_state_path, proxy_config=proxy_config
    )
    return manager, browser, context, page
