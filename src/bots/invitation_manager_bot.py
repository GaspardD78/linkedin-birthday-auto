"""
Bot de nettoyage des invitations envoyées LinkedIn.

Cible: https://www.linkedin.com/mynetwork/invitation-manager/sent/
Objectif: Retirer les invitations envoyées il y a plus de X mois.
"""
import time
import random
from typing import Any, Optional

from ..core.base_bot import BaseLinkedInBot
from ..utils.logging import get_logger
from ..utils.date_parser import DateParsingService
from ..utils.exceptions import LinkedInBotError

logger = get_logger(__name__)

class InvitationManagerBot(BaseLinkedInBot):
    """
    Bot dédié au nettoyage des invitations envoyées (Sent Requests).
    """

    def __init__(self, config=None, *args, **kwargs):
        super().__init__(config=config, *args, **kwargs)
        self.withdrawn_count = 0
        self.processed_count = 0
        self.errors_count = 0

    def run(self) -> dict[str, Any]:
        """Point d'entrée principal."""
        return super().run()

    def _run_internal(self) -> dict[str, Any]:
        """Logique principale du bot."""
        start_time = time.time()

        # 0. Vérifications préliminaires
        if not self.config.invitation_manager.enabled:
            logger.info("InvitationManager is disabled in config.")
            return {"status": "disabled"}

        if not self.check_login_status():
            return self._build_error_result("Login verification failed")

        threshold_months = self.config.invitation_manager.threshold_months
        threshold_days = threshold_months * 30
        max_withdrawals = self.config.invitation_manager.max_withdrawals_per_run

        logger.info(f"Starting Invitation Cleanup. Threshold: {threshold_months} months ({threshold_days} days). Max: {max_withdrawals}")

        # 1. Navigation
        target_url = "https://www.linkedin.com/mynetwork/invitation-manager/sent/"
        try:
            self.page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            return self._build_error_result(f"Navigation failed: {e}")

        # 2. Loop Items
        # Stratégie: On parcourt la liste. Si on retire un élément, la liste change (refresh partiel).
        # Donc il est plus sûr de relire la liste après chaque action réussie ou de parcourir prudemment.
        # Mais pour la performance, on essaie d'itérer. Si le DOM casse, on catch et on re-query.

        # Sélecteurs
        item_selector_list = self.selector_manager.get_selectors("invitation_manager.list_item") or ["li.invitation-card"]
        combined_item_selector = ", ".join(item_selector_list)

        no_new_items_count = 0

        while self.withdrawn_count < max_withdrawals:
            # Re-query items at start of loop iteration to handle DOM updates
            try:
                # Wait for items to be present (or empty state)
                try:
                    self.page.wait_for_selector(combined_item_selector, timeout=5000)
                except Exception:
                    logger.info("No more invitation cards found.")
                    break

                items = self.page.locator(combined_item_selector).all()
                logger.debug(f"Found {len(items)} invitations on page.")

                action_taken_in_pass = False

                for i, item in enumerate(items):
                    if self.withdrawn_count >= max_withdrawals:
                        break

                    try:
                        # Re-verify item attachment
                        if not item.is_visible():
                            continue

                        # Extract Name (for logs)
                        name_el = item.locator(".invitation-card__title").first
                        name = name_el.inner_text().strip() if name_el.count() > 0 else "Unknown"

                        # Extract Time
                        time_text = self._extract_time_text(item)
                        if not time_text:
                            logger.debug(f"Could not extract time for {name}. Skipping.")
                            continue

                        # Check Stale
                        elapsed_days = DateParsingService.parse_elapsed_days(time_text)
                        if elapsed_days is None:
                            logger.debug(f"Could not parse time '{time_text}' for {name}. Skipping.")
                            continue

                        logger.debug(f"Checking {name}: {time_text} ({elapsed_days} days)")

                        if elapsed_days >= threshold_days:
                            # MARK FOR WITHDRAWAL
                            logger.info(f"🗑️ Stale request detected: {name} sent {time_text} ({elapsed_days}d >= {threshold_days}d)")

                            if not self.config.dry_run:
                                success = self._perform_withdraw(item, name)
                                if success:
                                    self.withdrawn_count += 1
                                    action_taken_in_pass = True
                                    # Break inner loop to re-query DOM as it might have shifted
                                    break
                                else:
                                    self.errors_count += 1
                            else:
                                logger.info(f"[DRY RUN] Would withdraw request to {name}")
                                # In dry-run, we simulate but DO NOT increment withdrawn_count to avoid confusing stats
                                # or hitting loop limits prematurely based on fake actions
                                action_taken_in_pass = True
                                break

                    except Exception as e:
                        logger.warning(f"Error processing item {i}: {e}")
                        continue

                # If we took an action, we broke the loop to refresh DOM.
                # If we iterated all items without action, we need to scroll or break.
                if action_taken_in_pass:
                    # Wait a bit for list update
                    time.sleep(random.uniform(2, 3))
                    continue

                # Scroll Logic
                previous_height = self.page.evaluate("document.body.scrollHeight")
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(random.uniform(1.5, 2.5))
                new_height = self.page.evaluate("document.body.scrollHeight")

                if new_height == previous_height:
                    no_new_items_count += 1
                    if no_new_items_count >= 2:
                        logger.info("End of list reached (scroll).")
                        break
                else:
                    no_new_items_count = 0

            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                break

        duration = time.time() - start_time
        logger.info(f"Invitation Cleanup Finished. Withdrawn: {self.withdrawn_count}. Duration: {duration:.2f}s")

        return {
            "success": True,
            "withdrawn_count": self.withdrawn_count,
            "errors": self.errors_count,
            "duration": duration,
            "dry_run": self.config.dry_run
        }

    def _extract_time_text(self, item_locator) -> Optional[str]:
        """Extracts the time text from the card."""
        # Try configured selectors
        selectors = self.selector_manager.get_selectors("invitation_manager.time_element")
        for sel in selectors:
            try:
                el = item_locator.locator(sel).first
                if el.count() > 0:
                    text = el.inner_text().strip()
                    if text: return text
            except: pass

        # Fallback: look for text containing digits + "ago" or "il y a"
        try:
            text_content = item_locator.inner_text()
            # This is rough, extracting lines might be better
            lines = text_content.split('\n')
            for line in lines:
                if "ago" in line.lower() or "il y a" in line.lower():
                    return line.strip()
        except: pass

        return None

    def _perform_withdraw(self, item_locator, name: str) -> bool:
        """Clicks withdraw and handles modal."""
        try:
            # 1. Click Withdraw on Card
            withdraw_btn = self._find_element_by_cascade(item_locator, self.selector_manager.get_selectors("invitation_manager.withdraw_button"))

            if not withdraw_btn:
                logger.warning(f"Withdraw button not found for {name}")
                return False

            logger.debug(f"Clicking withdraw for {name}...")
            withdraw_btn.click()
            time.sleep(random.uniform(0.5, 1.0))

            # 2. Handle Modal
            modal_selector = self.selector_manager.get_combined_selector("invitation_manager.modal.container")
            try:
                self.page.wait_for_selector(modal_selector, state="visible", timeout=5000)
                logger.debug("Confirmation modal detected.")

                # Click Confirm inside modal
                confirm_btn_selectors = self.selector_manager.get_selectors("invitation_manager.modal.confirm_button")
                confirm_btn = self._find_element_by_cascade(self.page, confirm_btn_selectors)

                if confirm_btn:
                    # Random delay before confirm (Safety)
                    time.sleep(random.uniform(2.0, 3.0)) # "Wait 2000ms + random" as per spec
                    confirm_btn.click()
                    logger.info(f"✅ Confirmed withdrawal for {name}")
                    return True
                else:
                    logger.error("Confirm button not found in modal!")
                    # Try to close modal to recover
                    self.page.keyboard.press("Escape")
                    return False

            except Exception:
                # Modal might not appear (sometimes LinkedIn just does it)
                logger.warning("No modal appeared? Assuming success or error.")
                return True

        except Exception as e:
            logger.error(f"Failed to withdraw {name}: {e}")
            return False

    def _build_error_result(self, msg):
        return {"success": False, "error": msg}
