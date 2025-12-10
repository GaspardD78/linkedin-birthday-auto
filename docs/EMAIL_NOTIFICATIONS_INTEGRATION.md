# 📧 Intégration des Notifications Email dans les Bots

## État Actuel

Le système de notifications email **est déjà implémenté** mais **n'est pas connecté** aux bots (birthday_bot.py, visitor_bot.py).

### Ce qui existe déjà ✅

1. **Backend complet** : `src/services/notification_service.py`
2. **API routes** : `src/api/routes/notifications.py`
3. **Dashboard UI** : `/settings/notifications`
4. **Table database** : `notification_settings`, `notification_logs`

### Ce qui manque ⚠️

Les bots n'appellent **jamais** le `NotificationService` après exécution.

---

## Impact Utilisateur

**Actuellement** :
- ❌ Aucune alerte si le bot échoue (cookie expiré, CAPTCHA, etc.)
- ❌ Aucune notification de succès
- ❌ L'utilisateur doit checker les logs manuellement

**Après intégration** :
- ✅ Email automatique si erreur critique
- ✅ Email quotidien résumant les actions
- ✅ Alert si cookies LinkedIn expirent

---

## Guide d'Intégration (30 minutes)

### Étape 1 : Modifier `birthday_bot.py`

**Fichier** : `src/bots/birthday_bot.py`

**Ajouter en haut du fichier** :

```python
from ..services.notification_service import NotificationService
import asyncio
```

**Modifier la méthode `_run_internal()` (ligne ~142)** :

```python
def _run_internal(self) -> dict[str, Any]:
    """
    Exécute le bot pour envoyer des messages d'anniversaire.
    """
    start_time = time.time()

    # ... code existant ...

    try:
        # Boucle principale du bot (existant)
        for contact_data, contact_locator in self.yield_birthday_contacts():
            # ... traitement existant ...

        duration = time.time() - start_time

        # ✅ AJOUTER ICI : Notification de succès
        self._send_success_notification(messages_sent=self.run_stats["sent"])

        return self._build_result(
            messages_sent=self.run_stats["sent"],
            # ... autres paramètres existants ...
        )

    except Exception as e:
        # ✅ AJOUTER ICI : Notification d'erreur
        self._send_error_notification(error=e)

        return self._build_error_result(str(e))
```

**Ajouter ces méthodes helper à la fin de la classe BirthdayBot** :

```python
def _send_success_notification(self, messages_sent: int):
    """Envoie une notification de succès si configurée."""
    if not self.db:
        return

    try:
        notification_service = NotificationService(self.db)

        # Exécuter de façon asynchrone dans un event loop
        asyncio.run(notification_service.notify_success(message_count=messages_sent))

        logger.info(f"Success notification sent (messages_sent={messages_sent})")
    except Exception as e:
        logger.warning(f"Failed to send success notification: {e}")

def _send_error_notification(self, error: Exception):
    """Envoie une notification d'erreur si configurée."""
    if not self.db:
        return

    try:
        notification_service = NotificationService(self.db)

        error_message = str(error)
        error_details = f"Bot: BirthdayBot\nError Type: {type(error).__name__}\nTimestamp: {datetime.now().isoformat()}"

        # Exécuter de façon asynchrone
        asyncio.run(notification_service.notify_error(
            error_message=error_message,
            error_details=error_details
        ))

        logger.info(f"Error notification sent: {error_message}")
    except Exception as e:
        logger.warning(f"Failed to send error notification: {e}")
```

---

### Étape 2 : Modifier `visitor_bot.py`

**Fichier** : `src/bots/visitor_bot.py`

**Même approche que birthday_bot** :

1. Importer `NotificationService` et `asyncio`
2. Ajouter appels dans la méthode `run()` ou `_run_internal()`
3. Ajouter les méthodes helper `_send_success_notification()` et `_send_error_notification()`

**Exemple spécifique pour VisitorBot** :

```python
# Dans visitor_bot.py, ligne ~250 (fin de run())

# ✅ AJOUTER : Notification succès
self._send_visitor_success_notification(profiles_visited=self.stats["profiles_visited"])

return {
    "success": True,
    # ... reste du résultat ...
}
```

```python
def _send_visitor_success_notification(self, profiles_visited: int):
    """Notification spécifique VisitorBot."""
    if not self.db:
        return

    try:
        notification_service = NotificationService(self.db)

        # Message personnalisé pour VisitorBot
        subject = "✅ Visite de profils terminée - LinkedIn Bot"
        body = f"""
L'exécution du bot de visite de profils s'est terminée avec succès.

Profils visités: {profiles_visited}
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        settings = notification_service.get_settings()
        if settings["email_enabled"] and settings["email_address"]:
            asyncio.run(notification_service.send_email(
                to_email=settings["email_address"],
                subject=subject,
                body=body,
                event_type="visitor_success"
            ))

        logger.info("VisitorBot success notification sent")
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")
```

---

### Étape 3 : Notification Expiration Cookies

**Fichier** : `src/core/auth_manager.py`

**Ajouter une vérification automatique** :

