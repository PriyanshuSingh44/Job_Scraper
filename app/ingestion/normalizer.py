from typing import Optional
from app.schemas import JobCreate


def normalize_wwr(raw: dict) -> Optional[JobCreate]:
    """
    Normalize a raw WeWorkRemotely job dict to the common JobCreate schema.
    WWR fields: title, company_name, location, url, posted_date, source
    """
    return JobCreate(
        title=raw.get("title", "").strip(),
        company=raw.get("company_name", "").strip(),
        location=raw.get("location", "").strip() or "Remote",
        url=raw.get("url", "").strip(),
        posted_date=str(raw.get("posted_date", "")).strip() or None,
        source="weworkremotely",
    )


def normalize_indeed_rss(raw: dict) -> Optional[JobCreate]:
    """
    Normalize a raw Indeed RSS job dict to the common JobCreate schema.
    Indeed RSS fields: title, company_name, location, url, posted_date, source
    """
    return JobCreate(
        title=raw.get("title", "").strip(),
        company=raw.get("company_name", "").strip(),
        location=raw.get("location", "").strip() or "Remote",
        url=raw.get("url", "").strip(),
        posted_date=str(raw.get("posted_date", "")).strip() or None,
        source="indeed_rss",
    )
