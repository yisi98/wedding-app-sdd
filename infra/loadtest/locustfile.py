"""Load test for the 150-concurrent-user target (T086 / SC-003).

Run against a deployed/prod-like stack (not this dev box):

    pip install locust
    locust -f infra/loadtest/locustfile.py --host https://wedding.example.cn \
           --users 150 --spawn-rate 15 --run-time 5m --headless

Pass criteria: p95 latency stays within budget and error rate ~0 at 150 users.
"""

import random

from locust import HttpUser, between, task

EVENT_PASSWORD = "let-us-celebrate"  # supply the real password via --host env in practice


class GuestUser(HttpUser):
    wait_time = between(1, 4)

    def on_start(self) -> None:
        name = f"loadtest-{random.randint(1, 10_000)}"
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"display_name": name, "event_password": EVENT_PASSWORD},
        )
        token = resp.json().get("access_token") if resp.ok else None
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    @task(5)
    def browse_gallery(self) -> None:
        self.client.get("/api/v1/media?sort=newest&limit=24", headers=self.headers, name="gallery")

    @task(2)
    def activity(self) -> None:
        self.client.get("/api/v1/activity", headers=self.headers, name="activity")

    @task(1)
    def health(self) -> None:
        self.client.get("/api/v1/health", name="health")
