import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from typing import Optional
import asyncio

from app_v2.api.schemas import CampaignRequest, SourcingRequest, BotStatusResponse
from app_v2.core.config import Settings
from app_v2.services.birthday_service import BirthdayService
from app_v2.services.visitor_service import VisitorService
from app_v2.engine.browser_context import LinkedInBrowserContext
from app_v2.engine.action_manager import ActionManager
from app_v2.engine.auth_manager import AuthManager
from app_v2.engine.selector_engine import SmartSelectorEngine

# Global Lock to prevent concurrent runs
# Dans une vraie prod avec plusieurs workers, utiliser Redis.
# Ici, pour une instance unique V2, un Lock asyncio ou variable globale suffit.
GLOBAL_BOT_LOCK = asyncio.Lock()
CURRENT_JOB_TYPE: Optional[str] = None

router = APIRouter(prefix="/campaigns", tags=["Control"])
logger = logging.getLogger(__name__)

# --- Dependencies ---
# TODO: Move to app_v2/api/dependencies.py if it grows

def get_settings():
    return Settings()

# --- Helper Functions for Background Tasks ---

async def _run_birthday_wrapper(settings: Settings, request: CampaignRequest):
    global CURRENT_JOB_TYPE
    async with GLOBAL_BOT_LOCK:
        CURRENT_JOB_TYPE = "birthday_campaign"
        try:
            # Override settings with request params
            settings.process_late = request.process_late
            settings.max_days_late = request.max_days_late

            service = BirthdayService(settings)
            await service.run_daily_campaign(dry_run=request.dry_run)
        except Exception as e:
            logger.error(f"Error in Birthday Campaign: {e}", exc_info=True)
        finally:
            CURRENT_JOB_TYPE = None

async def _run_sourcing_wrapper(settings: Settings, request: SourcingRequest):
    global CURRENT_JOB_TYPE
    async with GLOBAL_BOT_LOCK:
        CURRENT_JOB_TYPE = "sourcing_campaign"
        try:
            # Init dependencies manually for the service
            # Note: VisitorService requires an active BrowserContext.
            # Unlike BirthdayService which manages its own context context manager,
            # VisitorService expects injected dependencies.
            # We need to wrap it in a context manager here.

            auth_manager = AuthManager(settings)
            async with LinkedInBrowserContext(settings, auth_manager) as context:
                selector_engine = SmartSelectorEngine(context.page, settings)
                action_manager = ActionManager(context, selector_engine)

                # Validate session first
                if not await auth_manager.validate_session(context.page):
                    logger.error("Sourcing aborted: Invalid session")
                    return

                service = VisitorService(context, action_manager, selector_engine, settings)

                await service.run_sourcing(
                    search_url=request.search_url,
                    max_profiles=request.limit,
                    criteria=request.criteria
                )
        except Exception as e:
            logger.error(f"Error in Sourcing Campaign: {e}", exc_info=True)
        finally:
            CURRENT_JOB_TYPE = None

# --- Endpoints ---

@router.post("/birthday", status_code=202)
async def start_birthday_campaign(
    request: CampaignRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings)
):
    """Lance la campagne d'anniversaires en arrière-plan."""
    if GLOBAL_BOT_LOCK.locked():
        raise HTTPException(status_code=409, detail=f"Un bot est déjà en cours d'exécution ({CURRENT_JOB_TYPE})")

    background_tasks.add_task(_run_birthday_wrapper, settings, request)
    return {"status": "accepted", "message": "Campagne anniversaire démarrée en arrière-plan"}

@router.post("/sourcing", status_code=202)
async def start_sourcing_campaign(
    request: SourcingRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings)
):
    """Lance une session de sourcing en arrière-plan."""
    if GLOBAL_BOT_LOCK.locked():
        raise HTTPException(status_code=409, detail=f"Un bot est déjà en cours d'exécution ({CURRENT_JOB_TYPE})")

    background_tasks.add_task(_run_sourcing_wrapper, settings, request)
    return {"status": "accepted", "message": "Campagne de sourcing démarrée en arrière-plan"}

@router.get("/status", response_model=BotStatusResponse)
async def get_bot_status():
    """Vérifie l'état du worker."""
    from datetime import datetime
    return BotStatusResponse(
        is_running=GLOBAL_BOT_LOCK.locked(),
        active_job=CURRENT_JOB_TYPE,
        last_update=datetime.now()
    )
