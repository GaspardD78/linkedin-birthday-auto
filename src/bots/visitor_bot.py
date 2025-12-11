"""
Bot LinkedIn pour la visite automatique de profils.

Ce bot effectue des recherches basées sur des mots-clés et une localisation,
puis visite les profils trouvés pour simuler de l'activité et générer des vues en retour.
"""
from datetime import datetime
import random
import time
import re
from typing import Any, Optional
import urllib.parse
import sys
import argparse
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from ..core.base_bot import BaseLinkedInBot
from ..core.database import get_database
from ..config.config_manager import get_config
from ..utils.exceptions import LinkedInBotError
from ..utils.logging import get_logger

logger = get_logger(__name__)

class VisitorBot(BaseLinkedInBot):
    """
    Bot LinkedIn pour la visite automatique de profils.

    Fonctionnalités :
    - Recherche de profils par mots-clés et lieu.
    - Visite ("view") des profils pour apparaître dans leurs notifications.
    - Scraping léger des informations publiques (Nom, Titre, Entreprise).
    - Simulation de comportement humain (scroll, délais aléatoires).
    - Respect des limites configurées (nombre de profils par jour).

    Usage:
        >>> from src.bots.visitor_bot import VisitorBot
        >>> with VisitorBot() as bot:
        >>>     bot.run()
    """

    def __init__(self, config=None, profiles_limit_override: Optional[int] = None, campaign_id: Optional[int] = None, *args, **kwargs):
        """
        Initialise le VisitorBot.

        Args:
            config: Configuration du bot
            profiles_limit_override: Override optionnel pour la limite de profils à visiter.
                                     Si None, utilise config.visitor.limits.profiles_per_run
            *args: Arguments passés à BaseLinkedInBot
            **kwargs: Arguments nommés passés à BaseLinkedInBot
        """
        super().__init__(config=config, *args, **kwargs)
        self.db = None

        # Override la limite si spécifié, sinon utilise config
        self.profiles_limit = (
            profiles_limit_override
            if profiles_limit_override is not None
            else self.config.visitor.limits.profiles_per_run
        )
        self.campaign_id = campaign_id

        logger.info(
            "VisitorBot initialized",
            keywords=self.config.visitor.keywords,
            location=self.config.visitor.location,
            profiles_limit=self.profiles_limit,
        )

    def run(self) -> dict[str, Any]:
        """Point d'entrée principal pour l'exécution du bot."""
        return super().run()

    def _run_internal(self) -> dict[str, Any]:
        """
        Logique interne d'exécution du bot de visite.

        Workflow :
        1. Validation de la configuration et de l'authentification.
        2. Boucle sur les pages de résultats de recherche.
        3. Pour chaque profil trouvé :
           a. Vérification si déjà visité (DB).
           b. Visite du profil.
           c. Simulation d'activité humaine.
           d. Enregistrement de la visite en base.
        """
        start_time = time.time()
        self._validate_visitor_config()

        # Initialisation de la base de données
        if self.config.database.enabled:
            try:
                self.db = get_database(self.config.database.db_path)
            except Exception as e:
                logger.warning(f"Database unavailable: {e}", exc_info=True)
                self.db = None

        if not self.check_login_status():
            return self._build_error_result("Login verification failed")

        self._validate_search_selectors()

        profiles_visited = 0
        profiles_attempted = 0
        profiles_failed = 0
        profiles_ignored = 0 # NEW: Counter for ignored profiles
        pages_scraped = 0

        current_page = 1
        max_pages = self.config.visitor.limits.max_pages_to_scrape
        profiles_per_run = self.profiles_limit  # Utilise la limite (config ou override)

        while current_page <= max_pages and profiles_visited < profiles_per_run:
            logger.info(f"Scraping page {current_page}/{max_pages}")
            pages_scraped = current_page

            profile_urls = self._search_profiles(current_page)

            if not profile_urls:
                logger.info(f"No more profiles found on page {current_page}. Stopping.")
                break

            for url in profile_urls:
                if profiles_visited >= profiles_per_run:
                    break

                if self._is_profile_already_visited(url):
                    profiles_ignored += 1
                    logger.debug(f"Skipping already visited profile: {url}")
                    continue

                profile_name = self._extract_profile_name_from_url(url)

                if not self.config.dry_run:
                    success, scraped_data = self._visit_profile_with_retry(url)
                    self._record_profile_visit(url, profile_name, success)

                    if success and scraped_data:
                        self._save_scraped_profile_data(scraped_data)

                    profiles_attempted += 1
                    if success:
                        profiles_visited += 1
                    else:
                        profiles_failed += 1
                else:
                    logger.info(f"[DRY RUN] Would have visited {url}")
                    self._record_profile_visit(url, profile_name, True)
                    profiles_visited += 1
                    profiles_attempted += 1

                self._random_delay_between_profiles()

            current_page += 1
            self._delay_page_navigation()

        duration = time.time() - start_time

        # Log execution stats to DB
        if self.db:
            try:
                self.db.log_bot_execution(
                    bot_name="VisitorBot",
                    start_time=start_time,
                    items_processed=profiles_visited,
                    items_ignored=profiles_ignored,
                    errors=profiles_failed,
                    status="success"
                )
            except Exception as e:
                logger.error(f"Failed to log execution stats: {e}")

        return self._build_result(
            profiles_visited, profiles_attempted, profiles_failed, pages_scraped, duration, profiles_ignored
        )

    # ═══════════════════════════════════════════════════════════════
    #  RECHERCHE (Améliorée avec Cascade)
    # ═══════════════════════════════════════════════════════════════

    def _search_profiles(self, page_number: int = 1) -> list[str]:
        """
        Effectue une recherche LinkedIn et retourne les URLs de profils.

        Args:
            page_number: Numéro de la page de résultats à scraper.

        Returns:
            Liste des URLs de profils trouvées.
        """
        keyword_str = " ".join(self.config.visitor.keywords)
        search_url = (
            f"https://www.linkedin.com/search/results/people/"
            f"?keywords={urllib.parse.quote(keyword_str)}"
            f"&location={urllib.parse.quote(self.config.visitor.location)}"
            f"&origin=GLOBAL_SEARCH_HEADER"
            f"&page={page_number}"
        )

        try:
            self.page.goto(search_url, timeout=60000)
            self._random_delay_generic()
        except PlaywrightTimeoutError:
            return []

        profile_links = []
        result_container_selector = self.selector_manager.get_combined_selector("visitor.search.result_container") or 'div[data-view-name="people-search-result"]'

        try:
            self.page.wait_for_selector(result_container_selector, timeout=20000)

            # Scroll simple pour charger (lazy loading)
            for _ in range(3):
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)

            containers = self.page.query_selector_all(result_container_selector)

            for container in containers:
                # Stratégie Cascade pour trouver le lien
                link_selectors = self.selector_manager.get_selectors("visitor.search.links")
                if not link_selectors:
                     link_selectors = [
                        'a[data-view-name="search-result-lockup-title"]',
                        'a.app-aware-link[href*="/in/"]',
                        'span.entity-result__title-text a'
                    ]
                # Appel à la méthode de la classe parente
                link_element = self._find_element_by_cascade(container, link_selectors)

                if link_element:
                    href = link_element.get_attribute("href")
                    if href and "/in/" in href:
                        profile_links.append(href.split("?")[0])

        except Exception as e:
            logger.warning(f"Search extraction warning: {e}", exc_info=True)

        return list(set(profile_links))

    # ═══════════════════════════════════════════════════════════════
    #  SCRAPING COMPLET (Amélioré & Scoring)
    # ═══════════════════════════════════════════════════════════════

    def _scrape_profile_data(self) -> dict[str, Any]:
        """
        Scrape les données détaillées d'un profil LinkedIn (Nom, Headline, Skills, Certs).
        Implémente également le calcul du Fit Score.

        Returns:
            Dictionnaire enrichi avec 'fit_score', 'skills', 'certifications', etc.
        """
        scraped_data = {
            "full_name": "Unknown",
            "first_name": "Unknown",
            "last_name": "Unknown",
            "headline": "",
            "summary": "",
            "relationship_level": "Unknown",
            "current_company": "Unknown",
            "education": "Unknown",
            "years_experience": 0,
            "skills": [],
            "certifications": [],
            "fit_score": 0.0,
            "profile_url": self.page.url.split("?")[0],
        }

        try:
            # 0. Scroll préliminaire pour déclencher le lazy-loading (Compétences, Infos)
            self._smart_scroll_to_bottom()

            # 1. NOM & PRÉNOM
            try:
                name_selectors = self.selector_manager.get_selectors("visitor.profile.name") or ["h1.text-heading-xlarge"]
                for selector in name_selectors:
                    name_element = self.page.locator(selector).first
                    if name_element.count() > 0:
                        full_name = name_element.inner_text(timeout=5000).strip()
                        if full_name:
                            scraped_data["full_name"] = full_name
                            parts = full_name.split()
                            if len(parts) >= 2:
                                scraped_data["first_name"] = parts[0]
                                scraped_data["last_name"] = " ".join(parts[1:])
                            elif len(parts) == 1:
                                scraped_data["first_name"] = parts[0]
                                scraped_data["last_name"] = ""
                            break
            except Exception: pass

            # 2. HEADLINE (Titre)
            try:
                headline_selector = self.selector_manager.get_combined_selector("visitor.profile.headline") or "div.text-body-medium"
                headline_el = self.page.locator(headline_selector).first
                if headline_el.count() > 0:
                    scraped_data["headline"] = headline_el.inner_text().strip()
            except Exception: pass

            # 3. RÉSUMÉ (Summary/About)
            try:
                about_selector = self.selector_manager.get_combined_selector("visitor.profile.sections.about")
                about_section = self.page.locator(about_selector).first if about_selector else self.page.locator('section:has-text("Infos"), section:has-text("About")').first
                if about_section.count() > 0:
                    # Click "Voir plus" si présent
                    see_more = about_section.locator('button.inline-show-more-text__button')
                    if see_more.count() > 0:
                        see_more.click(force=True)
                        time.sleep(0.5)

                    summary_text_el = about_section.locator('div.inline-show-more-text span[aria-hidden="true"]').first
                    if summary_text_el.count() > 0:
                        scraped_data["summary"] = summary_text_el.inner_text().strip()
            except Exception: pass

            # 4. COMPÉTENCES (Skills)
            try:
                skills_selector = self.selector_manager.get_combined_selector("visitor.profile.sections.skills")
                skills_section = self.page.locator(skills_selector).first if skills_selector else self.page.locator('section:has-text("Compétences")').first
                if skills_section.count() > 0:
                    # On essaie de récupérer les compétences visibles sans ouvrir le modal (plus rapide/stealth)
                    skill_items = skills_section.locator('a[data-field="skill_card_skill_topic"], div[data-field="skill_card_skill_topic"], span.pv-skill-category-entity__name-text')
                    count = skill_items.count()
                    for i in range(min(count, 5)): # Top 5 seulement
                        scraped_data["skills"].append(skill_items.nth(i).inner_text().strip())
            except Exception: pass

            # 5. CERTIFICATIONS
            try:
                cert_selector = self.selector_manager.get_combined_selector("visitor.profile.sections.certifications")
                cert_section = self.page.locator(cert_selector).first if cert_selector else self.page.locator('section:has-text("Licences et certifications")').first
                if cert_section.count() > 0:
                    cert_items = cert_section.locator('div[class*="pvs-entity"]')
                    count = cert_items.count()
                    for i in range(min(count, 3)): # Top 3
                         # Nom de la certif
                         cert_name_el = cert_items.nth(i).locator('span[aria-hidden="true"]').first
                         if cert_name_el.count() > 0:
                             scraped_data["certifications"].append(cert_name_el.inner_text().strip())
            except Exception: pass

            # 6. EXPÉRIENCE (Années)
            try:
                exp_selector = self.selector_manager.get_combined_selector("visitor.profile.sections.experience")
                exp_section = self.page.locator(exp_selector).first if exp_selector else self.page.locator('section:has-text("Expérience")').first
                if exp_section.count() > 0:
                    all_exps = exp_section.locator('div[class*="pvs-entity"]')
                    count = all_exps.count()
                    if count > 0:
                        last_exp = all_exps.nth(count - 1)
                        date_spans = last_exp.locator('span[class*="date"], span:has-text(" - ")')
                        if date_spans.count() > 0:
                            date_text = date_spans.first.inner_text().strip()
                            years = re.findall(r"\b(19|20)\d{2}\b", date_text)
                            if years:
                                start_year = int(years[0])
                                current_year = datetime.now().year
                                scraped_data["years_experience"] = max(0, current_year - start_year)

                    # Entreprise actuelle (Première expérience de la liste)
                    first_exp = all_exps.first
                    company_name_el = first_exp.locator('span.t-14.t-normal span[aria-hidden="true"]').first
                    if company_name_el.count() > 0:
                         scraped_data["current_company"] = company_name_el.inner_text().split("·")[0].strip()

            except Exception: pass

            # 7. CALCUL DU FIT SCORE
            scraped_data["fit_score"] = self._calculate_fit_score(scraped_data)

        except Exception as e:
            logger.error(f"Global scraping error: {e}")

        return scraped_data

    def _smart_scroll_to_bottom(self):
        """Scroll progressif et aléatoire pour charger toute la page."""
        try:
            total_height = self.page.evaluate("document.body.scrollHeight")
            viewport_height = self.page.viewport_size["height"]
            current_scroll = 0

            while current_scroll < total_height:
                scroll_step = random.randint(300, 600)
                current_scroll += scroll_step
                self.page.evaluate(f"window.scrollTo(0, {current_scroll})")
                time.sleep(random.uniform(0.3, 0.8))

                # Parfois une petite pause pour "lire"
                if random.random() < 0.2:
                    time.sleep(random.uniform(1.0, 2.0))

                # Recalculer la hauteur au cas où (lazy loading content added)
                total_height = self.page.evaluate("document.body.scrollHeight")
        except Exception: pass

    def _calculate_fit_score(self, data: dict) -> float:
        """
        Calcule un score de pertinence (0-100) basé sur les données extraites.

        Pondération :
        - Compétences techniques (Keywords match) : 40 pts
        - Expérience (années) : 20 pts
        - Certifications clés : 20 pts
        - Signal "Open to Work" / Headline : 20 pts
        """
        score = 0.0
        target_keywords = self.config.visitor.keywords or []

        # 1. Compétences & Headline (40 pts)
        text_corpus = (str(data.get("skills", "")) + " " + data.get("headline", "") + " " + data.get("summary", "")).lower()
        matches = 0
        for kw in target_keywords:
            # Simple count of occurrences isn't robust if unique keywords are few
            # But let's stick to checking presence of each keyword
            if kw.lower() in text_corpus:
                matches += 1

        # INCREASED SENSITIVITY: 20 pts per match, max 40
        if matches > 0:
            score += min(40, matches * 20)

        # 2. Expérience (20 pts)
        exp = data.get("years_experience", 0)
        if exp:
            if exp >= 5: score += 20
            elif exp >= 3: score += 15
            elif exp >= 1: score += 10

        # 3. Certifications (20 pts)
        certs = " ".join(data.get("certifications", [])).lower()
        key_certs = ["azure", "aws", "gcp", "kubernetes", "docker", "terraform", "scrum", "pmp", "cka", "ckad"]
        cert_matches = sum(1 for c in key_certs if c in certs)
        if cert_matches > 0:
            score += min(20, cert_matches * 10)

        # 4. Signals (20 pts)
        headline = data.get("headline", "").lower()
        if "open to work" in headline or "recherche" in headline or "looking for" in headline or "available" in headline:
            score += 20

        return min(100.0, score)

    # ═══════════════════════════════════════════════════════════════
    #  HELPER METHODS (Restaurées & Nettoyées)
    # ═══════════════════════════════════════════════════════════════

    def _visit_profile_with_retry(self, url: str) -> tuple[bool, Optional[dict[str, Any]]]:
        """Tente de visiter un profil avec mécanisme de retry."""
        max_attempts = self.config.visitor.retry.max_attempts
        backoff = self.config.visitor.retry.backoff_factor

        for attempt in range(max_attempts):
            try:
                logger.info(f"Visiting {url} (Attempt {attempt+1})")
                self.page.goto(url, timeout=90000, wait_until="domcontentloaded")
                self._simulate_human_interactions()
                data = self._scrape_profile_data()
                self._random_delay_profile_visit()
                return True, data
            except PlaywrightTimeoutError:
                time.sleep(backoff ** attempt)
            except Exception as e:
                logger.warning(f"Visit error: {e}")
                return False, None
        return False, None

    def _simulate_human_interactions(self) -> None:
        """Simule des interactions humaines (Scroll + Mouse) pour éviter la détection."""
        try:
            # Scroll
            for _ in range(random.randint(3, 5)):
                self.page.evaluate(f"window.scrollBy(0, {random.randint(300, 700)})")
                time.sleep(random.uniform(0.5, 1.5))

            # Mouse move (Bezier simplifié)
            self.page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        except Exception: pass

    def _is_profile_already_visited(self, url: str) -> bool:
        """Vérifie dans la DB si le profil a déjà été visité récemment."""
        if not self.db: return False
        return self.db.is_profile_visited(url, 30)

    def _record_profile_visit(self, url, name, success):
        """Enregistre la visite dans la base de données."""
        if self.db:
            try:
                self.db.add_profile_visit(
                    profile_name=name,
                    profile_url=url,
                    source_search="search",
                    keywords=self.config.visitor.keywords,
                    location=self.config.visitor.location,
                    success=success,
                    error_message=None if success else "Failed"
                )
            except Exception as e:
                logger.error(f"DB Error: {e}")

    def _save_scraped_profile_data(self, data):
        """Sauvegarde les données scrapées."""
        if self.db:
            try:
                # Add campaign_id context if available
                if self.campaign_id:
                    data["campaign_id"] = self.campaign_id

                self.db.save_scraped_profile(**data)
            except Exception as e:
                logger.error(f"Failed to save profile data: {e}")

    def _extract_profile_name_from_url(self, url: str) -> str:
        """Extrait le nom du profil depuis l'URL (fallback)."""
        try:
            if "/in/" in url:
                return url.split("/in/")[1].split("/")[0].replace("-", " ").title()
        except Exception: pass
        return "Unknown"

    def _validate_visitor_config(self):
        if not self.config.visitor.keywords:
            raise LinkedInBotError("Keywords missing")

    def _validate_search_selectors(self): pass # Optionnel

    def _check_session_valid(self):
        return "login" not in self.page.url

    def _random_delay_generic(self):
        self._random_delay_with_distribution(2, 5)

    def _random_delay_profile_visit(self):
        self._random_delay_with_distribution(10, 20)

    def _random_delay_between_profiles(self):
        self._random_delay_with_distribution(5, 15)

    def _delay_page_navigation(self):
        self._random_delay_with_distribution(3, 8)

    def _random_delay_with_distribution(self, min_s, max_s):
        time.sleep(random.uniform(min_s, max_s))

    def _build_result(self, pv, pa, pf, ps, dur, ignored=0):
        return {
            "success": True,
            "profiles_visited": pv,
            "profiles_attempted": pa,
            "profiles_failed": pf,
            "profiles_ignored": ignored,
            "pages_scraped": ps,
            "duration_seconds": round(dur, 2)
        }


