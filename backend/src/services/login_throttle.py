"""Login brute-force guard (companion to the nginx rate limit, T087).

nginx throttles request *rate* per IP, which must stay loose enough for a venue full
of guests behind one NAT IP. This module adds a failure-*count* lockout: after
MAX_FAILURES wrong passwords from one client IP within WINDOW_SECONDS, that IP is
rejected with 429 for LOCKOUT_SECONDS — cheap to hit with a shared event password.

Counts live in Redis when configured (production); without Redis (dev/test) the
guard is inert, mirroring how Celery is optional. Every Redis operation fails open:
a Redis outage must not lock every guest out of the site.
"""

import logging

from redis import asyncio as aioredis

from ..config import get_settings

logger = logging.getLogger("wmp.login_throttle")

MAX_FAILURES = 15
WINDOW_SECONDS = 15 * 60
LOCKOUT_SECONDS = 15 * 60

_client: aioredis.Redis | None = None


def _key(ip: str) -> str:
    return f"wmp:login:fail:{ip}"


async def _redis() -> aioredis.Redis | None:
    global _client
    if not get_settings().redis_url:
        return None
    if _client is None:
        _client = aioredis.from_url(get_settings().redis_url, decode_responses=True)
    return _client


async def is_locked(ip: str) -> bool:
    client = await _redis()
    if client is None:
        return False
    try:
        return int(await client.get(_key(ip)) or 0) >= MAX_FAILURES
    except Exception:  # fail open (see module docstring)
        logger.warning("Login throttle lookup failed", exc_info=True)
        return False


async def record_failure(ip: str) -> None:
    client = await _redis()
    if client is None:
        return
    try:
        pipe = client.pipeline()
        pipe.incr(_key(ip))
        pipe.expire(_key(ip), WINDOW_SECONDS)
        await pipe.execute()
    except Exception:
        logger.warning("Login throttle increment failed", exc_info=True)


async def clear_failures(ip: str) -> None:
    client = await _redis()
    if client is None:
        return
    try:
        await client.delete(_key(ip))
    except Exception:
        logger.warning("Login throttle reset failed", exc_info=True)
