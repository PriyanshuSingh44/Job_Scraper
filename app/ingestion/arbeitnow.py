import logging
import httpx
from typing import List
from app.ingestion.base import BaseSource

logger = logging.getLogger(__name__)

ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowSource(BaseSource):
    """
    Fallback data source: Arbeitnow public API.
    Endpoint: GET https://www.arbeitnow.com/api/job-board-api
    Returns JSON: { "data": [ {...}, ... ] }
    """

    source_name = "arbeitnow"

    async def fetch(self) -> List[dict]:
        logger.info("Fetching from Arbeitnow API (fallback)...")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                ARBEITNOW_URL,
                headers={
                    "User-Agent": "JobPipeline/1.0 (research project; contact via GitHub)",
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        jobs = data.get("data", [])
        logger.info(f"Arbeitnow returned {len(jobs)} raw records.")
        return jobs
