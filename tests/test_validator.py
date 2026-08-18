import pytest
from app.ingestion.validator import (
    validate_wwr_record,
    validate_indeed_rss_record,
    validate_and_filter,
)


# ── WWR Validator Tests ─────────────────────────────────────────
def test_valid_wwr_record():
    rec = {"title": "Python Developer", "url": "https://example.com/job/1", "company_name": "Acme"}
    ok, reason = validate_wwr_record(rec)
    assert ok is True
    assert reason is None


def test_wwr_missing_key_is_markup_drift():
    rec = {"title": "Python Developer", "url": "https://example.com/job/1"}  # missing company_name
    ok, reason = validate_wwr_record(rec)
    assert ok is False
    assert "markup_drift" in reason
    assert "company_name" in reason


def test_wwr_empty_title_rejected():
    rec = {"title": "", "url": "https://example.com/job/2", "company_name": "Acme"}
    ok, reason = validate_wwr_record(rec)
    assert ok is False
    assert reason == "empty_title"


# ── Indeed RSS Validator Tests ─────────────────────────────────
def test_valid_indeed_rss_record():
    rec = {"title": "DevOps Engineer", "url": "https://example.com/job/3", "company_name": "Corp"}
    ok, reason = validate_indeed_rss_record(rec)
    assert ok is True


def test_indeed_rss_empty_url_rejected():
    rec = {"title": "DevOps Engineer", "url": "", "company_name": "Corp"}
    ok, reason = validate_indeed_rss_record(rec)
    assert ok is False
    assert reason == "empty_url"


# ── validate_and_filter ────────────────────────────────────────
def test_filter_mixes_valid_and_invalid():
    records = [
        {"title": "Good Job", "url": "https://example.com/1", "company_name": "Co"},
        {"title": "", "url": "https://example.com/2", "company_name": "Co"},  # empty title
        {"title": "Another", "url": "https://example.com/3"},  # missing company_name
    ]
    valid, drift_count, reasons = validate_and_filter(records, "weworkremotely")
    assert len(valid) == 1
    assert drift_count == 2
    assert len(reasons) == 2
