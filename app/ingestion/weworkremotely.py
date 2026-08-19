import logging
import xml.etree.ElementTree as ET
from typing import List
from selectolax.parser import HTMLParser
from app.config import settings
from app.ingestion.base import BaseSource, MarkupDriftError
from app.scraping.client import ScrapingClient

logger = logging.getLogger(__name__)

BASE_DOMAIN = "https://weworkremotely.com"


class WeWorkRemotelySource(BaseSource):
    """
    Primary Scraper: We Work Remotely category page / feed.
    Uses selectolax HTML parser with multi-tier fallback strategy + XML auto-detection
    for markup drift resilience.
    """

    source_name = "weworkremotely"

    def __init__(self, scraping_client: ScrapingClient = None):
        self.client = scraping_client or ScrapingClient()

    def parse_xml(self, xml_content: str) -> List[dict]:
        """
        Parses RSS XML content if WWR returns XML feed for the category URL.
        """
        try:
            root = ET.fromstring(xml_content)
            channel = root.find("channel")
            items = channel.findall("item") if channel is not None else root.findall(".//item")
            jobs = []
            for item in items:
                title_raw = item.findtext("title") or ""
                link = item.findtext("link") or ""
                region = item.findtext("region") or item.findtext("location") or "Remote"
                pub_date = item.findtext("pubDate") or item.findtext("dc:date")
                company = "WeWorkRemotely Partner"
                title = title_raw
                if ":" in title_raw:
                    parts = title_raw.split(":", 1)
                    company = parts[0].strip()
                    title = parts[1].strip()
                if title and link:
                    jobs.append({
                        "title": title,
                        "company_name": company,
                        "location": region,
                        "url": link,
                        "posted_date": pub_date,
                        "source": self.source_name,
                    })
            return jobs
        except Exception as e:
            logger.debug(f"[WWR Scraper] XML parsing attempt failed: {e}")
            return []

    def parse_html(self, html_content: str) -> List[dict]:
        """
        Parses WWR HTML or RSS XML with multi-tier fallback selector chains.
        Raises MarkupDriftError if no job nodes can be identified.
        """
        content_stripped = html_content.lstrip()

        # Check if response is RSS/XML feed
        if content_stripped.startswith("<?xml") or "<rss" in content_stripped[:300]:
            logger.info("[WWR Scraper] XML response detected. Parsing as RSS feed...")
            jobs = self.parse_xml(html_content)
            if jobs:
                return jobs
            raise MarkupDriftError("WWR XML feed returned 0 job entries.")

        tree = HTMLParser(html_content)
        jobs = []
        seen_urls = set()

        # Tier 1: Primary CSS selectors for job container list items / articles
        nodes = tree.css("section.jobs li:not(.view-all)")
        selector_used = "Tier 1: section.jobs li"

        # Tier 2: Fallback CSS selectors
        if not nodes:
            nodes = tree.css(".jobs li, article.job, li.job-item, li.feature, li.new-listing-container, ul.jobs-list > li")
            selector_used = "Tier 2: .jobs li / article / feature"

        if nodes:
            for node in nodes:
                # Find link anchor pointing to a job page
                link_elem = None
                for a in node.css("a"):
                    href = a.attributes.get("href", "")
                    if "/remote-jobs/" in href:
                        link_elem = a
                        break

                if not link_elem:
                    anchors = node.css("a")
                    for a in anchors:
                        href = a.attributes.get("href", "")
                        if href and not href.startswith("#") and "/company/" not in href:
                            link_elem = a
                            break

                if not link_elem:
                    continue

                href = link_elem.attributes.get("href", "")
                if not href or href == "#":
                    continue

                full_url = href if href.startswith("http") else f"{BASE_DOMAIN}{href}"
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                # Extract Title
                title_elem = (
                    node.css_first("span.new-listing__header__title__text")
                    or node.css_first("h3.new-listing__header__title")
                    or node.css_first("span.title")
                    or node.css_first(".job-title")
                    or node.css_first("h3")
                    or link_elem
                )

                # Extract Company
                company_elem = (
                    node.css_first("p.new-listing__company-name")
                    or node.css_first("span.company")
                    or node.css_first(".company-name")
                    or node.css_first("span.company-title")
                )

                # Extract Location / Region
                location_elem = (
                    node.css_first("span.region")
                    or node.css_first(".location")
                    or node.css_first("span.location")
                )

                # Extract Date
                date_elem = (
                    node.css_first("p.new-listing__header__icons__date")
                    or node.css_first("span.date")
                    or node.css_first("time")
                    or node.css_first(".posted-date")
                )

                title = title_elem.text(strip=True) if title_elem else ""
                company = company_elem.text(strip=True) if company_elem else ""
                location = location_elem.text(strip=True) if location_elem else "Remote"
                posted_date = date_elem.text(strip=True) if date_elem else None

                # Fallback location extraction from category tags
                if location == "Remote":
                    cat_nodes = node.css("p.new-listing__categories__category")
                    for cat in cat_nodes:
                        txt = cat.text(strip=True)
                        if txt and txt not in ("Featured", "Top 100", "Full-Time", "Part-Time", "Contract"):
                            location = txt
                            break

                if title and full_url:
                    jobs.append({
                        "title": title,
                        "company_name": company or "WeWorkRemotely Partner",
                        "location": location,
                        "url": full_url,
                        "posted_date": posted_date,
                        "source": self.source_name,
                    })

        # Tier 3: Global anchor fallback across entire tree
        if not jobs:
            for a in tree.css("a"):
                href = a.attributes.get("href", "")
                if href and "/remote-jobs/" in href:
                    full_url = href if href.startswith("http") else f"{BASE_DOMAIN}{href}"
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)
                    title = a.text(strip=True)
                    if title and len(title) > 3 and "view" not in title.lower():
                        jobs.append({
                            "title": title,
                            "company_name": "WeWorkRemotely Listing",
                            "location": "Remote",
                            "url": full_url,
                            "posted_date": None,
                            "source": self.source_name,
                        })
            if jobs:
                selector_used = "Tier 3: global a search"

        # Final check: attempt XML parsing if HTML parsing produced 0 jobs
        if not jobs:
            xml_jobs = self.parse_xml(html_content)
            if xml_jobs:
                logger.info("[WWR Scraper] Fallback XML parser matched entries.")
                return xml_jobs

        if not jobs:
            logger.error("[WWR Scraper] All selector tiers failed — 0 job nodes found in HTML!")
            raise MarkupDriftError("WWR HTML markup drift: 0 job nodes match primary or fallback selector chains.")

        logger.info(f"[WWR Scraper] Parsed {len(jobs)} job nodes using {selector_used}.")
        return jobs

    async def fetch(self) -> List[dict]:
        url = settings.primary_source_url
        logger.info(f"[WWR Source] Fetching HTML from {url}...")
        html_content = await self.client.fetch(url, referer="https://weworkremotely.com/")
        return self.parse_html(html_content)

