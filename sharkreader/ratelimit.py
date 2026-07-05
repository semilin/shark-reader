"""Shared rate limiting coordinator for thread-safe global rate limit management."""

import threading
import time
from collections import deque


class RateLimitCoordinator:
    """Thread-safe coordinator that enforces a global requests-per-second cap
    and manages an escalating cooldown when the API returns 429.

    All threads share one instance so that rate-limit backoff applies across
    the entire pool rather than per-thread.
    """

    def __init__(
        self,
        requests_per_second: float = 15.0,
        initial_backoff: float = 2.0,
        max_backoff: float = 120.0,
    ) -> None:
        self._lock = threading.Lock()
        self._request_timestamps: deque[float] = deque()
        self._rps = requests_per_second
        self._global_cooldown_until: float = 0.0
        self._backoff: float = initial_backoff
        self._max_backoff = max_backoff

    def acquire(self) -> None:
        """Block the calling thread until it may make a request."""
        while True:
            with self._lock:
                now = time.time()

                if now < self._global_cooldown_until:
                    wait = self._global_cooldown_until - now
                else:
                    cutoff = now - 1.0
                    while (
                        self._request_timestamps
                        and self._request_timestamps[0] <= cutoff
                    ):
                        self._request_timestamps.popleft()

                    if len(self._request_timestamps) < self._rps:
                        self._request_timestamps.append(now)
                        return

                    wait = self._request_timestamps[0] + 1.0 - now

            time.sleep(wait)

    def report_rate_limit(self) -> None:
        """Record a 429 response and escalate the global cooldown."""
        with self._lock:
            self._global_cooldown_until = time.time() + self._backoff
            self._backoff = min(self._backoff * 2, self._max_backoff)

    def report_success(self) -> None:
        """Record a successful request and gradually relax the backoff."""
        with self._lock:
            self._backoff = max(1.0, self._backoff * 0.5)
