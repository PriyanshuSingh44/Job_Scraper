from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class JobBase(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    url: str
    posted_date: Optional[str] = None
    source: str


class JobCreate(JobBase):
    pass


class JobOut(JobBase):
    id: int
    fetched_at: datetime

    model_config = {"from_attributes": True}


class IngestionLogBase(BaseModel):
    source: str
    status: str
    records_pulled: int = 0
    error_message: Optional[str] = None


class IngestionLogOut(IngestionLogBase):
    id: int
    timestamp: datetime

    model_config = {"from_attributes": True}


class HealthOut(BaseModel):
    status: str
    last_ingestion: Optional[IngestionLogOut] = None
    total_jobs: int
