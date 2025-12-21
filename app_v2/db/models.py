from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from datetime import datetime
from typing import Optional
import uuid

class Base(AsyncAttrs, DeclarativeBase):
    pass

# Modèle 1 : contacts
class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String, unique=True)
    last_message_date: Mapped[Optional[str]] = mapped_column(String)  # Format ISO
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    relationship_score: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[str]] = mapped_column(String)
    updated_at: Mapped[Optional[str]] = mapped_column(String)

    # Relation vers messages
    messages: Mapped[list["BirthdayMessage"]] = relationship(back_populates="contact")

    def __repr__(self):
        return f"<Contact(id={self.id}, name='{self.name}')>"

# Modèle 2 : birthday_messages
class BirthdayMessage(Base):
    __tablename__ = "birthday_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("contacts.id"))
    contact_name: Mapped[Optional[str]] = mapped_column(String)
    message_text: Mapped[Optional[str]] = mapped_column(Text)
    sent_at: Mapped[Optional[str]] = mapped_column(String)
    is_late: Mapped[Optional[bool]] = mapped_column(Boolean)
    days_late: Mapped[Optional[int]] = mapped_column(Integer)
    script_mode: Mapped[Optional[str]] = mapped_column(String)  # "v1" ou "v2"

    # Relation vers contact
    contact: Mapped[Optional["Contact"]] = relationship(back_populates="messages")

    def __repr__(self):
        return f"<BirthdayMessage(id={self.id}, contact='{self.contact_name}', sent_at='{self.sent_at}')>"

# Modèle 3 : linkedin_selectors (pour le système heuristique)
class LinkedInSelector(Base):
    __tablename__ = "linkedin_selectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    element_type: Mapped[str] = mapped_column(String, nullable=False)  # "message_button", "textbox"...
    selector: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    last_success_at: Mapped[Optional[str]] = mapped_column(String)
    last_failure_at: Mapped[Optional[str]] = mapped_column(String)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    def __repr__(self):
        return f"<LinkedInSelector(type='{self.element_type}', score={self.score})>"

# Modèle 4 : campaigns (si tu veux tracker les exécutions)
class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[str] = mapped_column(String)
    ended_at: Mapped[Optional[str]] = mapped_column(String)
    messages_sent: Mapped[int] = mapped_column(Integer, default=0)
    messages_failed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="running")  # running, completed, failed

    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}', status='{self.status}')>"
