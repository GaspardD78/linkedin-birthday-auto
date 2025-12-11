"""
API Router pour le Sourcing Recruteur - Gestion des campagnes, profils et exports.

Workflow Recruteur:
1. Créer une fiche de poste (JobDescription)
2. Configurer une campagne de recherche (Campaign)
3. Lancer la recherche automatisée (VisitorBot)
4. Consulter et filtrer les profils trouvés
5. Exporter les candidats qualifiés (CSV)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import csv
import io
import json
import subprocess
import sys

from src.core.database import get_database
from src.config.config_manager import get_config
from src.utils.logging import get_logger
from ..security import verify_api_key

router = APIRouter(prefix="/sourcing", tags=["Sourcing Recruteur"])
logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
# MODÈLES PYDANTIC
# ═══════════════════════════════════════════════════════════════

class ProfileResponse(BaseModel):
    """Profil candidat enrichi avec toutes les données scrapées."""
    id: int
    profile_url: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    current_company: Optional[str] = None
    education: Optional[str] = None
    years_experience: Optional[int] = None
    skills: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    fit_score: Optional[float] = None
    scraped_at: str
    campaign_id: Optional[int] = None
    # Champs enrichis
    location: Optional[str] = None
    languages: Optional[List[str]] = None
    work_history: Optional[List[Dict[str, Any]]] = None
    connection_degree: Optional[str] = None
    school: Optional[str] = None
    degree: Optional[str] = None
    job_title: Optional[str] = None
    seniority_level: Optional[str] = None
    endorsements_count: Optional[int] = None
    profile_picture_url: Optional[str] = None
    open_to_work: Optional[bool] = None


class ProfileListResponse(BaseModel):
    profiles: List[ProfileResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class SearchFilters(BaseModel):
    """Filtres de recherche pour les profils scrapés."""
    keywords: Optional[List[str]] = Field(default=None, description="Mots-clés (recherche dans nom, headline, skills)")
    keywords_exclude: Optional[List[str]] = Field(default=None, description="Mots-clés à exclure")
    min_fit_score: Optional[float] = Field(default=None, ge=0, le=100)
    max_fit_score: Optional[float] = Field(default=None, ge=0, le=100)
    min_years_experience: Optional[int] = Field(default=None, ge=0)
    max_years_experience: Optional[int] = Field(default=None, ge=0)
    current_company: Optional[List[str]] = Field(default=None, description="Entreprises actuelles")
    skills_required: Optional[List[str]] = Field(default=None, description="Compétences requises (au moins une)")
    open_to_work_only: Optional[bool] = Field(default=False)
    campaign_id: Optional[int] = Field(default=None)
    scraped_after: Optional[str] = Field(default=None, description="Date ISO minimum")
    scraped_before: Optional[str] = Field(default=None, description="Date ISO maximum")


class ExportRequest(BaseModel):
    """Paramètres d'export CSV."""
    filters: Optional[SearchFilters] = Field(default=None)
    columns: Optional[List[str]] = Field(
        default=None,
        description="Colonnes à exporter. Si vide, exporte toutes les colonnes."
    )
    filename: Optional[str] = Field(default="sourcing_export.csv")


class SearchTemplateCreate(BaseModel):
    """Template de recherche sauvegardé."""
    name: str
    description: Optional[str] = None
    filters: SearchFilters


class SearchTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    filters: Dict[str, Any]
    created_at: str
    updated_at: str


# ═══════════════════════════════════════════════════════════════
# MODÈLES CAMPAGNES (Fiche de poste → Recherche)
# ═══════════════════════════════════════════════════════════════

