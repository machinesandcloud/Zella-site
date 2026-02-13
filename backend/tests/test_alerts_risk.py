import os
import sys

os.environ["USE_MOCK_IBKR"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.insert(0, os.path.abspath("backend"))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from core.init_db import init_db  # noqa: E402

init_db()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_alerts_and_risk_summary():
    with TestClient(app) as client:
        client.post(
            "/api/auth/register",
            json={"username": "risk_user", "email": "risk@example.com", "password": "pass123"},
        )
        resp = client.post("/api/auth/login", json={"username": "risk_user", "password": "pass123"})
        token = resp.json()["access_token"]

        resp = client.get("/api/risk/summary", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "accountMetrics" in data

        resp = client.get("/api/alerts?limit=5", headers=auth_header(token))
        assert resp.status_code == 200
