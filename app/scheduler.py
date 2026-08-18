import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import settings

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _run_pipeline_sync():
    """Bridge: APScheduler runs sync jobs; pipeline is async. We create a loop here."""
    from app.pipeline import run_ingestion
    try:
        asyncio.run(run_ingestion())
    except Exception as exc:
        logger.error(f"[scheduler] Pipeline error: {exc}")


def start_scheduler():
    interval = settings.ingest_interval_minutes
    scheduler.add_job(
        _run_pipeline_sync,
        trigger="interval",
        minutes=interval,
        id="ingestion_job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"[scheduler] Started — ingestion every {interval} minute(s).")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[scheduler] Stopped.")
