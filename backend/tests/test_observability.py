"""Тесты наблюдаемости: /health, /metrics, лог-фильтры и обработка сбоев."""

import logging

from fastapi.testclient import TestClient

from app.core.logging import SilentPathsFilter, resolve_level
from app.main import app


def test_health_reports_status_and_checks():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"catalog_dir": True, "data_dir": True}
    assert body["version"]
    assert body["uptime_s"] >= 0
    assert "errors_total" in body
    assert "rooms" in body and "sockets" in body


def test_metrics_are_prometheus_text_with_counters():
    with TestClient(app) as client:
        client.get("/health")
        client.get("/api/no-such-route")  # 404 уходит в бакет unmatched
        body = client.get("/metrics").text

    assert 'path="/health"' in body
    assert 'status="404"' in body
    assert 'path="unmatched"' in body
    assert "app_errors_total" in body
    assert "app_uptime_seconds" in body
    assert "app_rooms_total" in body
    assert "app_ws_connections_active" in body


def test_unhandled_exception_becomes_json_500_and_is_counted():
    @app.get("/_test/boom", include_in_schema=False)
    async def boom() -> dict:
        raise RuntimeError("тестовый сбой")

    with TestClient(app) as client:
        response = client.get("/_test/boom")
        metrics_body = client.get("/metrics").text

    assert response.status_code == 500
    assert response.json() == {"detail": "Внутренняя ошибка сервера"}
    assert 'path="/_test/boom"' in metrics_body
    assert 'status="500"' in metrics_body


def test_silent_paths_filter_drops_health_and_metrics():
    log_filter = SilentPathsFilter()
    template = '%s - "%s %s HTTP/%s" %d'

    def record(path: str) -> logging.LogRecord:
        return logging.LogRecord(
            "uvicorn.access",
            logging.INFO,
            "",
            0,
            template,
            ("1.2.3.4:5", "GET", path, "1.1", 200),
            None,
        )

    assert log_filter.filter(record("/health")) is False
    assert log_filter.filter(record("/health?probe=1")) is False
    assert log_filter.filter(record("/metrics")) is False
    assert log_filter.filter(record("/api/rooms")) is True


def test_resolve_level_falls_back_to_info():
    assert resolve_level("debug") == "DEBUG"
    assert resolve_level("WARNING") == "WARNING"
    assert resolve_level("не-уровень") == "INFO"
