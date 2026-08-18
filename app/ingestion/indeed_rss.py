import logging
from typing import List
import feedparser
from app.config import settings
from app.ingestion.base import BaseSource, MarkupDriftError
from app.scraping.client import ScrapingClient

logger = logging.getLogger(__name__)


class IndeedRSSSource(BaseSource):
    """
    Fallback Source: Indeed RSS XML Feed Parser.
    Parses RSS XML feeds using feedparser and maps to common raw dict format.
    """

    source_name = "indeed_rss"

    def __init__(self, scraping_client: ScrapingClient = None):
        self.client = scraping_client or ScrapingClient()

    def parse_xml(self, xml_content: str) -> List[dict]:
        """
        Parses Indeed RSS feed XML content.
        Raises MarkupDriftError if feed structure is corrupted or empty.
        """
        feed = feedparser.parse(xml_content)

        if feed.bozo and not feed.entries:
            bozo_msg = getattr(feed, "bozo_exception", "Unknown XML parse error")
            logger.error(f"[Indeed RSS] XML parsing failed bozo error: {bozo_msg}")
            raise MarkupDriftError(f"Indeed RSS XML drift/parse error: {bozo_msg}")

        entries = feed.entries
        if not entries:
            logger.warning("[Indeed RSS] 0 entries found in feed XML.")
            raise MarkupDriftError("Indeed RSS XML drift: 0 feed entries parsed.")

        jobs = []
        for entry in entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            author = getattr(entry, "author", "") or getattr(entry, "source", {}).get("title", "")
            company = author.strip() if author else "Indeed Employer"
            published = getattr(entry, "published", "") or getattr(entry, "updated", "")

            # If title is formatted like "Job Title - Company Name", clean title
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0].strip()
                if not author:
                    company = parts[1].strip()

            if title and link:
                jobs.append({
                    "title": title,
                    "company_name": company or "Indeed Remote",
                    "location": "Remote",
                    "url": link,
                    "posted_date": published or None,
                    "source": self.source_name,
                })

        logger.info(f"[Indeed RSS] Successfully parsed {len(jobs)} jobs from RSS XML feed.")
        return jobs

    async def fetch(self) -> List[dict]:
        url = settings.fallback_rss_url
        logger.info(f"[Indeed RSS Source] Fetching XML feed from {url}...")
        xml_content = await self.client.fetch(url, referer="https://www.indeed.com/")
        return self.parse_xml(xml_content)
