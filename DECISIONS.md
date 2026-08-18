# DECISIONS.md

## 1. Why HTML Scraping + RSS XML over JSON APIs?

**What I chose**: HTML scraping from WeWorkRemotely (`selectolax`) as the primary source,
backed by an Indeed RSS XML feed parser (`feedparser`) as an automatic fallback, with
browser header impersonation, request pacing jitter, a 3-tier CSS selector fallback chain,
and a circuit breaker.

**What I rejected**: Pure JSON endpoints (like Remotive or Arbeitnow API endpoints).

**Why I made that call**:

Using clean JSON APIs satisfies basic HTTP fetching, but it bypasses the real engineering
challenges of web data ingestion: HTML parsing, markup drift, browser header spoofing,
and anti-bot detection. By targeting WeWorkRemotely's server-rendered HTML, I am forced to
build real extraction logic that must handle structural changes in the DOM. Using Indeed's
RSS feed as a fallback demonstrates multi-format ingestion (HTML + XML) while keeping
the pipeline fully compliant with the assignment guardrails against live scraping of
hostile targets like LinkedIn.

---

## 2. Trade-Offs Made Under Time Constraints

**The Trade-off**: I implemented browser header impersonation and request jitter rather
than full `curl_cffi` TLS fingerprinting or a live residential proxy rotation pool.

Given a full development sprint:
1. **TLS Fingerprint Spoofing (`curl_cffi`)**: I would replace standard `httpx` with
   `curl_cffi` to mimic Chrome's exact JA3 SSL cipher suite order and HTTP/2 pseudo-headers,
   preventing CDN-level block decisions before HTTP requests even reach the application layer.
2. **Residential Proxy Rotation**: I would integrate a proxy manager (e.g. BrightData)
   to rotate residential IPs on HTTP 403/429 responses rather than relying solely on local
   request pacing.
3. **Automated Selector Discovery**: On `MarkupDriftError`, an LLM fallback parser could
   analyze updated DOM snapshots offline and suggest new CSS selector paths automatically.

---

## 3. Transparency: AI Assistance vs. Developer Ownership

### What AI helped scaffold:
- Generative drafting of initial `selectolax` parser boilerplates and `feedparser` structure.
- Conceptual review of anti-bot threat vectors (JA3 fingerprints, Sec-Fetch headers) for `design_doc.md`.

### What I personally engineered and verified:
- **3-Tier Selector Fallback Chain** (`app/ingestion/weworkremotely.py`): Designed the multi-stage fallback strategy (`section.jobs li` $\rightarrow$ `.jobs li` $\rightarrow$ `a[href*='/remote-jobs/']`) to detect DOM changes and explicitly raise `MarkupDriftError`.
- **Pipeline Failover Architecture** (`app/pipeline.py`): Ensured that when primary HTML scraping fails or encounters markup drift, the circuit breaker immediately records the failure and recovers within the exact same ingestion turn via the Indeed RSS fallback.
- **Scraping Infrastructure** (`app/scraping/client.py` & `headers.py`): Implemented request pacing jitter (`scrape_jitter_seconds`), full `Sec-Fetch-*` header spoofing, and block signature checks.
- **Test Suite** (`tests/test_parser.py` & `tests/test_validator.py`): Wrote unit tests against real HTML/XML fixtures verifying parser extraction and markup drift handling.
