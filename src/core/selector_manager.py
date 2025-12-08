"""
Manager responsible for loading CSS selectors from configuration and implementing
the cascade selection strategy (Anti-Fragile) and Heuristic Detection.

This segregates the "HOW" (selectors) from the "WHAT" (bot logic).
"""

import logging
from pathlib import Path
from typing import List, Optional, Union, Any, Dict
from difflib import SequenceMatcher

import yaml
from playwright.sync_api import Page, Locator

logger = logging.getLogger(__name__)


class SelectorManager:
    """
    Manages CSS selectors and implements cascade + heuristic finding strategies.
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
                return []

        if isinstance(value, str):
            return [value]
        elif isinstance(value, list):
            return value
        # Handle cases where the key points to a heuristic dict configuration
        elif isinstance(value, dict) and "candidates" in value:
             return []
        else:
            return []

    def get_heuristic_config(self, key: str) -> Optional[Dict]:
        """Retrieves the heuristic configuration for a given key."""
        keys = key.split(".")
        value = self.selectors
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None

        if isinstance(value, dict) and "candidates" in value:
            return value
        return None

    def find_heuristic(self, parent: Union[Page, Locator], key: str) -> Optional[Locator]:
        """
        Finds an element using a probabilistic heuristic approach.
        """
        config = self.get_heuristic_config(key)
        if not config:
            return None

        candidates_selector = config.get("candidates", "button")
        positive_keywords = config.get("positive_keywords", [])
        negative_keywords = config.get("negative_keywords", [])
        required_attributes = config.get("required_attributes", {})
        weights = config.get("weights", {"text": 40, "visible": 30, "aria": 30})
        threshold = config.get("threshold", 65)

        logger.debug(f"Starting heuristic search for '{key}' using '{candidates_selector}'")

        try:
            elements = parent.locator(candidates_selector).all()
        except Exception as e:
            logger.warning(f"Heuristic candidates fetch failed: {e}")
            return None

        best_score = -1
        best_element = None
        best_reason = ""

        for element in elements:
            try:
                score = 0
                reasons = []

                # 1. Negative Keywords Check (Quick Fail)
                text_content = element.inner_text().strip()
                aria_label = element.get_attribute("aria-label") or ""
                full_text_check = (text_content + " " + aria_label).lower()

                if any(neg.lower() in full_text_check for neg in negative_keywords):
                    continue

                # 2. Visibility Score
                is_visible = element.is_visible()
                if is_visible:
                    score += weights.get("visible", 0)
                    reasons.append("visible")

                # 3. Text/Keyword Score
                matched_keyword = False
                for kw in positive_keywords:
                    if kw.lower() in text_content.lower():
                        score += weights.get("text", 0)
                        reasons.append(f"text_match({kw})")
                        matched_keyword = True
                        break

                # Fuzzy match fallback using SequenceMatcher
                if not matched_keyword and text_content and positive_keywords:
                    for kw in positive_keywords:
                         ratio = SequenceMatcher(None, kw.lower(), text_content.lower()).ratio()
                         if ratio > 0.8: # High confidence fuzzy match
                             fuzzy_score = weights.get("text", 0) * ratio
                             score += fuzzy_score
                             reasons.append(f"fuzzy_match({kw}:{ratio:.2f})")
                             break

                # 4. Attributes Score (ARIA, Role, Data attributes)
                # Check specific required attributes
                attr_match = True
                for attr, val in required_attributes.items():
                    if element.get_attribute(attr) != val:
                        attr_match = False
                        break

                if not attr_match:
                    continue

                # Check ARIA keywords if not matched in text
                for kw in positive_keywords:
                        if kw.lower() in aria_label.lower():
                            score += weights.get("aria", 0)
                            reasons.append(f"aria_match({kw})")
                            break

                if score > best_score:
                    best_score = score
                    best_element = element
                    best_reason = ", ".join(reasons)

            except Exception:
                continue

        if best_score >= threshold and best_element:
            logger.info(f"🏆 Heuristic Match for '{key}': Score {best_score:.1f}/{threshold} [{best_reason}] Text: '{best_element.inner_text().strip()[:20]}'")
            return best_element

        logger.debug(f"Heuristic failed for '{key}'. Best score: {best_score}")
        return None

    def find_element(self, parent: Union[Page, Locator], key: str) -> Optional[Locator]:
        """
        Finds an element using the cascade strategy or heuristic strategy.
        Prioritizes heuristic if config exists, then falls back to standard selectors.
        """
        # 1. Try Heuristic (if key explicitly ends with _heuristic OR config exists)
        heuristic_key = key if key.endswith("_heuristic") else f"{key}_heuristic"

        # Check if heuristic config exists
        if self.get_heuristic_config(heuristic_key):
             found = self.find_heuristic(parent, heuristic_key)
             if found:
                 return found
             else:
                 logger.debug(f"Heuristic fallback: '{heuristic_key}' failed, trying standard selectors for '{key}'.")

        # 2. Standard Selectors
        # Clean the key if we were passed the _heuristic version explicitly
        standard_key = key.replace("_heuristic", "")
        selectors = self.get_selectors(standard_key)

        if not selectors:
            if not self.get_heuristic_config(heuristic_key): # Warn only if BOTH failed
                logger.warning(f"No selectors defined for key '{standard_key}'")
            return None

        # Combine selectors with comma (OR operator in CSS)
        combined_selector = ", ".join(selectors)

        try:
            return parent.locator(combined_selector)
        except Exception as e:
            logger.error(f"Error creating locator for key {standard_key}: {e}")
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