class JobDescriptionCreate(BaseModel):
    """Fiche de poste pour définir une recherche."""
    title: str = Field(..., description="Titre du poste (ex: DevOps Engineer)")
    description: Optional[str] = Field(None, description="Description du poste")
    # Critères de recherche
    keywords: List[str] = Field(..., description="Mots-clés booléens (ex: ['DevOps', 'AWS|Azure', '-junior'])")
    location: str = Field("France", description="Localisation de recherche")
    # Filtres avancés
    title_filters: Optional[List[str]] = Field(None, description="Titres de poste recherchés")
    keywords_exclude: Optional[List[str]] = Field(None, description="Mots-clés à exclure")
    seniority_level: Optional[List[str]] = Field(None, description="Niveaux: Entry, Associate, Mid-Senior, Director, VP, CXO")
    languages: Optional[List[str]] = Field(None, description="Langues requises")
    years_experience_min: Optional[int] = Field(None, ge=0, le=50)
    years_experience_max: Optional[int] = Field(None, ge=0, le=50)
    # Paramètres de campagne
    profiles_target: int = Field(50, ge=1, le=500, description="Nombre de profils cibles")


class CampaignCreate(BaseModel):
    """Création d'une campagne de sourcing."""
    name: str = Field(..., description="Nom de la campagne")
    job_description: JobDescriptionCreate
    auto_start: bool = Field(False, description="Démarrer automatiquement après création")


class CampaignResponse(BaseModel):
    """Réponse détaillée d'une campagne."""
    id: int
    name: str
    status: str  # pending, running, completed, failed
    job_title: str
    keywords: List[str]
    location: str
    profiles_target: int
    profiles_found: int
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    filters: Dict[str, Any]


class CampaignStartRequest(BaseModel):
    """Paramètres pour démarrer une campagne."""
    profiles_limit: Optional[int] = Field(None, ge=1, le=500, description="Override limite de profils")
    dry_run: bool = Field(False, description="Mode simulation (pas de visite)")


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS - CAMPAGNES
# ═══════════════════════════════════════════════════════════════

