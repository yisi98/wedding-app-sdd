"""Load test for the 150-concurrent-user target (T086 / SC-003).

SC-003 is "150 concurrent guests **browsing and uploading** without visible
degradation", so this exercises both. Upload is the expensive path — presigned URL
issue, the object PUT itself, then Celery doing thumbnail / WebP / dHash / LQIP / EXIF
work per file — and a browse-only run would produce a green result that does not mean
what the success criterion says.

Run against a deployed, prod-like stack (RDS, Redis, OSS, nginx), never the dev box::

    pip install locust
    export LOADTEST_EVENT_PASSWORD='...'          # the real event password
    locust -f infra/loadtest/locustfile.py --host https://wedding.example.cn \
           --users 150 --spawn-rate 15 --run-time 10m --headless

Pass/fail is evaluated automatically on exit against the budgets in ``BUDGETS_MS``, and
the process exits non-zero if any budget is missed, so this can gate a release.

Knobs, all optional environment variables:

- ``LOADTEST_EVENT_PASSWORD`` — the event password. Required; never hardcode it here.
- ``LOADTEST_UPLOAD_WEIGHT`` — upload task weight (default 2). Raise it to model the
  post-ceremony surge when everyone uploads at once.
- ``LOADTEST_PHOTO_BYTES`` — target upload size (default 1_500_000, ~a phone photo).
- ``LOADTEST_STRICT_UPLOAD`` — set to 1 to make an upload that cannot start fail the
  run, instead of being skipped. Default 0, so a deliberately paused-uploads config
  does not look like a fault.
- ``LOADTEST_P95_SCALE`` — multiplier on every latency budget (default 1.0).

Note on ``upload_confirm``: in production it only enqueues the Celery job, so it should
be fast. In dev the pipeline runs inline, so the same call also does the decode, resize
and hashing — do not read a dev timing as a production one.

**This writes real data.** Every virtual user creates real accounts, media rows and
objects in the bucket. Run it against staging and purge afterwards — everything it
creates is prefixed ``loadtest-`` so it can be found and removed.
"""

from __future__ import annotations

import hashlib
import os
import random
from pathlib import Path

from locust import HttpUser, between, events, tag, task

# --------------------------------------------------------------------------- config

EVENT_PASSWORD = os.getenv("LOADTEST_EVENT_PASSWORD", "")
UPLOAD_WEIGHT = int(os.getenv("LOADTEST_UPLOAD_WEIGHT", "2"))
PHOTO_BYTES = int(os.getenv("LOADTEST_PHOTO_BYTES", "1500000"))
STRICT_UPLOAD = os.getenv("LOADTEST_STRICT_UPLOAD", "0") == "1"

# A real JPEG, so the worker does genuine decode/resize/hash work. Junk bytes would be
# marked `failed` by the pipeline and would measure nothing but the queue.
SEED_JPEG = (Path(__file__).parent / "seed.jpg").read_bytes()

# Per-operation p95 budgets. SC-003 says "without visible degradation"; these turn that
# into something a run can actually fail on. Rationale for the numbers:
#   - Guests are on congested venue wifi inside mainland China, so these are generous
#     compared with a same-region API benchmark.
#   - `object_put` is bandwidth-bound and scales with LOADTEST_PHOTO_BYTES; it is
#     budgeted per megabyte rather than as a flat number.
BUDGETS_MS = {
    "gallery": 1500,
    "gallery_page2": 1500,
    "activity": 1500,
    "media_detail": 1200,
    "health": 500,
    "upload_init": 1500,
    "upload_confirm": 1500,
}
OBJECT_PUT_BUDGET_MS_PER_MB = 6000
MAX_FAILURE_RATIO = 0.005  # 0.5%

# Uniform multiplier on every latency budget, so staging can be tightened or loosened
# without editing the table. Also how the failure path gets exercised in CI: a tiny
# scale makes the gate trip on purpose.
P95_SCALE = float(os.getenv("LOADTEST_P95_SCALE", "1.0"))


def _unique_photo() -> tuple[bytes, str]:
    """A valid JPEG with unique content, plus its SHA-256.

    Bytes appended after the EOI marker are ignored by every decoder, so the image
    still decodes at 1280x960 — realistic processing cost — while the hash differs
    every time. Without that, deduplication (FR-007) would reject the second upload
    onwards with a 409 and the test would measure nothing.
    """
    padding = max(0, PHOTO_BYTES - len(SEED_JPEG))
    blob = SEED_JPEG + os.urandom(padding)
    return blob, hashlib.sha256(blob).hexdigest()


