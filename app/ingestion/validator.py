import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# Required fields that must be present and non-empty
REQUIRED_FIELDS_WWR = {"title", "url", "company_name"}
REQUIRED_FIELDS_INDEED_RSS = {"title", "url", "company_name"}


def validate_wwr_record(raw: dict) -> Tuple[bool, Optional[str]]:
    """
    Validate a raw WeWorkRemotely parsed record.
    Returns (is_valid, error_reason).
    """
    missing = REQUIRED_FIELDS_WWR - set(raw.keys())
    if missing:
        return False, f"markup_drift: missing required parsed keys {missing}"

    if not raw.get("title", "").strip():
        return False, "empty_title"
    if not raw.get("url", "").strip():
        return False, "empty_url"
    if not raw.get("company_name", "").strip():
        return False, "empty_company"

    return True, None


def validate_indeed_rss_record(raw: dict) -> Tuple[bool, Optional[str]]:
    """
    Validate a raw Indeed RSS parsed record.
    Returns (is_valid, error_reason).
    """
    missing = REQUIRED_FIELDS_INDEED_RSS - set(raw.keys())
    if missing:
        return False, f"markup_drift: missing required parsed keys {missing}"

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
    Logs each invalid record individually — pipeline does not crash on individual bad rows.
    """
    validator = validate_wwr_record if source == "weworkremotely" else validate_indeed_rss_record
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
        logger.warning(f"[{source}] {drift_count}/{len(records)} records had validation or markup issues.")

    return valid, drift_count, reasons
