"""
Rate Limiter et Circuit Breaker pour LinkedIn.

Ce module implémente un rate limiter et circuit breaker pour éviter
le blocage du compte LinkedIn en cas d'activité excessive.

Version 1.0.0 - Audit Phase 2
"""

from enum import Enum
import logging
import threading
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """États du circuit breaker."""

    CLOSED = "closed"  # Circuit fermé - fonctionnement normal
    OPEN = "open"  # Circuit ouvert - toutes les requêtes échouent
    HALF_OPEN = "half_open"  # Circuit semi-ouvert - tentative de récupération


class RateLimiter:
    """
    Rate limiter avec fenêtre glissante.

    Limite le nombre d'actions dans une fenêtre de temps donnée.
    Thread-safe pour utilisation concurrente.

    Exemples:
        >>> limiter = RateLimiter(max_calls=10, time_window=60)
        >>> if limiter.acquire():
        ...     # Action autorisée
        ...     send_message()
        ... else:
        ...     # Limite atteinte
        ...     print("Rate limit exceeded")
    """

    def __init__(self, max_calls: int, time_window: int):
        """
        Initialise le rate limiter.

        Args:
            max_calls: Nombre maximum d'appels autorisés
            time_window: Fenêtre de temps en secondes
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []  # Liste des timestamps d'appels
        self.lock = threading.Lock()

    def acquire(self) -> bool:
        """
        Tente d'acquérir un slot pour une action.

        Returns:
            True si l'action est autorisée, False sinon
        """
        with self.lock:
            current_time = time.time()
            cutoff_time = current_time - self.time_window

            # Nettoyer les appels expirés
            self.calls = [t for t in self.calls if t > cutoff_time]

            # Vérifier si on peut faire un nouvel appel
            if len(self.calls) < self.max_calls:
                self.calls.append(current_time)
                return True

            return False

    def wait_time(self) -> Optional[float]:
        """
        Retourne le temps d'attente avant le prochain slot disponible.

        Returns:
            Temps d'attente en secondes ou None si slot disponible
        """
        with self.lock:
            current_time = time.time()
            cutoff_time = current_time - self.time_window

            # Nettoyer les appels expirés
            self.calls = [t for t in self.calls if t > cutoff_time]

            # Si on peut faire un appel maintenant
            if len(self.calls) < self.max_calls:
                return None

            # Sinon, calculer le temps d'attente
            oldest_call = min(self.calls)
            wait_until = oldest_call + self.time_window
            return wait_until - current_time

    def get_stats(self) -> dict:
        """
        Retourne les statistiques du rate limiter.

        Returns:
            Dict avec les statistiques
        """
        with self.lock:
            current_time = time.time()
            cutoff_time = current_time - self.time_window
            self.calls = [t for t in self.calls if t > cutoff_time]

            return {
                "current_calls": len(self.calls),
                "max_calls": self.max_calls,
                "time_window": self.time_window,
                "available_slots": self.max_calls - len(self.calls),
                "wait_time": self.wait_time(),
            }

    def reset(self) -> None:
        """Réinitialise le compteur d'appels."""
        with self.lock:
            self.calls = []
            logger.info("Rate limiter reset")