```python
from ..services.notification_service import NotificationService
import asyncio

def validate_cookies(self, cookies: list[dict]) -> bool:
    """Valide que les cookies ne sont pas expirés."""
    now = int(time.time())

    for cookie in cookies:
        if "expires" in cookie:
            if cookie["expires"] < now:
                # ✅ AJOUTER : Notification cookies expirés
                self._notify_cookies_expired()
                return False

    return True

def _notify_cookies_expired(self):
    """Alerte l'utilisateur que les cookies ont expiré."""
    try:
        from ..core.database import get_database
        db = get_database("/app/data/linkedin.db")

        notification_service = NotificationService(db)
        asyncio.run(notification_service.notify_cookies_expiry())

        logger.warning("Cookies expiry notification sent")
    except Exception as e:
        logger.error(f"Failed to send cookies expiry notification: {e}")
```

---

## Configuration SMTP (Prérequis)

Pour que les notifications fonctionnent, configurez votre `.env` :

```bash
# SMTP Configuration (Gmail recommandé)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=votre.email@gmail.com
SMTP_PASSWORD=your_app_password  # Pas votre mot de passe Gmail !
SMTP_FROM_EMAIL=votre.email@gmail.com
```

### Obtenir un App Password Gmail

1. Allez sur https://myaccount.google.com/security
2. Activez "2-Step Verification"
3. Allez dans "App passwords"
4. Générez un mot de passe pour "Mail"
5. Copiez-le dans `SMTP_PASSWORD`

---

## Tester les Notifications

### Test 1 : Email de test

```bash
# Via Dashboard UI
# Allez sur /settings/notifications
# Configurez votre email
# Cliquez sur "Envoyer un test"

# Ou via curl
curl -X POST http://localhost:8000/notifications/test \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"email": "votre@email.com"}'
```

### Test 2 : Notification d'erreur

```python
# Provoquer une erreur volontaire dans le bot
from src.services.notification_service import NotificationService
from src.core.database import get_database
import asyncio

db = get_database("/app/data/linkedin.db")
service = NotificationService(db)

asyncio.run(service.notify_error(
    error_message="Test d'erreur",
    error_details="Ceci est un test"
))
```

### Test 3 : Notification de succès

```python
asyncio.run(service.notify_success(message_count=5))
```

---

## Types de Notifications Disponibles

| Événement | Méthode | Description |
|-----------|---------|-------------|
| Succès bot | `notify_success(message_count)` | Après exécution réussie |
| Erreur critique | `notify_error(error_message, error_details)` | En cas d'échec |
| Démarrage bot | `notify_bot_start()` | Bot démarre |
| Arrêt bot | `notify_bot_stop()` | Bot s'arrête |
| Cookies expirés | `notify_cookies_expiry()` | Authentification invalide |

---

## Logs de Notifications

Toutes les notifications sont loggées dans la table `notification_logs` :

```sql
SELECT * FROM notification_logs ORDER BY created_at DESC LIMIT 10;
```

Colonnes :
- `event_type` : Type d'événement (success, error, test, etc.)
- `recipient_email` : Destinataire
- `status` : sent, failed, pending
- `sent_at` : Date d'envoi
- `error_message` : Si échec

---

## Fréquence Recommandée

**Pour éviter le spam** :

- ✅ **Toujours** : Erreurs critiques (cookie expiré, crash bot)
- ✅ **Quotidien** : Résumé succès (1 email/jour max)
- ❌ **Jamais** : Chaque message envoyé (trop de notifications)

**Configuration dans le dashboard** :
- `notify_on_error` : **true** (recommandé)
- `notify_on_success` : **false** (sauf si vous voulez un résumé quotidien)
- `notify_on_cookies_expiry` : **true** (critique)

---

## Dépannage

### Problème : Emails non reçus

**Vérifiez** :

```bash
# 1. Configuration SMTP
docker compose -f docker-compose.pi4-standalone.yml exec api env | grep SMTP

# 2. Logs d'erreur
docker compose logs api | grep -i "smtp\|notification"

# 3. Table notification_logs
docker compose exec api sqlite3 /app/data/linkedin.db "SELECT * FROM notification_logs WHERE status='failed' ORDER BY created_at DESC LIMIT 5;"
```

### Problème : "Authentication failed"

- Gmail : Utilisez un **App Password**, pas votre mot de passe principal
- Outlook : Activez "SMTP AUTH" dans les paramètres
- Vérifiez `SMTP_USER` et `SMTP_FROM_EMAIL` sont identiques

### Problème : "Connection timeout"

- Vérifiez `SMTP_PORT` (Gmail = 587, Outlook = 587)
- Vérifiez `SMTP_USE_TLS=true`
- Testez depuis le Raspberry Pi : `telnet smtp.gmail.com 587`

---

## Résumé

**Temps d'implémentation** : ~30 minutes

**Étapes** :
1. ✅ Configurer SMTP dans `.env`
2. ✅ Tester avec `/api/notifications/test`
3. ✅ Ajouter appels dans `birthday_bot.py`
4. ✅ Ajouter appels dans `visitor_bot.py`
5. ✅ Ajouter alerte cookies dans `auth_manager.py`
6. ✅ Tester end-to-end

**Bénéfice** :
- Plus besoin de surveiller les logs manuellement
- Alerte immédiate si problème
- Tranquillité d'esprit (le bot vous prévient)

---

**Auteur** : Audit Sécurité 2025
**Version** : 1.0
