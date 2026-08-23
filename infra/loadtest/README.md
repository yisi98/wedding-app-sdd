# Load Test (SC-003: 150 concurrent users)

`locustfile.py` simulates guests **browsing and uploading** — SC-003 names both, and
upload is the expensive path: presigned URL issue, the object PUT, then Celery doing
thumbnail, WebP, dHash, LQIP and EXIF work per file. A browse-only run would go green
without measuring any of that.

Run it against a **deployed, prod-like** environment (AliCloud staging), not a dev box:
the target is 150 concurrent users against realistic infrastructure (RDS, Redis, OSS,
nginx), and a laptop measures the laptop.

```bash
pip install locust
export LOADTEST_EVENT_PASSWORD='<the real event password>'

locust -f infra/loadtest/locustfile.py --host https://<staging-host> \
       --users 150 --spawn-rate 15 --run-time 10m --headless
```

## Pass/fail is automatic

The run evaluates itself on exit and **exits non-zero if any budget is missed**, so it
can gate a release rather than relying on someone reading the table. Budgets live in
`BUDGETS_MS`:

| Operation | p95 budget |
|---|---|
| `gallery`, `gallery_page2`, `activity` | 1500 ms |
| `media_detail` | 1200 ms |
| `upload_init`, `upload_confirm` | 1500 ms |
| `health` | 500 ms |
| `object_put` | 6000 ms per MB uploaded |
| overall failure ratio | ≤ 0.5% |

They are deliberately generous: guests are on congested venue wifi inside mainland
China, not a same-region benchmark. Tighten or loosen everything at once with
`LOADTEST_P95_SCALE`.

## Knobs

| Variable | Default | Purpose |
|---|---|---|
| `LOADTEST_EVENT_PASSWORD` | — | **Required.** Never hardcode it in the script. |
| `LOADTEST_UPLOAD_WEIGHT` | `2` | Raise to model the post-ceremony surge when everyone uploads at once. |
| `LOADTEST_PHOTO_BYTES` | `1500000` | Upload size; roughly a phone photo. |
| `LOADTEST_P95_SCALE` | `1.0` | Multiplier on every latency budget. |
| `LOADTEST_STRICT_UPLOAD` | `0` | Set to `1` to treat a paused-uploads config as a failure. |

Run a subset with locust's tags: `--tags browse` or `--tags upload`.

## Two things to know before you run it

**It writes real data.** Every virtual user creates real accounts, media rows and
objects in the bucket. Everything is prefixed `loadtest-` so it can be found and purged
afterwards — do that before the event, or guests will see the test images in the
gallery.

**Watch the load generator, not just the server.** At 150 users and ~1.5 MB per photo
the client's uplink can saturate before the server does, which shows up as slow
`object_put` times that are not the server's fault. Run the generator close to the
staging region, or lower `LOADTEST_PHOTO_BYTES` and raise `LOADTEST_UPLOAD_WEIGHT` to
keep request pressure up without saturating bandwidth.

`seed.jpg` is a 21 KB, 1280×960 JPEG. Each upload appends random bytes after its EOI
marker: decoders ignore the tail, so the image still decodes at full size (realistic
processing cost) while every SHA-256 differs — otherwise deduplication (FR-007) would
reject every upload after the first with a 409.

## Status

**Script verified, 150-user run still outstanding (T086).**

Verified 2026-08-17 against a local backend: the full browse + upload path runs clean,
uploads reach `ready` with thumbnail, WebP and LQIP generated at 1280×960, the gate
passes at exit 0, and it correctly fails at exit 1 with a per-operation breakdown when
budgets are impossible.

What has **not** happened is the run that SC-003 actually requires: 150 concurrent users
against deployed infrastructure. That needs staging. Record the run summary below before
production sign-off.

<!-- Run summary goes here: date, host, users, duration, p95 per operation, failure ratio -->
