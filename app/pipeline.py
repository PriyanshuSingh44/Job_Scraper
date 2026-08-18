"""
Pipeline orchestrator: ingestion → validate → store → log

Flow:
1. Check circuit breaker state → pick primary or fallback source
2. Fetch raw records (with retry wrapper)
3. Check for empty response (200 OK + 0 results ≠ healthy)
4. Validate + filter records (schema drift detection)
5. Upsert valid jobs into DB (skip duplicates by URL)
6. Write to ingestion_log table with full status
7. Update circuit breaker based on outcome
"""

import logging
from datetime import datetime
from typing import List

import httpx
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import Job, IngestionLog
from app.schemas import JobCreate
from app.ingestion.remotive import RemotiveSource
from app.ingestion.arbeitnow import ArbeitnowSource
from app.ingestion.normalizer import normalize_remotive, normalize_arbeitnow
from app.ingestion.validator import validate_and_filter
from app.resilience.retry import retry_with_backoff
from app.resilience.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)

primary_source = RemotiveSource()
fallback_source = ArbeitnowSource()


@retry_with_backoff(max_attempts=3, base_delay=1.0, exceptions=(httpx.HTTPError, Exception))
async def _fetch_with_retry(source) -> List[dict]:
    """Thin wrapper so the retry decorator can be applied per-call."""
    return await source.fetch()


def _upsert_jobs(db: Session, jobs: List[JobCreate]) -> int:
    """
    Insert jobs, skip duplicates (unique constraint on url).
    Returns count of actually inserted rows.
    """
    inserted = 0
    for job in jobs:
        existing = db.query(Job).filter(Job.url == job.url).first()
        if existing:
            continue  # Skip duplicates silently
        db_job = Job(
            title=job.title,
            company=job.company,
            location=job.location,
            url=job.url,
            posted_date=job.posted_date,
            source=job.source,
            fetched_at=datetime.utcnow(),
        )
        db.add(db_job)
        try:
            db.flush()
            inserted += 1
        except IntegrityError:
            db.rollback()
    db.commit()
    return inserted


def _write_log(
    db: Session,
    source: str,
    status: str,
    records_pulled: int,
    error_message: str = None,
) -> None:
    log = IngestionLog(
        timestamp=datetime.utcnow(),
        source=source,
        status=status,
        records_pulled=records_pulled,
        error_message=error_message,
    )
    db.add(log)
    db.commit()
    logger.info(f"[pipeline] Log written: source={source} status={status} records={records_pulled}")


async def run_ingestion() -> dict:
    """
    Main pipeline entry point. Called by scheduler and the /ingest/trigger endpoint.
    Returns a summary dict for API responses.
    """
    db: Session = SessionLocal()
    used_fallback = False

    try:
        # Step 1: Decide source
        if circuit_breaker.should_use_fallback:
            logger.warning("[pipeline] Circuit breaker OPEN — using fallback source (Arbeitnow).")
            active_source = fallback_source
            normalizer = normalize_arbeitnow
            used_fallback = True
        else:
            active_source = primary_source
            normalizer = normalize_remotive

        source_name = active_source.get_name()

        # Step 2: Fetch with retry
        try:
            raw_records = await _fetch_with_retry(active_source)
        except Exception as exc:
            # All retries exhausted
            error_str = str(exc)
            logger.error(f"[pipeline] Fetch failed after all retries: {error_str}")
            circuit_breaker.record_failure()
            _write_log(db, source_name, "failed", 0, error_str)
            return {
                "status": "failed",
                "source": source_name,
                "records_pulled": 0,
                "error": error_str,
                "used_fallback": used_fallback,
            }

        # Step 3: Empty response detection
        if not raw_records:
            msg = "empty_response: source returned 200 OK with 0 records"
            logger.warning(f"[pipeline] {msg} from {source_name}")
            circuit_breaker.record_failure()
            _write_log(db, source_name, "empty_response", 0, msg)
            return {
                "status": "empty_response",
                "source": source_name,
                "records_pulled": 0,
                "error": msg,
                "used_fallback": used_fallback,
            }

        # Step 4: Validate + filter
        valid_recs, drift_count, drift_reasons = validate_and_filter(raw_records, source_name)

        # Step 5: Normalize
        normalized: List[JobCreate] = []
        for rec in valid_recs:
            job = normalizer(rec)
            if job and job.url and job.title:
                normalized.append(job)

        # Step 6: Upsert to DB
        inserted = _upsert_jobs(db, normalized)

        # Step 7: Log
        status = "success"
        extra = None
        if drift_count > 0:
            status = "schema_drift"
            extra = f"{drift_count} records had drift: {'; '.join(drift_reasons[:5])}"

        circuit_breaker.record_success()
        _write_log(db, source_name, status, inserted, extra)

        logger.info(
            f"[pipeline] Done. source={source_name} raw={len(raw_records)} "
            f"valid={len(valid_recs)} inserted={inserted} drift={drift_count}"
        )

        return {
            "status": status,
            "source": source_name,
            "records_pulled": inserted,
            "drift_count": drift_count,
            "used_fallback": used_fallback,
        }

    except Exception as exc:
        logger.exception(f"[pipeline] Unexpected error: {exc}")
        _write_log(db, "unknown", "failed", 0, str(exc))
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()
