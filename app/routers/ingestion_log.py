from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import IngestionLog
from app.schemas import IngestionLogOut

router = APIRouter(prefix="/ingestion-log", tags=["ingestion-log"])


@router.get("", response_model=List[IngestionLogOut])
def get_ingestion_log(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Return ingestion log entries, most recent first. This is the live evidence of resilience."""
    logs = (
        db.query(IngestionLog)
        .order_by(IngestionLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return logs
