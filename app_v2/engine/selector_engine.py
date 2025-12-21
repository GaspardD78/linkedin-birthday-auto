from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeout
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app_v2.db.models import LinkedInSelector
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class HeuristicSelectorEngine:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.cache = {}  # Cache en mémoire des sélecteurs qui marchent

    async def find_element_smart(
        self,
        page: Page,
        element_type: str,
        fallback_selectors: list[str] = None,
        timeout: int = 5000
    ) -> Locator | None:
        # 1. Récupère les candidats depuis la DB
        stmt = select(LinkedInSelector).where(
            LinkedInSelector.element_type == element_type,
            LinkedInSelector.is_deprecated == False
        ).order_by(LinkedInSelector.score.desc()).limit(5)

        result = await self.db_session.execute(stmt)
        candidates = result.scalars().all()

        logger.debug(f"🔍 {len(candidates)} sélecteurs candidats pour '{element_type}'")

        # 2. Essaie chaque candidat
        for selector_model in candidates:
            try:
                locator = page.locator(selector_model.selector).first

                # Vérifie visibilité avec timeout court
                await locator.wait_for(state="visible", timeout=timeout)

                # Vérifie enabled
                is_enabled = await locator.is_enabled()

                if is_enabled:
                    logger.info(f"✓ Sélecteur trouvé (heuristique) : {selector_model.selector}")
                    await self.record_selector_success(element_type, selector_model.selector)
                    return locator

            except PlaywrightTimeout:
                await self.record_selector_failure(element_type, selector_model.selector)
                continue
            except Exception as e:
                logger.warning(f"Erreur sélecteur {selector_model.selector}: {e}")
                continue

        # 3. Fallback si fourni
        if fallback_selectors:
            logger.debug(f"Essai fallback pour '{element_type}'")
            for fallback in fallback_selectors:
                try:
                    locator = page.locator(fallback).first
                    await locator.wait_for(state="visible", timeout=timeout)
                    if await locator.is_enabled():
                        logger.info(f"✓ Fallback trouvé : {fallback}")
                        return locator
                except:
                    continue

        logger.error(f"❌ Aucun sélecteur trouvé pour '{element_type}'")
        return None

    async def record_selector_success(self, element_type: str, selector: str):
        stmt = update(LinkedInSelector).where(
            LinkedInSelector.element_type == element_type,
            LinkedInSelector.selector == selector
        ).values(
            score=LinkedInSelector.score + 1,
            last_success_at=datetime.now().isoformat()
        )
        await self.db_session.execute(stmt)
        await self.db_session.commit()

    async def record_selector_failure(self, element_type: str, selector: str):
        stmt = update(LinkedInSelector).where(
            LinkedInSelector.element_type == element_type,
            LinkedInSelector.selector == selector
        ).values(
            score=LinkedInSelector.score - 1,
            last_failure_at=datetime.now().isoformat(),
            is_deprecated=(LinkedInSelector.score < -5)
        )
        await self.db_session.execute(stmt)
        await self.db_session.commit()

    async def seed_initial_selectors(self):
        # Vérifie si la table est vide
        stmt = select(LinkedInSelector).limit(1)
        result = await self.db_session.execute(stmt)
        if result.scalar():
            return

        logger.info("🌱 Seeding des sélecteurs LinkedIn initiaux...")

        # Sélecteurs basés sur LINKEDIN_SELECTORS_DEC2025.md
        initial_selectors = [
            # Page Anniversaires
            {"element_type": "birthday_list_item", "selector": "div[role='listitem']"},
            {"element_type": "birthday_list_item", "selector": "div.celebrations-entity-list-item"},
            {"element_type": "birthday_profile_link", "selector": "a.app-aware-link[href*='/in/']"},
            {"element_type": "birthday_message_button", "selector": "button[aria-label*='Message']"},
            {"element_type": "birthday_message_button", "selector": "button[aria-label*='envoyer un message']"},

            # Modal Message
            {"element_type": "message_textbox", "selector": "div[role='textbox'][contenteditable='true']"},
            {"element_type": "message_textbox", "selector": ".msg-form__contenteditable"},
            {"element_type": "message_send_button", "selector": "button[type='submit'][data-tracking-control-name*='send']"},
            {"element_type": "message_send_button", "selector": "button:has-text('Send')"},
            {"element_type": "message_send_button", "selector": "button:has-text('Envoyer')"},
        ]

        for data in initial_selectors:
            # On vérifie si le sélecteur existe déjà pour éviter les doublons si la table n'était pas complètement vide (double sécurité)
            # Mais comme on a vérifié "table vide" avant, c'est bon.
            selector = LinkedInSelector(
                element_type=data["element_type"],
                selector=data["selector"],
                score=10,  # Score initial positif
                is_deprecated=False
            )
            self.db_session.add(selector)

        await self.db_session.commit()
        logger.info("✅ Seeding terminé.")
