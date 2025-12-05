"""
Gestionnaire d'authentification LinkedIn.

Ce module gère le chargement, la validation et la persistance de l'état
d'authentification LinkedIn depuis différentes sources.
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict

import requests

from ..config.config_manager import get_config
from ..config.config_schema import AuthConfig
from ..utils.exceptions import AuthenticationError, InvalidAuthStateError

logger = logging.getLogger(__name__)


def normalize_same_site(value) -> str:
    """
    Normalizes sameSite cookie attribute to Playwright format.

    Playwright expects exactly one of: "Strict", "Lax", or "None".
    This function handles various formats from different cookie sources.

    Args:
        value: The sameSite value (can be string, None, or other types)

    Returns:
        One of "Strict", "Lax", or "None" (Playwright format)
    """
    if not value or not isinstance(value, str):
        return "Lax"

    # Normalize to lowercase for comparison
    value_lower = value.strip().lower()

    # Map common variations to Playwright format
    if value_lower in ("strict", "Strict"):
        return "Strict"
    elif value_lower in ("lax", "Lax"):
        return "Lax"
    elif value_lower in ("none", "None", "no_restriction", "unspecified"):
        return "None"
    else:
        # Default to Lax for any unrecognized value
        logger.warning(f"Unknown sameSite value '{value}', defaulting to 'Lax'")
        return "Lax"


def sanitize_cookies(cookies: list) -> list:
    """
    Sanitizes a list of cookies to ensure compatibility with Playwright.

    This function normalizes the sameSite attribute to one of the values
    expected by Playwright: "Strict", "Lax", or "None".

    Args:
        cookies: List of cookie dictionaries

    Returns:
        List of sanitized cookies
    """
    sanitized = []
    for cookie in cookies:
        # Make a copy to avoid modifying the original
        cookie_copy = cookie.copy()

        # Normalize sameSite value
        if "sameSite" in cookie_copy:
            cookie_copy["sameSite"] = normalize_same_site(cookie_copy["sameSite"])
        else:
            # Add default sameSite if missing
            cookie_copy["sameSite"] = "Lax"

        sanitized.append(cookie_copy)

    return sanitized


class AuthManager:
    """
    Gestionnaire d'authentification LinkedIn.

    Gère le chargement de l'auth state depuis plusieurs sources avec fallback :
    1. Variable d'environnement (GitHub Secrets)
    2. Fichier auth_state.json
    3. Fichier de secours (fallback)

    Supporte les formats :
    - JSON brut
    - Base64 encodé

    Exemples d'utilisation :
        >>> auth_mgr = AuthManager()
        >>> auth_path = auth_mgr.prepare_auth_state()
        >>> # ... utiliser auth_path avec BrowserManager
        >>> auth_mgr.cleanup()
    """

    def __init__(self, config: Optional[AuthConfig] = None):
        """
        Initialise le gestionnaire d'authentification.

        Args:
            config: Configuration auth (ou None pour config par défaut)
        """
        self.config = config or get_config().auth
        self._temp_auth_file: Optional[Path] = None
        logger.info("AuthManager initialized")

    def prepare_auth_state(self) -> str:
        """
        Prépare l'état d'authentification.

        Charge l'auth state depuis la première source disponible et
        le sauvegarde dans un fichier temporaire si nécessaire.

        Returns:
            Chemin vers le fichier auth_state.json

        Raises:
            InvalidAuthStateError: Si aucun auth state valide n'est trouvé
            AuthenticationError: Si le chargement échoue

        Exemples:
            >>> auth_mgr = AuthManager()
            >>> auth_path = auth_mgr.prepare_auth_state()
            >>> # auth_path peut être utilisé avec BrowserManager
        """
        # 1. Essayer depuis la variable d'environnement
        auth_from_env = self._load_from_env()
        if auth_from_env:
            try:
                return self._write_auth_to_file(auth_from_env)
            except Exception as e:
                logger.warning(f"Failed to write auth from env: {e}", exc_info=True)

        # 2. Essayer depuis le répertoire data writable (prioritaire pour les fichiers uploadés)
        writable_auth_file = Path("/app/data/auth_state.json")
        if writable_auth_file.exists():
            if self._validate_auth_file(writable_auth_file):
                logger.info(f"Using auth state from writable data dir: {writable_auth_file}")
                # Nettoyage automatique des cookies expirés
                self._clean_auth_file_in_place(writable_auth_file)
                return str(writable_auth_file)
            else:
                logger.warning(f"Invalid auth state in: {writable_auth_file}")

        # 3. Essayer depuis le fichier principal
        auth_file = Path(self.config.auth_file_path)
        if auth_file.exists():
            if self._validate_auth_file(auth_file):
                logger.info(f"Using auth state from: {auth_file}")
                # Nettoyage automatique des cookies expirés
                self._clean_auth_file_in_place(auth_file)
                return str(auth_file)
            else:
                logger.warning(f"Invalid auth state in: {auth_file}")

        # 4. Essayer depuis le fichier de secours
        if self.config.auth_fallback_path:
            fallback_file = Path(self.config.auth_fallback_path)
            if fallback_file.exists():
                if self._validate_auth_file(fallback_file):
                    logger.info(f"Using fallback auth state from: {fallback_file}")
                    # Nettoyage automatique des cookies expirés
                    self._clean_auth_file_in_place(fallback_file)
                    return str(fallback_file)
                else:
                    logger.warning(f"Invalid fallback auth state in: {fallback_file}")

        # Aucune source valide trouvée
        raise InvalidAuthStateError(
            "No valid auth state found. Please set LINKEDIN_AUTH_STATE "
            "environment variable or create auth_state.json"
        )

    def validate_session_network(self) -> bool:
        """
        Validates the current session by pinging LinkedIn with the stored cookies.
        Uses lightweight 'requests' instead of spinning up a browser.

        Returns:
            True if the session is valid (authenticated), False otherwise.
        """
        try:
            # Load the current auth state (don't prepare/write, just load into memory)
            auth_data = None

            # Try writable path first
            writable_auth_file = Path("/app/data/auth_state.json")
            if writable_auth_file.exists() and self._validate_auth_file(writable_auth_file):
                with open(writable_auth_file, encoding="utf-8") as f:
                    auth_data = json.load(f)
            else:
                # Try config path
                auth_file = Path(self.config.auth_file_path)
                if auth_file.exists() and self._validate_auth_file(auth_file):
                    with open(auth_file, encoding="utf-8") as f:
                        auth_data = json.load(f)

            if not auth_data:
                logger.warning("No auth data found for network validation.")
                return False

            # Extract cookies for requests
            cookies = {}
            for cookie in auth_data.get("cookies", []):
                # Only include cookies relevant for linkedin.com
                if "linkedin.com" in cookie.get("domain", ""):
                    cookies[cookie["name"]] = cookie["value"]

            # Li_at is the most critical cookie
            if "li_at" not in cookies:
                logger.warning("Missing critical 'li_at' cookie.")
                return False

            # Perform the ping
            # Using a lightweight endpoint that requires auth but is fast
            url = "https://www.linkedin.com/feed/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            }

            logger.info("Pinging LinkedIn to validate session...")
            response = requests.get(url, cookies=cookies, headers=headers, timeout=10, allow_redirects=False)

            # Analysis of response:
            # 200 OK -> Valid
            # 302/303 Redirect -> Likely to login page (Invalid) or maybe to feed?
            # Usually if unauthenticated, it redirects to /login or /checkpoint

            if response.status_code == 200:
                logger.info("Session network validation: SUCCESS (200 OK)")
                return True
            elif response.status_code in (302, 303, 307):
                location = response.headers.get("Location", "")
                if "login" in location or "checkpoint" in location or "auth" in location:
                    logger.warning(f"Session network validation: FAILED (Redirect to {location})")
                    return False
                else:
                    # Redirect to somewhere else (e.g. /feed/) might be fine?
                    # But usually /feed/ returns 200 if logged in.
                    logger.warning(f"Session network validation: AMBIGUOUS (Redirect to {location})")
                    # Assume false to be safe, or check if it redirects back to feed
                    return False
            else:
                logger.warning(f"Session network validation: FAILED (Status {response.status_code})")
                return False

        except Exception as e:
            logger.error(f"Network validation error: {e}", exc_info=True)
            return False

    def _load_from_env(self) -> Optional[dict]:
        """
        Charge l'auth state depuis la variable d'environnement.

        Returns:
            Dict contenant l'auth state ou None si non trouvé

        Format supportés :
            - JSON brut : {"cookies": [...], ...}
            - Base64 encodé : encodage base64 d'un JSON
        """
        env_var = self.config.auth_state_env_var
        auth_state_str = os.getenv(env_var)

        if not auth_state_str or not auth_state_str.strip():
            logger.debug(f"No auth state in env var: {env_var}")
            return None

        # Essayer JSON brut d'abord
        try:
            auth_data = json.loads(auth_state_str)
            logger.info("Loaded auth state from env var (JSON format)")
            return auth_data
        except json.JSONDecodeError:
            pass

        # Essayer Base64
        try:
            # Ajouter le padding manquant si nécessaire
            padding = "=" * (-len(auth_state_str) % 4)
            auth_state_padded = auth_state_str + padding

            # Décoder
            auth_state_bytes = base64.b64decode(auth_state_padded)

            # Parser JSON
            auth_data = json.loads(auth_state_bytes.decode("utf-8"))
            logger.info("Loaded auth state from env var (Base64 format)")
            return auth_data

        except (base64.binascii.Error, TypeError, json.JSONDecodeError) as e:
            logger.error(f"Failed to decode auth state from env var: {e}")
            return None

    def _clean_expired_cookies(self, auth_data: dict) -> dict:
        """
        Nettoie les cookies expirés d'un auth state et sanitize les cookies valides.

        Args:
            auth_data: Données d'authentification avec cookies

        Returns:
            Nouveau dict avec seulement les cookies valides et sanitisés

        Note:
            Les cookies expirés peuvent causer des problèmes d'authentification.
            Cette méthode les filtre et sanitize les cookies pour garantir une session propre.
        """
        if "cookies" not in auth_data or not isinstance(auth_data["cookies"], list):
            return auth_data

        import time

        current_time = time.time()
        original_count = len(auth_data["cookies"])

        # Filtrer les cookies expirés
        valid_cookies = []
        expired_count = 0

        for cookie in auth_data["cookies"]:
            expires = cookie.get("expires")

            # Garder les cookies:
            # - Sans date d'expiration (cookies de session)
            # - Avec expires=-1 (cookies permanents)
            # - Avec date d'expiration dans le futur (+ buffer de 5 min pour clock skew)
            if expires is None or expires == -1 or expires > (current_time - 300):
                valid_cookies.append(cookie)
            else:
                expired_count += 1
                logger.debug(f"Removing expired cookie: {cookie.get('name', 'unknown')}")

        if expired_count > 0:
            logger.info(
                f"Cleaned {expired_count} expired cookies "
                f"({len(valid_cookies)}/{original_count} cookies remaining)"
            )

        # Sanitize cookies to ensure sameSite compatibility
        sanitized_cookies = sanitize_cookies(valid_cookies)

        # Créer un nouveau dict avec les cookies nettoyés et sanitisés
        cleaned_data = auth_data.copy()
        cleaned_data["cookies"] = sanitized_cookies

        return cleaned_data

    def _clean_auth_file_in_place(self, auth_file: Path) -> None:
        """
        Nettoie les cookies expirés d'un fichier auth state existant.

        Args:
            auth_file: Chemin vers le fichier à nettoyer

        Note:
            Modifie le fichier en place si des cookies expirés sont trouvés.
        """
        try:
            # Lire le fichier
            with open(auth_file, encoding="utf-8") as f:
                auth_data = json.load(f)

            # Nettoyer les cookies expirés
            cleaned_data = self._clean_expired_cookies(auth_data)

            # Réécrire seulement si des changements ont été faits
            if len(cleaned_data.get("cookies", [])) < len(auth_data.get("cookies", [])):
                with open(auth_file, "w", encoding="utf-8") as f:
                    json.dump(cleaned_data, f, indent=2)
                logger.info(f"Auth file cleaned in place: {auth_file}")

        except Exception as e:
            logger.warning(f"Failed to clean auth file in place: {e}", exc_info=True)

    def _write_auth_to_file(self, auth_data: dict) -> str:
        """
        Écrit l'auth state dans un fichier temporaire.

        Args:
            auth_data: Données d'authentification (dict)

        Returns:
            Chemin vers le fichier créé

        Raises:
            AuthenticationError: Si l'écriture échoue
        """
        try:
            auth_file = Path(self.config.auth_file_path)

            # Nettoyage automatique des cookies expirés avant sauvegarde
            cleaned_auth_data = self._clean_expired_cookies(auth_data)

            # Écrire le fichier
            with open(auth_file, "w", encoding="utf-8") as f:
                json.dump(cleaned_auth_data, f, indent=2)

            self._temp_auth_file = auth_file
            logger.info(f"Auth state written to: {auth_file}")
            return str(auth_file)

        except Exception as e:
            logger.error(f"Failed to write auth state to file: {e}", exc_info=True)
            raise AuthenticationError(f"Failed to write auth state: {e}")

    def _validate_auth_file(self, auth_file: Path) -> bool:
        """
        Valide un fichier auth state.

        Args:
            auth_file: Chemin vers le fichier à valider

        Returns:
            True si valide, False sinon

        Un auth state valide doit contenir au minimum :
        - Un tableau "cookies" non vide
        - Des propriétés "origins" (optionnel mais recommandé)
        - Des cookies non expirés (ou sans date d'expiration)
        """
        try:
            with open(auth_file, encoding="utf-8") as f:
                auth_data = json.load(f)

            # Vérifier la structure minimale
            if not isinstance(auth_data, dict):
                logger.warning(f"Auth state is not a dict: {type(auth_data)}")
                return False

            if "cookies" not in auth_data:
                logger.warning("Auth state missing 'cookies' field")
                return False

            if not isinstance(auth_data["cookies"], list):
                logger.warning("Auth state 'cookies' is not a list")
                return False

            if len(auth_data["cookies"]) == 0:
                logger.warning("Auth state has no cookies")
                return False

            # Vérifier qu'il y a au moins un cookie LinkedIn
            linkedin_cookies = [
                c for c in auth_data["cookies"] if "linkedin.com" in c.get("domain", "")
            ]

            if not linkedin_cookies:
                logger.warning("Auth state has no LinkedIn cookies")
                return False

            # Vérifier l'expiration des cookies pour validation
            import time

            current_time = time.time()
            expired_count = 0
            valid_count = 0

            for cookie in linkedin_cookies:
                expires = cookie.get("expires")
                if expires is not None and expires != -1:
                    # Cookie a une date d'expiration
                    if expires < current_time:
                        expired_count += 1
                        logger.debug(f"Expired cookie: {cookie.get('name', 'unknown')}")
                    else:
                        valid_count += 1
                else:
                    # Cookie de session (pas d'expiration) - considéré valide
                    valid_count += 1

            if valid_count == 0:
                logger.warning(f"All LinkedIn cookies are expired ({expired_count} expired)")
                return False

            if expired_count > 0:
                logger.warning(
                    f"Some cookies expired ({expired_count}/{len(linkedin_cookies)}), but {valid_count} still valid"
                )

            logger.debug(
                f"Auth state validated: {valid_count} valid LinkedIn cookies (={expired_count} expired)"
            )
            return True

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in auth file: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to validate auth file: {e}", exc_info=True)
            return False

    def save_new_auth_state(self, auth_data: dict, output_path: Optional[str] = None) -> None:
        """
        Sauvegarde un nouvel état d'authentification.

        Args:
            auth_data: Données d'authentification à sauvegarder
            output_path: Chemin de destination (ou None pour fichier par défaut)

        Raises:
            AuthenticationError: Si la sauvegarde échoue
        """
        if output_path is None:
            output_path = self.config.auth_file_path

        try:
            # Nettoyer les cookies expirés avant sauvegarde
            cleaned_auth_data = self._clean_expired_cookies(auth_data)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(cleaned_auth_data, f, indent=2)

            # SECURITY: Set restrictive permissions (600) on auth file
            try:
                os.chmod(output_path, 0o600)
            except Exception as e:
                logger.warning(f"Failed to set 0600 permissions on {output_path}: {e}", exc_info=True)

            logger.info(f"New auth state saved to: {output_path}")

        except Exception as e:
            logger.error(f"Failed to save auth state: {e}", exc_info=True)
            raise AuthenticationError(f"Failed to save auth state: {e}")

    def cleanup(self, keep_file: bool = False) -> None:
        """
        Nettoie les fichiers temporaires d'authentification.

        Args:
            keep_file: Si True, garde le fichier temporaire

        Note:
            Pour la sécurité, il est recommandé de supprimer les fichiers
            auth temporaires après utilisation (sauf si vous voulez les
            réutiliser dans la même session).
        """
        if self._temp_auth_file and self._temp_auth_file.exists() and not keep_file:
            try:
                self._temp_auth_file.unlink()
                logger.info(f"Cleaned up temporary auth file: {self._temp_auth_file}")
                self._temp_auth_file = None
            except Exception as e:
                logger.warning(f"Failed to cleanup auth file: {e}", exc_info=True)

    def is_auth_available(self) -> bool:
        """
        Vérifie si un auth state est disponible.

        Returns:
            True si au moins une source d'auth est disponible

        Exemples:
            >>> auth_mgr = AuthManager()
            >>> if auth_mgr.is_auth_available():
            >>>     print("Authentication ready")
        """
        # Vérifier env var
        if self._load_from_env():
            return True

        # Vérifier répertoire data writable
        writable_auth_file = Path("/app/data/auth_state.json")
        if writable_auth_file.exists() and self._validate_auth_file(writable_auth_file):
            return True

        # Vérifier fichier principal
        auth_file = Path(self.config.auth_file_path)
        if auth_file.exists() and self._validate_auth_file(auth_file):
            return True

        # Vérifier fallback
        if self.config.auth_fallback_path:
            fallback_file = Path(self.config.auth_fallback_path)
            if fallback_file.exists() and self._validate_auth_file(fallback_file):
                return True

        return False

    def get_auth_source(self) -> Optional[str]:
        """
        Retourne la source d'authentification active.

        Returns:
            String décrivant la source ("env", "data", "file", "fallback") ou None

        Exemples:
            >>> auth_mgr = AuthManager()
            >>> source = auth_mgr.get_auth_source()
            >>> print(f"Using auth from: {source}")
        """
        # Vérifier env var
        if self._load_from_env():
            return "env"

        # Vérifier répertoire data writable
        writable_auth_file = Path("/app/data/auth_state.json")
        if writable_auth_file.exists() and self._validate_auth_file(writable_auth_file):
            return "data"

        # Vérifier fichier principal
        auth_file = Path(self.config.auth_file_path)
        if auth_file.exists() and self._validate_auth_file(auth_file):
            return "file"

        # Vérifier fallback
        if self.config.auth_fallback_path:
            fallback_file = Path(self.config.auth_fallback_path)
            if fallback_file.exists() and self._validate_auth_file(fallback_file):
                return "fallback"

        return None

    def __enter__(self):
        """Context manager entry."""
        self.prepare_auth_state()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()

    def __repr__(self) -> str:
        """Représentation string du manager."""
        source = self.get_auth_source()
        available = self.is_auth_available()
        return f"<AuthManager(source={source}, available={available})>"

    def save_cookies(self, cookies: list, output_path: Optional[str] = None):
        """
        Saves a list of cookies to the auth file.

        Args:
            cookies: A list of cookie dictionaries.
            output_path: The file path to save to. Defaults to the configured path.

        Note:
            Cookies are sanitized and expired cookies are automatically cleaned before saving.
        """
        if output_path is None:
            output_path = self.config.auth_file_path

        # Sanitize cookies to ensure sameSite compatibility
        sanitized_cookies = sanitize_cookies(cookies)
        auth_data = {"cookies": sanitized_cookies}
        # save_new_auth_state() appellera _clean_expired_cookies() automatiquement
        self.save_new_auth_state(auth_data, output_path)

    async def save_cookies_from_context(self, context, output_path: Optional[str] = None):
        """
        Extracts cookies from a Playwright context and saves them.

        Args:
            context: The Playwright BrowserContext.
            output_path: The file path to save to.

        Note:
            Cookies are automatically sanitized to ensure sameSite compatibility.
        """
        if not context:
            raise ValueError("Playwright context cannot be None.")

        logger.info("Extracting cookies from browser context...")
        cookies = await context.cookies()
        # save_cookies() will sanitize the cookies
        self.save_cookies(cookies, output_path)
        logger.info(f"Successfully saved {len(cookies)} cookies.")


# Fonctions helper pour accès rapide


def get_auth_path() -> str:
    """
    Fonction helper pour obtenir rapidement le chemin auth.

    Returns:
        Chemin vers auth_state.json

    Raises:
        InvalidAuthStateError: Si aucun auth state valide

    Exemples:
        >>> from src.core.auth_manager import get_auth_path
        >>> auth_path = get_auth_path()
        >>> # Utiliser auth_path avec BrowserManager
    """
    auth_mgr = AuthManager()
    return auth_mgr.prepare_auth_state()


def validate_auth() -> bool:
    """
    Fonction helper pour valider l'authentification.

    Returns:
        True si au moins une source d'auth valide existe

    Exemples:
        >>> from src.core.auth_manager import validate_auth
        >>> if not validate_auth():
        >>>     print("ERROR: No valid authentication found!")
    """
    auth_mgr = AuthManager()
    return auth_mgr.is_auth_available()
