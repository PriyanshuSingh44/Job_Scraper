# JobPipeline — Resilient HTML Job Scraper & Pipeline

A resilient job ingestion pipeline built with **FastAPI**, **selectolax** HTML parsing, **feedparser** RSS XML parsing, **httpx**, and **SQLite**. Pulls from WeWorkRemotely (primary HTML scraper) with an automatic failover to Indeed RSS (XML feed fallback).

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│             APScheduler with Jitter (-2m to +2m)              │
└──────────────────────────────┬───────────────────────────────┘
                               │ triggers
┌──────────────────────────────▼───────────────────────────────┐
│                        pipeline.py                           │
│  ┌─────────────────┐   ┌────────────────┐   ┌─────────────┐  │
│  │ Circuit Breaker │──▶│ Retry Backoff  │──▶│ Validator   │  │
│  │ State Machine   │   │ Exponential    │   │ Drift Det.  │  │
│  └────────┬────────┘   └────────────────┘   └──────┬──────┘  │
│           │                                        │         │
│  CLOSED ──┼──▶ WeWorkRemotely (HTML Scraper)       │ valid   │
│  OPEN   ──┴──▶ Indeed RSS (XML Feed Fallback)      │ records │
└────────────────────────────────────────────────────┼─────────┘
                                                     │ upsert
┌────────────────────────────────────────────────────▼─────────┐
│                     SQLite Storage                           │
│              (jobs + ingestion_log tables)                   │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                    FastAPI Web Service                       │
│  GET /jobs          GET /health          GET /ingestion-log  │
│  POST /ingest/trigger                   GET / (Dashboard)    │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Resilience Features

1. **HTML Parsing with Selector Fallback Chain**: 3-tier CSS selector fallbacks (`section.jobs li` $\rightarrow$ `.jobs li` $\rightarrow$ `a[href*='/remote-jobs/']`) in `weworkremotely.py` flag DOM changes as `MarkupDriftError`.
2. **Browser Header Impersonation & Jitter**: `ScrapingClient` spoofs browser headers (`User-Agent`, `Sec-Fetch-*`) and adds pre-request jitter to avoid timing flags.
3. **Circuit Breaker Failover**: Automatically switches to Indeed RSS XML parsing when WeWorkRemotely encounters $N$ consecutive failures or markup drift.
4. **Data Validation & Audit Trail**: Validates required fields for every record. Records pipeline execution history in `ingestion_log`.

---

## Local Setup

### 1. Clone repository
```bash
git clone git@github.com:PriyanshuSingh44/Job_Scraper.git
cd Job_Scraper
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run unit tests
```bash
python -m pytest tests/ -v
```

### 4. Start local development server
```bash
uvicorn app.main:app --reload --port 8000
```
- Web Dashboard: `http://localhost:8000/`
- Interactive API Docs: `http://localhost:8000/docs`

---

## Endpoints

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | HTML Monitoring Dashboard |
| `GET` | `/jobs` | Query jobs (`?source=weworkremotely&q=python&limit=50`) |
| `GET` | `/health` | Circuit breaker status & latest ingestion stats |
| `GET` | `/ingestion-log` | Audit log of all ingestion pipeline runs |
| `POST` | `/ingest/trigger` | Manually trigger an immediate ingestion cycle |
| `GET` | `/docs` | Swagger UI documentation |

---

## Demonstrating Circuit Breaker & Fallback Live

1. Open `http://localhost:8000/` in your browser.
2. Click **▶ Run Ingestion** to execute a live scrape of WeWorkRemotely.
3. View the **Pipeline Log** panel to inspect records pulled, source used, and execution timestamp.
4. To test circuit failover: edit `.env` set `PRIMARY_SOURCE_URL="https://weworkremotely.com/invalid-path-for-test"`, and trigger ingestion — watch the circuit breaker trip and automatically failover to Indeed RSS!
