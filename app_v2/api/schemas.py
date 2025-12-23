from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import Optional, List, Dict, Any
from datetime import datetime, date

# --- Control Schemas ---

class CampaignRequest(BaseModel):
    dry_run: bool = Field(default=True, description="Si True, n'envoie pas de messages réels.")
    mode: str = Field(default="standard", description="Mode du bot: 'standard' (jour même) ou 'unlimited' (rattrapage).")
    process_late: bool = Field(default=False, description="Activer le rattrapage des anniversaires manqués.")
    max_days_late: int = Field(default=7, description="Nombre de jours en arrière pour le rattrapage.")

class SourcingRequest(BaseModel):
    search_url: str = Field(..., description="URL de recherche LinkedIn (People Search).")
    limit: int = Field(default=50, ge=1, le=1000, description="Nombre maximum de profils à traiter.")
    criteria: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Critères de scoring (keywords, location, etc.).")
    dry_run: bool = Field(default=True, description="Mode simulation (pas d'écriture ou actions limitées).")

class BotStatusResponse(BaseModel):
    is_running: bool
    active_job: Optional[str] = None  # "birthday_campaign", "sourcing_campaign"
    last_update: datetime

# --- Data Schemas ---

class InteractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    status: str
    created_at: datetime
    payload: Optional[Dict[str, Any]] = None

class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    profile_url: str
    headline: Optional[str] = None
    location: Optional[str] = None
    open_to_work: bool = False
    fit_score: float = 0.0
    status: str
    birth_date: Optional[date] = None
    last_birthday_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Computed fields
    @computed_field
    def days_since_interaction(self) -> Optional[int]:
        if not self.last_birthday_message_at:
            return None
        delta = datetime.now() - self.last_birthday_message_at
        return delta.days
