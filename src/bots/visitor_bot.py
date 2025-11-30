"""
Bot LinkedIn pour la visite automatique de profils.
"""
from datetime import datetime
import random
import time
import re
from typing import Any, Optional
import urllib.parse
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from ..core.base_bot import BaseLinkedInBot
from ..core.database import get_database
from ..utils.exceptions import LinkedInBotError
from ..utils.logging import get_logger

logger = get_logger(__name__)

class VisitorBot(BaseLinkedInBot):
    """
    Bot LinkedIn pour la visite automatique de profils.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = None
        logger.info(
            "VisitorBot initialized",
            keywords=self.config.visitor.keywords,
            location=self.config.visitor.location,
        )

    def run(self) -> dict[str, Any]:
        return super().run()

    def _run_internal(self) -> dict[str, Any]:
        start_time = time.time()
        self._validate_visitor_config()

        # Database init
        if self.config.database.enabled:
            try:
                self.db = get_database(self.config.database.db_path)
            except Exception as e:
                logger.warning(f"Database unavailable: {e}")
                self.db = None

        if not self.check_login_status():
            return self._build_error_result("Login verification failed")

        self._validate_search_selectors()

        profiles_visited = 0
        profiles_attempted = 0
        profiles_failed = 0
        pages_scraped = 0

        current_page = 1
        max_pages = self.config.visitor.limits.max_pages_to_scrape
        profiles_per_run = self.config.visitor.limits.profiles_per_run

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
        return self._build_result(
            profiles_visited, profiles_attempted, profiles_failed, pages_scraped, duration
        )

    # ═══════════════════════════════════════════════════════════════
    #  RECHERCHE (Améliorée avec Cascade)
    # ═══════════════════════════════════════════════════════════════

    def _search_profiles(self, page_number: int = 1) -> list[str]:
        """Effectue une recherche LinkedIn et retourne les URLs de profils."""
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
        result_container_selector = 'div[data-view-name="people-search-result"]'

        try:
            self.page.wait_for_selector(result_container_selector, timeout=20000)

            # Scroll simple pour charger
            for _ in range(3):
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)

            containers = self.page.query_selector_all(result_container_selector)

            for container in containers:
                # Stratégie Cascade pour trouver le lien
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
            logger.warning(f"Search extraction warning: {e}")

        return list(set(profile_links))

    # ═══════════════════════════════════════════════════════════════
    #  SCRAPING COMPLET (Restauré)
    # ═══════════════════════════════════════════════════════════════

    def _scrape_profile_data(self) -> dict[str, Any]:
        """
        Scrape les données détaillées d'un profil LinkedIn.
        Restauration de la logique complète (Education, Expérience, etc.).
        """
        scraped_data = {
            "full_name": "Unknown",
            "first_name": "Unknown",
            "last_name": "Unknown",
            "relationship_level": "Unknown",
            "current_company": "Unknown",
            "education": "Unknown",
            "years_experience": None,
            "profile_url": self.page.url.split("?")[0],
        }

        try:
            # 1. NOM COMPLET
            try:
                name_selectors = [
                    "h1.text-heading-xlarge", "h1.inline", "div.ph5 h1", "h1[class*='heading']"
                ]
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

            # 2. NIVEAU DE RELATION
            try:
                rel_element = self.page.locator("span.dist-value").first
                if rel_element.count() > 0:
                    scraped_data["relationship_level"] = rel_element.inner_text().strip()
            except Exception: pass

            # 3. ENTREPRISE ACTUELLE
            try:
                company_selectors = ["div.text-body-medium", "div[class*='inline-show-more-text']"]
                for selector in company_selectors:
                    el = self.page.locator(selector).first
                    if el.count() > 0:
                        text = el.inner_text().strip()
                        if text:
                            scraped_data["current_company"] = text
                            break
            except Exception: pass

            # 4. FORMATION (Education)
            try:
                # Recherche section Formation
                education_section = self.page.locator('section:has-text("Formation"), section:has-text("Education")').first
                if education_section.count() > 0:
                    first_edu = education_section.locator('div[class*="pvs-entity"]').first
                    if first_edu.count() > 0:
                        # Tente de trouver le nom de l'école (souvent dans un span hidden ou visible)
                        edu_text = first_edu.locator('span[aria-hidden="true"]').first.inner_text().strip()
                        if edu_text:
                            scraped_data["education"] = edu_text
            except Exception: pass

            # 5. ANNÉES D'EXPÉRIENCE
            try:
                exp_section = self.page.locator('section:has-text("Expérience"), section:has-text("Experience")').first
                if exp_section.count() > 0:
                    all_exps = exp_section.locator('div[class*="pvs-entity"]')
                    count = all_exps.count()
                    if count > 0:
                        # On regarde la dernière expérience pour trouver une date ancienne
                        last_exp = all_exps.nth(count - 1)
                        date_spans = last_exp.locator('span[class*="date"]') # Souvent une classe contenant 'date' ou 't-14'
                        if date_spans.count() > 0:
                            date_text = date_spans.first.inner_text().strip()
                            # Utilisation de RE (légitime ici)
                            years = re.findall(r"\b(19|20)\d{2}\b", date_text)
                            if years:
                                start_year = int(years[0])
                                current_year = datetime.now().year
                                scraped_data["years_experience"] = max(0, current_year - start_year)
            except Exception: pass

        except Exception as e:
            logger.error(f"Global scraping error: {e}")

        return scraped_data

    # ═══════════════════════════════════════════════════════════════
    #  HELPER METHODS (Restaurées & Nettoyées)
    # ═══════════════════════════════════════════════════════════════

    def _visit_profile_with_retry(self, url: str) -> tuple[bool, Optional[dict[str, Any]]]:
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
        """Simule des interactions humaines (Scroll + Mouse)."""
        try:
            # Scroll
            for _ in range(random.randint(3, 5)):
                self.page.evaluate(f"window.scrollBy(0, {random.randint(300, 700)})")
                time.sleep(random.uniform(0.5, 1.5))

            # Mouse move (Bezier simplifié)
            self.page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        except Exception: pass

    def _is_profile_already_visited(self, url: str) -> bool:
        if not self.db: return False
        return self.db.is_profile_visited(url, 30)

    def _record_profile_visit(self, url, name, success):
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
        if self.db:
            try:
                self.db.save_scraped_profile(**data)
            except Exception: pass

    def _extract_profile_name_from_url(self, url: str) -> str:
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

    def _build_result(self, pv, pa, pf, ps, dur):
        return {
            "success": True,
            "profiles_visited": pv,
            "profiles_attempted": pa,
            "profiles_failed": pf,
            "pages_scraped": ps,
            "duration_seconds": round(dur, 2)
        }
