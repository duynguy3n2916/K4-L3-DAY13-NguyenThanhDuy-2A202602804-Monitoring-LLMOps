from __future__ import annotations

import json
import asyncio
from pathlib import Path

import httpx

from app import logging_config
from app.main import app


def test_chat_response_log_exposes_quality_for_dashboard(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/chat",
                json={
                    "user_id": "student-01",
                    "session_id": "session-01",
                    "feature": "qa",
                    "message": "Explain observability",
                },
            )

    response = asyncio.run(send_request())

    assert response.status_code == 200
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    response_event = next(event for event in events if event["event"] == "response_sent")
    assert response_event["quality_score"] == response.json()["quality_score"]
    assert response_event["ttft_ms"] == response.json()["ttft_ms"]
    assert response_event["tool_name"] == "retrieval"
    assert response_event["tool_success"] is True


def test_correlation_id_and_log_enrichment(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/chat",
                json={
                    "user_id": "student-test-01",
                    "session_id": "session-test-01",
                    "feature": "qa",
                    "message": "Hello observability",
                },
            )

    response = asyncio.run(send_request())
    assert response.status_code == 200

    cid = response.headers.get("x-request-id")
    assert cid is not None
    assert cid.startswith("req-")
    assert response.headers.get("x-response-time-ms") is not None
    assert response.json()["correlation_id"] == cid

    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    api_events = [e for e in events if e.get("service") == "api"]
    assert len(api_events) >= 2

    for event in api_events:
        assert event.get("correlation_id") == cid
        assert event.get("session_id") == "session-test-01"
        assert event.get("feature") == "qa"
        assert "user_id_hash" in event
        assert "model" in event
        assert "env" in event


def test_custom_correlation_id_and_context_isolation(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def run_scenario():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r1 = await client.post(
                "/chat",
                headers={"x-request-id": "req-custom01"},
                json={
                    "user_id": "user-A",
                    "session_id": "session-A",
                    "feature": "summary",
                    "message": "Summarize first",
                },
            )
            r2 = await client.post(
                "/chat",
                headers={"x-request-id": "req-custom02"},
                json={
                    "user_id": "user-B",
                    "session_id": "session-B",
                    "feature": "qa",
                    "message": "Query second",
                },
            )
            return r1, r2

    r1, r2 = asyncio.run(run_scenario())
    assert r1.headers.get("x-request-id") == "req-custom01"
    assert r2.headers.get("x-request-id") == "req-custom02"

    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    r1_events = [e for e in events if e.get("correlation_id") == "req-custom01"]
    r2_events = [e for e in events if e.get("correlation_id") == "req-custom02"]

    assert len(r1_events) >= 2
    assert len(r2_events) >= 2
    for e in r1_events:
        assert e.get("session_id") == "session-A"
        assert e.get("feature") == "summary"
    for e in r2_events:
        assert e.get("session_id") == "session-B"
        assert e.get("feature") == "qa"


def test_pii_redacted_in_chat_logs(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_pii_request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r1 = await client.post(
                "/chat",
                json={
                    "user_id": "user-pii-1",
                    "session_id": "session-pii-1",
                    "feature": "qa",
                    "message": "student@vinuni.edu.vn cccd 001234567890",
                },
            )
            r2 = await client.post(
                "/chat",
                json={
                    "user_id": "user-pii-2",
                    "session_id": "session-pii-2",
                    "feature": "qa",
                    "message": "phone 0987654321 card 4111 1111 1111 1111",
                },
            )
            return r1, r2

    r1, r2 = asyncio.run(send_pii_request())
    assert r1.status_code == 200
    assert r2.status_code == 200

    raw_logs = log_path.read_text(encoding="utf-8")
    assert "student@vinuni.edu.vn" not in raw_logs
    assert "001234567890" not in raw_logs
    assert "0987654321" not in raw_logs
    assert "4111 1111 1111 1111" not in raw_logs
    assert "REDACTED_EMAIL" in raw_logs
    assert "REDACTED_CCCD" in raw_logs
    assert "REDACTED_PHONE_VN" in raw_logs
    assert "REDACTED_CREDIT_CARD" in raw_logs
