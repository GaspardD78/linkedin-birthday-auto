"""
Bot LinkedIn pour la visite automatique de profils.

Ce bot effectue des recherches de profils LinkedIn par mots-clés et localisation,
puis visite automatiquement ces profils en simulant un comportement humain.
"""

from datetime import datetime
import random
import re
import time
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

    Ce bot recherche des profils LinkedIn selon des critères (mots-clés, localisation)
    et les visite en simulant un comportement humain naturel.

    Caractéristiques :
    - Recherche multi-critères (keywords + location)
    - Pagination des résultats de recherche
    - Visite avec retry automatique
    - Simulation de comportement humain (scroll, mouvements souris)
    - Tracking des profils visités (évite les doublons)
    - Support du mode dry-run

    Configuration requise :
    ```yaml
    visitor:
      keywords: ["python", "developer"]
      location: "France"
      limits:
        profiles_per_run: 15
        max_pages_to_scrape: 100
      delays:
        profile_visit_min: 15
        profile_visit_max: 35
    ```

    Exemples:
        >>> from src.bots.visitor_bot import VisitorBot
        >>> from src.config import get_config
        >>>
        >>> config = get_config()
        >>> with VisitorBot(config=config) as bot:
        >>>     results = bot.run()
        >>>     print(f"Profils visités : {results['profiles_visited']}")
    """

    def __init__(self, *args, **kwargs):
        """Initialise le VisitorBot."""
        super().__init__(*args, **kwargs)
        self.db = None

        logger.info(
            "VisitorBot initialized",
            keywords=self.config.visitor.keywords,
            location=self.config.visitor.location,
        )

    def run(self) -> dict[str, Any]:
        """Point d'entrée principal avec tracing."""
        return super().run()

    def _run_internal(self) -> dict[str, Any]:
        """
        Exécute le bot pour visiter des profils LinkedIn.

        Workflow:
        1. Validation de la configuration (keywords, location)
        2. Vérification de la connexion LinkedIn
        3. Recherche de profils (avec pagination)
        4. Filtrage des profils déjà visités
        5. Visite des profils avec simulation humaine
        6. Enregistrement en base de données

        Returns:
            Dict contenant les statistiques d'exécution :
            {
                'profiles_visited': int,
                'profiles_attempted': int,
                'profiles_failed': int,
                'pages_scraped': int,
                'duration_seconds': float
            }

        Raises:
            LinkedInBotError: Si la configuration est invalide
            SessionExpiredError: Si la session LinkedIn a expiré
        """
        start_time = time.time()

        logger.info("═" * 70)
        logger.info("🔍 Starting VisitorBot (Profile Visitor)")
        logger.info("═" * 70)
        logger.info(
            "configuration",
            dry_run=self.config.dry_run,
            keywords=self.config.visitor.keywords,
            location=self.config.visitor.location,
            profiles_per_run=self.config.visitor.limits.profiles_per_run,
        )
        logger.info("═" * 70)

        # Validation de la configuration
        self._validate_visitor_config()

        # Initialiser la database si activée
        if self.config.database.enabled:
            try:
                self.db = get_database(self.config.database.db_path)
            except Exception as e:
                logger.warning(f"Database unavailable: {e}")
                self.db = None

        # Vérifier la connexion LinkedIn
        if not self.check_login_status():
            return self._build_error_result("Login verification failed")

        # Valider les sélecteurs de recherche
        self._validate_search_selectors()

        # Variables de tracking
        profiles_visited = 0
        profiles_attempted = 0
        profiles_failed = 0
        pages_scraped = 0

        # Limites de configuration
        profiles_per_run = self.config.visitor.limits.profiles_per_run
        max_pages = self.config.visitor.limits.max_pages_to_scrape
        max_pages_without_new = self.config.visitor.limits.max_pages_without_new

        # Itération sur les pages de résultats
        current_page = 1
        pages_without_new_profiles = 0

        while current_page <= max_pages and profiles_visited < profiles_per_run:
            logger.info(f"Scraping page {current_page}/{max_pages}")
            pages_scraped = current_page

            # Rechercher les profils sur cette page
            profile_urls = self._search_profiles(current_page)

            if not profile_urls:
                logger.info(f"No more profiles found on page {current_page}. Stopping pagination.")
                break

            # Tracker si on a trouvé de nouveaux profils
            found_new_profiles = False

            for url in profile_urls:
                if profiles_visited >= profiles_per_run:
                    logger.info(f"Reached visit limit for this run ({profiles_per_run}).")
                    break

                # Vérifier si déjà visité
                if self._is_profile_already_visited(url):
                    logger.info(f"Skipping already visited profile: {url}")
                    continue

                found_new_profiles = True
                logger.info(f"Visiting profile: {url}")

                # Extraire le nom du profil depuis l'URL
                profile_name = self._extract_profile_name_from_url(url)

                if not self.config.dry_run:
                    # Visiter le profil avec retry et scraping
                    success, scraped_data = self._visit_profile_with_retry(url)

                    # Enregistrer la visite
                    self._record_profile_visit(url, profile_name, success)

                    # Sauvegarder les données scrapées
                    if success and scraped_data:
                        self._save_scraped_profile_data(scraped_data)

                    profiles_attempted += 1
                    if success:
                        profiles_visited += 1
                    else:
                        profiles_failed += 1

                    # Vérifier la session tous les 5 profils
                    if profiles_visited % 5 == 0:
                        if not self._check_session_valid():
                            logger.error("Session is no longer valid. Stopping.")
                            break
                else:
                    logger.info(f"[DRY RUN] Would have visited {url}")
                    self._record_profile_visit(url, profile_name, True)
                    profiles_visited += 1
                    profiles_attempted += 1

                logger.info(f"Profiles visited in this run: {profiles_visited}/{profiles_per_run}")
                self._random_delay_between_profiles()

            # Safety check: pas de nouveaux profils
            if not found_new_profiles:
                pages_without_new_profiles += 1
                logger.info(
                    f"No new profiles on page {current_page} "
                    f"({pages_without_new_profiles}/{max_pages_without_new} pages without new)"
                )
                if pages_without_new_profiles >= max_pages_without_new:
                    logger.info(
                        f"Stopping: {max_pages_without_new} consecutive pages with no new profiles."
                    )
                    break
            else:
                pages_without_new_profiles = 0  # Reset counter

            # Si limite atteinte, arrêter
            if profiles_visited >= profiles_per_run:
                break

            current_page += 1

            # Délai entre navigation de pages
            self._delay_page_navigation()

        # Résumé final
        duration = time.time() - start_time

        logger.info("")
        logger.info("═" * 70)
        logger.info("✅ VisitorBot execution completed")
        logger.info("═" * 70)
        logger.info(
            "execution_stats",
            profiles_visited=profiles_visited,
            profiles_attempted=profiles_attempted,
            profiles_failed=profiles_failed,
            pages_scraped=pages_scraped,
            duration=f"{duration:.1f}s",
        )
        logger.info("═" * 70)

        return self._build_result(
            profiles_visited=profiles_visited,
            profiles_attempted=profiles_attempted,
            profiles_failed=profiles_failed,
            pages_scraped=pages_scraped,
            duration_seconds=duration,
        )

    # ═══════════════════════════════════════════════════════════════
    # MÉTHODES DE RECHERCHE ET NAVIGATION
    # ═══════════════════════════════════════════════════════════════

    def _search_profiles(self, page_number: int = 1) -> list[str]:
        """
        Effectue une recherche LinkedIn et retourne les URLs de profils.

        Args:
            page_number: Numéro de la page de résultats

        Returns:
            Liste d'URLs de profils trouvés
        """
        keyword_str = " ".join(self.config.visitor.keywords)
        search_url = (
            f"https://www.linkedin.com/search/results/people/"
            f"?keywords={urllib.parse.quote(keyword_str)}"
            f"&location={urllib.parse.quote(self.config.visitor.location)}"
            f"&origin=GLOBAL_SEARCH_HEADER"
            f"&page={page_number}"
        )

        logger.info(f"Navigating to search URL (page {page_number}): {search_url}")

        try:
            self.page.goto(search_url, timeout=90000)
            self._random_delay_generic()
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout loading search page: {e}")
            return []

        # Screenshot pour debug
        if self.config.debug.save_screenshots:
            self.browser_manager.take_screenshot("search_results_page.png")

        profile_links = []

        # Sélecteurs de recherche (Fallback Strategy)
        result_container_strategies = [
            'div[data-view-name="people-search-result"]',
            'li.reusable-search__result-container',
            'li.search-result'
        ]

        try:
            # Attendre les résultats
            # On attend le premier sélecteur qui marche
            found_selector = None
            for selector in result_container_strategies:
                try:
                    self.page.wait_for_selector(selector, timeout=5000)
                    found_selector = selector
                    break
                except Exception:
                    continue

            if not found_selector:
                # Fallback sur un timeout plus long avec le sélecteur principal
                self.page.wait_for_selector(result_container_strategies[0], timeout=15000)
                found_selector = result_container_strategies[0]

            # Scroller pour charger plus de résultats
            for _ in range(5):
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self._random_delay_generic()

            # Extraire les liens
            result_containers = self.page.query_selector_all(found_selector)
            logger.info(f"Found {len(result_containers)} result containers on the page.")

            for container in result_containers:
                # Stratégie de recherche de lien dans le conteneur
                link_strategies = [
                   'a[data-view-name="search-result-lockup-title"]',
                   'span.entity-result__title-text a.app-aware-link',
                   'a.app-aware-link'
                ]

                link_element = None
                for link_sel in link_strategies:
                    link_element = container.query_selector(link_sel)
                    if link_element:
                        break

                if link_element:
                    href = link_element.get_attribute("href")
                    if href and "linkedin.com/in/" in href:
                        # Nettoyer l'URL
                        clean_url = href.split("?")[0]
                        profile_links.append(clean_url)

            logger.info(f"Extracted {len(profile_links)} potential profiles from containers.")

        except PlaywrightTimeoutError:
            logger.warning("Could not find profile result containers on the search results page.")
            if self.config.debug.save_screenshots:
                self.browser_manager.take_screenshot("error_search_no_results.png")

        # Retourner URLs uniques
        return list(dict.fromkeys(profile_links))

    def _visit_profile_with_retry(self, url: str) -> tuple[bool, Optional[dict[str, Any]]]:
        """
        Visite un profil avec retry logic et exponential backoff.

        Args:
            url: URL du profil à visiter

        Returns:
            Tuple (success, scraped_data) :
            - success: True si la visite a réussi, False sinon
            - scraped_data: Dictionnaire avec les données scrapées (ou None en cas d'échec)
        """
        max_attempts = self.config.visitor.retry.max_attempts
        backoff_factor = self.config.visitor.retry.backoff_factor

        for attempt in range(max_attempts):
            try:
                logger.info(f"Visiting profile (attempt {attempt + 1}/{max_attempts}): {url}")
                self.page.goto(url, timeout=60000)

                # Simuler des interactions humaines
                self._simulate_human_interactions()

                # Scraper les données du profil
                scraped_data = self._scrape_profile_data()

                # Délai de visite
                self._random_delay_profile_visit()

                return True, scraped_data

            except PlaywrightTimeoutError as e:
                wait_time = backoff_factor**attempt
                logger.warning(
                    f"Timeout visiting profile (attempt {attempt + 1}/{max_attempts}): {e}"
                )

                if attempt < max_attempts - 1:
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to visit profile after {max_attempts} attempts")
                    return False, None

            except Exception as e:
                logger.error(f"Unexpected error visiting profile: {e}")
                return False, None

        return False, None

    # ═══════════════════════════════════════════════════════════════
    # SIMULATION DE COMPORTEMENT HUMAIN
    # ═══════════════════════════════════════════════════════════════

    def _simulate_human_interactions(self) -> None:
        """Simule des interactions humaines (scroll, mouvements de souris)."""
        try:
            # Scroll aléatoire avec accélération/décélération
            total_scrolls = random.randint(3, 6)
            for i in range(total_scrolls):
                progress = i / total_scrolls
                if progress < 0.3:
                    scroll_amount = int(200 + (progress / 0.3) * 400)
                elif progress > 0.7:
                    scroll_amount = int(600 - ((progress - 0.7) / 0.3) * 400)
                else:
                    scroll_amount = random.randint(400, 600)

                self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                time.sleep(random.gauss(1.5, 0.4))

            # Mouvements de souris avec courbes de Bézier
            mouse_movements = random.randint(2, 4)
            current_pos = (random.randint(100, 400), random.randint(100, 300))

            for _ in range(mouse_movements):
                target_pos = (random.randint(100, 1200), random.randint(100, 800))

                curve = self._bezier_curve(current_pos, target_pos, control_points=2)

                for point in curve:
                    self.page.mouse.move(point[0], point[1])
                    time.sleep(random.uniform(0.01, 0.03))

                current_pos = target_pos
                time.sleep(random.gauss(0.8, 0.2))

            # Temps de lecture variable
            reading_time = random.gauss(10, 3)
            reading_time = max(5, min(15, reading_time))
            logger.debug(f"Simulation lecture: {reading_time:.1f}s")
            time.sleep(reading_time)

        except Exception as e:
            logger.debug(f"Erreur lors de la simulation d'interactions (non critique): {e}")

    def _bezier_curve(
        self, start: tuple[int, int], end: tuple[int, int], control_points: int = 3
    ) -> list[tuple[int, int]]:
        """
        Génère une courbe de Bézier pour mouvement de souris naturel.

        Args:
            start: Point de départ (x, y)
            end: Point d'arrivée (x, y)
            control_points: Nombre de points de contrôle

        Returns:
            Liste de points le long de la courbe
        """
        points = [start]
        for _ in range(control_points):
            x = random.randint(min(start[0], end[0]), max(start[0], end[0]))
            y = random.randint(min(start[1], end[1]), max(start[1], end[1]))
            points.append((x, y))
        points.append(end)

        curve_points = []
        steps = 20

        for t in range(steps + 1):
            t_normalized = t / steps
            temp_points = points[:]
            while len(temp_points) > 1:
                new_points = []
                for i in range(len(temp_points) - 1):
                    x = (1 - t_normalized) * temp_points[i][0] + t_normalized * temp_points[i + 1][
                        0
                    ]
                    y = (1 - t_normalized) * temp_points[i][1] + t_normalized * temp_points[i + 1][
                        1
                    ]
                    new_points.append((int(x), int(y)))
                temp_points = new_points
            curve_points.append(temp_points[0])

        return curve_points

    # ═══════════════════════════════════════════════════════════════
    # SCRAPING DE DONNÉES DE PROFILS
    # ═══════════════════════════════════════════════════════════════

    def _scrape_profile_data(self) -> dict[str, Any]:
        """
        Scrape les données détaillées d'un profil LinkedIn.

        Cette méthode extrait les informations suivantes du DOM :
        - Nom complet, prénom, nom de famille
        - Niveau de relation (1er, 2e, 3e)
        - Entreprise actuelle
        - Formation/Diplôme
        - Années d'expérience (estimées)

        Returns:
            Dictionnaire contenant les données scrapées :
            {
                'full_name': str,
                'first_name': str,
                'last_name': str,
                'relationship_level': str,
                'current_company': str,
                'education': str,
                'years_experience': int,
                'profile_url': str
            }

        Note:
            Gère les cas où les éléments sont introuvables (valeurs par défaut).
            Ne fait pas planter le bot en cas d'erreur de scraping.
        """
        scraped_data = {
            "full_name": "Unknown",
            "first_name": "Unknown",
            "last_name": "Unknown",
            "relationship_level": "Unknown",
            "current_company": "Unknown",
            "education": "Unknown",
            "years_experience": None,
            "profile_url": self.page.url.split("?")[0],  # URL nettoyée
        }

        try:
            # ─────────────────────────────────────────────────────────
            # 1. NOM COMPLET
            # ─────────────────────────────────────────────────────────
            try:
                # Sélecteur principal pour le nom
                name_selectors = [
                    "h1.text-heading-xlarge",
                    "h1.inline",
                    "div.ph5 h1",
                    "h1[class*='heading']",
                ]

                # Utilisation de la méthode de fallback du BaseBot si disponible
                if hasattr(self, '_find_element_by_cascade'):
                    name_element = self._find_element_by_cascade(self.page, name_selectors)
                    if name_element:
                         full_name = name_element.inner_text(timeout=5000).strip()
                         if full_name and len(full_name) > 0:
                            scraped_data["full_name"] = full_name

                            # Séparer prénom et nom
                            name_parts = full_name.split()
                            if len(name_parts) >= 2:
                                scraped_data["first_name"] = name_parts[0]
                                scraped_data["last_name"] = " ".join(name_parts[1:])
                            elif len(name_parts) == 1:
                                scraped_data["first_name"] = name_parts[0]
                                scraped_data["last_name"] = ""
                else:
                    # Fallback manuel si la méthode n'est pas héritée
                    for selector in name_selectors:
                        name_element = self.page.locator(selector).first
                        if name_element.count() > 0:
                            full_name = name_element.inner_text(timeout=5000).strip()
                            if full_name and len(full_name) > 0:
                                scraped_data["full_name"] = full_name

                                # Séparer prénom et nom
                                name_parts = full_name.split()
                                if len(name_parts) >= 2:
                                    scraped_data["first_name"] = name_parts[0]
                                    scraped_data["last_name"] = " ".join(name_parts[1:])
                                elif len(name_parts) == 1:
                                    scraped_data["first_name"] = name_parts[0]
                                    scraped_data["last_name"] = ""
                                break

            except Exception as e:
                logger.debug(f"Could not extract full name: {e}")

            # ─────────────────────────────────────────────────────────
            # 2. NIVEAU DE RELATION
            # ─────────────────────────────────────────────────────────
            try:
                relationship_selectors = [
                    "span.dist-value",
                    "div.pv-top-card--list-bullet li",
                    "span[class*='distance']",
                ]

                for selector in relationship_selectors:
                    rel_element = self.page.locator(selector).first
                    if rel_element.count() > 0:
                        rel_text = rel_element.inner_text(timeout=5000).strip()
                        # Chercher "1er", "2e", "3e" ou "1st", "2nd", "3rd"
                        if any(
                            level in rel_text.lower()
                            for level in ["1er", "2e", "3e", "1st", "2nd", "3rd"]
                        ):
                            scraped_data["relationship_level"] = rel_text
                            break

            except Exception as e:
                logger.debug(f"Could not extract relationship level: {e}")

            # ─────────────────────────────────────────────────────────
            # 3. ENTREPRISE ACTUELLE
            # ─────────────────────────────────────────────────────────
            try:
                # Chercher dans le sous-titre sous le nom
                company_selectors = [
                    "div.text-body-medium",
                    "div.pv-text-details__right-panel span[aria-hidden='true']",
                    "div[class*='inline-show-more-text']",
                ]

                for selector in company_selectors:
                    company_element = self.page.locator(selector).first
                    if company_element.count() > 0:
                        company_text = company_element.inner_text(timeout=5000).strip()
                        if company_text and len(company_text) > 0:
                            # Extraire l'entreprise (souvent après "chez" ou "at")
                            if " chez " in company_text.lower():
                                scraped_data["current_company"] = company_text.split(" chez ")[
                                    -1
                                ].strip()
                            elif " at " in company_text.lower():
                                scraped_data["current_company"] = company_text.split(" at ")[-1].strip()
                            else:
                                scraped_data["current_company"] = company_text
                            break

                # Fallback: chercher dans la section Expérience
                if scraped_data["current_company"] == "Unknown":
                    experience_section = self.page.locator('section:has-text("Expérience")').first
                    if experience_section.count() > 0:
                        first_experience = experience_section.locator(
                            'div[class*="pvs-entity"]'
                        ).first
                        if first_experience.count() > 0:
                            company_in_exp = (
                                first_experience.locator('span[aria-hidden="true"]')
                                .nth(1)
                                .inner_text(timeout=5000)
                                .strip()
                            )
                            if company_in_exp:
                                scraped_data["current_company"] = company_in_exp

            except Exception as e:
                logger.debug(f"Could not extract current company: {e}")

            # ─────────────────────────────────────────────────────────
            # 4. FORMATION
            # ─────────────────────────────────────────────────────────
            try:
                education_selectors = [
                    'section:has-text("Formation")',
                    'section:has-text("Education")',
                    'section[id*="education"]',
                ]

                for selector in education_selectors:
                    education_section = self.page.locator(selector).first
                    if education_section.count() > 0:
                        # Premier établissement
                        first_education = education_section.locator(
                            'div[class*="pvs-entity"]'
                        ).first
                        if first_education.count() > 0:
                            education_text = (
                                first_education.locator('span[aria-hidden="true"]')
                                .first.inner_text(timeout=5000)
                                .strip()
                            )
                            if education_text:
                                scraped_data["education"] = education_text
                                break

            except Exception as e:
                logger.debug(f"Could not extract education: {e}")

            # ─────────────────────────────────────────────────────────
            # 5. ANNÉES D'EXPÉRIENCE
            # ─────────────────────────────────────────────────────────
            try:
                # Chercher dans la section Expérience
                experience_section = self.page.locator(
                    'section:has-text("Expérience"), section:has-text("Experience")'
                ).first

                if experience_section.count() > 0:
                    # Récupérer toutes les expériences
                    all_experiences = experience_section.locator('div[class*="pvs-entity"]')
                    experience_count = all_experiences.count()

                    if experience_count > 0:
                        # Chercher la plus ancienne expérience (dernière dans la liste)
                        last_experience = all_experiences.nth(experience_count - 1)

                        # Chercher les dates (format varié : "2018 - 2020", "Jan 2018", etc.)
                        date_spans = last_experience.locator('span[class*="date"]')

                        if date_spans.count() > 0:
                            date_text = date_spans.first.inner_text(timeout=5000).strip()

                            # Parser la date de début (simple heuristique)
                            # Chercher une année à 4 chiffres
                            years = re.findall(r"\b(19|20)\d{2}\b", date_text)
                            if years:
                                start_year = int(years[0])
                                current_year = datetime.now().year
                                scraped_data["years_experience"] = max(0, current_year - start_year)

            except Exception as e:
                logger.debug(f"Could not extract years of experience: {e}")

            logger.info(
                f"Données récupérées pour {scraped_data['full_name']} "
                f"({scraped_data['current_company']})"
            )

        except Exception as e:
            logger.error(f"Error during profile scraping: {e}")

        return scraped_data

    # ═══════════════════════════════════════════════════════════════
    # GESTION DES DÉLAIS
    # ═══════════════════════════════════════════════════════════════

    def _random_delay_generic(self) -> None:
        """Délai aléatoire générique entre actions."""
        min_sec = self.config.visitor.delays.min_seconds
        max_sec = self.config.visitor.delays.max_seconds
        self._random_delay_with_distribution(min_sec, max_sec)

    def _random_delay_profile_visit(self) -> None:
        """Délai aléatoire pour la visite d'un profil."""
        min_sec = self.config.visitor.delays.profile_visit_min
        max_sec = self.config.visitor.delays.profile_visit_max
        self._random_delay_with_distribution(min_sec, max_sec)

    def _random_delay_between_profiles(self) -> None:
        """Délai entre la visite de deux profils."""
        if self.config.dry_run:
            delay = random.randint(1, 2)
            logger.info(f"⏸️  Pause (dry-run): {delay}s")
            time.sleep(delay)
        else:
            self._random_delay_profile_visit()

    def _delay_page_navigation(self) -> None:
        """Délai entre la navigation de pages de résultats."""
        min_sec = self.config.visitor.delays.page_navigation_min
        max_sec = self.config.visitor.delays.page_navigation_max
        self._random_delay_with_distribution(min_sec, max_sec)

    def _random_delay_with_distribution(self, min_seconds: float, max_seconds: float) -> None:
        """
        Délai aléatoire avec distribution normale pour plus de réalisme.

        Args:
            min_seconds: Durée minimale
            max_seconds: Durée maximale
        """
        mean = (min_seconds + max_seconds) / 2
        std_dev = (max_seconds - min_seconds) / 6
        delay = random.gauss(mean, std_dev)

        # Clamp
        delay = max(min_seconds, min(max_seconds, delay))

        # Pause prolongée occasionnelle (10% du temps)
        if random.random() < 0.1:
            extra_delay = random.uniform(30, 60)
            delay += extra_delay
            logger.info(f"Pause prolongée: {delay:.1f}s")

        time.sleep(delay)

    # ═══════════════════════════════════════════════════════════════
    # GESTION DE LA BASE DE DONNÉES
    # ═══════════════════════════════════════════════════════════════

    def _is_profile_already_visited(self, profile_url: str, days: int = 30) -> bool:
        """
        Vérifie si un profil a été visité récemment.

        Args:
            profile_url: URL du profil
            days: Nombre de jours à vérifier

        Returns:
            True si déjà visité, False sinon
        """
        if not self.db:
            return False

        try:
            return self.db.is_profile_visited(profile_url, days)
        except Exception as e:
            logger.error(f"Error checking if profile visited: {e}")
            return False

    def _record_profile_visit(self, profile_url: str, profile_name: str, success: bool) -> None:
        """
        Enregistre une visite de profil dans la database.

        Args:
            profile_url: URL du profil
            profile_name: Nom extrait du profil
            success: Si la visite a réussi
        """
        if not self.db:
            return

        try:
            source_search = (
                "keyword_search" if not self.config.dry_run else "keyword_search_dry_run"
            )

            self.db.add_profile_visit(
                profile_name=profile_name,
                profile_url=profile_url,
                source_search=source_search,
                keywords=self.config.visitor.keywords,
                location=self.config.visitor.location,
                success=success,
                error_message=None if success else "Failed after retries",
            )
        except Exception as e:
            logger.error(f"Failed to record profile visit to database: {e}")

    def _save_scraped_profile_data(self, scraped_data: dict[str, Any]) -> None:
        """
        Sauvegarde les données scrapées dans la base de données.

        Args:
            scraped_data: Dictionnaire contenant les données du profil scrapé
        """
        if not self.db:
            logger.warning("Database not available, cannot save scraped data")
            return

        try:
            self.db.save_scraped_profile(
                profile_url=scraped_data.get("profile_url"),
                first_name=scraped_data.get("first_name"),
                last_name=scraped_data.get("last_name"),
                full_name=scraped_data.get("full_name"),
                relationship_level=scraped_data.get("relationship_level"),
                current_company=scraped_data.get("current_company"),
                education=scraped_data.get("education"),
                years_experience=scraped_data.get("years_experience"),
            )
            logger.info(f"✅ Scraped data saved for {scraped_data.get('full_name')}")
        except Exception as e:
            logger.error(f"Failed to save scraped profile data to database: {e}")

    # ═══════════════════════════════════════════════════════════════
    # UTILITAIRES
    # ═══════════════════════════════════════════════════════════════

    def _extract_profile_name_from_url(self, url: str) -> str:
        """
        Extrait le nom du profil depuis l'URL LinkedIn.

        Args:
            url: URL du profil

        Returns:
            Nom extrait ou 'Unknown'
        """
        try:
            if "/in/" not in url:
                return "Unknown"

            parts = url.split("/in/")
            if len(parts) < 2:
                return "Unknown"

            identifier = parts[1].split("/")[0].split("?")[0]
            name = identifier.replace("-", " ").title()

            if not any(c.isalpha() for c in name):
                return "Unknown"

            return name

        except Exception as e:
            logger.warning(f"Error extracting profile name from URL {url}: {e}")
            return "Unknown"

    def _validate_visitor_config(self) -> None:
        """
        Valide la configuration du visitor.

        Raises:
            LinkedInBotError: Si la configuration est invalide
        """
        if not self.config.visitor.keywords or len(self.config.visitor.keywords) == 0:
            raise LinkedInBotError(
                "visitor.keywords est vide. Configurez au moins un mot-clé dans config.yaml",
                error_code=None,
                recoverable=False,
            )

        if not self.config.visitor.location or not self.config.visitor.location.strip():
            raise LinkedInBotError(
                "visitor.location est vide. Configurez une localisation dans config.yaml",
                error_code=None,
                recoverable=False,
            )

        logger.info(
            "✅ Visitor configuration validated",
            keywords_count=len(self.config.visitor.keywords),
            location=self.config.visitor.location,
        )

    def _validate_search_selectors(self) -> None:
        """Valide que les sélecteurs de recherche fonctionnent (optionnel)."""
        try:
            logger.info("🔍 Validating search page selectors...")
            test_search_url = (
                f"https://www.linkedin.com/search/results/people/"
                f"?keywords={self.config.visitor.keywords[0]}"
            )
            self.page.goto(test_search_url, timeout=60000)
            self.random_delay(1, 2)

            # Vérifier que le sélecteur existe
            result_container_selector = 'div[data-view-name="people-search-result"]'
            try:
                self.page.wait_for_selector(result_container_selector, timeout=10000)
                logger.info("✅ Search selectors are valid")
            except PlaywrightTimeoutError:
                logger.warning("⚠️ Search selectors validation failed - LinkedIn may have changed")

        except Exception as e:
            logger.warning(f"⚠️ Selector validation failed: {e}")

    def _check_session_valid(self) -> bool:
        """
        Vérifie que la session LinkedIn est toujours valide.

        Returns:
            True si valide, False sinon
        """
        try:
            current_url = self.page.url

            if "login" in current_url or "checkpoint" in current_url or "authwall" in current_url:
                logger.warning(f"Session appears invalid - on auth page: {current_url}")
                return False

            user_menu_selectors = [
                "img.global-nav__me-photo",
                "div.global-nav__me",
                "button[aria-label*='View profile']",
                "a[href*='/in/']",
            ]

            for selector in user_menu_selectors:
                try:
                    self.page.wait_for_selector(selector, timeout=10000)
                    logger.debug(f"Session valid - found selector: {selector}")
                    return True
                except PlaywrightTimeoutError:
                    continue

            logger.warning("Session may be invalid - couldn't find any user menu indicators")
            return False

        except Exception as e:
            logger.error(f"Error checking session validity: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # CONSTRUCTION DES RÉSULTATS
    # ═══════════════════════════════════════════════════════════════

    def _build_result(
        self,
        profiles_visited: int,
        profiles_attempted: int,
        profiles_failed: int,
        pages_scraped: int,
        duration_seconds: float,
    ) -> dict[str, Any]:
        """Construit le dictionnaire de résultats."""
        success_rate = (
            (profiles_visited / profiles_attempted * 100) if profiles_attempted > 0 else 0
        )

        return {
            "success": True,
            "bot_type": "visitor",
            "profiles_visited": profiles_visited,
            "profiles_attempted": profiles_attempted,
            "profiles_failed": profiles_failed,
            "success_rate": round(success_rate, 1),
            "pages_scraped": pages_scraped,
            "avg_time_per_profile": (
                duration_seconds / profiles_attempted if profiles_attempted > 0 else 0
            ),
            "duration_seconds": round(duration_seconds, 2),
            "dry_run": self.config.dry_run,
            "timestamp": datetime.now().isoformat(),
        }

    def _build_error_result(self, error_message: str) -> dict[str, Any]:
        """Construit un résultat d'erreur."""
        return {
            "success": False,
            "bot_type": "visitor",
            "error": error_message,
            "profiles_visited": 0,
            "profiles_attempted": 0,
            "timestamp": datetime.now().isoformat(),
        }


# Helper function pour usage simplifié
def run_visitor_bot(config=None, dry_run: bool = False) -> dict[str, Any]:
    """
    Fonction helper pour exécuter le VisitorBot facilement.

    Args:
        config: Configuration (ou None pour config par défaut)
        dry_run: Override du mode dry-run

    Returns:
        Résultats de l'exécution

    Exemples:
        >>> from src.bots.visitor_bot import run_visitor_bot
        >>>
        >>> # Mode dry-run
        >>> results = run_visitor_bot(dry_run=True)
        >>> print(f"Visited {results['profiles_visited']} profiles")
        >>>
        >>> # Mode production
        >>> results = run_visitor_bot()
    """
    from ..config import get_config

    if config is None:
        config = get_config()

    if dry_run:
        config.dry_run = True

    with VisitorBot(config=config) as bot:
        return bot.run()
