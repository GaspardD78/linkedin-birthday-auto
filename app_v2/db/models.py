from typing import Optional, Any, List
from datetime import date, datetime
from sqlalchemy import String, Boolean, Float, JSON, DateTime, Date, ForeignKey, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    profile_url: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    headline: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Sourcing (Visitor)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    open_to_work: Mapped[bool] = mapped_column(Boolean, default=False)
    fit_score: Mapped[float] = mapped_column(Float, default=0.0)
    skills: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)  # Text/JSON
    work_history: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)  # Text/JSON

    # Anniversaire
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_birthday_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Statut
    status: Mapped[str] = mapped_column(String, default="new")  # "new", "visited", "contacted", "blacklisted"

    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relations
    interactions: Mapped[List["Interaction"]] = relationship(back_populates="contact", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, name='{self.name}', status='{self.status}')>"

class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # "birthday_sent", "profile_visit", "invitation_withdrawn"
    status: Mapped[str] = mapped_column(String, nullable=False)  # "success", "failed"
    payload: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)  # Text/JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    contact: Mapped["Contact"] = relationship(back_populates="interactions")

    def __repr__(self) -> str:
        return f"<Interaction(id={self.id}, type='{self.type}', status='{self.status}')>"

class LinkedInSelector(Base):
    __tablename__ = "linkedin_selectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    selector_value: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<LinkedInSelector(key='{self.key}', score={self.score})>"

class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active")
    config_snapshot: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name='{self.name}', status='{self.status}')>"
