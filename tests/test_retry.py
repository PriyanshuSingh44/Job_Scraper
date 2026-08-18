"""
Tests for the retry decorator.
Run with: pytest tests/test_retry.py -v
"""

import asyncio
import pytest
from app.resilience.retry import retry_with_backoff


@pytest.mark.asyncio
async def test_succeeds_on_first_attempt():
    calls = []

    @retry_with_backoff(max_attempts=3, base_delay=0.01)
    async def fn():
        calls.append(1)
        return "ok"

    result = await fn()
    assert result == "ok"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_retries_then_succeeds():
    calls = []

    @retry_with_backoff(max_attempts=3, base_delay=0.01)
    async def fn():
        calls.append(1)
        if len(calls) < 2:
            raise ValueError("not yet")
        return "ok"

    result = await fn()
    assert result == "ok"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_raises_after_max_attempts():
    calls = []

    @retry_with_backoff(max_attempts=3, base_delay=0.01)
    async def fn():
        calls.append(1)
        raise RuntimeError("always fails")

    with pytest.raises(RuntimeError, match="always fails"):
        await fn()

    assert len(calls) == 3
