"""
API Router pour le Nurturing Automatisé - Segments et campagnes de suivi.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import json

from src.core.database import get_database
from src.config.config_manager import get_config
from src.utils.logging import get_logger
from ..security import verify_api_key

router = APIRouter(prefix="/nurturing", tags=["Nurturing Automatisé"])
logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
# ENUMS ET MODÈLES
# ═══════════════════════════════════════════════════════════════

class SegmentType(str, Enum):
    """Types de segments prédéfinis."""
    INACTIVE_CONTACTS = "inactive_contacts"  # Pas de message depuis X jours
    HIGH_SCORE_PROFILES = "high_score_profiles"  # Score > seuil
    OPEN_TO_WORK = "open_to_work"  # Profils disponibles
    RECENT_BIRTHDAYS = "recent_birthdays"  # Anniversaires récents non contactés
    NEW_CONNECTIONS = "new_connections"  # Nouveaux contacts
    CUSTOM = "custom"


class ContactSegment(BaseModel):
    """Un contact dans un segment."""
    name: str
    linkedin_url: Optional[str] = None
    last_contact_date: Optional[str] = None
    message_count: int = 0
    fit_score: Optional[float] = None
    days_since_contact: Optional[int] = None
    segment_reason: str


class SegmentResponse(BaseModel):
    """Réponse pour un segment de contacts."""
    segment_type: str
    segment_name: str
    description: str
    contacts: List[ContactSegment]
    total: int
    criteria: Dict[str, Any]


class NurturingStats(BaseModel):
    """Statistiques de nurturing."""
    inactive_contacts_count: int
    high_score_not_contacted: int
    open_to_work_count: int
    upcoming_birthdays: int
    avg_days_since_last_contact: float


class NurturingAlert(BaseModel):
    """Alerte de nurturing."""
    type: str
    priority: str  # high, medium, low
    title: str
    message: str
    contacts_count: int
    action_url: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS - SEGMENTS
# ═══════════════════════════════════════════════════════════════

@router.get("/segments/{segment_type}", response_model=SegmentResponse)
async def get_segment(
    segment_type: SegmentType,
    limit: int = Query(50, ge=1, le=500),
    days_inactive: int = Query(90, ge=7, le=365, description="Jours d'inactivité pour INACTIVE_CONTACTS"),
    min_score: float = Query(70, ge=0, le=100, description="Score minimum pour HIGH_SCORE_PROFILES"),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère un segment de contacts pour le nurturing.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)

        if segment_type == SegmentType.INACTIVE_CONTACTS:
            return await _get_inactive_contacts(db, days_inactive, limit)
        elif segment_type == SegmentType.HIGH_SCORE_PROFILES:
            return await _get_high_score_profiles(db, min_score, limit)
        elif segment_type == SegmentType.OPEN_TO_WORK:
            return await _get_open_to_work(db, limit)
        elif segment_type == SegmentType.RECENT_BIRTHDAYS:
            return await _get_recent_birthdays_not_contacted(db, limit)
        elif segment_type == SegmentType.NEW_CONNECTIONS:
            return await _get_new_connections(db, limit)
        else:
            raise HTTPException(status_code=400, detail="Segment type not implemented")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get segment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/segments")
async def list_segments(
    authenticated: bool = Depends(verify_api_key)
):
    """
    Liste tous les segments disponibles avec leur compte.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now()

            # Contacts inactifs (90+ jours)
            cutoff_90 = (now - timedelta(days=90)).isoformat()
            cursor.execute("""
                SELECT COUNT(DISTINCT contact_name) as count
                FROM birthday_messages
                WHERE contact_name NOT IN (
                    SELECT contact_name FROM birthday_messages WHERE sent_at >= ?
                )
            """, (cutoff_90,))
            inactive_count = cursor.fetchone()["count"]

            # High score profiles non contactés
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM scraped_profiles
                WHERE fit_score >= 70
                AND profile_url NOT IN (
                    SELECT DISTINCT profile_url FROM profile_visits WHERE profile_url IS NOT NULL
                )
            """)
            high_score_count = cursor.fetchone()["count"]

            # Open to work
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM scraped_profiles
                WHERE headline LIKE '%Open to Work%'
                   OR headline LIKE '%recherche%'
                   OR headline LIKE '%looking for%'
            """)
            open_to_work_count = cursor.fetchone()["count"]

            # Nouveaux contacts (30 derniers jours)
            cutoff_30 = (now - timedelta(days=30)).isoformat()
            cursor.execute("""
                SELECT COUNT(DISTINCT contact_name) as count
                FROM birthday_messages
                WHERE sent_at >= ?
                AND contact_name NOT IN (
                    SELECT contact_name FROM birthday_messages WHERE sent_at < ?
                )
            """, (cutoff_30, cutoff_30))
            new_contacts_count = cursor.fetchone()["count"]

            return {
                "segments": [
                    {
                        "type": "inactive_contacts",
                        "name": "Contacts Inactifs",
                        "description": "Contacts sans message depuis 90+ jours",
                        "count": inactive_count,
                        "priority": "high" if inactive_count > 10 else "medium"
                    },
                    {
                        "type": "high_score_profiles",
                        "name": "Profils Qualifiés",
                        "description": "Profils avec score >= 70 non encore contactés",
                        "count": high_score_count,
                        "priority": "high" if high_score_count > 5 else "medium"
                    },
                    {
                        "type": "open_to_work",
                        "name": "Open to Work",
                        "description": "Profils disponibles/en recherche",
                        "count": open_to_work_count,
                        "priority": "medium"
                    },
                    {
                        "type": "new_connections",
                        "name": "Nouveaux Contacts",
                        "description": "Premiers contacts des 30 derniers jours",
                        "count": new_contacts_count,
                        "priority": "low"
                    }
                ]
            }

    except Exception as e:
        logger.error(f"Failed to list segments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS - ALERTES ET STATS
# ═══════════════════════════════════════════════════════════════

@router.get("/alerts")
async def get_nurturing_alerts(
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère les alertes de nurturing prioritaires.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        alerts = []

        with db.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now()

            # Alerte: Contacts très inactifs (180+ jours)
            cutoff_180 = (now - timedelta(days=180)).isoformat()
            cursor.execute("""
                SELECT COUNT(DISTINCT bm.contact_name) as count
                FROM birthday_messages bm
                WHERE bm.contact_name NOT IN (
                    SELECT contact_name FROM birthday_messages WHERE sent_at >= ?
                )
            """, (cutoff_180,))
            very_inactive = cursor.fetchone()["count"]

            if very_inactive > 0:
                alerts.append(NurturingAlert(
                    type="very_inactive",
                    priority="high",
                    title="Contacts à réactiver",
                    message=f"{very_inactive} contacts n'ont pas reçu de message depuis plus de 6 mois",
                    contacts_count=very_inactive,
                    action_url="/nurturing?segment=inactive_contacts"
                ))

            # Alerte: Profils haute qualité non contactés
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM scraped_profiles
                WHERE fit_score >= 80
                AND scraped_at >= ?
            """, ((now - timedelta(days=30)).isoformat(),))
            high_quality_recent = cursor.fetchone()["count"]

            if high_quality_recent > 0:
                alerts.append(NurturingAlert(
                    type="high_quality_leads",
                    priority="high",
                    title="Leads qualifiés récents",
                    message=f"{high_quality_recent} profils avec score 80+ scrapés ce mois",
                    contacts_count=high_quality_recent,
                    action_url="/sourcing?min_fit_score=80"
                ))

            # Alerte: Open to work récents
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM scraped_profiles
                WHERE (headline LIKE '%Open to Work%' OR headline LIKE '%recherche%')
                AND scraped_at >= ?
            """, ((now - timedelta(days=14)).isoformat(),))
            recent_open = cursor.fetchone()["count"]

            if recent_open > 0:
                alerts.append(NurturingAlert(
                    type="open_to_work_recent",
                    priority="medium",
                    title="Candidats disponibles",
                    message=f"{recent_open} profils 'Open to Work' détectés ces 2 dernières semaines",
                    contacts_count=recent_open,
                    action_url="/sourcing?open_to_work=true"
                ))

            # Alerte: Faible activité ce mois
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM birthday_messages
                WHERE sent_at >= ?
            """, ((now - timedelta(days=30)).isoformat(),))
            messages_this_month = cursor.fetchone()["count"]

            if messages_this_month < 10:
                alerts.append(NurturingAlert(
                    type="low_activity",
                    priority="medium",
                    title="Activité faible",
                    message=f"Seulement {messages_this_month} messages envoyés ce mois",
                    contacts_count=messages_this_month,
                    action_url="/"
                ))

        return {"alerts": alerts, "count": len(alerts)}

    except Exception as e:
        logger.error(f"Failed to get alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=NurturingStats)
async def get_nurturing_stats(
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère les statistiques de nurturing.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now()

            # Contacts inactifs
            cutoff_90 = (now - timedelta(days=90)).isoformat()
            cursor.execute("""
                SELECT COUNT(DISTINCT contact_name) as count
                FROM birthday_messages
                WHERE contact_name NOT IN (
                    SELECT contact_name FROM birthday_messages WHERE sent_at >= ?
                )
            """, (cutoff_90,))
            inactive_count = cursor.fetchone()["count"]

            # High score non contactés
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM scraped_profiles
                WHERE fit_score >= 70
            """)
            high_score_count = cursor.fetchone()["count"]

            # Open to work
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM scraped_profiles
                WHERE headline LIKE '%Open to Work%'
                   OR headline LIKE '%recherche%'
            """)
            open_to_work = cursor.fetchone()["count"]

            # Anniversaires à venir (7 prochains jours - approximatif)
            # Note: Ceci est une approximation car nous n'avons pas les dates d'anniversaire exactes
            upcoming = 0  # Placeholder

            # Moyenne jours depuis dernier contact
            cursor.execute("""
                SELECT AVG(julianday('now') - julianday(last_msg)) as avg_days
                FROM (
                    SELECT contact_name, MAX(sent_at) as last_msg
                    FROM birthday_messages
                    GROUP BY contact_name
                )
            """)
            avg_result = cursor.fetchone()
            avg_days = avg_result["avg_days"] if avg_result and avg_result["avg_days"] else 0

            return NurturingStats(
                inactive_contacts_count=inactive_count,
                high_score_not_contacted=high_score_count,
                open_to_work_count=open_to_work,
                upcoming_birthdays=upcoming,
                avg_days_since_last_contact=round(avg_days, 1)
            )

    except Exception as e:
        logger.error(f"Failed to get nurturing stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# FONCTIONS HELPER POUR LES SEGMENTS
# ═══════════════════════════════════════════════════════════════

async def _get_inactive_contacts(db, days_inactive: int, limit: int) -> SegmentResponse:
    """Récupère les contacts inactifs depuis X jours."""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days_inactive)).isoformat()

        cursor.execute("""
            SELECT
                bm.contact_name as name,
                c.linkedin_url,
                MAX(bm.sent_at) as last_contact_date,
                COUNT(bm.id) as message_count,
                CAST(julianday('now') - julianday(MAX(bm.sent_at)) AS INTEGER) as days_since
            FROM birthday_messages bm
            LEFT JOIN contacts c ON bm.contact_id = c.id
            GROUP BY bm.contact_name
            HAVING MAX(bm.sent_at) < ?
            ORDER BY days_since DESC
            LIMIT ?
        """, (cutoff, limit))

        contacts = []
        for row in cursor.fetchall():
            contacts.append(ContactSegment(
                name=row["name"],
                linkedin_url=row["linkedin_url"],
                last_contact_date=row["last_contact_date"],
                message_count=row["message_count"],
                days_since_contact=row["days_since"],
                segment_reason=f"Pas de contact depuis {row['days_since']} jours"
            ))

        return SegmentResponse(
            segment_type="inactive_contacts",
            segment_name="Contacts Inactifs",
            description=f"Contacts sans message depuis plus de {days_inactive} jours",
            contacts=contacts,
            total=len(contacts),
            criteria={"days_inactive": days_inactive}
        )


async def _get_high_score_profiles(db, min_score: float, limit: int) -> SegmentResponse:
    """Récupère les profils avec score élevé."""
    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                sp.full_name as name,
                sp.profile_url as linkedin_url,
                sp.fit_score,
                sp.scraped_at as last_contact_date,
                sp.headline
            FROM scraped_profiles sp
            WHERE sp.fit_score >= ?
            ORDER BY sp.fit_score DESC
            LIMIT ?
        """, (min_score, limit))

        contacts = []
        for row in cursor.fetchall():
            contacts.append(ContactSegment(
                name=row["name"] or "Unknown",
                linkedin_url=row["linkedin_url"],
                last_contact_date=row["last_contact_date"],
                fit_score=row["fit_score"],
                segment_reason=f"Score: {row['fit_score']:.0f} - {row['headline'][:50] if row['headline'] else 'N/A'}"
            ))

        return SegmentResponse(
            segment_type="high_score_profiles",
            segment_name="Profils Qualifiés",
            description=f"Profils avec score >= {min_score}",
            contacts=contacts,
            total=len(contacts),
            criteria={"min_score": min_score}
        )


