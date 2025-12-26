from fastapi import APIRouter, Depends, Query, Header, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app_v2.api.schemas import ContactResponse, InteractionResponse
from app_v2.db.engine import get_session_maker
from app_v2.db.models import Contact, Interaction
from app_v2.core.config import Settings

router = APIRouter(tags=["Data"])

# Dependencies
def get_settings():
    return Settings()

def verify_api_key(
    x_api_key: Optional[str] = Header(None),
    settings: Settings = Depends(get_settings)
) -> Settings:
    """Verify API key from X-API-Key header."""
    if not x_api_key:
        raise HTTPException(status_code=403, detail="Missing API key")

    expected_key = settings.api_key.get_secret_value() if hasattr(settings.api_key, 'get_secret_value') else str(settings.api_key)

    if x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return settings

# Dependency for DB Session
async def get_db_session(settings: Settings = Depends(verify_api_key)):
    # Note: In a real app, this should be a proper dependency with yield
    # utilizing the session_maker from engine
    session_maker = get_session_maker(settings)
    async with session_maker() as session:
        yield session

@router.get("/contacts", response_model=List[ContactResponse])
async def list_contacts(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    min_score: Optional[float] = None,
    session: AsyncSession = Depends(get_db_session)
):
    """Liste paginée des contacts avec filtres optionnels."""
    stmt = select(Contact)

    if status:
        stmt = stmt.where(Contact.status == status)

    if min_score is not None:
        stmt = stmt.where(Contact.fit_score >= min_score)

    stmt = stmt.order_by(desc(Contact.created_at)).offset(skip).limit(limit)

    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/interactions", response_model=List[InteractionResponse])
async def list_interactions(
    skip: int = 0,
    limit: int = 50,
    type: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    """Historique des interactions."""
    stmt = select(Interaction)

    if type:
        stmt = stmt.where(Interaction.type == type)

    stmt = stmt.order_by(desc(Interaction.created_at)).offset(skip).limit(limit)

    result = await session.execute(stmt)
    return result.scalars().all()
