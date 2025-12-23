from typing import Optional, List, Any
from datetime import date, datetime
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, Date, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.sql import func

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Contact(Base):
    __tablename__ = "contacts"

    # Champs de base
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    profile_url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String, default="new")

    # Champs Sourcing (pour VisitorBot)
    headline: Mapped[Optional[str]] = mapped_column(String)
    location: Mapped[Optional[str]] = mapped_column(String)
    open_to_work: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    fit_score: Mapped[Optional[float]] = mapped_column(Float)
    skills: Mapped[Optional[Any]] = mapped_column(JSON)
    work_history: Mapped[Optional[Any]] = mapped_column(JSON)

    # Champs Métier
    last_birthday_message_date: Mapped[Optional[date]] = mapped_column(Date)
    next_birthday_date: Mapped[Optional[date]] = mapped_column(Date)

    # Relations
    interactions: Mapped[List["Interaction"]] = relationship(back_populates="contact", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, name='{self.name}', url='{self.profile_url}')>"

class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # ex: "birthday_msg", "profile_visit", "invitation_withdraw"
    status: Mapped[str] = mapped_column(String, nullable=False)  # "success", "failed", "pending"
    payload: Mapped[Optional[Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relations
    contact: Mapped["Contact"] = relationship(back_populates="interactions")

    def __repr__(self) -> str:
        return f"<Interaction(id={self.id}, type='{self.type}', status='{self.status}', created_at='{self.created_at}')>"

class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # ex: "birthday", "sourcing"
    status: Mapped[str] = mapped_column(String, default="active")

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name='{self.name}', type='{self.type}', status='{self.status}')>"
