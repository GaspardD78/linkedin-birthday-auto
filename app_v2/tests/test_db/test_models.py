"""
Unit tests for database models (app_v2/db/models.py).

Tests ORM mappings, relationships, and model validation.
"""

import pytest
import pytest_asyncio
from datetime import date, datetime, timezone
from sqlalchemy import select, inspect

from app_v2.db.models import Contact, Interaction, LinkedInSelector


@pytest.mark.integration
class TestContactModel:
    """Test Contact ORM model."""

    @pytest.mark.asyncio
    async def test_create_contact(self, test_db_session):
        """Test creating a contact in the database."""
        contact = Contact(
            name="Test User",
            profile_url="https://linkedin.com/in/testuser",
            birth_date=date(1990, 1, 15),
            status="new",
        )

        test_db_session.add(contact)
        await test_db_session.commit()
        await test_db_session.refresh(contact)

        assert contact.id is not None
        assert contact.name == "Test User"
        assert contact.status == "new"
        assert contact.created_at is not None

    @pytest.mark.asyncio
    async def test_contact_indexes_exist(self, test_db_engine):
        """Test that Contact table has required indexes."""
        async with test_db_engine.connect() as conn:
            inspector = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn)
            )

        indexes = inspector.get_indexes("contact")
        index_names = {idx["name"] for idx in indexes}

        # Check for critical indexes
        assert "idx_contact_birth_date" in index_names
        assert "idx_contact_status" in index_names
        assert "idx_contact_created_at" in index_names

    @pytest.mark.asyncio
    async def test_contact_with_interactions(self, test_db_session):
        """Test contact with related interactions."""
        contact = Contact(
            name="User With Interactions",
            profile_url="https://linkedin.com/in/userinteractions",
            birth_date=date(1992, 6, 20),
            status="contacted",
        )

        test_db_session.add(contact)
        await test_db_session.flush()

        interaction = Interaction(
            contact_id=contact.id,
            type="birthday_sent",
            status="success",
            payload={"message": "Happy Birthday!"},
        )

        test_db_session.add(interaction)
        await test_db_session.commit()

        # Verify relationship
        result = await test_db_session.execute(
            select(Contact).where(Contact.id == contact.id)
        )
        loaded_contact = result.scalar_one()
        assert loaded_contact.id == contact.id


@pytest.mark.integration
class TestInteractionModel:
    """Test Interaction ORM model."""

    @pytest.mark.asyncio
    async def test_create_interaction(self, test_db_session):
        """Test creating an interaction."""
        # Create contact first
        contact = Contact(
            name="Test Contact",
            profile_url="https://linkedin.com/in/testcontact",
            birth_date=date(1995, 3, 10),
            status="new",
        )
        test_db_session.add(contact)
        await test_db_session.flush()

        # Create interaction
        interaction = Interaction(
            contact_id=contact.id,
            type="profile_visit",
            status="success",
            payload={"selector": "test_selector"},
        )

        test_db_session.add(interaction)
        await test_db_session.commit()
        await test_db_session.refresh(interaction)

        assert interaction.id is not None
        assert interaction.contact_id == contact.id
        assert interaction.type == "profile_visit"
        assert interaction.created_at is not None

    @pytest.mark.asyncio
    async def test_interaction_indexes_exist(self, test_db_engine):
        """Test that Interaction table has composite index."""
        async with test_db_engine.connect() as conn:
            inspector = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn)
            )

        indexes = inspector.get_indexes("interaction")
        index_names = {idx["name"] for idx in indexes}

        # Check for composite index
        assert "idx_interaction_contact_type" in index_names

    @pytest.mark.asyncio
    async def test_interaction_payload_json(self, test_db_session):
        """Test that interaction payload stores JSON correctly."""
        contact = Contact(
            name="JSON Test",
            profile_url="https://linkedin.com/in/jsontest",
            birth_date=date(1988, 12, 25),
            status="new",
        )
        test_db_session.add(contact)
        await test_db_session.flush()

        payload = {
            "message_text": "Test message",
            "response_code": 200,
            "nested": {"key": "value"},
        }

        interaction = Interaction(
            contact_id=contact.id,
            type="birthday_sent",
            status="success",
            payload=payload,
        )

        test_db_session.add(interaction)
        await test_db_session.commit()
        await test_db_session.refresh(interaction)

        assert interaction.payload == payload
        assert interaction.payload["nested"]["key"] == "value"


