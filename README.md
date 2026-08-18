# JobPipeline — Job Scraper API

A live job ingestion pipeline with resilience built in. Pulls from Remotive (primary) and Arbeitnow (fallback), validates every record, and exposes a FastAPI service with a dashboard.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      APScheduler (30min)                 │
└───────────────────────────┬─────────────────────────────┘
                            │ triggers
┌───────────────────────────▼─────────────────────────────┐
│                     pipeline.py                          │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │ Circuit      │   │ Retry +      │   │ Validator   │  │
│  │ Breaker      │──▶│ Backoff      │──▶│ Drift Det.  │  │
│  └──────────────┘   └──────────────┘   └──────┬──────┘  │
│         │                                      │         │
│  OPEN → fallback (Arbeitnow)           valid records     │
│  CLOSED → primary (Remotive)                   │         │
└────────────────────────────────────────────────┼─────────┘
                                                 │ upsert
┌────────────────────────────────────────────────▼─────────┐
│                  SQLite (jobs + ingestion_log)            │
└───────────────────────────┬──────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────┐
│                     FastAPI                              │
│  GET /jobs          GET /health      GET /ingestion-log  │
│  POST /ingest/trigger               GET /secret          │
│  GET / (HTML dashboard)                                  │
└──────────────────────────────────────────────────────────┘
```

## Setup (Local)

```bash
# 1. Clone
git clone <your-repo-url>
cd Scraper

# 2. Create virtualenv
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # Mac/Linux

# 3. Install
pip install -r requirements.txt

# 4. Optional: copy env file
cp .env.example .env

# 5. Run
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000` for the dashboard, `http://localhost:8000/docs` for the Swagger UI.

## Endpoints

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | HTML dashboard |
| `GET` | `/jobs` | List jobs (`?source=remotive&q=python&limit=50`) |
| `GET` | `/health` | Service health + last ingestion |
| `GET` | `/ingestion-log` | Full pipeline audit log |
| `POST` | `/ingest/trigger` | Manually trigger ingestion |
| `GET` | `/docs` | Swagger UI |

## Resilience Demo

1. Visit `/ingestion-log` — see every run's status, source, record count, and any errors.
2. To simulate a failure: stop the service mid-run, restart — the log shows the recovery.
3. To force fallback: set `MAX_FAILURES_BEFORE_FALLBACK=1` in `.env`, restart — next
   failed run trips the circuit breaker and routes to Arbeitnow automatically.

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

## Deploy on Render

1. Push to GitHub
2. Create a new **Web Service** on Render
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add env vars from `.env.example` if needed

## Tech Stack

- **FastAPI** — API framework
- **httpx** — async HTTP client
- **SQLAlchemy** — ORM
- **SQLite** — storage (swap to Postgres for multi-replica)
- **APScheduler** — background scheduling
- **Pydantic** — validation + settings

## Files

```
app/
  main.py          # FastAPI entry + lifespan
  config.py        # Settings
  database.py      # Engine + session
  models.py        # Job + IngestionLog ORM
  schemas.py       # Pydantic models
  pipeline.py      # Core orchestrator ← read this first
  scheduler.py     # APScheduler wrapper
  ingestion/
    base.py        # Abstract source
    remotive.py    # Primary source
    arbeitnow.py   # Fallback source
    normalizer.py  # Raw → common schema
    validator.py   # Drift detection
  resilience/
    retry.py       # Exponential backoff
    circuit_breaker.py  # Failure tracker + fallback trigger
  routers/
    jobs.py
    health.py
    ingestion_log.py
frontend/
  index.html       # Dashboard
design_doc.md      # Architecture + ethics
DECISIONS.md       # 3 required questions
```
