from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job, IngestionLog
from app.schemas import HealthOut, IngestionLogOut
from app.resilience.circuit_breaker import circuit_breaker

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthOut)
def health(db: Session = Depends(get_db)):
    """Service health check with last ingestion status and total job count."""
    total_jobs = db.query(Job).count()
    last_log = (
        db.query(IngestionLog)
        .order_by(IngestionLog.timestamp.desc())
        .first()
    )

    return HealthOut(
        status="ok" if not circuit_breaker.is_open else "degraded",
        last_ingestion=IngestionLogOut.model_validate(last_log) if last_log else None,
        total_jobs=total_jobs,
    )
