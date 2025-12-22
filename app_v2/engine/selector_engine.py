"""
Moteur de sélection intelligent pour le Bot LinkedIn V2.
Implémente une stratégie robuste de résolution de sélecteurs en 3 étapes :
1. Configuration statique (YAML)
2. Apprentissage (Base de données)
3. Heuristique (Règles génériques)

Ref: Tâche : Crée 'app_v2/engine/selector_engine.py'.
"""

import logging
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Union
from datetime import datetime

from playwright.async_api import Locator, Page, TimeoutError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app_v2.db.models import LinkedInSelector
from app_v2.db.engine import get_session_maker
from app_v2.core.config import Settings

logger = logging.getLogger(__name__)

class SmartSelectorEngine:
    """
    Moteur de sélection d'éléments intelligent utilisant une stratégie hybride
    (Config -> DB -> Heuristique) pour maximiser la résilience face aux changements du DOM.
    """

    def __init__(self, page: Page, settings: Settings, config_path: str = "config/selectors.yaml"):
        """
        Initialise le moteur avec la page Playwright et charge la configuration.

        Args:
            page: Instance de la page Playwright.
            settings: Configuration de l'application (pour la DB).
            config_path: Chemin vers le fichier YAML des sélecteurs.
        """
        self.page = page
        self.settings = settings
        self.config_path = Path(config_path)
        self.selectors = self._load_selectors()
        self.session_maker = get_session_maker(settings)

    def _load_selectors(self) -> dict:
        """Charge les sélecteurs depuis le fichier YAML en mémoire."""
        if not self.config_path.exists():
            logger.warning(f"Selector config not found at {self.config_path}")
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load selectors from {self.config_path}: {e}")
            return {}

    def _resolve_yaml_selectors(self, key: str) -> List[str]:
        """Récupère la liste des sélecteurs YAML pour une clé donnée."""
        keys = key.split(".")
        value = self.selectors
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return []

        if isinstance(value, str):
            return [value]
        elif isinstance(value, list):
            return [v for v in value if isinstance(v, str)]
        return []

    async def get(self, key: str, timeout: int = 2000) -> Optional[Locator]:
        """
        Récupère un Locator pour la clé donnée en suivant la stratégie A -> B -> C.
        """
        # Étape A : Teste le sélecteur du YAML
        yaml_selectors = self._resolve_yaml_selectors(key)
        for selector in yaml_selectors:
            locator = self.page.locator(selector)
            try:
                if await locator.first.is_visible(timeout=timeout):
                    return locator
            except Exception:
                continue

        # Étape B : Requête la DB (Async)
        try:
            async with self.session_maker() as session:
                # element_type correspond à la clé (ex: login.submit)
                stmt = select(LinkedInSelector).where(
                    LinkedInSelector.element_type == key,
                    LinkedInSelector.is_deprecated == False
                ).order_by(LinkedInSelector.score.desc())

                result = await session.execute(stmt)
                db_selectors = result.scalars().all()

                for db_selector in db_selectors:
                    if db_selector.score > 5:
                        selector_value = db_selector.selector
                        # Gestion des sélecteurs spéciaux heuristiques
                        if selector_value.startswith("heuristic:"):
                            locator = self._resolve_heuristic_selector(selector_value)
                        else:
                            locator = self.page.locator(selector_value)

                        if locator:
                            try:
                                if await locator.first.is_visible(timeout=timeout):
                                    # Update score
                                    db_selector.score += 1
                                    db_selector.last_success_at = datetime.now().isoformat()
                                    await session.commit()
                                    return locator
                                else:
                                    # Decrease score
                                    db_selector.score -= 1
                                    db_selector.last_failure_at = datetime.now().isoformat()
                                    await session.commit()
                            except Exception:
                                pass
        except Exception as e:
            logger.warning(f"Error querying DB for selector '{key}': {e}")

        # Étape C : Heuristique
        heuristic_locator, selector_str = await self._apply_heuristics(key)
        if heuristic_locator:
            # Sauvegarde en DB
            await self._learn(key, selector_str)
            return heuristic_locator

        return None

    def _resolve_heuristic_selector(self, value: str) -> Optional[Locator]:
        """Convertit une chaîne heuristique stockée en Locator."""
        if value.startswith("heuristic:role:"):
            # Format: heuristic:role:button:name:Submit
            parts = value.split(":")
            if len(parts) >= 5:
                role = parts[2]
                name = parts[4]
                return self.page.get_by_role(role, name=name)
        elif value.startswith("heuristic:label:"):
            # Format: heuristic:label:Email
            parts = value.split(":")
            if len(parts) >= 3:
                label = parts[2]
                return self.page.get_by_label(label)
        elif value.startswith("heuristic:placeholder:"):
            parts = value.split(":")
            if len(parts) >= 3:
                text = parts[2]
                return self.page.get_by_placeholder(text)
        return None

    async def _apply_heuristics(self, key: str) -> tuple[Optional[Locator], Optional[str]]:
        """
        Applique des règles heuristiques.
        Retourne (Locator, selector_string_for_db).
        """
        parts = key.split(".")
        name = parts[-1].lower()

        strategies = []
        if "button" in name or "btn" in name:
            label_guess = name.replace("_button", "").replace("button_", "").replace("_", " ")
            strategies.append(("role", "button", label_guess))
            if "submit" in name:
                strategies.append(("role", "button", "Envoyer"))
                strategies.append(("role", "button", "Send"))

        if "input" in name or "field" in name:
            label_guess = name.replace("_input", "").replace("input_", "").replace("_", " ")
            strategies.append(("label", label_guess))
            strategies.append(("placeholder", label_guess))

        if "link" in name:
             label_guess = name.replace("_link", "").replace("link_", "").replace("_", " ")
             strategies.append(("role", "link", label_guess))

        for strategy in strategies:
            locator = None
            selector_str = ""

            try:
                if strategy[0] == "role":
                    role = strategy[1]
                    label = strategy[2]
                    locator = self.page.get_by_role(role, name=label)
                    selector_str = f"heuristic:role:{role}:name:{label}"

                elif strategy[0] == "label":
                    label = strategy[1]
                    locator = self.page.get_by_label(label)
                    selector_str = f"heuristic:label:{label}"

                elif strategy[0] == "placeholder":
                    text = strategy[1]
                    locator = self.page.get_by_placeholder(text)
                    selector_str = f"heuristic:placeholder:{text}"

                if locator:
                    if await locator.first.is_visible(timeout=1000):
                        # Tente d'améliorer le sélecteur si possible (ex: ID)
                        try:
                            element_id = await locator.first.get_attribute("id")
                            if element_id:
                                # Si un ID est présent, c'est bien plus robuste
                                return locator, f"#{element_id}"
                        except Exception:
                            pass

                        return locator, selector_str

            except Exception:
                continue

        return None, None

    async def _learn(self, key: str, selector_value: str):
        """Sauvegarde un nouveau sélecteur trouvé en base de données."""
        if not selector_value:
            return

        try:
            async with self.session_maker() as session:
                # Check existance
                stmt = select(LinkedInSelector).where(
                    LinkedInSelector.element_type == key,
                    LinkedInSelector.selector == selector_value
                )
                result = await session.execute(stmt)
                existing = result.scalars().first()

                now_str = datetime.now().isoformat()

                if existing:
                    existing.score += 2  # Bonus for rediscovery
                    existing.last_success_at = now_str
                    existing.is_deprecated = False
                else:
                    new_selector = LinkedInSelector(
                        element_type=key,
                        selector=selector_value,
                        score=10, # Initial confidence
                        last_success_at=now_str,
                        created_at=now_str
                    )
                    session.add(new_selector)

                await session.commit()
                logger.info(f"Learned selector for '{key}': {selector_value}")

        except Exception as e:
            logger.error(f"Failed to learn selector for '{key}': {e}")
