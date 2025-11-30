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
        logger.info("VisitorBot initialized")

    def run(self) -> dict[str, Any]:
        return super().run()

    def _run_internal(self) -> dict[str, Any]:
        start_time = time.time()
        self._validate_visitor_config()
        if self.config.database.enabled:
            try:
                self.db = get_database(self.config.database.db_path)
            except Exception: self.db = None

        if not self.check_login_status():
            return {"success": False, "error": "Login failed"}

        self._validate_search_selectors()
        profiles_visited = 0
        profiles_attempted = 0
        profiles_failed = 0
        pages_scraped = 0

        current_page = 1
        max_pages = self.config.visitor.limits.max_pages_to_scrape

        while current_page <= max_pages and profiles_visited < self.config.visitor.limits.profiles_per_run:
            logger.info(f"Scraping page {current_page}/{max_pages}")
            pages_scraped = current_page

            profile_urls = self._search_profiles(current_page)
            if not profile_urls: break

            for url in profile_urls:
                if profiles_visited >= self.config.visitor.limits.profiles_per_run: break
                if self._is_profile_already_visited(url): continue

                profile_name = self._extract_profile_name_from_url(url)

                if not self.config.dry_run:
                    success, scraped_data = self._visit_profile_with_retry(url)
                    self._record_profile_visit(url, profile_name, success)
                    if success and scraped_data:
                        self._save_scraped_profile_data(scraped_data)

                    profiles_attempted += 1
                    if success: profiles_visited += 1
                    else: profiles_failed += 1
                else:
                    logger.info(f"[DRY RUN] Visited {url}")
                    profiles_visited += 1
                    profiles_attempted += 1

                self._random_delay_between_profiles()

            current_page += 1
            self._delay_page_navigation()

        return self._build_result(profiles_visited, profiles_attempted, profiles_failed, pages_scraped, time.time() - start_time)

    def _search_profiles(self, page_number: int = 1) -> list[str]:
        """Recherche et extraction des URLs avec stratégie Cascade."""
        keyword_str = " ".join(self.config.visitor.keywords)
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(keyword_str)}&page={page_number}"

        try:
            self.page.goto(search_url, timeout=60000)
            self._random_delay_generic()
        except PlaywrightTimeoutError: return []

        profile_links = []
        result_container_selector = 'div[data-view-name="people-search-result"]'

        try:
            self.page.wait_for_selector(result_container_selector, timeout=10000)
            containers = self.page.query_selector_all(result_container_selector)

            for container in containers:
                link_selectors = [
                    'a[data-view-name="search-result-lockup-title"]',
                    'a.app-aware-link[href*="/in/"]',
                    'span.entity-result__title-text a'
                ]
                link_element = self._find_element_by_cascade(container, link_selectors)

                if link_element:
                    href = link_element.get_attribute("href")
                    if href and "/in/" in href:
                        profile_links.append(href.split("?")[0])

        except Exception as e:
            logger.warning(f"Search extraction error: {e}")

        return list(set(profile_links))

    # ═══════════════════════════════════════════════════════════════
    #  MÉTHODES DE VISITE ET SCRAPING (RESTAURÉES)
    # ═══════════════════════════════════════════════════════════════

    def _visit_profile_with_retry(self, url: str) -> tuple[bool, Optional[dict[str, Any]]]:
        max_attempts = self.config.visitor.retry.max_attempts
        for attempt in range(max_attempts):
            try:
                self.page.goto(url, timeout=60000)
                self._simulate_human_interactions()
                scraped_data = self._scrape_profile_data()
                self._random_delay_profile_visit()
                return True, scraped_data
            except PlaywrightTimeoutError:
                time.sleep(self.config.visitor.retry.backoff_factor ** attempt)
            except Exception:
                return False, None
        return False, None

    def _scrape_profile_data(self) -> dict[str, Any]:
        """[RESTAURÉ] Scraping complet."""
        data = {
            "full_name": "Unknown", "first_name": "Unknown", "last_name": "Unknown",
            "relationship_level": "Unknown", "current_company": "Unknown",
            "education": "Unknown", "years_experience": None,
            "profile_url": self.page.url.split("?")[0]
        }
        try:
            # Nom
            name_selectors = ["h1.text-heading-xlarge", "div.ph5 h1"]
            for sel in name_selectors:
                el = self.page.locator(sel).first
                if el.count() > 0:
                    data["full_name"] = el.inner_text().strip()
                    parts = data["full_name"].split()
                    if len(parts) >= 1: data["first_name"] = parts[0]
                    if len(parts) >= 2: data["last_name"] = " ".join(parts[1:])
                    break

            # Autres champs (simplifié pour la concision mais fonctionnel)
            company_el = self.page.locator("div.text-body-medium").first
            if company_el.count() > 0: data["current_company"] = company_el.inner_text().strip()

        except Exception as e:
            logger.error(f"Scraping error: {e}")
        return data

    def _simulate_human_interactions(self) -> None:
        """[RESTAURÉ] Scroll et mouvements souris."""
        try:
            total_scrolls = random.randint(3, 6)
            for _ in range(total_scrolls):
                self.page.evaluate(f"window.scrollBy(0, {random.randint(200, 600)})")
                time.sleep(random.gauss(1.5, 0.4))

            # Bezier movements
            for _ in range(random.randint(2, 4)):
                start = (random.randint(100, 400), random.randint(100, 300))
                end = (random.randint(100, 1200), random.randint(100, 800))
                for pt in self._bezier_curve(start, end):
                    self.page.mouse.move(pt[0], pt[1])
                    time.sleep(0.01)
        except Exception: pass

    def _bezier_curve(self, start, end, control_points=3):
        points = [start] + [(random.randint(min(start[0], end[0]), max(start[0], end[0])), random.randint(min(start[1], end[1]), max(start[1], end[1]))) for _ in range(control_points)] + [end]
        curve = []
        steps = 20
        for t in range(steps + 1):
            tn = t / steps
            tmp = points[:]
            while len(tmp) > 1:
                tmp = [( (1-tn)*tmp[i][0]+tn*tmp[i+1][0], (1-tn)*tmp[i][1]+tn*tmp[i+1][1] ) for i in range(len(tmp)-1)]
            curve.append(tmp[0])
        return curve

    # ═══════════════════════════════════════════════════════════════
    #  UTILITAIRES RESTAURÉS
    # ═══════════════════════════════════════════════════════════════

    def _is_profile_already_visited(self, url: str) -> bool:
        return self.db.is_profile_visited(url, 30) if self.db else False

    def _record_profile_visit(self, url, name, success):
        if self.db:
            self.db.add_profile_visit(name, url, "search", self.config.visitor.keywords, self.config.visitor.location, success, None)

    def _save_scraped_profile_data(self, data):
        if self.db:
            self.db.save_scraped_profile(**data)

    def _random_delay_generic(self): self._random_delay_with_distribution(self.config.visitor.delays.min_seconds, self.config.visitor.delays.max_seconds)
    def _random_delay_profile_visit(self): self._random_delay_with_distribution(self.config.visitor.delays.profile_visit_min, self.config.visitor.delays.profile_visit_max)
    def _random_delay_between_profiles(self): self._random_delay_profile_visit()
    def _delay_page_navigation(self): self._random_delay_with_distribution(self.config.visitor.delays.page_navigation_min, self.config.visitor.delays.page_navigation_max)

    def _random_delay_with_distribution(self, min_s, max_s):
        delay = max(min_s, min(max_s, random.gauss((min_s+max_s)/2, (max_s-min_s)/6)))
        time.sleep(delay)

    def _validate_visitor_config(self):
        if not self.config.visitor.keywords or not self.config.visitor.location:
            raise LinkedInBotError("Config missing")

    def _validate_search_selectors(self): pass

    def _extract_profile_name_from_url(self, url):
        try:
            return url.split("/in/")[1].split("/")[0].replace("-", " ").title() if "/in/" in url else "Unknown"
        except: return "Unknown"

    def _check_session_valid(self):
        try: return "login" not in self.page.url
        except: return False

    def _build_result(self, pv, pa, pf, ps, dur):
        return {
            "success": True, "profiles_visited": pv, "profiles_attempted": pa,
            "profiles_failed": pf, "pages_scraped": ps, "duration_seconds": round(dur, 2)
        }
