"""
Load test — Loan Wizard API.

Run: locust -f locustfile.py --host=http://localhost:8000

Simulates realistic user behaviour:
1. Login → get JWT
2. Submit KYC audio → get decision
3. View application history
"""
from locust import HttpUser, task, between, events
from locust.exception import StopUser

# Minimal valid WAV file (44-byte header, no audio data)
# Enough to pass the "not empty" check without triggering Whisper
_WAV_HEADER = bytes([
    0x52, 0x49, 0x46, 0x46,  # "RIFF"
    0x24, 0x00, 0x00, 0x00,  # chunk size
    0x57, 0x41, 0x56, 0x45,  # "WAVE"
    0x66, 0x6D, 0x74, 0x20,  # "fmt "
    0x10, 0x00, 0x00, 0x00,  # subchunk size = 16
    0x01, 0x00,              # PCM format
    0x01, 0x00,              # 1 channel (mono)
    0x44, 0xAC, 0x00, 0x00,  # 44100 Hz sample rate
    0x88, 0x58, 0x01, 0x00,  # byte rate
    0x02, 0x00,              # block align
    0x10, 0x00,              # bits per sample = 16
    0x64, 0x61, 0x74, 0x61,  # "data"
    0x00, 0x00, 0x00, 0x00,  # data size = 0
])


class KYCUser(HttpUser):
    wait_time = between(1, 3)
    token: str = ""

    def on_start(self):
        """Login once per simulated user."""
        resp = self.client.post(
            "/api/v1/auth/login",
            data={"username": "applicant", "password": "demo123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200:
            raise StopUser()
        self.token = resp.json()["access_token"]

    def _auth(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def submit_kyc(self):
        """Most common action — submit a KYC session."""
        self.client.post(
            "/api/v1/kyc/sessions",
            files={"file": ("audio.wav", _WAV_HEADER, "audio/wav")},
            data={"loan_product": "personal"},
            headers=self._auth(),
            name="/api/v1/kyc/sessions",
        )

    @task(2)
    def view_my_applications(self):
        self.client.get(
            "/api/v1/applications/my",
            headers=self._auth(),
            name="/api/v1/applications/my",
        )

    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health")


class AuditorUser(HttpUser):
    """Simulates an auditor reviewing the queue."""
    wait_time = between(2, 5)
    token: str = ""

    def on_start(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            data={"username": "auditor", "password": "demo123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200:
            raise StopUser()
        self.token = resp.json()["access_token"]

    def _auth(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(2)
    def view_queue(self):
        self.client.get("/api/v1/auditor/queue", headers=self._auth())

    @task(1)
    def view_stats(self):
        self.client.get("/api/v1/auditor/stats", headers=self._auth())
