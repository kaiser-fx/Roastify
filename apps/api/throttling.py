"""
Rate limiting utility for the Roastify API.
Tracks request count per client IP using Django cache.
"""

from __future__ import annotations

import time
from django.conf import settings
from django.core.cache import cache


def get_client_ip(request) -> str:
    """Extract client IP address from request headers."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "127.0.0.1")


def is_rate_limited(ip: str) -> bool:
    """
    Check if an IP address has exceeded the per-minute rate limit.
    Returns True if rate limited, False if allowed.
    """
    limit = getattr(settings, "RATE_LIMIT_PER_MINUTE", 10)
    current_minute = int(time.time() // 60)
    cache_key = f"rl:{ip}:{current_minute}"

    try:
        count = cache.get(cache_key, 0)
        if count >= limit:
            return True
        cache.set(cache_key, count + 1, timeout=65)
        return False
    except Exception:
        # If cache backend is unavailable, do not block user requests.
        return False