async def _get_open_to_work(db, limit: int) -> SegmentResponse:
    """Récupère les profils 'Open to Work'."""
    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                sp.full_name as name,
                sp.profile_url as linkedin_url,
                sp.fit_score,
                sp.scraped_at as last_contact_date,
                sp.headline
            FROM scraped_profiles sp
            WHERE sp.headline LIKE '%Open to Work%'
               OR sp.headline LIKE '%recherche%'
               OR sp.headline LIKE '%looking for%'
               OR sp.headline LIKE '%available%'
            ORDER BY sp.scraped_at DESC
            LIMIT ?
        """, (limit,))

        contacts = []
        for row in cursor.fetchall():
            contacts.append(ContactSegment(
                name=row["name"] or "Unknown",
                linkedin_url=row["linkedin_url"],
                last_contact_date=row["last_contact_date"],
                fit_score=row["fit_score"],
                segment_reason="Open to Work"
            ))

        return SegmentResponse(
            segment_type="open_to_work",
            segment_name="Open to Work",
            description="Profils indiquant être disponibles ou en recherche",
            contacts=contacts,
            total=len(contacts),
            criteria={}
        )


async def _get_recent_birthdays_not_contacted(db, limit: int) -> SegmentResponse:
    """Récupère les contacts avec anniversaire récent non encore contacté cette année."""
    # Cette fonctionnalité nécessiterait une table d'anniversaires - simplifié ici
    return SegmentResponse(
        segment_type="recent_birthdays",
        segment_name="Anniversaires Récents",
        description="Contacts avec anniversaire récent (fonctionnalité à venir)",
        contacts=[],
        total=0,
        criteria={}
    )


async def _get_new_connections(db, limit: int) -> SegmentResponse:
    """Récupère les nouveaux contacts des 30 derniers jours."""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()

        cursor.execute("""
            SELECT
                bm.contact_name as name,
                c.linkedin_url,
                MIN(bm.sent_at) as first_contact_date,
                COUNT(bm.id) as message_count
            FROM birthday_messages bm
            LEFT JOIN contacts c ON bm.contact_id = c.id
            GROUP BY bm.contact_name
            HAVING MIN(bm.sent_at) >= ?
            ORDER BY first_contact_date DESC
            LIMIT ?
        """, (cutoff, limit))

        contacts = []
        for row in cursor.fetchall():
            contacts.append(ContactSegment(
                name=row["name"],
                linkedin_url=row["linkedin_url"],
                last_contact_date=row["first_contact_date"],
                message_count=row["message_count"],
                segment_reason="Nouveau contact"
            ))

        return SegmentResponse(
            segment_type="new_connections",
            segment_name="Nouveaux Contacts",
            description="Contacts établis dans les 30 derniers jours",
            contacts=contacts,
            total=len(contacts),
            criteria={"days": 30}
        )
