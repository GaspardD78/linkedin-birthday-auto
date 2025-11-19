"""
Module de validation des sélecteurs LinkedIn
Détecte les changements de structure DOM et alerte quand les sélecteurs ne fonctionnent plus
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from database import get_database


class SelectorValidator:
    """Validateur de sélecteurs CSS pour LinkedIn"""

    def __init__(self, page: Page, enable_alerts: bool = True):
        """
        Initialise le validateur de sélecteurs

        Args:
            page: Page Playwright active
            enable_alerts: Active les alertes en cas de sélecteur invalide
        """
        self.page = page
        self.enable_alerts = enable_alerts
        self.db = get_database()
        self.validation_results = {}

    def validate_selector(self, selector_name: str, timeout: int = 5000) -> bool:
        """
        Valide qu'un sélecteur existe sur la page

        Args:
            selector_name: Nom du sélecteur à valider (dans la BDD)
            timeout: Timeout en millisecondes

        Returns:
            True si le sélecteur est valide, False sinon
        """
        selector_data = self.db.get_selector(selector_name)

        if not selector_data:
            logging.error(f"❌ Sélecteur '{selector_name}' non trouvé dans la base de données")
            return False

        selector_value = selector_data['selector_value']
        page_type = selector_data['page_type']

        try:
            # Vérifier si le sélecteur existe sur la page
            element = self.page.query_selector(selector_value)

            if element:
                logging.info(f"✅ Sélecteur '{selector_name}' ({page_type}) est valide")
                self.db.update_selector_validation(selector_name, is_valid=True)
                self.validation_results[selector_name] = True
                return True
            else:
                logging.warning(f"⚠️  Sélecteur '{selector_name}' ({page_type}) non trouvé sur la page")
                self.db.update_selector_validation(selector_name, is_valid=False)
                self.validation_results[selector_name] = False

                if self.enable_alerts:
                    self._log_validation_failure(selector_name, selector_value, page_type)

                return False

        except Exception as e:
            logging.error(f"❌ Erreur lors de la validation du sélecteur '{selector_name}': {e}")
            self.db.update_selector_validation(selector_name, is_valid=False)
            self.validation_results[selector_name] = False
            return False

    def validate_multiple_selectors(self, selector_names: List[str]) -> Dict[str, bool]:
        """
        Valide plusieurs sélecteurs en une seule passe

        Args:
            selector_names: Liste des noms de sélecteurs à valider

        Returns:
            Dictionnaire {selector_name: is_valid}
        """
        results = {}

        for selector_name in selector_names:
            results[selector_name] = self.validate_selector(selector_name)

        return results

    def validate_all_selectors_for_page(self, page_type: str) -> Dict[str, bool]:
        """
        Valide tous les sélecteurs d'un type de page donné

        Args:
            page_type: Type de page (birthday_feed, messaging, search, etc.)

        Returns:
            Dictionnaire {selector_name: is_valid}
        """
        all_selectors = self.db.get_all_selectors()
        page_selectors = [s for s in all_selectors if s['page_type'] == page_type]

        results = {}
        for selector in page_selectors:
            results[selector['selector_name']] = self.validate_selector(selector['selector_name'])

        return results

    def get_validation_summary(self) -> Dict[str, any]:
        """
        Retourne un résumé de la validation

        Returns:
            Dictionnaire avec les statistiques de validation
        """
        total = len(self.validation_results)
        valid = sum(1 for v in self.validation_results.values() if v)
        invalid = total - valid

        return {
            "total_selectors": total,
            "valid_selectors": valid,
            "invalid_selectors": invalid,
            "validation_rate": (valid / total * 100) if total > 0 else 0,
            "details": self.validation_results
        }

    def _log_validation_failure(self, selector_name: str, selector_value: str, page_type: str):
        """
        Enregistre un échec de validation dans la base de données

        Args:
            selector_name: Nom du sélecteur
            selector_value: Valeur du sélecteur CSS
            page_type: Type de page
        """
        error_message = f"Sélecteur '{selector_name}' non trouvé sur page '{page_type}'"
        error_details = f"Selector value: {selector_value}\nPage URL: {self.page.url}"

        self.db.log_error(
            script_name="selector_validator",
            error_type="SelectorNotFound",
            error_message=error_message,
            error_details=error_details
        )

        logging.error(f"🔴 ALERTE: {error_message}")
        logging.error(f"   → Sélecteur: {selector_value}")
        logging.error(f"   → Page: {self.page.url}")
        logging.error(f"   → LinkedIn a peut-être changé sa structure DOM")

    def suggest_alternative_selectors(self, selector_name: str) -> List[str]:
        """
        Suggère des sélecteurs alternatifs en cas d'échec

        Args:
            selector_name: Nom du sélecteur qui a échoué

        Returns:
            Liste de sélecteurs alternatifs potentiels
        """
        suggestions = []

        # Mapping de sélecteurs alternatifs connus
        alternatives = {
            "birthday_card": [
                "div.feed-shared-update-v2",
                "div.occludable-update",
                "li.feed-shared-update-v2",
                "[data-urn*='birthday']"
            ],
            "birthday_name": [
                "span.update-components-actor__name",
                "span[aria-hidden='true']",
                ".update-components-actor__name > span > span > span:first-child",
                "a.app-aware-link > span > span"
            ],
            "birthday_date": [
                "span.update-components-actor__supplementary-actor-info",
                "span.visually-hidden",
                ".update-components-actor__sub-description"
            ],
            "message_button": [
                "button.message-anywhere-button",
                "button[aria-label*='message']",
                "a[aria-label*='Envoyer un message']",
                "button:has-text('Message')"
            ],
            "message_textarea": [
                "div.msg-form__contenteditable",
                "div[role='textbox']",
                ".msg-form__contenteditable[contenteditable='true']",
                "div.msg-form__msg-content-container div[contenteditable]"
            ],
            "send_button": [
                "button.msg-form__send-button",
                "button[type='submit']",
                "button:has-text('Envoyer')",
                ".msg-form__send-button"
            ],
            "profile_card": [
                "li.reusable-search__result-container",
                "div[data-view-name='people-search-result']",
                ".search-results-container li",
                ".reusable-search__result-container"
            ]
        }

        if selector_name in alternatives:
            suggestions = alternatives[selector_name]

        return suggestions

    def auto_fix_selector(self, selector_name: str) -> Optional[str]:
        """
        Tente de trouver automatiquement un sélecteur alternatif qui fonctionne

        Args:
            selector_name: Nom du sélecteur à réparer

        Returns:
            Nouveau sélecteur qui fonctionne, ou None si aucun n'est trouvé
        """
        alternatives = self.suggest_alternative_selectors(selector_name)

        for alt_selector in alternatives:
            try:
                element = self.page.query_selector(alt_selector)
                if element:
                    logging.info(f"✅ Sélecteur alternatif trouvé pour '{selector_name}': {alt_selector}")
                    return alt_selector
            except Exception as e:
                logging.debug(f"Sélecteur alternatif '{alt_selector}' ne fonctionne pas: {e}")
                continue

        logging.warning(f"⚠️  Aucun sélecteur alternatif trouvé pour '{selector_name}'")
        return None

    def run_full_validation(self) -> bool:
        """
        Exécute une validation complète de tous les sélecteurs

        Returns:
            True si tous les sélecteurs sont valides, False sinon
        """
        logging.info("🔍 Démarrage de la validation complète des sélecteurs LinkedIn...")

        all_selectors = self.db.get_all_selectors()

        for selector in all_selectors:
            self.validate_selector(selector['selector_name'])

        summary = self.get_validation_summary()

        logging.info(f"\n📊 Résumé de validation:")
        logging.info(f"   Total: {summary['total_selectors']}")
        logging.info(f"   Valides: {summary['valid_selectors']} ✅")
        logging.info(f"   Invalides: {summary['invalid_selectors']} ❌")
        logging.info(f"   Taux de réussite: {summary['validation_rate']:.1f}%\n")

        if summary['invalid_selectors'] > 0:
            logging.warning("⚠️  Des sélecteurs invalides ont été détectés!")
            logging.warning("   LinkedIn a peut-être modifié sa structure DOM.")
            logging.warning("   Vérifiez les erreurs ci-dessus et mettez à jour les sélecteurs si nécessaire.")

            # Tenter une réparation automatique
            for selector_name, is_valid in summary['details'].items():
                if not is_valid:
                    alternative = self.auto_fix_selector(selector_name)
                    if alternative:
                        logging.info(f"💡 Suggestion: Mettre à jour '{selector_name}' avec: {alternative}")

            return False

        logging.info("✅ Tous les sélecteurs sont valides!")
        return True


def validate_birthday_feed_selectors(page: Page) -> bool:
    """
    Fonction utilitaire pour valider les sélecteurs du fil d'anniversaires

    Args:
        page: Page Playwright active

    Returns:
        True si tous les sélecteurs sont valides
    """
    validator = SelectorValidator(page)

    selectors_to_check = [
        "birthday_card",
        "birthday_name",
        "birthday_date",
        "message_button"
    ]

    results = validator.validate_multiple_selectors(selectors_to_check)
    all_valid = all(results.values())

    if not all_valid:
        logging.warning("⚠️  Certains sélecteurs du fil d'anniversaires sont invalides:")
        for name, valid in results.items():
            if not valid:
                logging.warning(f"   - {name}: ❌")

    return all_valid


def validate_messaging_selectors(page: Page) -> bool:
    """
    Fonction utilitaire pour valider les sélecteurs de messagerie

    Args:
        page: Page Playwright active

    Returns:
        True si tous les sélecteurs sont valides
    """
    validator = SelectorValidator(page)

    selectors_to_check = [
        "message_textarea",
        "send_button"
    ]

    results = validator.validate_multiple_selectors(selectors_to_check)
    all_valid = all(results.values())

    if not all_valid:
        logging.warning("⚠️  Certains sélecteurs de messagerie sont invalides:")
        for name, valid in results.items():
            if not valid:
                logging.warning(f"   - {name}: ❌")

    return all_valid


def validate_search_selectors(page: Page) -> bool:
    """
    Fonction utilitaire pour valider les sélecteurs de recherche

    Args:
        page: Page Playwright active

    Returns:
        True si tous les sélecteurs sont valides
    """
    validator = SelectorValidator(page)

    selectors_to_check = [
        "profile_card"
    ]

    results = validator.validate_multiple_selectors(selectors_to_check)
    all_valid = all(results.values())

    if not all_valid:
        logging.warning("⚠️  Certains sélecteurs de recherche sont invalides:")
        for name, valid in results.items():
            if not valid:
                logging.warning(f"   - {name}: ❌")

    return all_valid


if __name__ == "__main__":
    # Test du validateur (nécessite une page Playwright active)
    from playwright.sync_api import sync_playwright

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    print("Ce module nécessite une session Playwright active pour être testé.")
    print("Utilisez-le en l'important dans vos scripts principaux.")
    print("\nExemple d'utilisation:")
    print("""
    from selector_validator import SelectorValidator, validate_birthday_feed_selectors

    # Dans votre script avec une page active:
    validator = SelectorValidator(page)
    is_valid = validator.run_full_validation()

    # Ou pour un type de page spécifique:
    is_valid = validate_birthday_feed_selectors(page)
    """)
