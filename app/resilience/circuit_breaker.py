import logging
from app.config import settings

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Tracks consecutive failures for the primary source (Remotive).
    When failure_count reaches the threshold, trips the breaker and
    signals the pipeline to use the fallback source (Arbeitnow).

    The breaker resets automatically on a successful ingestion run.
    """

    def __init__(self, threshold: int = None):
        self.threshold = threshold or settings.max_failures_before_fallback
        self.failure_count: int = 0
        self.is_open: bool = False  # True = circuit is tripped, use fallback

    def record_failure(self) -> None:
        self.failure_count += 1
        logger.warning(
            f"[circuit_breaker] Primary failure #{self.failure_count}/{self.threshold}"
        )
        if self.failure_count >= self.threshold:
            if not self.is_open:
                logger.error(
                    f"[circuit_breaker] TRIPPED after {self.failure_count} consecutive failures. "
                    "Switching to fallback source."
                )
            self.is_open = True

    def record_success(self) -> None:
        if self.is_open:
            logger.info("[circuit_breaker] Primary source recovered. Resetting breaker.")
        self.failure_count = 0
        self.is_open = False

    @property
    def should_use_fallback(self) -> bool:
        return self.is_open


# Singleton — shared across the application lifetime
circuit_breaker = CircuitBreaker()
