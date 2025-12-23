import asyncio
import logging
import random
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app_v2.core.config import Settings
from app_v2.db.engine import get_session_maker
from app_v2.db.models import Contact, Interaction
from app_v2.engine.action_manager import ActionManager
from app_v2.engine.auth_manager import AuthManager
from app_v2.engine.browser_context import LinkedInBrowserContext
from app_v2.engine.selector_engine import SmartSelectorEngine

logger = logging.getLogger(__name__)


class BirthdayService:
    """
    Service de gestion des campagnes d'anniversaire (V2).
    Migre la logique du 'BirthdayBot' V1 vers une architecture orientée service.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.session_maker = get_session_maker(settings)
        self.auth_manager = AuthManager(settings)

    async def run_daily_campaign(self, dry_run: bool = False):
        """
        Exécute la campagne quotidienne d'anniversaires.
        Orchestre la sélection des contacts, la vérification des quotas et l'envoi des messages.

        Args:
            dry_run: Si True, simule l'envoi des messages sans les envoyer réellement.
        """
        logger.info(f"🎂 Démarrage de la campagne d'anniversaires (Dry Run: {dry_run})")

        # 1. Vérification des quotas avant de commencer (Fail-Fast)
        async with self.session_maker() as session:
            try:
                limit = await self._calculate_max_allowed_messages(session)
                if limit <= 0:
                    logger.warning("Quota atteint pour aujourd'hui ou la semaine. Arrêt de la campagne.")
                    return
                logger.info(f"✅ Budget messages pour cette exécution : {limit}")
            except Exception as e:
                logger.error(f"Erreur lors de la vérification des quotas : {e}")
                return

        # 2. Sélection des contacts éligibles
        async with self.session_maker() as session:
            contacts = await self._select_contacts(session)
            if not contacts:
                logger.info("Aucun contact à souhaiter aujourd'hui.")
                return
            logger.info(f"Contacts sélectionnés : {len(contacts)}")

        # 3. Exécution de la campagne avec le navigateur
        async with LinkedInBrowserContext(self.settings, self.auth_manager) as context:
            # Initialisation du moteur de sélecteurs et de l'ActionManager
            selector_engine = SmartSelectorEngine(context.page, self.settings)
            bot = ActionManager(context, selector_engine)

            # Vérification initiale de la session
            is_logged_in = await self.auth_manager.validate_session(context.page)
            if not is_logged_in:
                logger.error("Échec de la validation de session LinkedIn. Arrêt.")
                return

            messages_sent = 0

            # Réouverture de session pour le traitement (pour commit au fur et à mesure)
            # Note: On utilise une session par itération ou une session longue ?
            # Pour la robustesse, on peut utiliser une session par interaction ou une longue session avec commit
            # Ici, on va utiliser une session pour mettre à jour les contacts au fur et à mesure.

            for contact in contacts:
                if messages_sent >= limit:
                    logger.info("Limite de messages atteinte pour cette exécution.")
                    break

                try:
                    logger.info(f"Traitement de {contact.name} ({contact.profile_url})...")

                    # Navigation
                    await bot.goto_profile(contact.profile_url)

                    # Simulation humaine (aléatoire)
                    if random.random() < 0.3:
                        await bot.visit_profile()

                    # Message
                    # TODO: Implémenter un gestionnaire de templates de messages plus avancé
                    message = self._get_birthday_message(contact, dry_run)

                    success = False
                    if dry_run:
                        logger.info(f"[DRY-RUN] Envoi simulé à {contact.name}: '{message}'")
                        success = True
                        await asyncio.sleep(random.uniform(1, 2))
                    else:
                        success = await bot.send_message(message)

                    # Enregistrement du résultat
                    async with self.session_maker() as session:
                        # Re-fetch contact to ensure attached to session
                        current_contact = await session.get(Contact, contact.id)
                        if current_contact:
                            status = "success" if success else "failed"

                            interaction = Interaction(
                                contact_id=current_contact.id,
                                type="birthday_sent",
                                status=status,
                                payload={"message": message, "dry_run": dry_run}
                            )
                            session.add(interaction)

                            if success:
                                # Important : Ne PAS mettre à jour la date en mode Dry Run
                                # pour éviter de "consommer" l'anniversaire sans l'envoyer.
                                if not dry_run:
                                    current_contact.last_birthday_message_at = datetime.now()

                                messages_sent += 1
                                logger.info(f"✅ Message envoyé à {contact.name}")
                            else:
                                logger.warning(f"❌ Échec de l'envoi pour {contact.name}")

                            await session.commit()

                    # Pause entre les messages
                    if success:
                         await self._wait_between_messages(dry_run)

                except Exception as e:
                    logger.error(f"Erreur lors du traitement de {contact.name}: {e}")
                    # On continue avec le suivant
                    continue

        logger.info(f"🏁 Campagne terminée. Messages envoyés : {messages_sent}/{len(contacts)}")

    async def _select_contacts(self, session: AsyncSession) -> list[Contact]:
        """
        Sélectionne les contacts éligibles pour un souhait d'anniversaire.
        Critères :
        - Anniversaire aujourd'hui
        - OU (En retard ET config.process_late=True)
        - ET Pas encore contacté cette année (basé sur last_birthday_message_at)
        """
        today = date.today()
        current_year = today.year

        # Format SQLite strftime: '%m-%d'
        # Attention: birth_date est stocké comme Date.
        # SQLAlchemy func.strftime('%m-%d', Contact.birth_date)

        today_str = today.strftime('%m-%d')

        # Filtre de base : Pas de message cette année
        # On vérifie si last_birthday_message_at est NULL ou si l'année est < current_year
        not_contacted_this_year = or_(
            Contact.last_birthday_message_at.is_(None),
            func.strftime('%Y', Contact.last_birthday_message_at) != str(current_year)
        )

        # 1. Anniversaire Aujourd'hui
        is_today = func.strftime('%m-%d', Contact.birth_date) == today_str

        criteria = is_today

        # 2. Gestion des retards (Late)
        if self.settings.process_late:
            # On cherche les dates entre (today - max_days_late) et (today - 1)
            # C'est complexe en SQL pur sur le jour/mois sans l'année.
            # Approche simplifiée : On récupère tous les anniversaires "probables" et on filtre en Python,
            # ou on construit une condition OR complexe.
            # Pour V2/SQLite, une approche hybride est souvent plus simple et robuste :
            # Récupérer les contacts non contactés cette année et filtrer en Python si le volume n'est pas énorme.
            # Cependant, pour respecter "SQLAlchemy Async", essayons de faire le maximum en SQL.

            # Alternative : On peut générer la liste des chaines "MM-DD" pour les N derniers jours.
            late_dates = []
            for i in range(1, self.settings.max_days_late + 1):
                d = today - timedelta(days=i)
                late_dates.append(d.strftime('%m-%d'))

            if late_dates:
                is_late = func.strftime('%m-%d', Contact.birth_date).in_(late_dates)
                criteria = or_(is_today, is_late)

        stmt = select(Contact).where(
            and_(
                criteria,
                not_contacted_this_year,
                Contact.status != 'blacklisted'  # Exclure les blacklistés
            )
        )

        result = await session.execute(stmt)
        return result.scalars().all()

    async def _calculate_max_allowed_messages(self, session: AsyncSession) -> int:
        """
        Calcule le nombre de messages autorisés en fonction des quotas configurés (Daily/Weekly).
        Inspire de '_calculate_max_allowed_messages' de la V1.
        """
        # 1. Quota Run (Config)
        max_run = self.settings.max_messages_per_execution

        # 2. Quota Hebdomadaire
        # Compter les interactions de type 'birthday_sent' et status 'success' depuis 7 jours
        one_week_ago = datetime.now() - timedelta(days=7)
        stmt_weekly = select(func.count(Interaction.id)).where(
            Interaction.type == 'birthday_sent',
            Interaction.status == 'success',
            Interaction.created_at >= one_week_ago
        )
        weekly_count = (await session.execute(stmt_weekly)).scalar() or 0
        weekly_remaining = max(0, self.settings.max_messages_per_week - weekly_count)

        # 3. Quota Journalier
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        stmt_daily = select(func.count(Interaction.id)).where(
            Interaction.type == 'birthday_sent',
            Interaction.status == 'success',
            Interaction.created_at >= today_start
        )
        daily_count = (await session.execute(stmt_daily)).scalar() or 0
        daily_remaining = max(0, self.settings.max_messages_per_day - daily_count)

        logger.info(f"Stats Quotas : Daily sent={daily_count} (rem={daily_remaining}), Weekly sent={weekly_count} (rem={weekly_remaining})")

        return min(max_run, daily_remaining, weekly_remaining)

    async def _wait_between_messages(self, dry_run: bool):
        """Pause aléatoire entre les messages."""
        if dry_run:
            delay = random.uniform(2, 5)
            logger.info(f"⏸️ Pause (Dry Run): {delay:.1f}s")
            await asyncio.sleep(delay)
        else:
            delay = random.uniform(
                self.settings.min_delay_between_messages,
                self.settings.max_delay_between_messages
            )
            logger.info(f"⏸️ Pause: {int(delay)}s")
            await asyncio.sleep(delay)

    def _get_birthday_message(self, contact: Contact, dry_run: bool) -> str:
        """
        Génère le message d'anniversaire.
        Pourrait être étendu pour utiliser des templates ou des fichiers externes.
        """
        # TODO: Charger depuis un fichier ou la config comme dans V1
        first_name = contact.name.split()[0] if contact.name else ""
        return f"Joyeux anniversaire {first_name} ! 🎂"
