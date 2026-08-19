import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pathlib import Path

from app.database import init_db
from app.scheduler import start_scheduler, stop_scheduler
from app.pipeline import run_ingestion
from app.routers import jobs, health, ingestion_log

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    logger.info("Starting up Job Scraper service...")
    init_db()
    # Run initial ingestion immediately on startup
    logger.info("Running initial ingestion on startup...")
    await run_ingestion()
    start_scheduler()
    yield
    # ── Shutdown ─────────────────────────────────────────────
    stop_scheduler()
    logger.info("Job Scraper service shut down cleanly.")


app = FastAPI(
    title="Job Scraper API",
    description=(
        "Live job ingestion pipeline pulling HTML from We Work Remotely (primary) and "
        "XML RSS from Indeed (fallback). Features request pacing jitter, browser header "
        "spoofing, 3-tier CSS selector fallback for markup drift detection, exponential "
        "backoff retry, and an automatic circuit breaker."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(jobs.router)
app.include_router(health.router)
app.include_router(ingestion_log.router)


from typing import Optional
from fastapi import Query


# ── Manual trigger ────────────────────────────────────────────
@app.post("/ingest/trigger", tags=["ingestion"])
async def trigger_ingestion(source: Optional[str] = Query(None, description="Specific source to ingest: 'weworkremotely' or 'indeed_rss'")):
    """Manually trigger a full ingestion run for all or a specific source."""
    result = await run_ingestion(target_source=source)
    return result


# ── Frontend ──────────────────────────────────────────────────
frontend_path = Path(__file__).parent.parent / "frontend"


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend():
    index = frontend_path / "index.html"
    if index.exists():
        return HTMLResponse(content=index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)
