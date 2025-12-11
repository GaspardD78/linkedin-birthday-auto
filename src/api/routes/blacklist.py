"""
Routes API pour la gestion de la blacklist de contacts.

Permet d'exclure certains contacts des envois automatiques de messages.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from ...core.database import Database
from ..security import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blacklist", tags=["blacklist"])


class BlacklistEntry(BaseModel):
    """Modèle pour une entrée de blacklist."""

    contact_name: str = Field(..., min_length=1, description="Nom du contact à bloquer")
    linkedin_url: Optional[str] = Field(default=None, description="URL du profil LinkedIn")
    reason: Optional[str] = Field(default=None, description="Raison du blocage")


class BlacklistResponse(BaseModel):
    """Modèle de réponse pour une entrée de blacklist."""

    id: int
    contact_name: str
    linkedin_url: Optional[str]
    reason: Optional[str]
    added_at: str
    added_by: str
    is_active: bool


class BlacklistUpdateRequest(BaseModel):
    """Modèle pour la mise à jour d'une entrée."""

    contact_name: Optional[str] = Field(default=None, description="Nouveau nom")
    linkedin_url: Optional[str] = Field(default=None, description="Nouvelle URL")
    reason: Optional[str] = Field(default=None, description="Nouvelle raison")


def get_database() -> Database:
    """Dependency pour obtenir la base de données."""
    return Database("/app/data/linkedin.db")


@router.get("", dependencies=[Depends(verify_api_key)])
async def get_blacklist(
    include_inactive: bool = False,
    db: Database = Depends(get_database)
) -> dict:
    """
    Récupère la liste des contacts blacklistés.

    Args:
        include_inactive: Inclure les entrées désactivées

    Returns:
        Liste des entrées de la blacklist
    """
    try:
        entries = db.get_blacklist(include_inactive=include_inactive)
        count = db.get_blacklist_count()

        return {
            "success": True,
            "count": count,
            "entries": entries
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la blacklist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", dependencies=[Depends(verify_api_key)])
async def add_to_blacklist(
    entry: BlacklistEntry,
    db: Database = Depends(get_database)
) -> dict:
    """
    Ajoute un contact à la blacklist.

    Args:
        entry: Données du contact à bloquer

    Returns:
        ID de l'entrée créée
    """
    try:
        entry_id = db.add_to_blacklist(
            contact_name=entry.contact_name,
            linkedin_url=entry.linkedin_url,
            reason=entry.reason,
            added_by="api"
        )

        return {
            "success": True,
            "id": entry_id,
            "message": f"Contact '{entry.contact_name}' ajouté à la blacklist"
        }
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout à la blacklist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{entry_id}", dependencies=[Depends(verify_api_key)])
async def remove_from_blacklist(
    entry_id: int,
    db: Database = Depends(get_database)
) -> dict:
    """
    Supprime (désactive) une entrée de la blacklist.

    Args:
        entry_id: ID de l'entrée à supprimer

    Returns:
        Confirmation de la suppression
    """
    try:
        success = db.remove_from_blacklist(entry_id)

        if not success:
            raise HTTPException(status_code=404, detail="Entrée non trouvée")

        return {
            "success": True,
            "message": f"Entrée {entry_id} supprimée de la blacklist"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de la blacklist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{entry_id}", dependencies=[Depends(verify_api_key)])
async def update_blacklist_entry(
    entry_id: int,
    update: BlacklistUpdateRequest,
    db: Database = Depends(get_database)
) -> dict:
    """
    Met à jour une entrée de la blacklist.

    Args:
        entry_id: ID de l'entrée à modifier
        update: Nouvelles données

    Returns:
        Confirmation de la mise à jour
    """
    try:
        success = db.update_blacklist_entry(
            blacklist_id=entry_id,
            contact_name=update.contact_name,
            linkedin_url=update.linkedin_url,
            reason=update.reason
        )

        if not success:
            raise HTTPException(status_code=404, detail="Entrée non trouvée ou aucune modification")

        return {
            "success": True,
            "message": f"Entrée {entry_id} mise à jour"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de la blacklist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check/{contact_name}", dependencies=[Depends(verify_api_key)])
async def check_blacklist(
    contact_name: str,
    linkedin_url: Optional[str] = None,
    db: Database = Depends(get_database)
) -> dict:
    """
    Vérifie si un contact est dans la blacklist.

    Args:
        contact_name: Nom du contact à vérifier
        linkedin_url: URL du profil (optionnel)

    Returns:
        Statut de blacklist du contact
    """
    try:
        is_blacklisted = db.is_blacklisted(contact_name, linkedin_url)

        return {
            "success": True,
            "contact_name": contact_name,
            "is_blacklisted": is_blacklisted
        }
    except Exception as e:
        logger.error(f"Erreur lors de la vérification de la blacklist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", dependencies=[Depends(verify_api_key)])
async def bulk_add_to_blacklist(
    entries: List[BlacklistEntry],
    db: Database = Depends(get_database)
) -> dict:
    """
    Ajoute plusieurs contacts à la blacklist en une seule opération.

    Args:
        entries: Liste des contacts à bloquer

    Returns:
        Nombre d'entrées ajoutées
    """
    try:
        added_count = 0
        errors = []

        for entry in entries:
            try:
                db.add_to_blacklist(
                    contact_name=entry.contact_name,
                    linkedin_url=entry.linkedin_url,
                    reason=entry.reason,
                    added_by="api_bulk"
                )
                added_count += 1
            except Exception as e:
                errors.append({"contact": entry.contact_name, "error": str(e)})

        return {
            "success": True,
            "added_count": added_count,
            "total_requested": len(entries),
            "errors": errors if errors else None
        }
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout en masse à la blacklist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
