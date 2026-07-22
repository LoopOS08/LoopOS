import asyncio
import random
import time
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, max_calls: int, period_seconds: float = 60.0):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self.calls: list[float] = []

    async def acquire(self):
        now = time.monotonic()
        self.calls = [t for t in self.calls if now - t < self.period_seconds]
        if len(self.calls) >= self.max_calls:
            wait = self.calls[0] + self.period_seconds - now
            if wait > 0:
                logger.debug(f"Rate limit hit, waiting {wait:.2f}s")
                await asyncio.sleep(wait)
        self.calls.append(time.monotonic())


def exponential_backoff_delay(attempt: int, base: float = 1.0, max_delay: float = 60.0) -> float:
    delay = min(base * (2 ** attempt), max_delay)
    jitter = random.uniform(-delay * 0.5, delay * 0.5)
    return max(0, min(delay + jitter, max_delay))


async def retry_with_backoff(coro_factory, max_retries: int = 3, base_delay: float = 1.0):
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await coro_factory()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = exponential_backoff_delay(attempt, base_delay)
                logger.warning(f"Attempt {attempt+1} failed, retrying in {delay:.1f}s: {e}")
                await asyncio.sleep(delay)
    raise last_exception
