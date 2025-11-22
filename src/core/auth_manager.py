"""
Gestionnaire d'authentification LinkedIn.

Ce module gère le chargement, la validation et la persistance de l'état
d'authentification LinkedIn depuis différentes sources.
"""

import os
import json
import base64
import logging
from typing import Optional
from pathlib import Path

from ..config.config_manager import get_config
from ..config.config_schema import AuthConfig
from ..utils.exceptions import (
    AuthenticationError,
    InvalidAuthStateError
)

logger = logging.getLogger(__name__)


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
                logger.warning(f"Failed to write auth from env: {e}")

        # 2. Essayer depuis le fichier principal
        auth_file = Path(self.config.auth_file_path)
        if auth_file.exists():
            if self._validate_auth_file(auth_file):
                logger.info(f"Using auth state from: {auth_file}")
                return str(auth_file)
            else:
                logger.warning(f"Invalid auth state in: {auth_file}")

        # 3. Essayer depuis le fichier de secours
        if self.config.auth_fallback_path:
            fallback_file = Path(self.config.auth_fallback_path)
            if fallback_file.exists():
                if self._validate_auth_file(fallback_file):
                    logger.info(f"Using fallback auth state from: {fallback_file}")
                    return str(fallback_file)
                else:
                    logger.warning(f"Invalid fallback auth state in: {fallback_file}")

        # Aucune source valide trouvée
        raise InvalidAuthStateError(
            "No valid auth state found. Please set LINKEDIN_AUTH_STATE "
            "environment variable or create auth_state.json"
        )

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
            logger.info(f"Loaded auth state from env var (JSON format)")
            return auth_data
        except json.JSONDecodeError:
            pass

        # Essayer Base64
        try:
            # Ajouter le padding manquant si nécessaire
            padding = '=' * (-len(auth_state_str) % 4)
            auth_state_padded = auth_state_str + padding

            # Décoder
            auth_state_bytes = base64.b64decode(auth_state_padded)

            # Parser JSON
            auth_data = json.loads(auth_state_bytes.decode('utf-8'))
            logger.info(f"Loaded auth state from env var (Base64 format)")
            return auth_data

        except (base64.binascii.Error, TypeError, json.JSONDecodeError) as e:
            logger.error(f"Failed to decode auth state from env var: {e}")
            return None

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

            # Écrire le fichier
            with open(auth_file, 'w', encoding='utf-8') as f:
                json.dump(auth_data, f, indent=2)

            self._temp_auth_file = auth_file
            logger.info(f"Auth state written to: {auth_file}")
            return str(auth_file)

        except Exception as e:
            logger.error(f"Failed to write auth state to file: {e}")
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
        """
        try:
            with open(auth_file, 'r', encoding='utf-8') as f:
                auth_data = json.load(f)

            # Vérifier la structure minimale
            if not isinstance(auth_data, dict):
                logger.warning(f"Auth state is not a dict: {type(auth_data)}")
                return False

            if 'cookies' not in auth_data:
                logger.warning("Auth state missing 'cookies' field")
                return False

            if not isinstance(auth_data['cookies'], list):
                logger.warning("Auth state 'cookies' is not a list")
                return False

            if len(auth_data['cookies']) == 0:
                logger.warning("Auth state has no cookies")
                return False

            # Vérifier qu'il y a au moins un cookie LinkedIn
            linkedin_cookies = [
                c for c in auth_data['cookies']
                if 'linkedin.com' in c.get('domain', '')
            ]

            if not linkedin_cookies:
                logger.warning("Auth state has no LinkedIn cookies")
                return False

            logger.debug(f"Auth state validated: {len(linkedin_cookies)} LinkedIn cookies")
            return True

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in auth file: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to validate auth file: {e}")
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
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(auth_data, f, indent=2)

            logger.info(f"New auth state saved to: {output_path}")

        except Exception as e:
            logger.error(f"Failed to save auth state: {e}")
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
                logger.warning(f"Failed to cleanup auth file: {e}")

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
            String décrivant la source ("env", "file", "fallback") ou None

        Exemples:
            >>> auth_mgr = AuthManager()
            >>> source = auth_mgr.get_auth_source()
            >>> print(f"Using auth from: {source}")
        """
        # Vérifier env var
        if self._load_from_env():
            return "env"

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
        return (
            f"<AuthManager(source={source}, available={available})>"
        )


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
