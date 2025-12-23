import asyncio
import random
import logging

from app_v2.engine.browser_context import LinkedInBrowserContext
from app_v2.engine.selector_engine import SmartSelectorEngine

logger = logging.getLogger(__name__)

class ActionManager:
    """
    Module de haut niveau pour effectuer les actions humaines sur LinkedIn.
    Orchestre la navigation et les interactions via LinkedInBrowserContext et SmartSelectorEngine.
    """

    def __init__(self, context: LinkedInBrowserContext, selector_engine: SmartSelectorEngine):
        self.context = context
        self.selector_engine = selector_engine

    async def _random_delay(self, min_s: float = 1.0, max_s: float = 3.0):
        """Ajoute un délai aléatoire pour simuler le comportement humain."""
        delay = random.uniform(min_s, max_s)
        await asyncio.sleep(delay)

    async def _handle_popups(self):
        """Gère les popups intempestifs après navigation (ex: abonnement Premium, notifications)."""
        if not self.context.page:
            return

        # Liste de clés de sélecteurs pour les popups courants
        popup_keys = [
            "popups.close_button",
            "popups.dismiss",
            "popups.no_thanks"
        ]

        for key in popup_keys:
            try:
                # Timeout court pour ne pas bloquer le flux
                locator = await self.selector_engine.get(key, timeout=1000)
                if locator and await locator.is_visible():
                    logger.info(f"Popup détecté ({key}), fermeture...")
                    await locator.click()
                    await self._random_delay(0.5, 1.0)
            except Exception:
                pass

    # ==========================================
    # 1. Méthodes de Navigation
    # ==========================================

    async def goto_profile(self, url: str):
        """Navigue vers un profil LinkedIn."""
        try:
            if not self.context.page:
                raise RuntimeError("Page non initialisée")

            logger.info(f"Navigation vers le profil : {url}")
            await self.context.page.goto(url)
            await self._handle_popups()
            await self._random_delay(2.0, 4.0)
        except Exception as e:
            logger.error(f"Erreur lors de la navigation vers {url} : {e}")

    async def goto_messaging(self):
        """Accède à la messagerie."""
        try:
            if not self.context.page:
                raise RuntimeError("Page non initialisée")

            # Utilise un sélecteur global ou l'URL directe
            messaging_url = "https://www.linkedin.com/messaging/"
            logger.info("Accès à la messagerie...")
            await self.context.page.goto(messaging_url)
            await self._handle_popups()
            await self._random_delay(1.5, 3.0)
        except Exception as e:
            logger.error(f"Erreur accès messagerie : {e}")

    async def goto_network(self):
        """Accède à la page 'Mon Réseau'."""
        try:
            network_url = "https://www.linkedin.com/mynetwork/"
            logger.info("Accès au réseau...")
            await self.context.page.goto(network_url)
            await self._handle_popups()
            await self._random_delay(1.5, 3.0)
        except Exception as e:
            logger.error(f"Erreur accès réseau : {e}")

    # ==========================================
    # 2. Méthodes d'Interaction
    # ==========================================

    async def send_message(self, text: str) -> bool:
        """
        Envoie un message depuis la page de profil actuelle ou une conversation ouverte.
        """
        try:
            logger.info("Tentative d'envoi de message...")

            # 1. Trouver et cliquer sur le bouton "Se connecter" ou "Message" sur le profil
            # On essaie d'abord le bouton "Message" direct
            msg_btn = await self.selector_engine.get("profile.message_button", timeout=3000)
            if msg_btn:
                await msg_btn.click()
                await self._random_delay(1.0, 2.0)
            else:
                logger.warning("Bouton message non trouvé, tentative via menu 'Plus' ou connexion...")
                # Logique simplifiée ici, pourrait nécessiter plus de cas (Connect -> Add Note)
                return False

            # 2. Trouver la zone de texte
            textbox = await self.selector_engine.get("messaging.textbox", timeout=5000)
            if not textbox:
                logger.error("Zone de texte introuvable")
                return False

            # 3. Écrire le message (simulation frappe humaine)
            logger.debug(f"Écriture du message : {text[:20]}...")
            await textbox.fill(text) # .fill est plus sûr que .type pour les longs textes, mais moins "humain"
            # Pour simuler l'humain, on peut faire un délai après
            await self._random_delay(1.0, 2.0)

            # 4. Envoyer
            send_btn = await self.selector_engine.get("messaging.send_button", timeout=2000)
            if send_btn:
                await send_btn.click()
                logger.info("Message envoyé avec succès")
                await self._random_delay(1.0, 2.0)

                # Fermer la fenêtre de message si c'est un popup
                close_msg = await self.selector_engine.get("messaging.close_overlay", timeout=2000)
                if close_msg:
                    await close_msg.click()

                return True
            else:
                logger.error("Bouton d'envoi introuvable")
                return False

        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message : {e}")
            return False

    async def visit_profile(self):
        """
        Simule une visite complète de profil (scroll bas/haut).
        """
        try:
            if not self.context.page:
                return

            logger.info("Visite du profil (simulation humaine)...")

            # Scroll vers le bas progressivement
            for _ in range(random.randint(3, 6)):
                scroll_y = random.randint(300, 700)
                await self.context.page.mouse.wheel(0, scroll_y)
                await self._random_delay(0.5, 2.0)

            # Parfois remonter un peu
            if random.choice([True, False]):
                await self.context.page.mouse.wheel(0, -random.randint(200, 500))
                await self._random_delay(1.0, 2.0)

            logger.info("Visite terminée.")

        except Exception as e:
            logger.error(f"Erreur pendant la visite du profil : {e}")

    async def withdraw_invitation(self, name: str) -> bool:
        """
        Retire une invitation envoyée à une personne spécifique.
        """
        try:
            # Assure qu'on est sur la page des invitations envoyées
            sent_invites_url = "https://www.linkedin.com/mynetwork/invitation-manager/sent/"
            if self.context.page.url != sent_invites_url:
                await self.context.page.goto(sent_invites_url)
                await self._random_delay(2.0, 3.0)

            logger.info(f"Recherche de l'invitation pour : {name}")

            # Utilise un sélecteur qui cherche le nom dans la liste
            # Note: Cela dépend fortement de la structure DOM de la liste d'invitations
            # On suppose ici que SmartSelectorEngine peut gérer des sélecteurs dynamiques ou on utilise XPath ici pour l'exemple

            # Stratégie : trouver le conteneur qui a le texte 'name', puis le bouton 'Retirer' associé
            # Ceci est une simplification. Idéalement, SmartSelectorEngine gèrerait "invitation_row"

            # On cherche un élément visible contenant le nom
            target_locator = self.context.page.get_by_text(name, exact=False).first

            if await target_locator.is_visible():
                # On cherche le bouton "Retirer" à proximité (parent/sibling)
                # Cette partie est délicate sans voir le DOM exact, on tente une approche générique
                # Souvent: Card -> Header(Name) ... Footer(Button Withdraw)

                # On essaie de trouver le bouton "Retirer" dans le même conteneur parent
                # On remonte de quelques niveaux pour trouver le conteneur de la carte
                card = target_locator.locator("xpath=./ancestor::li[contains(@class, 'invitation-card')]")

                withdraw_btn = card.get_by_role("button", name="Retirer") # ou "Withdraw"

                if await withdraw_btn.is_visible():
                    await withdraw_btn.click()
                    await self._random_delay(0.5, 1.0)

                    # Gestion du modal de confirmation "Voulez-vous retirer...?"
                    confirm_btn = await self.selector_engine.get("popups.confirm_withdraw", timeout=2000)
                    if confirm_btn:
                        await confirm_btn.click()
                    else:
                        # Fallback: essaie de cliquer sur le bouton "Retirer" du modal
                        await self.context.page.get_by_role("button", name="Retirer").click()

                    logger.info(f"Invitation retirée pour {name}")
                    return True

            logger.warning(f"Invitation non trouvée pour {name}")
            return False

        except Exception as e:
            logger.error(f"Erreur lors du retrait de l'invitation pour {name} : {e}")
            return False
