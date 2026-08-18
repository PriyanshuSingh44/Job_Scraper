import asyncio
import logging
from functools import wraps
from typing import Callable, Type, Tuple

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator: retry an async function with exponential backoff.

    Delay formula: base_delay * (2 ** attempt)
    e.g. attempt 0→1s, 1→2s, 2→4s

    Raises the last exception if all attempts are exhausted.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"[retry] {func.__name__} attempt {attempt + 1}/{max_attempts} failed: "
                        f"{exc!r} — retrying in {delay:.1f}s"
                    )
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay)
            logger.error(f"[retry] {func.__name__} exhausted all {max_attempts} attempts.")
            raise last_exc
        return wrapper
    return decorator