if __name__ == "__main__":
    # Point d'entrée pour l'exécution via subprocess (Dashboard)
    parser = argparse.ArgumentParser(description="LinkedIn Visitor Bot")
    parser.add_argument("--keywords", nargs="+", help="Mots-clés de recherche")
    parser.add_argument("--location", help="Localisation (ex: Paris, France)")
    parser.add_argument("--limit", type=int, help="Limite de profils à visiter")
    parser.add_argument("--campaign-id", type=int, help="ID de la campagne (optionnel)")
    parser.add_argument("--dry-run", action="store_true", help="Mode simulation")

    args = parser.parse_args()

    try:
        # Chargement de la config de base
        config = get_config()

        # Surcharge avec les arguments CLI
        if args.keywords:
            config.visitor.keywords = args.keywords
        if args.location:
            config.visitor.location = args.location
        if args.dry_run:
            config.dry_run = True

        profiles_limit = args.limit if args.limit else None
        campaign_id = args.campaign_id

        logger.info(f"Starting VisitorBot via CLI with keywords={config.visitor.keywords}, location={config.visitor.location}, campaign_id={campaign_id}")

        with VisitorBot(config=config, profiles_limit_override=profiles_limit, campaign_id=campaign_id) as bot:
            bot.run()

    except Exception as e:
        logger.critical(f"Critical error in VisitorBot CLI execution: {e}", exc_info=True)
        sys.exit(1)