@pytest.mark.integration
class TestLinkedInSelectorModel:
    """Test LinkedInSelector ORM model."""

    @pytest.mark.asyncio
    async def test_create_selector(self, test_db_session):
        """Test creating a LinkedIn selector."""
        selector = LinkedInSelector(
            name="test_selector",
            xpath="//button[@data-test='send-message']",
            description="Test selector for messages",
        )

        test_db_session.add(selector)
        await test_db_session.commit()
        await test_db_session.refresh(selector)

        assert selector.id is not None
        assert selector.name == "test_selector"
        assert selector.success_count == 0
        assert selector.failure_count == 0

    @pytest.mark.asyncio
    async def test_selector_success_tracking(self, test_db_session):
        """Test selector success/failure tracking."""
        selector = LinkedInSelector(
            name="tracked_selector",
            xpath="//div[@class='message-button']",
            description="Tracked selector",
            success_count=5,
            failure_count=2,
        )

        test_db_session.add(selector)
        await test_db_session.commit()
        await test_db_session.refresh(selector)

        assert selector.success_count == 5
        assert selector.failure_count == 2

    @pytest.mark.asyncio
    async def test_selector_indexes_exist(self, test_db_engine):
        """Test that LinkedInSelector table has required indexes."""
        async with test_db_engine.connect() as conn:
            inspector = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn)
            )

        indexes = inspector.get_indexes("linkedin_selector")
        index_names = {idx["name"] for idx in indexes}

        # Check for success tracking index
        assert "idx_selector_success" in index_names


@pytest.mark.integration
class TestModelRelationships:
    """Test relationships between models."""

    @pytest.mark.asyncio
    async def test_contact_interaction_foreign_key(self, test_db_session):
        """Test foreign key constraint between Contact and Interaction."""
        contact = Contact(
            name="FK Test",
            profile_url="https://linkedin.com/in/fktest",
            birth_date=date(1993, 7, 4),
            status="new",
        )
        test_db_session.add(contact)
        await test_db_session.flush()

        interaction = Interaction(
            contact_id=contact.id,
            type="test_interaction",
            status="success",
        )

        test_db_session.add(interaction)
        await test_db_session.commit()

        # Verify interaction is linked to contact
        result = await test_db_session.execute(
            select(Interaction).where(Interaction.contact_id == contact.id)
        )
        loaded_interaction = result.scalar_one()
        assert loaded_interaction.contact_id == contact.id

    @pytest.mark.asyncio
    async def test_query_contacts_with_interactions(self, test_db_session):
        """Test querying contacts and their interactions."""
        # Create multiple contacts with interactions
        contact1 = Contact(
            name="Contact 1",
            profile_url="https://linkedin.com/in/contact1",
            birth_date=date(1990, 1, 1),
            status="contacted",
        )
        contact2 = Contact(
            name="Contact 2",
            profile_url="https://linkedin.com/in/contact2",
            birth_date=date(1991, 2, 2),
            status="new",
        )

        test_db_session.add_all([contact1, contact2])
        await test_db_session.flush()

        # Add interactions for contact1 only
        interaction1 = Interaction(
            contact_id=contact1.id,
            type="birthday_sent",
            status="success",
        )
        interaction2 = Interaction(
            contact_id=contact1.id,
            type="profile_visit",
            status="success",
        )

        test_db_session.add_all([interaction1, interaction2])
        await test_db_session.commit()

        # Query contacts with interactions
        result = await test_db_session.execute(
            select(Interaction).where(Interaction.contact_id == contact1.id)
        )
        interactions = result.scalars().all()

        assert len(interactions) == 2
