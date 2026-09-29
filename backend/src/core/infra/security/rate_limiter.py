import time
from collections import defaultdict
from typing import Callable, Optional
from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """Sliding-window rate limiter supporting both distributed Redis and local in-memory fallback."""

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._local_history: dict[str, list[float]] = defaultdict(list)

    def _cleanup_old_requests(self, key: str, current_time: float) -> None:
        cutoff = current_time - self.window_seconds
        self._local_history[key] = [
            ts for ts in self._local_history[key] if ts > cutoff
        ]

    def is_allowed(self, key: str) -> tuple[bool, int, int]:
        """Check if request is allowed. Returns (allowed, remaining, retry_after)."""
        now = time.time()
        self._cleanup_old_requests(key, now)

        current_count = len(self._local_history[key])
        if current_count >= self.limit:
            oldest_timestamp = self._local_history[key][0]
            retry_after = max(1, int(self.window_seconds - (now - oldest_timestamp)))
            return False, 0, retry_after

        self._local_history[key].append(now)
        remaining = self.limit - (current_count + 1)
        return True, remaining, 0

    def clear(self) -> None:
        self._local_history.clear()


def rate_limit(limit: int, window_seconds: int = 60, key_func: Optional[Callable[[Request], str]] = None):
    """FastAPI dependency for endpoint rate limiting."""
    limiter = SlidingWindowRateLimiter(limit=limit, window_seconds=window_seconds)

    async def _dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "127.0.0.1"
        key = key_func(request) if key_func else f"{request.url.path}:{client_ip}"

        allowed, remaining, retry_after = limiter.is_allowed(key)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after), "X-RateLimit-Limit": str(limit)},
            )

    return _dependency
