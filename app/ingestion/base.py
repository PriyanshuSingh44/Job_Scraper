from abc import ABC, abstractmethod
from typing import List
from app.schemas import JobCreate


class BaseSource(ABC):
    """Abstract base class for all job data sources."""

    source_name: str = "unknown"

    @abstractmethod
    async def fetch(self) -> List[dict]:
        """Fetch raw job data from the source. Returns a list of raw dicts."""
        ...

    def get_name(self) -> str:
        return self.source_name
