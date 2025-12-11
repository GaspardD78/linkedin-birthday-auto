"""
API Router pour la gestion CRM - Historique des relations contacts.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from src.core.database import get_database
from src.config.config_manager import get_config
from src.utils.logging import get_logger
from ..security import verify_api_key

router = APIRouter(prefix="/crm", tags=["CRM - Relations"])
logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
# MODÈLES PYDANTIC
# ═══════════════════════════════════════════════════════════════

class ContactMessage(BaseModel):
    """Un message envoyé à un contact."""
    id: int
    message_text: str
    sent_at: str
    is_late: bool
    days_late: int
    script_mode: Optional[str] = None


class ContactProfileVisit(BaseModel):
    """Une visite de profil."""
    id: int
    visited_at: str
    source_search: Optional[str] = None
    success: bool


class ContactDetail(BaseModel):
    """Détail complet d'un contact avec historique."""
    id: Optional[int] = None
    name: str
    linkedin_url: Optional[str] = None
    message_count: int
    last_message_date: Optional[str] = None
    relationship_score: Optional[float] = None
    created_at: Optional[str] = None
    messages: List[ContactMessage] = []
    profile_visits: List[ContactProfileVisit] = []
    is_blacklisted: bool = False


class ContactSummary(BaseModel):
    """Résumé d'un contact pour la liste."""
    id: Optional[int] = None
    name: str
    linkedin_url: Optional[str] = None
    message_count: int
    last_message_date: Optional[str] = None
    relationship_score: Optional[float] = None
    first_contact_date: Optional[str] = None
    is_blacklisted: bool = False


class ContactListResponse(BaseModel):
    contacts: List[ContactSummary]
    total: int
    page: int
    per_page: int
    total_pages: int


class CRMStats(BaseModel):
    """Statistiques CRM globales."""
    total_contacts: int
    total_messages_sent: int
    contacts_this_month: int
    messages_this_month: int
    avg_messages_per_contact: float
    top_contacted: List[Dict[str, Any]]


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS - CONTACTS
# ═══════════════════════════════════════════════════════════════

@router.get("/contacts", response_model=ContactListResponse)
async def get_contacts(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, description="Recherche par nom"),
    sort_by: str = Query("last_message_date", description="message_count, last_message_date, name"),
    sort_order: str = Query("desc"),
    min_messages: Optional[int] = Query(None, ge=0),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère la liste des contacts avec statistiques de relation.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Construction de la requête
            where_clauses = ["1=1"]
            params = []

            if search:
                where_clauses.append("bm.contact_name LIKE ?")
                params.append(f"%{search}%")

            if min_messages:
                where_clauses.append("message_count >= ?")
                params.append(min_messages)

            where_sql = " AND ".join(where_clauses)

            # Validation du tri
            allowed_sort = ["message_count", "last_message_date", "name", "first_contact_date"]
            sort_field = sort_by if sort_by in allowed_sort else "last_message_date"
            if sort_field == "name":
                sort_field = "bm.contact_name"
            sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"

            # Compter le total
            count_sql = f"""
                SELECT COUNT(DISTINCT bm.contact_name) as total
                FROM birthday_messages bm
                LEFT JOIN contacts c ON bm.contact_id = c.id
                WHERE {where_sql}
            """
            cursor.execute(count_sql, tuple(params))
            total = cursor.fetchone()["total"]

            # Pagination
            offset = (page - 1) * per_page
            total_pages = (total + per_page - 1) // per_page if total > 0 else 1

            # Récupérer les contacts
            query_sql = f"""
                SELECT
                    c.id,
                    bm.contact_name as name,
                    c.linkedin_url,
                    COUNT(bm.id) as message_count,
                    MAX(bm.sent_at) as last_message_date,
                    MIN(bm.sent_at) as first_contact_date,
                    c.relationship_score,
                    CASE WHEN bl.id IS NOT NULL THEN 1 ELSE 0 END as is_blacklisted
                FROM birthday_messages bm
                LEFT JOIN contacts c ON bm.contact_id = c.id
                LEFT JOIN blacklist bl ON (bm.contact_name = bl.contact_name AND bl.is_active = 1)
                WHERE {where_sql}
                GROUP BY bm.contact_name
                ORDER BY {sort_field} {sort_direction}
                LIMIT ? OFFSET ?
            """
            cursor.execute(query_sql, tuple(params) + (per_page, offset))

            contacts = []
            for row in cursor.fetchall():
                contacts.append(ContactSummary(
                    id=row["id"],
                    name=row["name"],
                    linkedin_url=row["linkedin_url"],
                    message_count=row["message_count"],
                    last_message_date=row["last_message_date"],
                    first_contact_date=row["first_contact_date"],
                    relationship_score=row["relationship_score"],
                    is_blacklisted=bool(row["is_blacklisted"])
                ))

            return ContactListResponse(
                contacts=contacts,
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages
            )

    except Exception as e:
        logger.error(f"Failed to get contacts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contacts/{contact_name}", response_model=ContactDetail)
