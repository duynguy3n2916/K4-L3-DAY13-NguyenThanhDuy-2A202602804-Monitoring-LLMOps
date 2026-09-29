from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.dashboard import DASHBOARD_HTML, dashboard_snapshot, read_recent_records


def test_runtime_dashboard_contains_exactly_six_named_panels() -> None:
    for panel_id in ("latency", "traffic", "errors", "cost", "tokens", "quality"):
        assert DASHBOARD_HTML.count(f'id="{panel_id}"') == 1
    assert "60-minute window" in DASHBOARD_HTML
    assert "refresh 30s" in DASHBOARD_HTML


def test_dashboard_aggregates_jsonl_runtime_data(tmp_path: Path) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    records = [
        {"ts": timestamp, "event": "request_received"},
        {
            "ts": timestamp,
            "event": "response_sent",
            "latency_ms": 200,
            "ttft_ms": 50,
            "cost_usd": 0.01,
            "tokens_in": 20,
            "tokens_out": 80,
            "quality_score": 0.8,
            "tool_success": True,
        },
    ]
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text(
        "\n".join(json.dumps(record) for record in records), encoding="utf-8"
    )

    snapshot = dashboard_snapshot(read_recent_records(log_path))

    assert snapshot["latency"]["p95_ms"] == 200
    assert snapshot["errors"]["retrieval_success_pct"] == 100
    assert snapshot["cost"]["total_usd"] == 0.01
    assert snapshot["tokens"]["input_total"] == 20
    assert snapshot["quality"]["average"] == 0.8
