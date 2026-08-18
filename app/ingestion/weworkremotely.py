import logging
from typing import List
from selectolax.parser import HTMLParser
from app.config import settings
from app.ingestion.base import BaseSource, MarkupDriftError
from app.scraping.client import ScrapingClient

logger = logging.getLogger(__name__)

BASE_DOMAIN = "https://weworkremotely.com"


class WeWorkRemotelySource(BaseSource):
    """
    Primary HTML Scraper: We Work Remotely category page.
    Uses selectolax HTML parser with a 3-tier selector fallback strategy for markup drift resilience.
    """

    source_name = "weworkremotely"

    def __init__(self, scraping_client: ScrapingClient = None):
        self.client = scraping_client or ScrapingClient()

    def parse_html(self, html_content: str) -> List[dict]:
        """
        Parses WWR HTML with multi-tier fallback selector chains.
        Raises MarkupDriftError if no job nodes can be identified.
        """
        tree = HTMLParser(html_content)
        jobs = []

        # Tier 1: Primary CSS selectors
        nodes = tree.css("section.jobs li:not(.view-all)")
        selector_used = "Tier 1: section.jobs li"

        # Tier 2: Fallback CSS selectors
        if not nodes:
            nodes = tree.css(".jobs li, article.job, li.job-item, ul.jobs-list > li")
            selector_used = "Tier 2: .jobs li / article.job"

        # Tier 3: Loose link-based selector fallback
        if not nodes:
            link_nodes = tree.css('a[href*="/remote-jobs/"]')
            if link_nodes:
                selector_used = "Tier 3: a[href*='/remote-jobs/']"
                for link in link_nodes:
                    href = link.attributes.get("href", "")
                    title = link.text(strip=True)
                    if href and title and len(title) > 3:
                        full_url = href if href.startswith("http") else f"{BASE_DOMAIN}{href}"
                        jobs.append({
                            "title": title,
                            "company_name": "WeWorkRemotely Listing",
                            "location": "Remote",
                            "url": full_url,
                            "posted_date": None,
                            "source": self.source_name,
                        })

        if not nodes and not jobs:
            logger.error("[WWR Scraper] All selector tiers failed — 0 job nodes found in HTML!")
            raise MarkupDriftError("WWR HTML markup drift: 0 job nodes match primary or fallback selector chains.")

        logger.info(f"[WWR Scraper] Parsed job nodes using {selector_used}. Found {len(nodes) or len(jobs)} items.")

        seen_urls = set()
        if nodes and not jobs:
            for node in nodes:
                # Find link anchor
                link_elem = node.css_first("a[href*='/remote-jobs/']") or node.css_first("a")
                if not link_elem:
                    continue

                href = link_elem.attributes.get("href", "")
                if not href or href == "#":
                    continue

                full_url = href if href.startswith("http") else f"{BASE_DOMAIN}{href}"
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                # Extract title, company, location, date
                title_elem = (
                    node.css_first("span.title")
                    or node.css_first(".job-title")
                    or node.css_first("h3")
                    or link_elem
                )
                company_elem = (
                    node.css_first("span.company")
                    or node.css_first(".company-name")
                    or node.css_first("span.company-title")
                )
                location_elem = (
                    node.css_first("span.region")
                    or node.css_first(".location")
                    or node.css_first("span.location")
                )
                date_elem = (
                    node.css_first("span.date")
                    or node.css_first("time")
                    or node.css_first(".posted-date")
                )

                title = title_elem.text(strip=True) if title_elem else ""
                company = company_elem.text(strip=True) if company_elem else ""
                location = location_elem.text(strip=True) if location_elem else "Remote"
                posted_date = date_elem.text(strip=True) if date_elem else None

                # Clean title if company name is attached or formatting is needed
                if title and company and title != company:
                    pass

                if title and full_url:
                    jobs.append({
                        "title": title,
                        "company_name": company or "WeWorkRemotely Partner",
                        "location": location,
                        "url": full_url,
                        "posted_date": posted_date,
                        "source": self.source_name,
                    })

        if not jobs:
            raise MarkupDriftError("WWR HTML markup drift: nodes found but failed to extract title and URL.")

        return jobs

    async def fetch(self) -> List[dict]:
        url = settings.primary_source_url
        logger.info(f"[WWR Source] Fetching HTML from {url}...")
        html_content = await self.client.fetch(url, referer="https://weworkremotely.com/")
        return self.parse_html(html_content)