async def get_contact_detail(
    contact_name: str,
    years: int = Query(5, ge=1, le=10, description="Années d'historique"),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère le détail d'un contact avec tout son historique de relation.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=365 * years)).isoformat()

            # Infos de base du contact
            cursor.execute("""
                SELECT
                    c.id,
                    bm.contact_name as name,
                    c.linkedin_url,
                    c.relationship_score,
                    c.created_at,
                    COUNT(bm.id) as message_count,
                    MAX(bm.sent_at) as last_message_date,
                    CASE WHEN bl.id IS NOT NULL THEN 1 ELSE 0 END as is_blacklisted
                FROM birthday_messages bm
                LEFT JOIN contacts c ON bm.contact_id = c.id
                LEFT JOIN blacklist bl ON (bm.contact_name = bl.contact_name AND bl.is_active = 1)
                WHERE bm.contact_name = ?
                GROUP BY bm.contact_name
            """, (contact_name,))

            contact_row = cursor.fetchone()
            if not contact_row:
                raise HTTPException(status_code=404, detail="Contact not found")

            # Messages envoyés
            cursor.execute("""
                SELECT id, message_text, sent_at, is_late, days_late, script_mode
                FROM birthday_messages
                WHERE contact_name = ? AND sent_at >= ?
                ORDER BY sent_at DESC
            """, (contact_name, cutoff_date))

            messages = [ContactMessage(
                id=row["id"],
                message_text=row["message_text"],
                sent_at=row["sent_at"],
                is_late=bool(row["is_late"]),
                days_late=row["days_late"] or 0,
                script_mode=row["script_mode"]
            ) for row in cursor.fetchall()]

            # Visites de profil (si le contact a une URL LinkedIn)
            profile_visits = []
            if contact_row["linkedin_url"]:
                cursor.execute("""
                    SELECT id, visited_at, source_search, success
                    FROM profile_visits
                    WHERE profile_url LIKE ? AND visited_at >= ?
                    ORDER BY visited_at DESC
                """, (f"%{contact_row['linkedin_url']}%", cutoff_date))

                profile_visits = [ContactProfileVisit(
                    id=row["id"],
                    visited_at=row["visited_at"],
                    source_search=row["source_search"],
                    success=bool(row["success"])
                ) for row in cursor.fetchall()]

            return ContactDetail(
                id=contact_row["id"],
                name=contact_row["name"],
                linkedin_url=contact_row["linkedin_url"],
                message_count=contact_row["message_count"],
                last_message_date=contact_row["last_message_date"],
                relationship_score=contact_row["relationship_score"],
                created_at=contact_row["created_at"],
                messages=messages,
                profile_visits=profile_visits,
                is_blacklisted=bool(contact_row["is_blacklisted"])
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get contact detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS - TIMELINE / ACTIVITÉ
# ═══════════════════════════════════════════════════════════════

@router.get("/timeline")
async def get_relationship_timeline(
    days: int = Query(90, ge=1, le=365),
    contact_name: Optional[str] = Query(None),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère la timeline des interactions (messages + visites).
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            events = []

            # Messages
            if contact_name:
                cursor.execute("""
                    SELECT 'message' as type, id, contact_name, message_text as detail, sent_at as event_date, is_late
                    FROM birthday_messages
                    WHERE contact_name = ? AND sent_at >= ?
                    ORDER BY sent_at DESC
                """, (contact_name, cutoff_date))
            else:
                cursor.execute("""
                    SELECT 'message' as type, id, contact_name, message_text as detail, sent_at as event_date, is_late
                    FROM birthday_messages
                    WHERE sent_at >= ?
                    ORDER BY sent_at DESC
                    LIMIT 500
                """, (cutoff_date,))

            for row in cursor.fetchall():
                events.append({
                    "type": "message",
                    "id": row["id"],
                    "contact_name": row["contact_name"],
                    "detail": row["detail"][:100] + "..." if len(row["detail"]) > 100 else row["detail"],
                    "event_date": row["event_date"],
                    "is_late": bool(row["is_late"])
                })

            # Visites (si pas de contact spécifique, limiter)
            if not contact_name:
                cursor.execute("""
                    SELECT 'visit' as type, id, profile_name as contact_name, profile_url as detail, visited_at as event_date, success
                    FROM profile_visits
                    WHERE visited_at >= ?
                    ORDER BY visited_at DESC
                    LIMIT 200
                """, (cutoff_date,))

                for row in cursor.fetchall():
                    events.append({
                        "type": "visit",
                        "id": row["id"],
                        "contact_name": row["contact_name"],
                        "detail": row["detail"],
                        "event_date": row["event_date"],
                        "success": bool(row["success"])
                    })

            # Trier par date
            events.sort(key=lambda x: x["event_date"], reverse=True)

            return {
                "events": events[:500],
                "total": len(events),
                "days": days
            }

    except Exception as e:
        logger.error(f"Failed to get timeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS - STATISTIQUES CRM
# ═══════════════════════════════════════════════════════════════

@router.get("/stats", response_model=CRMStats)
async def get_crm_stats(
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère les statistiques CRM globales.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            month_ago = (datetime.now() - timedelta(days=30)).isoformat()

            # Stats globales
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT contact_name) as total_contacts,
                    COUNT(*) as total_messages
                FROM birthday_messages
            """)
            global_stats = dict(cursor.fetchone())

            # Stats ce mois
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT contact_name) as contacts_this_month,
                    COUNT(*) as messages_this_month
                FROM birthday_messages
                WHERE sent_at >= ?
            """, (month_ago,))
            month_stats = dict(cursor.fetchone())

            # Top contacts
            cursor.execute("""
                SELECT
                    contact_name as name,
                    COUNT(*) as message_count,
                    MAX(sent_at) as last_message
                FROM birthday_messages
                GROUP BY contact_name
                ORDER BY message_count DESC
                LIMIT 10
            """)
            top_contacted = [dict(row) for row in cursor.fetchall()]

            # Moyenne
            avg_messages = (global_stats["total_messages"] / global_stats["total_contacts"]
                          if global_stats["total_contacts"] > 0 else 0)

            return CRMStats(
                total_contacts=global_stats["total_contacts"],
                total_messages_sent=global_stats["total_messages"],
                contacts_this_month=month_stats["contacts_this_month"],
                messages_this_month=month_stats["messages_this_month"],
                avg_messages_per_contact=round(avg_messages, 2),
                top_contacted=top_contacted
            )

    except Exception as e:
        logger.error(f"Failed to get CRM stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/contacts/{contact_name}/notes")
async def update_contact_notes(
    contact_name: str,
    notes: str = "",
    authenticated: bool = Depends(verify_api_key)
):
    """
    Met à jour les notes d'un contact.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Vérifier que le contact existe
            cursor.execute("SELECT id FROM contacts WHERE name = ?", (contact_name,))
            contact = cursor.fetchone()

            if not contact:
                raise HTTPException(status_code=404, detail="Contact not found")

            # Mettre à jour les notes
            cursor.execute("""
                UPDATE contacts
                SET notes = ?, updated_at = ?
                WHERE name = ?
            """, (notes, datetime.now().isoformat(), contact_name))

            return {"status": "updated", "contact_name": contact_name}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update notes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
