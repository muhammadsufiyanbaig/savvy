import time
import logging
from functools import wraps
from typing import Callable, Type, Tuple

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """Decorator: retry sync function with exponential backoff."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exc: Exception = RuntimeError("No attempts made")

            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        logger.warning(
                            "Attempt %d/%d failed for %s: %s — retrying in %.1fs",
                            attempt,
                            max_retries,
                            func.__name__,
                            exc,
                            delay,
                        )
                        time.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        logger.error(
                            "All %d attempts failed for %s: %s",
                            max_retries,
                            func.__name__,
                            exc,
                        )
            raise last_exc

        return wrapper

    return decorator