class GuestUser(HttpUser):
    wait_time = between(1, 4)

    def on_start(self) -> None:
        if not EVENT_PASSWORD:
            raise RuntimeError(
                "LOADTEST_EVENT_PASSWORD is not set — every login would 401 and the "
                "run would report a meaningless 100% failure rate."
            )
        name = f"loadtest-{random.randint(1, 1_000_000)}"
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"display_name": name, "event_password": EVENT_PASSWORD},
            name="login",
        )
        token = resp.json().get("access_token") if resp.ok else None
        if not token:
            # Without a token every later request 401s, so the run would report a
            # failure rate that says nothing about capacity. Stop loudly instead.
            raise RuntimeError(f"login failed: {resp.status_code} {resp.text[:200]}")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.seen_ids: list[int] = []

    # ------------------------------------------------------------------ browse path

    @tag("browse")
    @task(5)
    def browse_gallery(self) -> None:
        resp = self.client.get(
            "/api/v1/media?sort=newest&limit=24", headers=self.headers, name="gallery"
        )
        if resp.ok:
            # Remember a few ids so detail views hit real rows rather than 404s.
            self.seen_ids = [item["id"] for item in resp.json().get("items", [])][:24]

    @tag("browse")
    @task(2)
    def scroll_second_page(self) -> None:
        # Infinite scroll: the second page is the offset query that actually exercises
        # the index, and is where a missing one shows up first.
        self.client.get(
            "/api/v1/media?sort=newest&limit=24&offset=24",
            headers=self.headers,
            name="gallery_page2",
        )

    @tag("browse")
    @task(2)
    def open_item(self) -> None:
        if not self.seen_ids:
            return
        media_id = random.choice(self.seen_ids)
        self.client.get(
            f"/api/v1/media/{media_id}", headers=self.headers, name="media_detail"
        )

    @tag("browse")
    @task(2)
    def activity(self) -> None:
        self.client.get("/api/v1/activity", headers=self.headers, name="activity")

    @tag("browse")
    @task(1)
    def health(self) -> None:
        self.client.get("/api/v1/health", name="health")

    # ------------------------------------------------------------------ upload path

    @tag("upload")
    @task(UPLOAD_WEIGHT)
    def upload_photo(self) -> None:
        blob, digest = _unique_photo()

        with self.client.post(
            "/api/v1/media/upload/init",
            json={
                "original_filename": f"loadtest-{digest[:12]}.jpg",
                "mime_type": "image/jpeg",
                "file_size": len(blob),
                "file_hash": digest,
            },
            headers=self.headers,
            name="upload_init",
            catch_response=True,
        ) as init:
            if init.status_code == 403:
                # Uploads are paused (archive mode, FR-010) — a valid configuration.
                init.failure("uploads paused") if STRICT_UPLOAD else init.success()
                return
            if init.status_code == 409:
                # Hash collision against an earlier run; not a server fault.
                init.success()
                return
            if not init.ok:
                init.failure(f"init {init.status_code}")
                return
            payload = init.json()
            init.success()

        upload_url = payload["upload_url"]
        media_id = payload["media_id"]

        # Two shapes, and the auth header differs between them:
        #   prod — an absolute presigned OSS URL. The signature is in the query string;
        #          sending our bearer token as well is unnecessary and some
        #          S3-compatible gateways reject the extra Authorization header.
        #   dev  — a relative /media/upload/raw path on this API, which does need it.
        put_headers = {"Content-Type": "image/jpeg"}
        if not upload_url.lower().startswith(("http://", "https://")):
            put_headers.update(self.headers)

        self.client.put(
            upload_url,
            data=blob,
            headers=put_headers,
            name="object_put",
        )

        self.client.post(
            "/api/v1/media/upload/confirm",
            json={"media_id": media_id},
            headers=self.headers,
            name="upload_confirm",
        )


# ------------------------------------------------------------------ pass/fail gate


@events.quitting.add_listener
def _assert_budgets(environment, **_kwargs) -> None:
    """Turn "within budget" into an actual exit code.

    Locust exits 0 by default no matter how bad the numbers are, which is how a load
    test ends up "passing" without anyone reading it.
    """
    stats = environment.stats
    failures: list[str] = []

    ratio = stats.total.fail_ratio
    if ratio > MAX_FAILURE_RATIO:
        failures.append(f"failure ratio {ratio:.2%} > {MAX_FAILURE_RATIO:.2%}")

    for name, budget in BUDGETS_MS.items():
        # Request names are set explicitly on every call, so match on name across
        # methods rather than guessing the verb.
        matches = [e for e in stats.entries.values() if e.name == name]
        if not matches:
            continue
        scaled = budget * P95_SCALE
        p95 = max(m.get_response_time_percentile(0.95) or 0 for m in matches)
        if p95 > scaled:
            failures.append(f"{name} p95 {p95:.0f}ms > {scaled:.0f}ms")

    put_matches = [e for e in stats.entries.values() if e.name == "object_put"]
    if put_matches:
        budget = (
            OBJECT_PUT_BUDGET_MS_PER_MB * max(PHOTO_BYTES / 1_000_000, 0.1) * P95_SCALE
        )
        p95 = max(m.get_response_time_percentile(0.95) or 0 for m in put_matches)
        if p95 > budget:
            failures.append(f"object_put p95 {p95:.0f}ms > {budget:.0f}ms")

    if failures:
        print("\nSC-003 FAILED:")
        for line in failures:
            print(f"  - {line}")
        environment.process_exit_code = 1
    else:
        print(f"\nSC-003 PASSED at {stats.total.num_requests} requests.")
        environment.process_exit_code = 0
