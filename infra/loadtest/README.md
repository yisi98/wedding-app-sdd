# Load Test (SC-003: 150 concurrent users)

`locustfile.py` simulates guests logging in and browsing. Execute it against a
**deployed, prod-like** environment (AliCloud staging), not the local dev box, since the
target is 150 concurrent users with realistic infra (RDS, Redis, OSS, nginx).

```bash
pip install locust
locust -f infra/loadtest/locustfile.py --host https://<staging-host> \
       --users 150 --spawn-rate 15 --run-time 5m --headless
```

**Go-live gate**: error rate ≈ 0% and p95 within budget at 150 users. Record the run
summary here before production sign-off.

> Status: script ready. The 150-user run must be executed against staging (requires the
> deployed stack) — it cannot be run from a developer laptop.
