from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job
from app.schemas import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=List[JobOut])
def list_jobs(
    source: Optional[str] = Query(None, description="Filter by source: remotive or arbeitnow"),
    q: Optional[str] = Query(None, description="Keyword search in title or company"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List jobs with optional filtering by source and keyword."""
    query = db.query(Job)

    if source:
        query = query.filter(Job.source == source)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            Job.title.ilike(pattern) | Job.company.ilike(pattern)
        )

    jobs = query.order_by(Job.fetched_at.desc()).limit(limit).all()
    return jobs
