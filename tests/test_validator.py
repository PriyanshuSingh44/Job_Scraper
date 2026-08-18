"""
Tests for the validator module.
Run with: pytest tests/test_validator.py -v
"""

import pytest
from app.ingestion.validator import (
    validate_remotive_record,
    validate_arbeitnow_record,
    validate_and_filter,
)


# ── Remotive ───────────────────────────────────────────────────
def test_valid_remotive_record():
    rec = {"title": "Python Dev", "url": "https://example.com/job/1", "company_name": "Acme"}
    ok, reason = validate_remotive_record(rec)
    assert ok is True
    assert reason is None


def test_remotive_missing_key_is_drift():
    rec = {"title": "Python Dev", "url": "https://example.com/job/1"}  # missing company_name
    ok, reason = validate_remotive_record(rec)
    assert ok is False
    assert "schema_drift" in reason
    assert "company_name" in reason


def test_remotive_empty_title_rejected():
    rec = {"title": "", "url": "https://example.com/job/2", "company_name": "Acme"}
    ok, reason = validate_remotive_record(rec)
    assert ok is False
    assert reason == "empty_title"


# ── Arbeitnow ──────────────────────────────────────────────────
def test_valid_arbeitnow_record():
    rec = {"title": "DevOps Eng", "url": "https://example.com/job/3", "company_name": "Corp"}
    ok, reason = validate_arbeitnow_record(rec)
    assert ok is True


def test_arbeitnow_empty_url_rejected():
    rec = {"title": "DevOps Eng", "url": "", "company_name": "Corp"}
    ok, reason = validate_arbeitnow_record(rec)
    assert ok is False
    assert reason == "empty_url"


# ── validate_and_filter ────────────────────────────────────────
def test_filter_mixes_valid_and_invalid():
    records = [
        {"title": "Good Job", "url": "https://example.com/1", "company_name": "Co"},
        {"title": "", "url": "https://example.com/2", "company_name": "Co"},  # empty title
        {"title": "Another", "url": "https://example.com/3"},  # missing company_name
    ]
    valid, drift_count, reasons = validate_and_filter(records, "remotive")
    assert len(valid) == 1
    assert drift_count == 2
    assert len(reasons) == 2


def test_filter_all_valid():
    records = [
        {"title": f"Job {i}", "url": f"https://example.com/{i}", "company_name": "Co"}
        for i in range(5)
    ]
    valid, drift_count, _ = validate_and_filter(records, "remotive")
    assert len(valid) == 5
    assert drift_count == 0
