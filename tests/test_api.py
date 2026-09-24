"""Integration tests for the SafeSite AI API."""
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_list_violations_returns_200():
    response = client.get("/violations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_violation_valid_succeeds():
    payload = {
        "camera_id": 1,
        "violation_type": "no_vest",
        "confidence": 0.75,
        "started_at": "2026-09-24T10:00:00",
    }
    response = client.post("/violations", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["violation_type"] == "no_vest"
    assert body["confidence"] == 0.75


def test_create_violation_invalid_confidence_rejected():
    payload = {
        "camera_id": 1,
        "violation_type": "no_vest",
        "confidence": 5.0,
        "started_at": "2026-09-24T10:00:00",
    }
    response = client.post("/violations", json=payload)
    assert response.status_code == 422


def test_filter_by_violation_type_works():
    response = client.get("/violations?violation_type=no_helmet&limit=5")
    assert response.status_code == 200
    body = response.json()
    for violation in body:
        assert violation["violation_type"] == "no_helmet"
