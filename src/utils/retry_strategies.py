"""
Retry Strategies for Resilient Network Operations

Implements exponential backoff with jitter for robust handling of transient
network failures, timeouts, and temporary connectivity issues.

Usage:
    from src.utils.retry_strategies import exponential_backoff_with_jitter

    for attempt in range(max_retries):
        try:
            do_something_unreliable()
            break
        except TimeoutError as e:
            if attempt < max_retries - 1:
                delay = exponential_backoff_with_jitter(attempt)
                logger.warning(f"Retry in {delay:.1f}s (attempt {attempt+1})")
                time.sleep(delay)
            else:
                raise
"""

import random
import time
from typing import Callable, Any, TypeVar, Optional
from functools import wraps

from ..utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


def exponential_backoff_with_jitter(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter_fraction: float = 0.2
) -> float:
    """
    Calculate delay using exponential backoff with random jitter.

    Formula: delay = min(base_delay * 2^attempt, max_delay)
             + random jitter (±jitter_fraction * delay)

    Examples:
        Attempt 0: ~0.8-1.2s
        Attempt 1: ~1.6-2.4s
        Attempt 2: ~3.2-4.8s
        Attempt 3: ~6.4-9.6s
        Attempt 4: ~12.8-19.2s
        ...capped at max_delay

    Args:
        attempt: Zero-based attempt number (0, 1, 2, ...)
        base_delay: Initial delay in seconds (default 1.0)
        max_delay: Maximum delay cap in seconds (default 60.0)
        jitter_fraction: Jitter range as fraction of delay (default 0.2 = ±20%)

    Returns:
        Delay time in seconds (float)
    """
    # Exponential backoff: 2^attempt
    exponential_delay = base_delay * (2 ** attempt)

    # Cap at maximum delay
    capped_delay = min(exponential_delay, max_delay)

    # Add random jitter to avoid thundering herd
    # Jitter range: [delay * (1 - jitter_fraction), delay * (1 + jitter_fraction)]
    jitter = capped_delay * random.uniform(-jitter_fraction, jitter_fraction)
    final_delay = max(0, capped_delay + jitter)

    return final_delay


def retry_with_backoff(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_exceptions: tuple = (Exception,),
    log_level: str = "warning"
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for automatic retry with exponential backoff.

    Usage:
        @retry_with_backoff(max_retries=3, backoff_exceptions=(TimeoutError, ConnectionError))
        def flaky_network_call():
            return requests.get("https://api.example.com")

    Args:
        max_retries: Maximum number of retry attempts (default 5)
        base_delay: Initial delay in seconds (default 1.0)
        max_delay: Maximum delay cap in seconds (default 60.0)
        backoff_exceptions: Tuple of exceptions to retry on (default all)
        log_level: Log level for retry messages (default "warning")

    Returns:
        Decorated function with automatic retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(
                            f"call_succeeded_after_retry",
                            function=func.__name__,
                            attempts=attempt + 1
                        )
                    return result

                except backoff_exceptions as e:
                    last_exception = e

                    if attempt < max_retries - 1:
                        delay = exponential_backoff_with_jitter(
                            attempt,
                            base_delay=base_delay,
                            max_delay=max_delay
                        )

                        # Log the retry attempt
                        error_type = type(e).__name__
                        logger.log(
                            getattr(logger, log_level),
                            f"retry_attempt_scheduled",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_retries,
                            error=error_type,
                            delay_seconds=delay,
                            exc_info=False
                        )

                        # Wait before retry
                        time.sleep(delay)
                    else:
                        # Final attempt failed
                        logger.error(
                            f"all_retries_exhausted",
                            function=func.__name__,
                            attempts=max_retries,
                            error=error_type
                        )

            # All retries exhausted
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(f"Function {func.__name__} failed after {max_retries} retries")

        return wrapper

    return decorator


class RetryBackoffCalculator:
    """
    Stateful calculator for managing retry delays across multiple attempts.

    Usage:
        calc = RetryBackoffCalculator(base_delay=1.0, max_delay=60.0)
        for attempt in range(5):
            try:
                do_something()
                break
            except Exception:
                if attempt < 4:
                    delay = calc.get_delay(attempt)
                    time.sleep(delay)
    """

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter_fraction: float = 0.2
    ):
        """Initialize calculator with backoff parameters."""
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_fraction = jitter_fraction
        self.attempt_count = 0

    def get_delay(self, attempt: int) -> float:
        """Get delay for specific attempt number."""
        self.attempt_count = attempt
        return exponential_backoff_with_jitter(
            attempt,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            jitter_fraction=self.jitter_fraction
        )

    def get_next_delay(self) -> float:
        """Get delay for next attempt (auto-increment)."""
        delay = self.get_delay(self.attempt_count)
        self.attempt_count += 1
        return delay

    def reset(self) -> None:
        """Reset attempt counter to 0."""
        self.attempt_count = 0


