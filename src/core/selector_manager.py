"""
Manager responsible for loading CSS selectors from configuration and implementing
the cascade selection strategy (Anti-Fragile).

This segregates the "HOW" (selectors) from the "WHAT" (bot logic).
"""

import logging
from pathlib import Path
from typing import List, Optional, Union, Any

import yaml
from playwright.sync_api import Page, Locator

logger = logging.getLogger(__name__)


class SelectorManager:
    """
    Manages CSS selectors and implements the cascade finding strategy.
    Loads selectors from a YAML configuration file.
    """

    def __init__(self, config_path: str = "config/selectors.yaml"):
        self.config_path = Path(config_path)
        self.selectors = self._load_selectors()

    def _load_selectors(self) -> dict:
        """Loads selectors from the YAML file."""
        if not self.config_path.exists():
            logger.warning(f"Selector config not found at {self.config_path}. Using empty config.")
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load selectors from {self.config_path}: {e}")
            return {}

    def get_selectors(self, key: str) -> List[str]:
        """
        Retrieves a list of selectors for a given key (dot notation).
        Example: 'login.indicators' -> ['img.photo', '#nav', ...]
        """
        keys = key.split(".")
        value = self.selectors

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                logger.warning(f"Selector key not found: {key}")
                return []

        if isinstance(value, str):
            return [value]
        elif isinstance(value, list):
            return value
        else:
            logger.warning(f"Invalid selector type for {key}: {type(value)}")
            return []

    def find_element(self, parent: Union[Page, Locator], key: str) -> Optional[Locator]:
        """
        Finds an element using the cascade strategy.
        Uses Playwright's combined selector capability (comma-separated) to efficiently
        wait for and find the first matching element among all strategies.

        Args:
            parent: The Playwright Page or Locator to search within.
            key: The dot-notation key for the selectors (e.g., 'messaging.send_button').

        Returns:
            The base Locator matching ANY of the configured selectors.
        """
        selectors = self.get_selectors(key)
        if not selectors:
            logger.warning(f"No selectors defined for key '{key}'")
            return None

        # Combine selectors with comma (OR operator in CSS)
        combined_selector = ", ".join(selectors)

        try:
            # Return the locator for the combined selector.
            # This allows Playwright to wait for ANY of them to appear.
            return parent.locator(combined_selector)
        except Exception as e:
            logger.error(f"Error creating locator for key {key}: {e}")
            return None

    def get_combined_selector(self, key: str) -> str:
        """
        Returns a single comma-separated selector string for the given key.
        Useful for wait_for_selector(combined_selector).
        """
        selectors = self.get_selectors(key)
        if not selectors:
            return ""
        return ", ".join(selectors)

    def find_all(self, parent: Union[Page, Locator], key: str) -> List[Locator]:
        """
        Finds all elements matching the first working selector strategy.
        """
        selectors = self.get_selectors(key)
        for selector in selectors:
            try:
                locator = parent.locator(selector)
                if locator.count() > 0:
                    return locator.all()
            except Exception:
                continue
        return []
