import time
import pytest
from src.core.infra.security.rate_limiter import SlidingWindowRateLimiter


def test_rate_limiter_allows_under_limit():
    limiter = SlidingWindowRateLimiter(limit=3, window_seconds=10)
    key = "user_1"

    allowed1, remaining1, _ = limiter.is_allowed(key)
    assert allowed1 is True
    assert remaining1 == 2

    allowed2, remaining2, _ = limiter.is_allowed(key)
    assert allowed2 is True
    assert remaining2 == 1

    allowed3, remaining3, _ = limiter.is_allowed(key)
    assert allowed3 is True
    assert remaining3 == 0


def test_rate_limiter_blocks_over_limit():
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=10)
    key = "user_2"

    assert limiter.is_allowed(key)[0] is True
    assert limiter.is_allowed(key)[0] is True

    allowed, remaining, retry_after = limiter.is_allowed(key)
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0


def test_rate_limiter_resets_after_window():
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=1)
    key = "user_3"

    assert limiter.is_allowed(key)[0] is True
    assert limiter.is_allowed(key)[0] is False

    time.sleep(1.1)
    assert limiter.is_allowed(key)[0] is True
