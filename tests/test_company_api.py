"""API tests. Smoke test ensures pytest collects tests (CI exit code 5 otherwise)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_app_import():
    """Приложение импортируется и является экземпляром FastAPI."""
    from app.main import app
    assert isinstance(app, FastAPI)


def test_health_status_returns_200():
    """Эндпоинт /api/health/status отвечает 200 и возвращает словарь проверок."""
    from app.main import app
    client = TestClient(app)
    response = client.get("/api/health/status")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "database" in data or "overall" in data
