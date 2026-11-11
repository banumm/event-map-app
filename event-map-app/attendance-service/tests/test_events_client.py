"""Тесты межсервисной проверки события (attendance → events-service)."""

import urllib.error

import pytest

import events_client
from tests_helpers import auth, payload


@pytest.fixture()
def events_enabled(monkeypatch):
    monkeypatch.setenv("EVENTS_SERVICE_URL", "http://events-service:5001")
    monkeypatch.setenv("EVENTS_SERVICE_RETRIES", "2")
    monkeypatch.setenv("EVENTS_SERVICE_BACKOFF_SECONDS", "0")


def fake_responses(monkeypatch, *responses):
    """Подменяет HTTP-вызов: каждый элемент — статус или исключение."""
    calls = []
    queue = list(responses)

    def _request(url, timeout):
        calls.append(url)
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, Exception):
            raise item
        return item, {}

    monkeypatch.setattr(events_client, "_request", _request)
    return calls


def test_existing_event_allows_marking(client, events_enabled, monkeypatch):
    calls = fake_responses(monkeypatch, 200)
    response = client.post("/attendance", json=payload(), headers=auth("user"))
    assert response.status_code == 201
    assert calls[0].startswith("http://events-service:5001/events/")


def test_missing_event_returns_404(client, events_enabled, monkeypatch):
    fake_responses(monkeypatch, 404)
    response = client.post("/attendance", json=payload(), headers=auth("user"))
    assert response.status_code == 404
    assert response.get_json()["error"]["details"][0]["field"] == "event_id"


def test_retry_after_server_error_then_success(client, events_enabled, monkeypatch):
    calls = fake_responses(monkeypatch, 502, 200)
    response = client.post("/attendance", json=payload(), headers=auth("user"))
    assert response.status_code == 201
    assert len(calls) == 2


def test_unavailable_events_service_returns_503_after_retries(client, events_enabled, monkeypatch):
    calls = fake_responses(monkeypatch, urllib.error.URLError("connection refused"))
    response = client.post("/attendance", json=payload(), headers=auth("user"))
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "ServiceUnavailable"
    assert len(calls) == 3  # 1 попытка + 2 повтора


def test_timeout_is_handled_as_unavailable(client, events_enabled, monkeypatch):
    fake_responses(monkeypatch, TimeoutError("timed out"))
    response = client.post("/attendance", json=payload(), headers=auth("user"))
    assert response.status_code == 503


def test_health_degraded_when_events_service_down(client, events_enabled, monkeypatch):
    fake_responses(monkeypatch, urllib.error.URLError("connection refused"))
    response = client.get("/health")
    assert response.status_code == 503
    body = response.get_json()
    assert body["status"] == "degraded"
    assert body["checks"]["events_service"]["status"] == "error"


def test_health_ok_without_integration(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["checks"]["events_service"]["status"] == "disabled"


def test_metrics_endpoint(client):
    client.get("/health")
    text = client.get("/metrics").get_data(as_text=True)
    assert 'http_requests_total{method="GET",path="/health",status="200"}' in text
