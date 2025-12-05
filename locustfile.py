from locust import HttpUser, task, between
import random

class ARViewerUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def view_ar_content(self):
        self.client.get("/ar/abc123-def456")

    @task(1)
    def get_active_video(self):
        self.client.get("/api/ar/abc123-def456/active-video")

class AdminUser(HttpUser):
    @task
    def create_company(self):
        self.client.post("/api/companies/", json={
            "name": f"LoadTest-{random.randint(1,1000)}",
            "storage_connection_id": 1
        })
