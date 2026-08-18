import asyncio
import logging
import random
import httpx
from app.config import settings
from app.scraping.headers import get_browser_headers

logger = logging.getLogger(__name__)


class BlockDetectedError(Exception):
    """Raised when anti-bot / CAPTCHA / IP block is detected."""
    pass


class ScrapingClient:
    """
    HTTP client wrapper for web scraping with:
    - Cookie persistence (httpx.AsyncClient session)
    - Realistic browser headers
    - Pre-request jitter to avoid request timing predictability
    - Anti-bot / CAPTCHA block detection
    """

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def _check_blocked(self, response: httpx.Response):
        """
        Inspect response for signs of blocking, CAPTCHA, or anti-bot walls.
        """
        if response.status_code in (403, 429, 503):
            raise BlockDetectedError(f"Anti-bot block or rate-limit HTTP {response.status_code}")

        text = response.text.lower()
        captcha_signatures = [
            "g-recaptcha",
            "hcaptcha",
            "cf-challenge",
            "cloudflare-nginx",
            "access denied",
            "please verify you are a human",
            "security check to continue",
            "pardon our interruption",
            "just a moment...",
            "just a moment",
        ]
        for sig in captcha_signatures:
            if sig in text and len(text) < 10000:
                raise BlockDetectedError(f"Block signature detected in response: '{sig}'")

        if len(text.strip()) == 0:
            raise BlockDetectedError("Empty body response received from target host")

    async def fetch(self, url: str, referer: str = "https://www.google.com/") -> str:
        """
        Executes a GET request with jitter, headers, session cookies, and block detection.
        Returns raw response body text.
        """
        # Apply jitter pacing
        jitter = settings.scrape_jitter_seconds + random.uniform(0, 1.5)
        logger.info(f"[ScrapingClient] Pacing request with {jitter:.2f}s jitter before fetching {url}")
        await asyncio.sleep(jitter)

        headers = get_browser_headers(referer=referer)

        async with httpx.AsyncClient(
            headers=headers,
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            self._check_blocked(resp)
            return resp.text
