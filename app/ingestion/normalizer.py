from typing import Optional
from app.schemas import JobCreate


def normalize_remotive(raw: dict) -> Optional[JobCreate]:
    """
    Normalize a raw Remotive job dict to the common JobCreate schema.
    Remotive fields: id, url, title, company_name, candidate_required_location, publication_date
    """
    return JobCreate(
        title=raw.get("title", "").strip(),
        company=raw.get("company_name", "").strip(),
        location=raw.get("candidate_required_location", "").strip() or None,
        url=raw.get("url", "").strip(),
        posted_date=raw.get("publication_date", "").strip() or None,
        source="remotive",
    )


def normalize_arbeitnow(raw: dict) -> Optional[JobCreate]:
    """
    Normalize a raw Arbeitnow job dict to the common JobCreate schema.
    Arbeitnow fields: slug, url, title, company_name, location, created_at
    """
    return JobCreate(
        title=raw.get("title", "").strip(),
        company=raw.get("company_name", "").strip(),
        location=raw.get("location", "").strip() or None,
        url=raw.get("url", "").strip(),
        posted_date=str(raw.get("created_at", "")).strip() or None,
        source="arbeitnow",
    )