@router.post("/campaigns", response_model=CampaignResponse)
async def create_campaign(
    campaign: CampaignCreate,
    background_tasks: BackgroundTasks,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Crée une nouvelle campagne de sourcing à partir d'une fiche de poste.

    Workflow:
    1. Reçoit la fiche de poste avec critères
    2. Crée la campagne en base
    3. Optionnellement démarre la recherche en background
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        job = campaign.job_description

        # Préparer les filtres JSON
        filters = {
            "title_filters": job.title_filters or [],
            "keywords_exclude": job.keywords_exclude or [],
            "seniority_level": job.seniority_level or [],
            "languages": job.languages or [],
            "years_experience_min": job.years_experience_min,
            "years_experience_max": job.years_experience_max,
        }

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Créer la campagne
            cursor.execute("""
                INSERT INTO sourcing_campaigns
                (name, job_title, job_description, keywords, location, filters, profiles_target, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                campaign.name,
                job.title,
                job.description,
                json.dumps(job.keywords, ensure_ascii=False),
                job.location,
                json.dumps(filters, ensure_ascii=False),
                job.profiles_target,
                "pending",
                datetime.now().isoformat()
            ))
            conn.commit()
            campaign_id = cursor.lastrowid

            # Si auto_start, lancer en background
            if campaign.auto_start:
                background_tasks.add_task(
                    _run_campaign_task,
                    campaign_id,
                    job.keywords,
                    job.location,
                    filters,
                    job.profiles_target
                )

            return CampaignResponse(
                id=campaign_id,
                name=campaign.name,
                status="running" if campaign.auto_start else "pending",
                job_title=job.title,
                keywords=job.keywords,
                location=job.location,
                profiles_target=job.profiles_target,
                profiles_found=0,
                created_at=datetime.now().isoformat(),
                started_at=datetime.now().isoformat() if campaign.auto_start else None,
                completed_at=None,
                filters=filters
            )

    except Exception as e:
        logger.error(f"Failed to create campaign: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(
    status: Optional[str] = Query(None, description="Filtrer par statut"),
    limit: int = Query(20, ge=1, le=100),
    authenticated: bool = Depends(verify_api_key)
):
    """Liste toutes les campagnes de sourcing."""
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # S'assurer que la table existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sourcing_campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    job_title TEXT,
                    job_description TEXT,
                    keywords TEXT,
                    location TEXT,
                    filters TEXT,
                    profiles_target INTEGER DEFAULT 50,
                    profiles_found INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    started_at TEXT,
                    completed_at TEXT
                )
            """)
            conn.commit()

            query = "SELECT * FROM sourcing_campaigns"
            params = []
            if status:
                query += " WHERE status = ?"
                params.append(status)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, tuple(params))
            campaigns = []

            for row in cursor.fetchall():
                row_dict = dict(row)
                campaigns.append(CampaignResponse(
                    id=row_dict["id"],
                    name=row_dict["name"],
                    status=row_dict["status"],
                    job_title=row_dict.get("job_title", ""),
                    keywords=json.loads(row_dict.get("keywords", "[]")),
                    location=row_dict.get("location", ""),
                    profiles_target=row_dict.get("profiles_target", 50),
                    profiles_found=row_dict.get("profiles_found", 0),
                    created_at=row_dict.get("created_at", ""),
                    started_at=row_dict.get("started_at"),
                    completed_at=row_dict.get("completed_at"),
                    filters=json.loads(row_dict.get("filters", "{}"))
                ))

            return campaigns

    except Exception as e:
        logger.error(f"Failed to list campaigns: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    authenticated: bool = Depends(verify_api_key)
):
    """Récupère les détails d'une campagne."""
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sourcing_campaigns WHERE id = ?", (campaign_id,))
            row = cursor.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Campaign not found")

            row_dict = dict(row)

            # Compter les profils trouvés
            cursor.execute(
                "SELECT COUNT(*) as count FROM scraped_profiles WHERE campaign_id = ?",
                (campaign_id,)
            )
            profiles_found = cursor.fetchone()["count"]

            return CampaignResponse(
                id=row_dict["id"],
                name=row_dict["name"],
                status=row_dict["status"],
                job_title=row_dict.get("job_title", ""),
                keywords=json.loads(row_dict.get("keywords", "[]")),
                location=row_dict.get("location", ""),
                profiles_target=row_dict.get("profiles_target", 50),
                profiles_found=profiles_found,
                created_at=row_dict.get("created_at", ""),
                started_at=row_dict.get("started_at"),
                completed_at=row_dict.get("completed_at"),
                filters=json.loads(row_dict.get("filters", "{}"))
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get campaign: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaigns/{campaign_id}/start")
async def start_campaign(
    campaign_id: int,
    request: CampaignStartRequest,
    background_tasks: BackgroundTasks,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Démarre une campagne de sourcing.

    Lance le VisitorBot en background avec les filtres de la campagne.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sourcing_campaigns WHERE id = ?", (campaign_id,))
            row = cursor.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Campaign not found")

            row_dict = dict(row)

            if row_dict["status"] == "running":
                raise HTTPException(status_code=400, detail="Campaign is already running")

            # Mettre à jour le statut
            cursor.execute("""
                UPDATE sourcing_campaigns
                SET status = 'running', started_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), campaign_id))
            conn.commit()

            # Parser les données
            keywords = json.loads(row_dict.get("keywords", "[]"))
            location = row_dict.get("location", "France")
            filters = json.loads(row_dict.get("filters", "{}"))
            profiles_limit = request.profiles_limit or row_dict.get("profiles_target", 50)

            # Lancer en background
            background_tasks.add_task(
                _run_campaign_task,
                campaign_id,
                keywords,
                location,
                filters,
                profiles_limit,
                request.dry_run
            )

            return {
                "message": "Campaign started",
                "campaign_id": campaign_id,
                "status": "running",
                "profiles_limit": profiles_limit,
                "dry_run": request.dry_run
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start campaign: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaigns/{campaign_id}/stop")
async def stop_campaign(
    campaign_id: int,
    authenticated: bool = Depends(verify_api_key)
):
    """Arrête une campagne en cours (marque comme completed)."""
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sourcing_campaigns
                SET status = 'completed', completed_at = ?
                WHERE id = ? AND status = 'running'
            """, (datetime.now().isoformat(), campaign_id))
            conn.commit()

            if cursor.rowcount == 0:
                raise HTTPException(status_code=400, detail="Campaign not running or not found")

            return {"message": "Campaign stopped", "campaign_id": campaign_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop campaign: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    delete_profiles: bool = Query(False, description="Supprimer aussi les profils associés"),
    authenticated: bool = Depends(verify_api_key)
):
    """Supprime une campagne."""
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Vérifier que la campagne existe
            cursor.execute("SELECT id FROM sourcing_campaigns WHERE id = ?", (campaign_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Campaign not found")

            # Supprimer les profils si demandé
            if delete_profiles:
                cursor.execute("DELETE FROM scraped_profiles WHERE campaign_id = ?", (campaign_id,))

            # Supprimer la campagne
            cursor.execute("DELETE FROM sourcing_campaigns WHERE id = ?", (campaign_id,))
            conn.commit()

            return {"message": "Campaign deleted", "campaign_id": campaign_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete campaign: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# FONCTION BACKGROUND - EXÉCUTION CAMPAGNE
# ═══════════════════════════════════════════════════════════════

def _run_campaign_task(
    campaign_id: int,
    keywords: List[str],
    location: str,
    filters: Dict[str, Any],
    profiles_limit: int,
    dry_run: bool = False
):
    """
    Tâche background pour exécuter une campagne de sourcing.

    Lance le VisitorBot via subprocess avec les paramètres de la campagne.
    """
    try:
        logger.info(f"Starting campaign {campaign_id} with keywords={keywords}, location={location}")

        # Construire la commande
        cmd = [
            sys.executable,
            "-m", "src.bots.visitor_bot",
            "--keywords", *keywords,
            "--location", location,
            "--limit", str(profiles_limit),
            "--campaign-id", str(campaign_id),
        ]

        if dry_run:
            cmd.append("--dry-run")

        # Exécuter le bot
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 heure max
        )

        # Mettre à jour le statut
        config = get_config()
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Compter les profils trouvés
            cursor.execute(
                "SELECT COUNT(*) as count FROM scraped_profiles WHERE campaign_id = ?",
                (campaign_id,)
            )
            profiles_found = cursor.fetchone()["count"]

            status = "completed" if result.returncode == 0 else "failed"
            cursor.execute("""
                UPDATE sourcing_campaigns
                SET status = ?, completed_at = ?, profiles_found = ?
                WHERE id = ?
            """, (status, datetime.now().isoformat(), profiles_found, campaign_id))
            conn.commit()

        logger.info(f"Campaign {campaign_id} finished with status={status}, profiles={profiles_found}")

    except subprocess.TimeoutExpired:
        logger.error(f"Campaign {campaign_id} timed out")
        _update_campaign_status(campaign_id, "failed")
    except Exception as e:
        logger.error(f"Campaign {campaign_id} failed: {e}", exc_info=True)
        _update_campaign_status(campaign_id, "failed")


def _update_campaign_status(campaign_id: int, status: str):
    """Met à jour le statut d'une campagne."""
    try:
        config = get_config()
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sourcing_campaigns
                SET status = ?, completed_at = ?
                WHERE id = ?
            """, (status, datetime.now().isoformat(), campaign_id))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to update campaign status: {e}")


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS - PROFILS
# ═══════════════════════════════════════════════════════════════

@router.get("/profiles", response_model=ProfileListResponse)
async def get_profiles(
    page: int = Query(1, ge=1, description="Numéro de page"),
    per_page: int = Query(50, ge=1, le=200, description="Éléments par page"),
    sort_by: str = Query("scraped_at", description="Champ de tri"),
    sort_order: str = Query("desc", description="asc ou desc"),
    # Filtres inline
    keywords: Optional[str] = Query(None, description="Mots-clés séparés par virgule"),
    min_fit_score: Optional[float] = Query(None, ge=0, le=100),
    min_years: Optional[int] = Query(None, ge=0),
    max_years: Optional[int] = Query(None, ge=0),
    company: Optional[str] = Query(None, description="Filtrer par entreprise"),
    skills: Optional[str] = Query(None, description="Compétences séparées par virgule"),
    open_to_work: Optional[bool] = Query(None),
    campaign_id: Optional[int] = Query(None),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère les profils scrapés avec filtres et pagination.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)

        # Construction des filtres
        filters = SearchFilters(
            keywords=keywords.split(",") if keywords else None,
            min_fit_score=min_fit_score,
            min_years_experience=min_years,
            max_years_experience=max_years,
            current_company=[company] if company else None,
            skills_required=skills.split(",") if skills else None,
            open_to_work_only=open_to_work or False,
            campaign_id=campaign_id
        )

        # Appel DB avec filtres
        result = _get_filtered_profiles(
            db, filters, page, per_page, sort_by, sort_order
        )

        return result

    except Exception as e:
        logger.error(f"Failed to get profiles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/profiles/search", response_model=ProfileListResponse)
async def search_profiles(
    filters: SearchFilters,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    sort_by: str = Query("fit_score", description="Champ de tri"),
    sort_order: str = Query("desc"),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Recherche avancée de profils avec filtres JSON.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        result = _get_filtered_profiles(db, filters, page, per_page, sort_by, sort_order)
        return result

    except Exception as e:
        logger.error(f"Failed to search profiles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: int,
    authenticated: bool = Depends(verify_api_key)
):
    """Récupère un profil par son ID."""
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scraped_profiles WHERE id = ?", (profile_id,))
            row = cursor.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Profile not found")

            return _row_to_profile(dict(row))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS - EXPORT CSV
# ═══════════════════════════════════════════════════════════════

@router.post("/export/csv")
async def export_profiles_csv(
    request: ExportRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Exporte les profils filtrés au format CSV.
    Permet de sélectionner les colonnes à exporter.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)

        # Récupérer tous les profils avec les filtres (sans pagination)
        result = _get_filtered_profiles(
            db,
            request.filters or SearchFilters(),
            page=1,
            per_page=10000,  # Max export
            sort_by="fit_score",
            sort_order="desc"
        )

        profiles = result["profiles"]

        # Colonnes disponibles
        all_columns = [
            "id", "profile_url", "first_name", "last_name", "full_name",
            "headline", "summary", "current_company", "education",
            "years_experience", "skills", "certifications", "fit_score",
            "scraped_at", "campaign_id", "location", "languages"
        ]

        # Colonnes à exporter
        columns = request.columns if request.columns else all_columns
        # Valider les colonnes
        columns = [c for c in columns if c in all_columns]

        # Générer le CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()

        for profile in profiles:
            row = {}
            for col in columns:
                value = profile.get(col, "")
                # Convertir les listes en string
                if isinstance(value, list):
                    value = "; ".join(str(v) for v in value)
                row[col] = value
            writer.writerow(row)

        # Retourner le fichier
        output.seek(0)
        filename = request.filename or "sourcing_export.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )

    except Exception as e:
        logger.error(f"Failed to export CSV: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/csv")
async def export_profiles_csv_get(
    min_fit_score: Optional[float] = Query(None, ge=0, le=100),
    campaign_id: Optional[int] = Query(None),
    columns: Optional[str] = Query(None, description="Colonnes séparées par virgule"),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Export CSV simplifié via GET.
    """
    filters = SearchFilters(
        min_fit_score=min_fit_score,
        campaign_id=campaign_id
    )

    request = ExportRequest(
        filters=filters,
        columns=columns.split(",") if columns else None
    )

    return await export_profiles_csv(request, authenticated)


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS - STATISTIQUES SOURCING
# ═══════════════════════════════════════════════════════════════

@router.get("/stats")
async def get_sourcing_stats(
    days: int = Query(30, ge=1, le=365),
    campaign_id: Optional[int] = Query(None),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Statistiques globales de sourcing.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cutoff = (datetime.now() - __import__('datetime').timedelta(days=days)).isoformat()

            # Base query with optional campaign filter
            campaign_filter = "AND campaign_id = ?" if campaign_id else ""
            params = [cutoff, campaign_id] if campaign_id else [cutoff]

            # Stats générales
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_profiles,
                    AVG(fit_score) as avg_fit_score,
                    MAX(fit_score) as max_fit_score,
                    MIN(fit_score) as min_fit_score,
                    AVG(years_experience) as avg_experience,
                    SUM(CASE WHEN fit_score >= 70 THEN 1 ELSE 0 END) as qualified_count,
                    SUM(CASE WHEN headline LIKE '%Open to Work%' OR headline LIKE '%recherche%' THEN 1 ELSE 0 END) as open_to_work_count
                FROM scraped_profiles
                WHERE scraped_at >= ? {campaign_filter}
            """, tuple(params))

            stats = dict(cursor.fetchone())

            # Distribution des scores
            cursor.execute(f"""
                SELECT
                    CASE
                        WHEN fit_score >= 80 THEN 'excellent'
                        WHEN fit_score >= 60 THEN 'good'
                        WHEN fit_score >= 40 THEN 'average'
                        ELSE 'low'
                    END as score_range,
                    COUNT(*) as count
                FROM scraped_profiles
                WHERE scraped_at >= ? {campaign_filter}
                GROUP BY score_range
            """, tuple(params))

            score_distribution = {row["score_range"]: row["count"] for row in cursor.fetchall()}

            # Top entreprises
            cursor.execute(f"""
                SELECT current_company, COUNT(*) as count
                FROM scraped_profiles
                WHERE scraped_at >= ? AND current_company IS NOT NULL {campaign_filter}
                GROUP BY current_company
                ORDER BY count DESC
                LIMIT 10
            """, tuple(params))

            top_companies = [{"name": row["current_company"], "count": row["count"]} for row in cursor.fetchall()]

            return {
                "period_days": days,
                "total_profiles": stats["total_profiles"] or 0,
                "avg_fit_score": round(stats["avg_fit_score"] or 0, 1),
                "max_fit_score": round(stats["max_fit_score"] or 0, 1),
                "min_fit_score": round(stats["min_fit_score"] or 0, 1),
                "avg_experience_years": round(stats["avg_experience"] or 0, 1),
                "qualified_count": stats["qualified_count"] or 0,
                "open_to_work_count": stats["open_to_work_count"] or 0,
                "score_distribution": score_distribution,
                "top_companies": top_companies
            }

    except Exception as e:
        logger.error(f"Failed to get sourcing stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════

def _get_filtered_profiles(
    db,
    filters: SearchFilters,
    page: int,
    per_page: int,
    sort_by: str,
    sort_order: str
) -> dict:
    """
    Récupère les profils avec filtres et pagination.
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Construction de la requête WHERE
        where_clauses = ["1=1"]
        params = []

        if filters.keywords:
            keyword_conditions = []
            for kw in filters.keywords:
                keyword_conditions.append(
                    "(full_name LIKE ? OR headline LIKE ? OR skills LIKE ? OR summary LIKE ?)"
                )
                params.extend([f"%{kw}%"] * 4)
            where_clauses.append(f"({' OR '.join(keyword_conditions)})")

        if filters.keywords_exclude:
            for kw in filters.keywords_exclude:
                where_clauses.append(
                    "NOT (full_name LIKE ? OR headline LIKE ? OR skills LIKE ?)"
                )
                params.extend([f"%{kw}%"] * 3)

        if filters.min_fit_score is not None:
            where_clauses.append("fit_score >= ?")
            params.append(filters.min_fit_score)

        if filters.max_fit_score is not None:
            where_clauses.append("fit_score <= ?")
            params.append(filters.max_fit_score)

        if filters.min_years_experience is not None:
            where_clauses.append("years_experience >= ?")
            params.append(filters.min_years_experience)

        if filters.max_years_experience is not None:
            where_clauses.append("years_experience <= ?")
            params.append(filters.max_years_experience)

        if filters.current_company:
            company_conditions = []
            for comp in filters.current_company:
                company_conditions.append("current_company LIKE ?")
                params.append(f"%{comp}%")
            where_clauses.append(f"({' OR '.join(company_conditions)})")

        if filters.skills_required:
            skills_conditions = []
            for skill in filters.skills_required:
                skills_conditions.append("skills LIKE ?")
                params.append(f"%{skill}%")
            where_clauses.append(f"({' OR '.join(skills_conditions)})")

        if filters.open_to_work_only:
            where_clauses.append(
                "(headline LIKE '%Open to Work%' OR headline LIKE '%recherche%' OR headline LIKE '%looking for%')"
            )

        if filters.campaign_id:
            where_clauses.append("campaign_id = ?")
            params.append(filters.campaign_id)

        if filters.scraped_after:
            where_clauses.append("scraped_at >= ?")
            params.append(filters.scraped_after)

        if filters.scraped_before:
            where_clauses.append("scraped_at <= ?")
            params.append(filters.scraped_before)

        where_sql = " AND ".join(where_clauses)

        # Validation du tri (protection SQL injection)
        allowed_sort_fields = ["id", "full_name", "fit_score", "years_experience", "scraped_at", "current_company"]
        if sort_by not in allowed_sort_fields:
            sort_by = "scraped_at"
        sort_order = "DESC" if sort_order.lower() == "desc" else "ASC"

        # Compter le total
        cursor.execute(f"SELECT COUNT(*) as total FROM scraped_profiles WHERE {where_sql}", tuple(params))
        total = cursor.fetchone()["total"]

        # Pagination
        offset = (page - 1) * per_page
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1

        # Récupérer les profils
        cursor.execute(f"""
            SELECT * FROM scraped_profiles
            WHERE {where_sql}
            ORDER BY {sort_by} {sort_order}
            LIMIT ? OFFSET ?
        """, tuple(params) + (per_page, offset))

        profiles = [_row_to_profile(dict(row)) for row in cursor.fetchall()]

        return {
            "profiles": profiles,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }


def _row_to_profile(row: dict) -> dict:
    """Convertit une row DB en ProfileResponse avec tous les champs enrichis."""

    def safe_json_parse(value, default=None):
        """Parse JSON de manière sécurisée."""
        if not value:
            return default
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default

    # Parser les champs JSON
    skills = safe_json_parse(row.get("skills"), [])
    certifications = safe_json_parse(row.get("certifications"), [])
    languages = safe_json_parse(row.get("languages"), [])
    work_history = safe_json_parse(row.get("work_history"), [])

    # Convertir open_to_work en boolean
    open_to_work = None
    if row.get("open_to_work") is not None:
        open_to_work = bool(row.get("open_to_work"))

    return {
        "id": row["id"],
        "profile_url": row["profile_url"],
        "first_name": row.get("first_name"),
        "last_name": row.get("last_name"),
        "full_name": row.get("full_name"),
        "headline": row.get("headline"),
        "summary": row.get("summary"),
        "current_company": row.get("current_company"),
        "education": row.get("education"),
        "years_experience": row.get("years_experience"),
        "skills": skills,
        "certifications": certifications,
        "fit_score": row.get("fit_score"),
        "scraped_at": row.get("scraped_at", ""),
        "campaign_id": row.get("campaign_id"),
        # Champs enrichis
        "location": row.get("location"),
        "languages": languages,
        "work_history": work_history,
        "connection_degree": row.get("connection_degree"),
        "school": row.get("school"),
        "degree": row.get("degree"),
        "job_title": row.get("job_title"),
        "seniority_level": row.get("seniority_level"),
        "endorsements_count": row.get("endorsements_count"),
        "profile_picture_url": row.get("profile_picture_url"),
        "open_to_work": open_to_work,
    }
