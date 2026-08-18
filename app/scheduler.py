import asyncio
import logging
import random
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import settings

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _run_pipeline_sync():
    """Bridge: APScheduler runs sync jobs; pipeline is async. We create an event loop here."""
    from app.pipeline import run_ingestion
    try:
        asyncio.run(run_ingestion())
    except Exception as exc:
        logger.error(f"[scheduler] Pipeline error: {exc}")


def start_scheduler():
    base_interval = settings.ingest_interval_minutes
    # Add random jitter of -2 to +2 minutes to prevent strict interval detection
    jitter_minutes = random.uniform(-2.0, 2.0)
    effective_interval = max(1.0, base_interval + jitter_minutes)

    scheduler.add_job(
        _run_pipeline_sync,
        trigger="interval",
        minutes=effective_interval,
        id="ingestion_job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"[scheduler] Started — ingestion scheduled every ~{effective_interval:.1f} minute(s) (with jitter).")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[scheduler] Stopped.")
