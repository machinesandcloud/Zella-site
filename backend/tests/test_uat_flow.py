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


def test_uat_smoke_flow():
    with TestClient(app) as client:
        # Register
        resp = client.post(
            "/api/auth/register",
            json={"username": "uat_user", "email": "uat@example.com", "password": "pass123"},
        )
        assert resp.status_code in (200, 400)

        # Login
        resp = client.post("/api/auth/login", json={"username": "uat_user", "password": "pass123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        # Health
        resp = client.get("/api/qa/health")
        assert resp.status_code == 200

        # IBKR status (mock)
        resp = client.get("/api/ibkr/status", headers=auth_header(token))
        assert resp.status_code == 200

        # Connect IBKR (mock)
        resp = client.post(
            "/api/ibkr/connect",
            headers=auth_header(token),
            json={"host": "127.0.0.1", "port": 7497, "client_id": 1, "is_paper_trading": True},
        )
        assert resp.status_code == 200

        # AI scan (mock)
        resp = client.get("/api/ai/top?limit=3", headers=auth_header(token))
        assert resp.status_code == 200

        # Auto-trade blocked without confirm
        resp = client.post("/api/ai/auto-trade?limit=2&execute=true", headers=auth_header(token))
        assert resp.status_code == 400

        # Auto-trade with confirm (paper only)
        resp = client.post(
            "/api/ai/auto-trade?limit=2&execute=true&confirm_execute=true",
            headers=auth_header(token),
        )
        assert resp.status_code == 200

        # Place paper order (mock)
        resp = client.post(
            "/api/trading/order",
            headers=auth_header(token),
            json={"symbol": "AAPL", "action": "BUY", "quantity": 1, "order_type": "MKT"},
        )
        assert resp.status_code == 200
