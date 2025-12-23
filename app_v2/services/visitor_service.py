import asyncio
import json
import logging
import random
import re
from datetime import datetime
from typing import Optional, List, Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app_v2.core.config import Settings
from app_v2.db.engine import get_session_maker
from app_v2.db.models import Contact, Interaction
from app_v2.engine.action_manager import ActionManager
from app_v2.engine.browser_context import LinkedInBrowserContext
from app_v2.engine.selector_engine import SmartSelectorEngine

logger = logging.getLogger(__name__)

class VisitorService:
    """
    Service de sourcing et de visite de profils (Migration V1 -> V2).
    Intègre la logique de navigation, scraping, scoring et persistance.
    """

    def __init__(
        self,
        context: LinkedInBrowserContext,
        action_manager: ActionManager,
        selector_engine: SmartSelectorEngine,
        settings: Settings
    ):
        self.context = context
        self.action_manager = action_manager
        self.selector_engine = selector_engine
        self.settings = settings
        self.session_maker = get_session_maker(settings)
        # Accès direct à la page pour le scraping intensif
        self.page = context.page

    async def run_sourcing(self, search_url: str, max_profiles: int, criteria: Optional[Dict[str, Any]] = None):
        """
        Exécute une session de sourcing complète :
        1. Navigation vers l'URL de recherche.
        2. Extraction des profils.
        3. Pour chaque profil : Visite -> Scraping -> Scoring -> Sauvegarde.
        """
        if not self.context.page:
            logger.error("Page non initialisée")
            return

        # Mise à jour de la référence locale si le contexte a changé (ex: nouveau login)
        self.page = self.context.page

        logger.info(f"Début du sourcing sur : {search_url}")
        criteria = criteria or {}

        # 1. Navigation Recherche
        try:
            await self.page.goto(search_url, timeout=60000)
            await self.action_manager._handle_popups()
            await self.action_manager._random_delay(2.0, 4.0)
        except Exception as e:
            logger.error(f"Erreur navigation recherche : {e}")
            return

        profiles_processed = 0

        while profiles_processed < max_profiles:
            # Scroll progressif pour charger les résultats
            await self._scroll_results()

            # Extraction des URLs
            urls = await self._extract_profile_urls_from_search()
            if not urls:
                logger.info("Aucun profil trouvé sur cette page.")
                break

            logger.info(f"Profils trouvés sur la page : {len(urls)}")

            for url in urls:
                if profiles_processed >= max_profiles:
                    break

                # Vérification anti-doublon (visite récente)
                if await self._is_profile_visited(url):
                    logger.debug(f"Profil déjà visité : {url}")
                    continue

                # Traitement du profil
                success = await self._process_single_profile(url, criteria)
                if success:
                    profiles_processed += 1

                # Délai entre les profils
                await self.action_manager._random_delay(5.0, 15.0)

            # Pagination (Bouton Suivant)
            # Sélecteur heuristique pour le bouton "Suivant"
            next_btn = self.page.locator("button.artdeco-pagination__button--next")
            if await next_btn.is_visible() and await next_btn.is_enabled():
                logger.info("Passage à la page suivante...")
                await next_btn.click()
                await self.action_manager._random_delay(3.0, 5.0)
            else:
                logger.info("Fin de la pagination.")
                break

    async def _scroll_results(self):
        """Scroll progressif pour charger le contenu (lazy loading)."""
        try:
            for i in range(4):
                await self.page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/4})")
                await asyncio.sleep(random.uniform(0.5, 1.0))
        except Exception:
            pass

    async def _extract_profile_urls_from_search(self) -> List[str]:
        """Extrait les URLs des profils depuis la liste de résultats."""
        urls = []
        try:
            # Recherche de liens contenant '/in/' (profils)
            links = self.page.locator('a.app-aware-link[href*="/in/"]')
            count = await links.count()

            for i in range(count):
                try:
                    href = await links.nth(i).get_attribute("href")
                    if href and "/in/" in href and "google" not in href:
                        clean_url = href.split("?")[0]
                        if clean_url not in urls:
                            urls.append(clean_url)
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Erreur extraction URLs : {e}")
        return urls

    async def _process_single_profile(self, url: str, criteria: Dict[str, Any]) -> bool:
        """Pipeline complet pour un profil : Visite, Scrap, Score, Save."""
        try:
            logger.info(f"Traitement du profil : {url}")

            # 1. Visite avec ActionManager (Navigation + Popups)
            await self.action_manager.goto_profile(url)

            # 2. Simulation d'activité humaine sur le profil
            await self.action_manager.visit_profile()

            # 3. Scraping des données
            data = await self._scrape_profile_data()
            if not data:
                return False

            data["profile_url"] = url

            # 4. Calcul du Fit Score (Réimplémentation V1)
            data["fit_score"] = self._calculate_fit_score(data, criteria)

            # 5. Sauvegarde en base (Contact)
            await self._save_contact(data)

            # 6. Enregistrement de l'interaction
            await self._record_interaction(url, "visit", "success", {"score": data["fit_score"]})

            return True

        except Exception as e:
            logger.error(f"Erreur traitement profil {url} : {e}")
            await self._record_interaction(url, "visit", "failed", {"error": str(e)})
            return False

    async def _scrape_profile_data(self) -> Dict[str, Any]:
        """
        Scrape les informations clés du profil.
        Extrait : Headline, Location, About, Experience, Skills, etc.
        """
        data = {
            "full_name": "Unknown",
            "headline": "",
            "summary": "",
            "location": None,
            "skills": [],
            "work_history": [],
            "education": None,
            "certifications": [],
            "languages": [],
            "open_to_work": False,
            "years_experience": 0,
            "job_title": None,
            "current_company": None
        }

        try:
            # Pré-scroll pour charger les sections dynamiques
            await self._smart_scroll_to_bottom()

            # --- Extraction des champs ---

            # Nom
            h1 = self.page.locator("h1.text-heading-xlarge, .pv-top-card h1").first
            if await h1.count() > 0:
                data["full_name"] = (await h1.inner_text()).strip()

            # Headline
            headline = self.page.locator("div.text-body-medium.break-words, .pv-top-card--list .text-body-medium").first
            if await headline.count() > 0:
                data["headline"] = (await headline.inner_text()).strip()

            # Location
            loc = self.page.locator("span.text-body-small.inline.t-black--light.break-words, .pv-top-card--list-bullet .text-body-small").first
            if await loc.count() > 0:
                text = (await loc.inner_text()).strip()
                if text and "connexion" not in text.lower():
                    data["location"] = text

            # About / Résumé
            about = self.page.locator('section:has-text("Infos"), section:has-text("About")').first
            if await about.count() > 0:
                # Tenter de cliquer sur "Voir plus"
                try:
                    see_more = about.locator('button.inline-show-more-text__button')
                    if await see_more.count() > 0:
                        await see_more.click(timeout=1000)
                except: pass

                summary_el = about.locator('div.inline-show-more-text span[aria-hidden="true"]').first
                if await summary_el.count() > 0:
                    data["summary"] = (await summary_el.inner_text()).strip()

            # Expérience
            await self._scrape_experience_full(data)

            # Compétences (Skills)
            await self._scrape_skills(data)

            # Open To Work
            await self._scrape_open_to_work(data)

            # Certifications
            await self._scrape_certifications(data)

        except Exception as e:
            logger.error(f"Erreur scraping global : {e}")

        return data

    async def _scrape_experience_full(self, data: dict):
        """Scrape la section expérience."""
        try:
            section = self.page.locator('section:has-text("Expérience"), section:has-text("Experience")').first
            if await section.count() == 0:
                return

            items = section.locator('li.pvs-list__paged-list-item, div.pvs-entity')
            count = await items.count()
            work_history = []

            for i in range(min(count, 10)):
                try:
                    item = items.nth(i)
                    exp = {}

                    # Titre
                    title_el = item.locator('span[aria-hidden="true"]').first
                    if await title_el.count() > 0:
                        exp["title"] = (await title_el.inner_text()).strip()

                    # Entreprise
                    # Souvent le 2ème span dans la hiérarchie ou span spécifique
                    company_el = item.locator('span.t-14.t-normal span[aria-hidden="true"]').first
                    if await company_el.count() > 0:
                        company_raw = (await company_el.inner_text()).strip()
                        exp["company"] = company_raw.split("·")[0].strip()

                    # Dates
                    date_el = item.locator('span.pvs-entity__caption-wrapper, span.t-14.t-black--light').first
                    if await date_el.count() > 0:
                        exp["date_text"] = (await date_el.inner_text()).strip()
                        years = re.findall(r"\b(19|20)\d{2}\b", exp["date_text"])
                        if years:
                            exp["start_year"] = int(years[0])

                    if exp.get("title"):
                        work_history.append(exp)

                except Exception:
                    continue

            data["work_history"] = work_history

            # Calcul années d'expérience et poste actuel
            if work_history:
                years = [x.get("start_year") for x in work_history if x.get("start_year")]
                if years:
                    data["years_experience"] = max(0, datetime.now().year - min(years))

                data["current_company"] = work_history[0].get("company")
                data["job_title"] = work_history[0].get("title")

        except Exception:
            pass

    async def _scrape_skills(self, data: dict):
        """Scrape les compétences."""
        try:
            section = self.page.locator('section:has-text("Compétences"), section:has-text("Skills")').first
            if await section.count() == 0:
                return

            skills = []
            # On cherche les textes dans les éléments de liste
            list_items = section.locator('li.pvs-list__paged-list-item span[aria-hidden="true"]')
            count = await list_items.count()

            for i in range(min(count, 30)):
                try:
                    text = (await list_items.nth(i).inner_text()).strip()
                    # Filtrage basique pour éviter les textes parasites (ex: "Validé par...")
                    if text and len(text) < 50 and "validé" not in text.lower():
                        if text not in skills:
                            skills.append(text)
                except Exception:
                    continue

            data["skills"] = skills
        except Exception:
            pass

    async def _scrape_certifications(self, data: dict):
        """Scrape les certifications."""
        try:
            section = self.page.locator('section:has-text("Licences et certifications"), section:has-text("Licenses & certifications")').first
            if await section.count() > 0:
                certs = []
                # Sélecteur approximatif pour les titres de certifs
                items = section.locator('li.pvs-list__paged-list-item span[aria-hidden="true"]')
                count = await items.count()
                for i in range(min(count, 20)):
                    try:
                        text = (await items.nth(i).inner_text()).strip()
                        # Filtrage sommaire
                        if text and len(text) > 3 and "délivré" not in text.lower():
                             if text not in certs:
                                certs.append(text)
                    except: continue
                data["certifications"] = certs
        except: pass

    async def _scrape_open_to_work(self, data: dict):
        """Détecte le badge Open To Work."""
        try:
            # Sélecteur de badge
            otw_badge = self.page.locator("main").get_by_text("Open to work", exact=False)
            if await otw_badge.count() > 0:
                data["open_to_work"] = True
                return

            # Vérification dans le Headline
            headline = data.get("headline", "").lower()
            keywords = ["open to work", "en recherche", "looking for", "#opentowork", "à l'écoute"]
            if any(k in headline for k in keywords):
                data["open_to_work"] = True
        except Exception:
            pass

    async def _smart_scroll_to_bottom(self):
        """Scroll aléatoire pour simuler la lecture et charger le contenu."""
        try:
            total_height = await self.page.evaluate("document.body.scrollHeight")
            current = 0
            while current < total_height:
                step = random.randint(300, 800)
                current += step
                await self.page.evaluate(f"window.scrollTo(0, {current})")
                await asyncio.sleep(random.uniform(0.1, 0.3))
                # Update height in case of lazy loading
                new_height = await self.page.evaluate("document.body.scrollHeight")
                if new_height > total_height:
                    total_height = new_height
        except Exception:
            pass

    def _calculate_fit_score(self, data: Dict[str, Any], criteria: Dict[str, Any]) -> float:
        """
        Calcule le score de pertinence (0-100) basé sur la logique V1.

        Facteurs :
        - Mots-clés (Skills, Headline, Summary) : 35 pts
        - Expérience (Années) : 20 pts
        - Open to Work : 15 pts
        - Localisation : 5 pts
        - Bonus divers : 25 pts
        """
        score = 0.0
        target_keywords = criteria.get("keywords", [])

        # 1. Mots-clés (35 pts)
        if target_keywords:
            # Corpus de texte
            skills_text = " ".join(data.get("skills", [])).lower()
            corpus = f"{skills_text} {data.get('headline', '')} {data.get('summary', '')} {data.get('job_title', '')}".lower()

            clean_kws = [k.lower().strip() for k in target_keywords if k]
            matches = sum(1 for kw in clean_kws if kw in corpus)

            if len(clean_kws) > 0 and matches > 0:
                # Ratio de match
                ratio = matches / len(clean_kws)
                score += min(35, ratio * 45) # Formule V1

        # 2. Expérience (20 pts)
        exp = data.get("years_experience", 0)
        if exp >= 5: score += 15
        elif exp >= 3: score += 10
        elif exp >= 1: score += 5

        # Bonus fourchette
        min_exp = criteria.get("years_experience_min")
        max_exp = criteria.get("years_experience_max")
        if min_exp or max_exp:
            in_range = True
            if min_exp and exp < min_exp: in_range = False
            if max_exp and exp > max_exp: in_range = False
            if in_range: score += 5

        # 3. Open to Work (15 pts)
        if data.get("open_to_work"):
            score += 15

        # 4. Localisation (5 pts)
        target_loc = criteria.get("location")
        if target_loc and data.get("location"):
            if target_loc.lower() in data["location"].lower():
                score += 5

        # 5. Certifications / Bonus techniques
        certs = " ".join(data.get("certifications", [])).lower()
        key_certs = ["aws", "azure", "gcp", "kubernetes", "docker", "pmp", "scrum"]
        if any(c in certs for c in key_certs):
            score += 5

        return min(100.0, score)

    async def _save_contact(self, data: Dict[str, Any]):
        """Upsert du contact dans la base de données."""
        try:
            async with self.session_maker() as session:
                # Recherche existant
                stmt = select(Contact).where(Contact.profile_url == data["profile_url"])
                result = await session.execute(stmt)
                contact = result.scalars().first()

                if contact:
                    # Update
                    contact.name = data.get("full_name", "Unknown")
                    contact.headline = data.get("headline")
                    contact.location = data.get("location")
                    contact.open_to_work = data.get("open_to_work", False)
                    contact.fit_score = data.get("fit_score", 0.0)
                    contact.skills = data.get("skills")
                    contact.work_history = data.get("work_history")
                    contact.updated_at = datetime.now()
                else:
                    # Create
                    contact = Contact(
                        name=data.get("full_name", "Unknown"),
                        profile_url=data["profile_url"],
                        headline=data.get("headline"),
                        location=data.get("location"),
                        open_to_work=data.get("open_to_work", False),
                        fit_score=data.get("fit_score", 0.0),
                        skills=data.get("skills"),
                        work_history=data.get("work_history"),
                        status="new"
                    )
                    session.add(contact)

                await session.commit()
                logger.info(f"Contact sauvegardé : {data.get('full_name')}")
        except Exception as e:
            logger.error(f"Erreur sauvegarde DB : {e}")

    async def _record_interaction(self, url: str, type_: str, status: str, payload: dict = None):
        """Enregistre l'interaction (visite) liée au contact."""
        try:
            async with self.session_maker() as session:
                stmt = select(Contact).where(Contact.profile_url == url)
                result = await session.execute(stmt)
                contact = result.scalars().first()

                if contact:
                    interaction = Interaction(
                        contact_id=contact.id,
                        type=type_,
                        status=status,
                        payload=payload
                    )
                    session.add(interaction)
                    await session.commit()
        except Exception as e:
            logger.error(f"Erreur enregistrement interaction : {e}")

    async def _is_profile_visited(self, url: str) -> bool:
        """Vérifie si le profil a déjà été visité avec succès."""
        try:
            async with self.session_maker() as session:
                stmt = select(Interaction).join(Contact).where(
                    Contact.profile_url == url,
                    Interaction.type == "visit",
                    Interaction.status == "success"
                )
                result = await session.execute(stmt)
                return result.scalars().first() is not None
        except Exception:
            return False