# ============================================================================
# INTEGRATION WITH PLAYWRIGHT FOR BROWSER OPERATIONS
# ============================================================================

class PlaywrightRetryHelper:
    """
    Helper class for Playwright operations with exponential backoff retry.

    Usage:
        helper = PlaywrightRetryHelper(max_retries=3, timeout=120000)
        helper.goto_with_retry(page, url, timeout=60000)
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 2.0,
        max_delay: float = 60.0
    ):
        """Initialize Playwright retry helper."""
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def goto_with_retry(
        self,
        page: Any,
        url: str,
        timeout: int = 120000,
        wait_until: str = "commit"
    ) -> None:
        """
        Navigate page to URL with exponential backoff retry.

        Args:
            page: Playwright page object
            url: URL to navigate to
            timeout: Navigation timeout in milliseconds
            wait_until: Wait condition ('commit', 'domcontentloaded', 'load')

        Raises:
            PlaywrightTimeoutError: After max retries exhausted
        """
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Navigating to {url} (attempt {attempt+1}/{self.max_retries})")
                page.goto(url, timeout=timeout, wait_until=wait_until)

                if attempt > 0:
                    logger.info(f"Navigation succeeded after {attempt+1} attempts")
                return

            except PlaywrightTimeoutError as e:
                last_error = e

                if attempt < self.max_retries - 1:
                    delay = exponential_backoff_with_jitter(
                        attempt,
                        base_delay=self.base_delay,
                        max_delay=self.max_delay
                    )

                    logger.warning(
                        f"Navigation timeout",
                        url=url,
                        attempt=attempt + 1,
                        delay_seconds=f"{delay:.1f}",
                        error=str(e)
                    )

                    time.sleep(delay)
                else:
                    logger.error(f"Navigation failed after {self.max_retries} attempts: {e}")

        # All retries exhausted
        if last_error:
            raise last_error
        else:
            raise RuntimeError(f"Navigation to {url} failed after {self.max_retries} retries")


# ============================================================================
# PREDICATES FOR SELECTIVE RETRY
# ============================================================================

def is_transient_error(exception: Exception) -> bool:
    """
    Check if exception is transient (retryable).

    Transient errors: TimeoutError, ConnectionError, temporary network issues
    Permanent errors: ValueError, KeyError (retrying won't help)

    Args:
        exception: Exception to check

    Returns:
        True if error is transient and can be retried
    """
    transient_types = (
        TimeoutError,
        ConnectionError,
        ConnectionResetError,
        ConnectionAbortedError,
        BrokenPipeError,
        OSError,  # Network-related
    )

    return isinstance(exception, transient_types)


def is_linkedin_rate_limit(exception: Exception) -> bool:
    """Check if exception is LinkedIn rate limiting."""
    error_str = str(exception).lower()
    return any(keyword in error_str for keyword in ["rate limit", "429", "too many requests"])


def is_session_expired(exception: Exception) -> bool:
    """Check if exception indicates session expiration."""
    error_str = str(exception).lower()
    return any(keyword in error_str for keyword in ["session expired", "unauthorized", "403"])


__all__ = [
    "exponential_backoff_with_jitter",
    "retry_with_backoff",
    "RetryBackoffCalculator",
    "PlaywrightRetryHelper",
    "is_transient_error",
    "is_linkedin_rate_limit",
    "is_session_expired",
]
