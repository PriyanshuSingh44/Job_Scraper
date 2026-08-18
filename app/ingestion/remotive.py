import logging
import httpx
from typing import List
from app.ingestion.base import BaseSource

logger = logging.getLogger(__name__)

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"


class RemotiveSource(BaseSource):
    """
    Primary data source: Remotive public API.
    Endpoint: GET https://remotive.com/api/remote-jobs
    Returns JSON: { "jobs": [ {...}, ... ] }
    """

    source_name = "remotive"

    async def fetch(self) -> List[dict]:
        logger.info("Fetching from Remotive API...")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                REMOTIVE_URL,
                headers={
                    "User-Agent": "JobPipeline/1.0 (research project; contact via GitHub)",
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        jobs = data.get("jobs", [])
        logger.info(f"Remotive returned {len(jobs)} raw records.")
        return jobs
