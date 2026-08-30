"""Celery application for background media processing.

Real deployments run a worker against the Redis broker (on Windows dev: `--pool=solo`).
When no `REDIS_URL` is configured (dev/test), processing runs inline/eager instead — see
`services.media.confirm_upload`.
"""

from celery import Celery

from ..config import get_settings

_settings = get_settings()

celery_app = Celery(
    "wedding_media",
    broker=_settings.redis_url or "memory://",
    backend=_settings.redis_url or "cache+memory://",
    # The worker registers tasks by importing these modules at startup. Without this,
    # `send_task("process_media")` messages arrive at a worker that has no handler
    # and are rejected with KeyError (dev never sees it — no REDIS_URL means inline).
    include=["src.workers.media_processing"],
)
celery_app.conf.task_always_eager = _settings.redis_url is None
