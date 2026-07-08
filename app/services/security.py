"""Security services: input validation/cleaning and rate limiter.

Provides sanitization utility to clean up raw text input and a thread-safe
in-memory rate limiter using the Token Bucket algorithm.
"""

from __future__ import annotations

import re
import threading
import time

_MAX_INPUT_LENGTH = 280
_RUN_WHITESPACE = re.compile(r"\s+")


def clean_user_input(text: str) -> str:
    """Sanitize user text input to guard against command injection and log forging.

    Strips control characters, collapses whitespace runs, and truncates length.

    Args:
        text (str): The raw user input text string.

    Returns:
        str: The sanitized, cleaned, and bounded text string.
    """
    # Remove control characters below space (0x20) and delete (0x7f)
    cleaned = "".join(char for char in text if ord(char) >= 32 and ord(char) != 127)
    cleaned = _RUN_WHITESPACE.sub(" ", cleaned).strip()
    return cleaned[:_MAX_INPUT_LENGTH]


class RateLimiter:
    """Per-IP request rate limiter implementing the token bucket algorithm.

    Attributes:
        capacity (int): The burst capacity of the token bucket.
        refill_rate (float): The rate at which tokens are added to the bucket per second.
        max_records (int): Maximum entries allowed in the rate buckets cache before eviction.
    """

    def __init__(self, capacity: int, refill_rate: float, max_records: int = 10_000) -> None:
        """Initialize the rate limiter with capacity, refill rate, and max cache records.

        Args:
            capacity (int): Token capacity limit. Must be >= 1.
            refill_rate (float): Amount of tokens replenished per second. Must be >= 0.0.
            max_records (int): Maximum size of IP address tracking dict. Defaults to 10,000.

        Raises:
            ValueError: If capacity or max_records is less than 1.
        """
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        if max_records < 1:
            raise ValueError("max_records must be >= 1")
        self._capacity = float(capacity)
        self._refill = float(refill_rate)
        self._max_records = max_records
        self._rate_buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def _prune_old_entries(self) -> None:
        """Evict oldest entries when records exceed self._max_records."""
        overflow = len(self._rate_buckets) - self._max_records
        if overflow <= 0:
            return
        sorted_keys = sorted(self._rate_buckets, key=lambda k: self._rate_buckets[k][1])
        for key in sorted_keys[:overflow]:
            del self._rate_buckets[key]

    def check(self, ip_address: str) -> tuple[bool, float]:
        """Check if request from ip_address is allowed.

        Args:
            ip_address (str): The client IP address requesting access.

        Returns:
            tuple[bool, float]: (is_allowed, retry_after_seconds) where retry_after_seconds
                                represents the estimated wait time in seconds if blocked.
        """
        now = time.monotonic()
        with self._lock:
            tokens, last_update = self._rate_buckets.get(ip_address, (self._capacity, now))
            tokens = min(self._capacity, tokens + (now - last_update) * self._refill)

            if tokens >= 1.0:
                self._rate_buckets[ip_address] = (tokens - 1.0, now)
                allowed, retry_after = True, 0.0
            else:
                self._rate_buckets[ip_address] = (tokens, now)
                retry_after = (1.0 - tokens) / self._refill if self._refill > 0 else 60.0
                allowed = False

            self._prune_old_entries()
            return allowed, retry_after

    def clear(self) -> None:
        """Reset rate limiter state, clearing all IP bucket histories."""
        with self._lock:
            self._rate_buckets.clear()
