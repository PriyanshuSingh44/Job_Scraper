import logging
from typing import Optional, List, Tuple
from app.schemas import JobCreate

logger = logging.getLogger(__name__)

# Required fields that must be non-empty for a record to be accepted
REQUIRED_FIELDS_REMOTIVE = {"title", "url", "company_name"}
REQUIRED_FIELDS_ARBEITNOW = {"title", "url", "company_name"}


def validate_remotive_record(raw: dict) -> Tuple[bool, Optional[str]]:
    """
    Validate a raw Remotive record.
    Returns (is_valid, error_reason).
    Detects schema drift if expected keys are missing.
    """
    missing = REQUIRED_FIELDS_REMOTIVE - set(raw.keys())
    if missing:
        return False, f"schema_drift: missing keys {missing}"

    if not raw.get("title", "").strip():
        return False, "empty_title"
    if not raw.get("url", "").strip():
        return False, "empty_url"
    if not raw.get("company_name", "").strip():
        return False, "empty_company"

    return True, None


def validate_arbeitnow_record(raw: dict) -> Tuple[bool, Optional[str]]:
    """
    Validate a raw Arbeitnow record.
    Returns (is_valid, error_reason).
    """
    missing = REQUIRED_FIELDS_ARBEITNOW - set(raw.keys())
    if missing:
        return False, f"schema_drift: missing keys {missing}"

    if not raw.get("title", "").strip():
        return False, "empty_title"
    if not raw.get("url", "").strip():
        return False, "empty_url"
    if not raw.get("company_name", "").strip():
        return False, "empty_company"

    return True, None


def validate_and_filter(
    records: List[dict], source: str
) -> Tuple[List[dict], int, List[str]]:
    """
    Validate all records for a given source.
    Returns (valid_records, drift_count, drift_reasons).
    Logs each invalid record individually — doesn't crash the pipeline.
    """
    validator = validate_remotive_record if source == "remotive" else validate_arbeitnow_record
    valid, drift_count, reasons = [], 0, []

    for i, rec in enumerate(records):
        ok, reason = validator(rec)
        if ok:
            valid.append(rec)
        else:
            drift_count += 1
            reasons.append(reason)
            logger.warning(f"[{source}] Record #{i} rejected — {reason}: {rec.get('title','<no title>')!r}")

    if drift_count:
        logger.warning(f"[{source}] {drift_count}/{len(records)} records had validation issues.")

    return valid, drift_count, reasons
