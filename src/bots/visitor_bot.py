"""
Bot LinkedIn pour la visite automatique de profils et le sourcing recruteur.

Ce bot effectue des recherches avancées basées sur des mots-clés, filtres booléens,
localisation et critères de séniorité, puis visite les profils trouvés pour
simuler de l'activité et enrichir la base de données candidats.

Fonctionnalités recruteur:
- Recherche booléenne avancée (AND, OR, NOT, parenthèses)
- Filtres par titre de poste, entreprise, niveau hiérarchique
- Scraping enrichi (compétences complètes, historique, langues)
- Détection "Open to Work"
- Export CSV avec colonnes personnalisables
"""
from datetime import datetime
import json
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

# Mapping LinkedIn seniority levels to URL parameter values
SENIORITY_LEVEL_MAP = {
    "entry": "1",
    "associate": "2",
    "mid-senior": "3",
    "director": "4",
    "vp": "5",
    "cxo": "6",
    "executive": "6",
}

# Mapping connection degrees to LinkedIn network parameter
NETWORK_DEGREE_MAP = {
    "1st": "F",
    "2nd": "S",
    "3rd": "O",
    "3rd+": "O",
}

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
    #  RECHERCHE AVANCÉE (Filtres Booléens + LinkedIn Filters)
    # ═══════════════════════════════════════════════════════════════

    def _build_boolean_keywords(self) -> str:
        """
        Construit une chaîne de recherche booléenne à partir des mots-clés.

        Supporte:
        - AND implicite entre mots simples
        - OR explicite avec |
        - NOT avec -
        - Groupes avec parenthèses
        - Phrases exactes avec guillemets

        Exemple: ["DevOps", "AWS|Azure", "-junior", '"Site Reliability"']
        Donne: DevOps AND (AWS OR Azure) NOT junior "Site Reliability"
        """
        keywords = self.config.visitor.keywords or []
        filters = self.config.visitor.search_filters

        parts = []

        for kw in keywords:
            kw = kw.strip()
            if not kw:
                continue

            # Déjà une phrase entre guillemets
            if kw.startswith('"') and kw.endswith('"'):
                parts.append(kw)
            # Opérateur OR (pipe)
            elif '|' in kw:
                or_terms = [t.strip() for t in kw.split('|') if t.strip()]
                if or_terms:
                    parts.append(f"({' OR '.join(or_terms)})")
            # Exclusion (NOT)
            elif kw.startswith('-'):
                excluded = kw[1:].strip()
                if excluded:
                    parts.append(f'NOT "{excluded}"')
            # Mot simple
            else:
                parts.append(kw)

        # Ajouter les exclusions depuis les filtres
        if filters and filters.keywords_exclude:
            for excl in filters.keywords_exclude:
                if excl.strip():
                    parts.append(f'NOT "{excl.strip()}"')

        return " ".join(parts)

    def _build_advanced_search_url(self, page_number: int = 1) -> str:
        """
        Construit l'URL de recherche LinkedIn avec tous les filtres avancés.

        Paramètres LinkedIn supportés:
        - keywords: Recherche booléenne
        - geoUrn: Location (via texte libre si pas d'URN)
        - titleFreeText: Titre de poste
        - network: Degré de connexion [F=1st, S=2nd, O=3rd+]
        - seniorityIncluded: Niveaux hiérarchiques [1-6]
        - profileLanguage: Langues du profil
        """
        filters = self.config.visitor.search_filters

        # Base keywords avec opérateurs booléens
        keyword_str = self._build_boolean_keywords()

        # Ajouter les titres recherchés aux keywords si présents
        if filters and filters.title:
            title_query = " OR ".join(f'"{t}"' for t in filters.title if t.strip())
            if title_query and keyword_str:
                keyword_str = f"({keyword_str}) AND ({title_query})"
            elif title_query:
                keyword_str = title_query

        # Construction de l'URL de base
        params = {
            "keywords": keyword_str,
            "origin": "FACETED_SEARCH",
            "page": str(page_number),
        }

        # Location (texte libre - LinkedIn fait le matching)
        if self.config.visitor.location:
            # Pour la location, on l'ajoute via geoUrn si possible, sinon via keywords
            params["geoUrn"] = f'["{urllib.parse.quote(self.config.visitor.location)}"]'

        # Filtres de titre (titleFreeText)
        if filters and filters.title:
            # LinkedIn accepte titleFreeText pour filtrage additionnel
            params["titleFreeText"] = filters.title[0] if len(filters.title) == 1 else filters.title[0]

        # Séniorité (niveaux hiérarchiques)
        if filters and filters.seniority_level:
            seniority_values = []
            for level in filters.seniority_level:
                level_key = level.lower().strip()
                if level_key in SENIORITY_LEVEL_MAP:
                    seniority_values.append(SENIORITY_LEVEL_MAP[level_key])
            if seniority_values:
                params["seniorityIncluded"] = f"[{','.join(seniority_values)}]"

        # Langues du profil
        if filters and filters.languages:
            lang_codes = []
            # Mapping de noms vers codes ISO
            lang_map = {
                "français": "fr", "french": "fr",
                "anglais": "en", "english": "en",
                "espagnol": "es", "spanish": "es",
                "allemand": "de", "german": "de",
                "italien": "it", "italian": "it",
                "portugais": "pt", "portuguese": "pt",
                "chinois": "zh", "chinese": "zh",
                "japonais": "ja", "japanese": "ja",
                "arabe": "ar", "arabic": "ar",
            }
            for lang in filters.languages:
                lang_lower = lang.lower().strip()
                if len(lang_lower) == 2:  # Déjà un code ISO
                    lang_codes.append(lang_lower)
                elif lang_lower in lang_map:
                    lang_codes.append(lang_map[lang_lower])
            if lang_codes:
                quoted_codes = ",".join(f'"{c}"' for c in lang_codes)
                params["profileLanguage"] = f"[{quoted_codes}]"

        # Construction de l'URL finale
        base_url = "https://www.linkedin.com/search/results/people/?"
        query_parts = []
        safe_chars = '[]"'
        for key, value in params.items():
            if value:
                query_parts.append(f"{key}={urllib.parse.quote(str(value), safe=safe_chars)}")

        search_url = base_url + "&".join(query_parts)

        logger.info(f"Built advanced search URL: {search_url[:200]}...")
        return search_url

    def _search_profiles(self, page_number: int = 1) -> list[str]:
        """
        Effectue une recherche LinkedIn avancée et retourne les URLs de profils.

        Args:
            page_number: Numéro de la page de résultats à scraper.

        Returns:
            Liste des URLs de profils trouvées.
        """
        # Utilise la construction d'URL avancée
        search_url = self._build_advanced_search_url(page_number)

        try:
            self.page.goto(search_url, timeout=60000)
            self._random_delay_generic()
        except PlaywrightTimeoutError:
            logger.warning(f"Timeout loading search page {page_number}")
            return []

        profile_links = []
        result_container_selector = self.selector_manager.get_combined_selector("visitor.search.result_container") or 'div[data-view-name="people-search-result"]'

        try:
            self.page.wait_for_selector(result_container_selector, timeout=20000)

            # Scroll progressif pour charger (lazy loading)
            for i in range(4):
                self.page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/4})")
                time.sleep(random.uniform(0.8, 1.5))

            containers = self.page.query_selector_all(result_container_selector)
            logger.info(f"Found {len(containers)} profile containers on page {page_number}")

            # Optimization: Fetch selectors once outside the loop
            link_selectors = self.selector_manager.get_selectors("visitor.search.links")
            if not link_selectors:
                link_selectors = [
                    'a[data-view-name="search-result-lockup-title"]',
                    'a.app-aware-link[href*="/in/"]',
                    'span.entity-result__title-text a',
                    'a[href*="/in/"]'  # Fallback générique
                ]

            for container in containers:
                # Stratégie Cascade pour trouver le lien
                link_element = self._find_element_by_cascade(container, link_selectors)

                if link_element:
                    href = link_element.get_attribute("href")
                    if href and "/in/" in href:
                        clean_url = href.split("?")[0]
                        profile_links.append(clean_url)

        except Exception as e:
            logger.warning(f"Search extraction warning: {e}", exc_info=True)

        unique_profiles = list(set(profile_links))
        logger.info(f"Extracted {len(unique_profiles)} unique profiles from page {page_number}")
        return unique_profiles

    # ═══════════════════════════════════════════════════════════════
    #  SCRAPING COMPLET (Amélioré & Scoring)
    # ═══════════════════════════════════════════════════════════════

    def _scrape_profile_data(self) -> dict[str, Any]:
        """
        Scrape complet des données d'un profil LinkedIn pour le sourcing recruteur.

        Données extraites:
        - Identité: nom, prénom, headline
        - Localisation: ville, pays
        - Expérience: historique complet (titre, entreprise, durée)
        - Formation: école, diplôme
        - Compétences: TOUTES les skills (pas de limite)
        - Certifications: toutes les certifications
        - Langues: langues parlées
        - Signaux: Open to Work, degré de connexion
        - Score: Fit Score calculé

        Returns:
            Dictionnaire enrichi avec toutes les données du profil.
        """
        scraped_data = {
            # Identité de base
            "full_name": "Unknown",
            "first_name": "Unknown",
            "last_name": "Unknown",
            "headline": "",
            "summary": "",
            "profile_url": self.page.url.split("?")[0],

            # Localisation
            "location": None,

            # Expérience
            "current_company": "Unknown",
            "job_title": None,
            "years_experience": 0,
            "work_history": [],  # Liste de dict: {title, company, start_date, end_date, duration}

            # Formation
            "school": None,
            "degree": None,
            "education": "Unknown",

            # Compétences & Certifications
            "skills": [],  # TOUTES les compétences
            "certifications": [],
            "endorsements_count": 0,

            # Langues
            "languages": [],

            # Signaux recruteur
            "open_to_work": False,
            "connection_degree": None,  # "1st", "2nd", "3rd+"
            "profile_picture_url": None,

            # Scoring
            "fit_score": 0.0,
            "seniority_level": None,
        }

        try:
            # 0. Scroll préliminaire pour déclencher le lazy-loading
            self._smart_scroll_to_bottom()

            # 1. NOM & PRÉNOM
            self._scrape_name(scraped_data)

            # 2. HEADLINE (Titre actuel)
            self._scrape_headline(scraped_data)

            # 3. LOCALISATION
            self._scrape_location(scraped_data)

            # 4. OPEN TO WORK BADGE
            self._scrape_open_to_work(scraped_data)

            # 5. DEGRÉ DE CONNEXION
            self._scrape_connection_degree(scraped_data)

            # 6. PHOTO DE PROFIL
            self._scrape_profile_picture(scraped_data)

            # 7. RÉSUMÉ (About)
            self._scrape_summary(scraped_data)

            # 8. EXPÉRIENCE COMPLÈTE (Work History)
            self._scrape_experience_full(scraped_data)

            # 9. FORMATION (Education)
            self._scrape_education(scraped_data)

            # 10. COMPÉTENCES COMPLÈTES
            self._scrape_skills_full(scraped_data)

            # 11. CERTIFICATIONS
            self._scrape_certifications(scraped_data)

            # 12. LANGUES
            self._scrape_languages(scraped_data)

            # 13. CALCUL DU FIT SCORE ENRICHI
            scraped_data["fit_score"] = self._calculate_fit_score(scraped_data)

            # 14. DÉDUCTION DU NIVEAU DE SÉNIORITÉ
            scraped_data["seniority_level"] = self._infer_seniority_level(scraped_data)

        except Exception as e:
            logger.error(f"Global scraping error: {e}", exc_info=True)

        return scraped_data

    def _scrape_name(self, data: dict) -> None:
        """Extrait le nom complet du profil."""
        try:
            name_selectors = self.selector_manager.get_selectors("visitor.profile.name") or [
                "h1.text-heading-xlarge",
                "h1[data-anonymize='person-name']",
                ".pv-top-card h1"
            ]
            for selector in name_selectors:
                name_element = self.page.locator(selector).first
                if name_element.count() > 0:
                    full_name = name_element.inner_text(timeout=5000).strip()
                    if full_name:
                        data["full_name"] = full_name
                        parts = full_name.split()
                        if len(parts) >= 2:
                            data["first_name"] = parts[0]
                            data["last_name"] = " ".join(parts[1:])
                        elif len(parts) == 1:
                            data["first_name"] = parts[0]
                            data["last_name"] = ""
                        break
        except Exception:
            pass

    def _scrape_headline(self, data: dict) -> None:
        """Extrait le titre/headline du profil."""
        try:
            headline_selectors = [
                "div.text-body-medium.break-words",
                "div.text-body-medium",
                ".pv-top-card--list .text-body-medium"
            ]
            for selector in headline_selectors:
                headline_el = self.page.locator(selector).first
                if headline_el.count() > 0:
                    headline = headline_el.inner_text().strip()
                    if headline:
                        data["headline"] = headline
                        # Extraire le job title depuis le headline
                        # Format courant: "Job Title at Company" ou "Job Title | Company"
                        if " at " in headline:
                            data["job_title"] = headline.split(" at ")[0].strip()
                        elif " chez " in headline.lower():
                            data["job_title"] = headline.lower().split(" chez ")[0].strip()
                        elif " | " in headline:
                            data["job_title"] = headline.split(" | ")[0].strip()
                        break
        except Exception:
            pass

    def _scrape_location(self, data: dict) -> None:
        """Extrait la localisation du profil."""
        try:
            location_selectors = [
                "span.text-body-small.inline.t-black--light.break-words",
                ".pv-top-card--list-bullet .text-body-small",
                "span[class*='t-black--light']"
            ]
            for selector in location_selectors:
                loc_el = self.page.locator(selector).first
                if loc_el.count() > 0:
                    location = loc_el.inner_text().strip()
                    # Filtrer les valeurs qui ne sont pas des locations
                    if location and not location.startswith("·") and "connexion" not in location.lower():
                        data["location"] = location
                        break
        except Exception:
            pass

    def _scrape_open_to_work(self, data: dict) -> None:
        """Détecte le badge 'Open to Work'."""
        try:
            # Badge visible sur la photo ou dans le profil
            otw_selectors = [
                "div[class*='open-to-work']",
                "span:has-text('Open to work')",
                "span:has-text('En recherche')",
                ".pv-top-card-profile-picture__container .live-video-hero-image--is-open-to-work",
                "[data-test-open-to-work-badge]"
            ]
            for selector in otw_selectors:
                if self.page.locator(selector).count() > 0:
                    data["open_to_work"] = True
                    break

            # Aussi vérifier dans le headline
            if not data["open_to_work"]:
                headline = data.get("headline", "").lower()
                if any(kw in headline for kw in ["open to work", "en recherche", "looking for", "recherche active", "#opentowork"]):
                    data["open_to_work"] = True
        except Exception:
            pass

    def _scrape_connection_degree(self, data: dict) -> None:
        """Extrait le degré de connexion (1st, 2nd, 3rd+)."""
        try:
            degree_selectors = [
                "span.dist-value",
                "span[class*='distance-badge']",
                ".pv-top-card--list span.pvs-inline-entity-button__text"
            ]
            for selector in degree_selectors:
                degree_el = self.page.locator(selector).first
                if degree_el.count() > 0:
                    degree_text = degree_el.inner_text().strip().lower()
                    if "1" in degree_text:
                        data["connection_degree"] = "1st"
                    elif "2" in degree_text:
                        data["connection_degree"] = "2nd"
                    elif "3" in degree_text:
                        data["connection_degree"] = "3rd+"
                    break
        except Exception:
            pass

    def _scrape_profile_picture(self, data: dict) -> None:
        """Extrait l'URL de la photo de profil."""
        try:
            img_selectors = [
                "img.pv-top-card-profile-picture__image",
                ".pv-top-card-profile-picture img",
                "img[data-anonymous='person-image']"
            ]
            for selector in img_selectors:
                img_el = self.page.locator(selector).first
                if img_el.count() > 0:
                    src = img_el.get_attribute("src")
                    if src and "data:image" not in src:  # Ignorer les placeholders base64
                        data["profile_picture_url"] = src
                        break
        except Exception:
            pass

    def _scrape_summary(self, data: dict) -> None:
        """Extrait le résumé/About du profil."""
        try:
            about_section = self.page.locator('section:has-text("Infos"), section:has-text("About")').first
            if about_section.count() > 0:
                # Cliquer sur "Voir plus" si présent
                see_more = about_section.locator('button.inline-show-more-text__button')
                if see_more.count() > 0:
                    try:
                        see_more.click(force=True)
                        time.sleep(0.5)
                    except Exception:
                        pass

                summary_el = about_section.locator('div.inline-show-more-text span[aria-hidden="true"]').first
                if summary_el.count() > 0:
                    data["summary"] = summary_el.inner_text().strip()
        except Exception:
            pass

    def _scrape_experience_full(self, data: dict) -> None:
        """Extrait l'historique complet des expériences professionnelles."""
        try:
            exp_section = self.page.locator('section:has-text("Expérience"), section:has-text("Experience")').first
            if exp_section.count() == 0:
                return

            work_history = []
            all_exps = exp_section.locator('li.pvs-list__paged-list-item, div[class*="pvs-entity"]')
            count = all_exps.count()

            for i in range(min(count, 10)):  # Max 10 expériences
                try:
                    exp_item = all_exps.nth(i)
                    exp_data = {}

                    # Titre du poste
                    title_el = exp_item.locator('span[aria-hidden="true"]').first
                    if title_el.count() > 0:
                        exp_data["title"] = title_el.inner_text().strip()

                    # Entreprise
                    company_el = exp_item.locator('span.t-14.t-normal span[aria-hidden="true"]').first
                    if company_el.count() > 0:
                        company_text = company_el.inner_text().strip()
                        # Format: "Company · Type d'emploi" ou juste "Company"
                        exp_data["company"] = company_text.split("·")[0].strip()

                    # Dates
                    date_el = exp_item.locator('span.pvs-entity__caption-wrapper, span.t-14.t-normal.t-black--light').first
                    if date_el.count() > 0:
                        date_text = date_el.inner_text().strip()
                        exp_data["duration_text"] = date_text

                        # Parser les années
                        years = re.findall(r"\b(19|20)\d{2}\b", date_text)
                        if years:
                            exp_data["start_year"] = int(years[0])
                            if len(years) > 1:
                                exp_data["end_year"] = int(years[1])
                            elif "présent" in date_text.lower() or "present" in date_text.lower():
                                exp_data["end_year"] = datetime.now().year

                    if exp_data.get("title") or exp_data.get("company"):
                        work_history.append(exp_data)

                        # Première expérience = current company
                        if i == 0:
                            data["current_company"] = exp_data.get("company", "Unknown")
                            if not data["job_title"]:
                                data["job_title"] = exp_data.get("title")

                except Exception:
                    continue

            data["work_history"] = work_history

            # Calculer les années d'expérience totales
            if work_history:
                earliest_year = None
                for exp in work_history:
                    if "start_year" in exp:
                        if earliest_year is None or exp["start_year"] < earliest_year:
                            earliest_year = exp["start_year"]
                if earliest_year:
                    data["years_experience"] = max(0, datetime.now().year - earliest_year)

        except Exception:
            pass

    def _scrape_education(self, data: dict) -> None:
        """Extrait les informations de formation."""
        try:
            edu_section = self.page.locator('section:has-text("Formation"), section:has-text("Education")').first
            if edu_section.count() == 0:
                return

            edu_items = edu_section.locator('li.pvs-list__paged-list-item, div[class*="pvs-entity"]')
            if edu_items.count() > 0:
                first_edu = edu_items.first

                # Nom de l'école
                school_el = first_edu.locator('span[aria-hidden="true"]').first
                if school_el.count() > 0:
                    data["school"] = school_el.inner_text().strip()
                    data["education"] = data["school"]

                # Diplôme
                degree_el = first_edu.locator('span.t-14.t-normal span[aria-hidden="true"]').first
                if degree_el.count() > 0:
                    data["degree"] = degree_el.inner_text().strip()
                    if data["school"]:
                        data["education"] = f"{data['degree']} - {data['school']}"

        except Exception:
            pass

    def _scrape_skills_full(self, data: dict) -> None:
        """Extrait TOUTES les compétences (pas de limite)."""
        try:
            skills_section = self.page.locator('section:has-text("Compétences"), section:has-text("Skills")').first
            if skills_section.count() == 0:
                return

            all_skills = []
            total_endorsements = 0

            # Sélecteurs multiples pour les skills
            skill_selectors = [
                'a[data-field="skill_card_skill_topic"]',
                'div[data-field="skill_card_skill_topic"]',
                'span.pv-skill-category-entity__name-text',
                '.pvs-list__item--line-separated span[aria-hidden="true"]'
            ]

            for selector in skill_selectors:
                skill_items = skills_section.locator(selector)
                count = skill_items.count()

                for i in range(min(count, 50)):  # Max 50 skills
                    try:
                        skill_text = skill_items.nth(i).inner_text().strip()
                        if skill_text and skill_text not in all_skills:
                            # Éviter les doublons et les textes parasites
                            if len(skill_text) < 100 and not skill_text.isdigit():
                                all_skills.append(skill_text)
                    except Exception:
                        continue

                if all_skills:
                    break  # On a trouvé des skills, on arrête

            # Compter les endorsements si disponibles
            try:
                endorsement_els = skills_section.locator('span.pvs-skill-category-entity__top-skills-endorsement-count')
                for i in range(endorsement_els.count()):
                    try:
                        count_text = endorsement_els.nth(i).inner_text().strip()
                        count = int(re.sub(r'[^\d]', '', count_text) or 0)
                        total_endorsements += count
                    except Exception:
                        continue
            except Exception:
                pass

            data["skills"] = all_skills
            data["endorsements_count"] = total_endorsements

        except Exception:
            pass

    def _scrape_certifications(self, data: dict) -> None:
        """Extrait toutes les certifications."""
        try:
            cert_section = self.page.locator('section:has-text("Licences et certifications"), section:has-text("Licenses & certifications")').first
            if cert_section.count() == 0:
                return

            certifications = []
            cert_items = cert_section.locator('li.pvs-list__paged-list-item, div[class*="pvs-entity"]')
            count = cert_items.count()

            for i in range(min(count, 20)):  # Max 20 certifications
                try:
                    cert_item = cert_items.nth(i)
                    cert_name_el = cert_item.locator('span[aria-hidden="true"]').first
                    if cert_name_el.count() > 0:
                        cert_name = cert_name_el.inner_text().strip()
                        if cert_name and cert_name not in certifications:
                            certifications.append(cert_name)
                except Exception:
                    continue

            data["certifications"] = certifications

        except Exception:
            pass

    def _scrape_languages(self, data: dict) -> None:
        """Extrait les langues parlées."""
        try:
            lang_section = self.page.locator('section:has-text("Langues"), section:has-text("Languages")').first
            if lang_section.count() == 0:
                return

            languages = []
            lang_items = lang_section.locator('li.pvs-list__paged-list-item, div[class*="pvs-entity"]')
            count = lang_items.count()

            for i in range(min(count, 10)):  # Max 10 langues
                try:
                    lang_item = lang_items.nth(i)
                    lang_name_el = lang_item.locator('span[aria-hidden="true"]').first
                    if lang_name_el.count() > 0:
                        lang_name = lang_name_el.inner_text().strip()
                        if lang_name and lang_name not in languages:
                            languages.append(lang_name)
                except Exception:
                    continue

            data["languages"] = languages

        except Exception:
            pass

    def _infer_seniority_level(self, data: dict) -> Optional[str]:
        """Déduit le niveau de séniorité à partir des données."""
        headline = (data.get("headline") or "").lower()
        job_title = (data.get("job_title") or "").lower()
        years = data.get("years_experience", 0)

        combined = f"{headline} {job_title}"

        # C-Level
        if any(term in combined for term in ["ceo", "cto", "cfo", "coo", "chief", "founder", "co-founder", "président", "directeur général"]):
            return "CXO"

        # VP Level
        if any(term in combined for term in ["vice president", "vp ", "svp", "evp"]):
            return "VP"

        # Director Level
        if any(term in combined for term in ["director", "directeur", "head of"]):
            return "Director"

        # Senior/Lead
        if any(term in combined for term in ["senior", "lead", "principal", "staff", "architect"]):
            return "Mid-Senior"

        # Manager
        if "manager" in combined or "responsable" in combined:
            return "Mid-Senior"

        # Junior/Entry
        if any(term in combined for term in ["junior", "intern", "stagiaire", "apprenti", "entry"]):
            return "Entry"

        # Déduction par années d'expérience
        if years >= 15:
            return "Director"
        elif years >= 8:
            return "Mid-Senior"
        elif years >= 3:
            return "Associate"
        elif years >= 0:
            return "Entry"

        return None

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

        Pondération enrichie pour le sourcing recruteur:
        - Compétences techniques (Keywords match) : 35 pts
        - Expérience (années + critères min/max) : 20 pts
        - Certifications clés : 15 pts
        - Signal "Open to Work" : 15 pts
        - Langues (si critère) : 10 pts
        - Localisation (si match) : 5 pts
        """
        score = 0.0
        target_keywords = self.config.visitor.keywords or []
        filters = self.config.visitor.search_filters

        # 1. COMPÉTENCES & CONTENU (35 pts)
        skills_list = data.get("skills", [])
        skills_text = " ".join(skills_list).lower() if isinstance(skills_list, list) else str(skills_list).lower()
        text_corpus = f"{skills_text} {data.get('headline', '')} {data.get('summary', '')} {data.get('job_title', '')}".lower()

        # Compter les matches de keywords (nettoyer les opérateurs booléens)
        clean_keywords = []
        for kw in target_keywords:
            kw = kw.strip()
            if kw.startswith('-'):
                continue  # Ignorer les exclusions
            if '|' in kw:
                clean_keywords.extend([t.strip() for t in kw.split('|')])
            elif kw.startswith('"') and kw.endswith('"'):
                clean_keywords.append(kw[1:-1])
            else:
                clean_keywords.append(kw)

        matches = sum(1 for kw in clean_keywords if kw.lower() in text_corpus)
        if matches > 0 and len(clean_keywords) > 0:
            match_ratio = matches / len(clean_keywords)
            score += min(35, match_ratio * 45)  # Bonus pour ratio élevé

        # 2. EXPÉRIENCE (20 pts)
        exp = data.get("years_experience", 0)
        exp_min = filters.years_experience_min if filters else None
        exp_max = filters.years_experience_max if filters else None

        if exp:
            # Score de base par années
            if exp >= 10:
                score += 15
            elif exp >= 5:
                score += 12
            elif exp >= 3:
                score += 8
            elif exp >= 1:
                score += 5

            # Bonus si dans la fourchette demandée
            in_range = True
            if exp_min and exp < exp_min:
                in_range = False
            if exp_max and exp > exp_max:
                in_range = False
            if in_range and (exp_min or exp_max):
                score += 5

        # 3. CERTIFICATIONS (15 pts)
        certs = " ".join(data.get("certifications", [])).lower()
        key_certs = [
            "azure", "aws", "gcp", "kubernetes", "docker", "terraform",
            "scrum", "pmp", "cka", "ckad", "itil", "prince2", "safe",
            "cissp", "ccna", "ccnp", "comptia", "pmi", "agile"
        ]
        cert_matches = sum(1 for c in key_certs if c in certs)
        if cert_matches > 0:
            score += min(15, cert_matches * 5)

        # 4. OPEN TO WORK (15 pts)
        if data.get("open_to_work"):
            score += 15
        else:
            # Vérification texte (fallback)
            headline = data.get("headline", "").lower()
            if any(kw in headline for kw in ["open to work", "en recherche", "looking for", "available", "#opentowork"]):
                score += 15

        # 5. LANGUES (10 pts)
        if filters and filters.languages:
            profile_langs = [l.lower() for l in data.get("languages", [])]
            required_langs = [l.lower() for l in filters.languages]
            lang_matches = sum(1 for rl in required_langs if any(rl in pl or pl in rl for pl in profile_langs))
            if lang_matches > 0:
                score += min(10, lang_matches * 5)

        # 6. LOCALISATION (5 pts)
        if self.config.visitor.location:
            profile_location = (data.get("location") or "").lower()
            target_location = self.config.visitor.location.lower()
            if target_location in profile_location or profile_location in target_location:
                score += 5

        return min(100.0, score)

    # ═══════════════════════════════════════════════════════════════
    #  HELPER METHODS (Restaurées & Nettoyées)
    # ═══════════════════════════════════════════════════════════════

    def _visit_profile_with_retry(self, url: str) -> tuple[bool, Optional[dict[str, Any]]]:
        """
        Visite un profil avec retry automatique.

        Returns:
            (True, scraped_data) si succès
            (False, None) si tous les retries échouent
        """
        max_attempts = self.config.visitor.retry.max_attempts or 3
        backoff_factor = self.config.visitor.retry.backoff_factor or 1.5

        last_error = None

        for attempt in range(max_attempts):
            try:
                logger.info(f"Visiting {url} (Attempt {attempt+1}/{max_attempts})")

                self.page.goto(url, timeout=90000, wait_until="domcontentloaded")
                self._simulate_human_interactions()
                data = self._scrape_profile_data()
                self._random_delay_profile_visit()

                logger.debug(f"✅ Successfully visited {url}")
                return True, data

            except PlaywrightTimeoutError as e:
                last_error = e
                if attempt < max_attempts - 1:
                    wait_time = backoff_factor ** attempt
                    logger.warning(
                        f"Timeout visiting {url} (Attempt {attempt+1}/{max_attempts}). "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Failed to visit {url} after {max_attempts} timeout attempts")
                    return False, None

            except Exception as e:
                last_error = e
                logger.warning(f"Visit error on attempt {attempt+1}: {e}")

                if attempt < max_attempts - 1:
                    wait_time = backoff_factor ** (attempt + 1)
                    logger.info(f"Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    return False, None

        logger.error(f"Failed to visit {url}: {last_error}")
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

    def _serialize_safe_to_json(self, obj: Any, max_string_length: int = 1000) -> Optional[str]:
        """
        Sérialise un objet en JSON de manière sécurisée.

        Args:
            obj: Objet à sérialiser (list, dict, etc.)
            max_string_length: Longueur max pour les strings

        Returns:
            JSON string ou None si erreur
        """
        if not obj:
            return None

        def sanitize_value(val):
            """Convertit les valeurs non-sérialisables."""
            if isinstance(val, (str, int, float, bool, type(None))):
                return val
            elif isinstance(val, (list, tuple)):
                return [sanitize_value(v) for v in val]
            elif isinstance(val, dict):
                return {k: sanitize_value(v) for k, v in val.items()}
            else:
                # Objet Playwright, Locator, etc.
                try:
                    return str(val)[:max_string_length]
                except:
                    return f"<{type(val).__name__}>"

        try:
            sanitized = sanitize_value(obj)
            return json.dumps(sanitized, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"JSON serialization failed for {type(obj).__name__}: {e}")
            return None

    def _save_scraped_profile_data(self, data: dict) -> None:
        """
        Sauvegarde les données scrapées enrichies vers la base de données.

        Mapping complet des champs extraits vers les colonnes DB.
        """
        if not self.db:
            return

        try:
            # Ajouter le campaign_id si disponible
            campaign_id = self.campaign_id if hasattr(self, 'campaign_id') else None

            # Convertir les listes en JSON strings pour stockage
            skills_json = self._serialize_safe_to_json(data.get("skills", []))
            certifications_json = self._serialize_safe_to_json(data.get("certifications", []))
            languages_json = self._serialize_safe_to_json(data.get("languages", []))
            work_history_json = self._serialize_safe_to_json(data.get("work_history", []))

            # Appel à la méthode DB avec tous les champs
            self.db.save_scraped_profile(
                # Identité
                profile_url=data.get("profile_url"),
                full_name=data.get("full_name"),
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                headline=data.get("headline"),
                summary=data.get("summary"),

                # Expérience
                current_company=data.get("current_company"),
                years_experience=data.get("years_experience"),

                # Formation (legacy field)
                education=data.get("education"),

                # Compétences & Certifications (JSON)
                skills=skills_json,
                certifications=certifications_json,

                # Score
                fit_score=data.get("fit_score"),

                # Campaign
                campaign_id=campaign_id,

                # ── Nouveaux champs enrichis ──

                # Localisation
                location=data.get("location"),

                # Langues (JSON)
                languages=languages_json,

                # Historique professionnel (JSON)
                work_history=work_history_json,

                # Connexion
                connection_degree=data.get("connection_degree"),

                # Formation détaillée
                school=data.get("school"),
                degree=data.get("degree"),

                # Titre extrait
                job_title=data.get("job_title"),

                # Séniorité
                seniority_level=data.get("seniority_level"),

                # Endorsements
                endorsements_count=data.get("endorsements_count"),

                # Photo
                profile_picture_url=data.get("profile_picture_url"),

                # Open to Work
                open_to_work=data.get("open_to_work"),
            )

            logger.debug(f"Saved enriched profile data for {data.get('full_name', 'Unknown')}")

        except Exception as e:
            logger.error(f"Failed to save profile data: {e}", exc_info=True)

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
    parser.add_argument("--filters-json", help="Filtres avancés en JSON (SearchFiltersConfig structure)")
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

        # Surcharge des filtres avancés
        if args.filters_json:
            try:
                filters_data = json.loads(args.filters_json)
                if isinstance(filters_data, dict):
                    # Mise à jour des champs de search_filters
                    for key, value in filters_data.items():
                        if hasattr(config.visitor.search_filters, key):
                            setattr(config.visitor.search_filters, key, value)
                    logger.info(f"Applied advanced filters from CLI: {filters_data.keys()}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON for --filters-json: {e}")
            except Exception as e:
                logger.error(f"Error applying filters: {e}")

        profiles_limit = args.limit if args.limit else None
        campaign_id = args.campaign_id

        logger.info(f"Starting VisitorBot via CLI with keywords={config.visitor.keywords}, location={config.visitor.location}, campaign_id={campaign_id}")

        with VisitorBot(config=config, profiles_limit_override=profiles_limit, campaign_id=campaign_id) as bot:
            bot.run()

    except Exception as e:
        logger.critical(f"Critical error in VisitorBot CLI execution: {e}", exc_info=True)
        sys.exit(1)