class CircuitBreaker:
    """
    Circuit breaker pour protéger contre les pannes en cascade.

    Implémente le pattern Circuit Breaker pour détecter les erreurs
    répétées et "ouvrir" le circuit temporairement.

    Exemples:
        >>> breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        >>> with breaker:
        ...     # Code protégé
        ...     call_linkedin_api()
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60, half_open_max_calls: int = 1):
        """
        Initialise le circuit breaker.

        Args:
            failure_threshold: Nombre d'échecs avant ouverture du circuit
            timeout: Durée d'ouverture du circuit en secondes
            half_open_max_calls: Nombre de tentatives en état half-open
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED

        self.lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Exécute une fonction protégée par le circuit breaker.

        Args:
            func: Fonction à exécuter
            *args: Arguments positionnels
            **kwargs: Arguments nommés

        Returns:
            Résultat de la fonction

        Raises:
            CircuitOpenError: Si le circuit est ouvert
            Exception: Exception de la fonction appelée
        """
        with self.lock:
            # Vérifier l'état du circuit
            current_state = self._get_state()

            if current_state == CircuitState.OPEN:
                raise CircuitOpenError(
                    f"Circuit breaker is OPEN. Retry after {self._time_until_half_open():.1f}s"
                )

            if current_state == CircuitState.HALF_OPEN:
                if self.success_count >= self.half_open_max_calls:
                    raise CircuitOpenError(
                        "Circuit breaker is in HALF_OPEN state with max calls reached"
                    )

        # Exécuter la fonction
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _get_state(self) -> CircuitState:
        """Retourne l'état actuel du circuit."""
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._open_circuit()
                return CircuitState.OPEN
            return CircuitState.CLOSED

        elif self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._half_open_circuit()
                return CircuitState.HALF_OPEN
            return CircuitState.OPEN

        else:  # HALF_OPEN
            return CircuitState.HALF_OPEN

    def _open_circuit(self) -> None:
        """Ouvre le circuit."""
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()
        logger.warning(f"🔴 Circuit breaker OPENED after {self.failure_count} failures")

    def _half_open_circuit(self) -> None:
        """Passe le circuit en état semi-ouvert."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        logger.info("🟡 Circuit breaker HALF-OPEN - testing recovery")

    def _close_circuit(self) -> None:
        """Ferme le circuit (récupération)."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        logger.info("🟢 Circuit breaker CLOSED - normal operation")

    def _should_attempt_reset(self) -> bool:
        """Vérifie si on doit tenter de réinitialiser le circuit."""
        if self.last_failure_time is None:
            return False
        return (time.time() - self.last_failure_time) >= self.timeout

    def _time_until_half_open(self) -> float:
        """Retourne le temps avant passage en HALF_OPEN."""
        if self.last_failure_time is None:
            return 0
        elapsed = time.time() - self.last_failure_time
        return max(0, self.timeout - elapsed)

    def _on_success(self) -> None:
        """Appelé après une exécution réussie."""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.half_open_max_calls:
                    self._close_circuit()
            elif self.state == CircuitState.CLOSED:
                # Réinitialiser le compteur d'échecs en cas de succès
                self.failure_count = max(0, self.failure_count - 1)

    def _on_failure(self) -> None:
        """Appelé après une exécution échouée."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                # Échec en HALF_OPEN → réouverture immédiate
                self._open_circuit()
            elif self.failure_count >= self.failure_threshold:
                self._open_circuit()

    def get_stats(self) -> dict:
        """Retourne les statistiques du circuit breaker."""
        with self.lock:
            return {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "failure_threshold": self.failure_threshold,
                "time_until_reset": self._time_until_half_open()
                if self.state == CircuitState.OPEN
                else 0,
            }

    def reset(self) -> None:
        """Force la réinitialisation du circuit breaker."""
        with self.lock:
            self._close_circuit()
            logger.info("Circuit breaker manually reset")

    def __enter__(self):
        """Context manager entry - vérifie l'état du circuit."""
        with self.lock:
            current_state = self._get_state()
            if current_state == CircuitState.OPEN:
                raise CircuitOpenError(
                    f"Circuit breaker is OPEN. Retry after {self._time_until_half_open():.1f}s"
                )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - enregistre succès/échec."""
        if exc_type is None:
            self._on_success()
        else:
            self._on_failure()
        return False  # Ne pas supprimer l'exception


class CircuitOpenError(Exception):
    """Exception levée quand le circuit breaker est ouvert."""

    pass


class LinkedInRateLimiter:
    """
    Rate limiter spécialisé pour LinkedIn.

    Combine rate limiting et circuit breaker pour une protection optimale.

    Configuration recommandée pour Raspberry Pi 4:
    - Messages par heure: 10-15
    - Messages par jour: 50
    - Circuit breaker: 5 échecs, 300s timeout
    """

    def __init__(
        self,
        messages_per_hour: int = 10,
        messages_per_day: int = 50,
        circuit_breaker_failures: int = 5,
        circuit_breaker_timeout: int = 300,
    ):
        """
        Initialise le rate limiter LinkedIn.

        Args:
            messages_per_hour: Messages max par heure
            messages_per_day: Messages max par jour
            circuit_breaker_failures: Échecs avant ouverture du circuit
            circuit_breaker_timeout: Timeout du circuit breaker en secondes
        """
        self.hourly_limiter = RateLimiter(messages_per_hour, 3600)
        self.daily_limiter = RateLimiter(messages_per_day, 86400)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_failures, timeout=circuit_breaker_timeout
        )

        logger.info(
            f"LinkedIn rate limiter initialized: "
            f"{messages_per_hour}/hour, {messages_per_day}/day, "
            f"circuit breaker: {circuit_breaker_failures} failures/{circuit_breaker_timeout}s"
        )

    def can_send_message(self) -> bool:
        """
        Vérifie si on peut envoyer un message.

        Returns:
            True si autorisé, False sinon
        """
        # Vérifier le circuit breaker
        if self.circuit_breaker.state == CircuitState.OPEN:
            return False

        # Vérifier les rate limiters
        return self.hourly_limiter.acquire() and self.daily_limiter.acquire()

    def wait_time(self) -> Optional[float]:
        """
        Retourne le temps d'attente avant de pouvoir envoyer un message.

        Returns:
            Temps d'attente en secondes ou None si disponible
        """
        hourly_wait = self.hourly_limiter.wait_time()
        daily_wait = self.daily_limiter.wait_time()

        wait_times = [w for w in [hourly_wait, daily_wait] if w is not None]
        return max(wait_times) if wait_times else None

    def get_stats(self) -> dict:
        """Retourne les statistiques complètes."""
        return {
            "hourly": self.hourly_limiter.get_stats(),
            "daily": self.daily_limiter.get_stats(),
            "circuit_breaker": self.circuit_breaker.get_stats(),
        }

    def reset(self) -> None:
        """Réinitialise tous les compteurs."""
        self.hourly_limiter.reset()
        self.daily_limiter.reset()
        self.circuit_breaker.reset()
        logger.info("LinkedIn rate limiter reset")


# Instance globale (singleton thread-safe)
_linkedin_rate_limiter: Optional[LinkedInRateLimiter] = None
_limiter_lock = threading.Lock()


def get_linkedin_rate_limiter() -> LinkedInRateLimiter:
    """
    Retourne l'instance singleton du rate limiter LinkedIn.

    Returns:
        Instance de LinkedInRateLimiter
    """
    global _linkedin_rate_limiter

    if _linkedin_rate_limiter is None:
        with _limiter_lock:
            if _linkedin_rate_limiter is None:
                _linkedin_rate_limiter = LinkedInRateLimiter()

    return _linkedin_rate_limiter
