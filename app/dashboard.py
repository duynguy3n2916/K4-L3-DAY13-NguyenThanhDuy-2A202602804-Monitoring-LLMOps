from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from .logging_config import LOG_PATH
from .metrics import percentile


WINDOW_MINUTES = 60


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def read_recent_records(
    path: Path | None = None, *, now: datetime | None = None
) -> list[dict[str, Any]]:
    log_path = path or LOG_PATH
    if not log_path.exists():
        return []

    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(minutes=WINDOW_MINUTES)
    records: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        timestamp = _timestamp(record.get("ts"))
        if timestamp is not None and timestamp >= cutoff:
            records.append(record)
    return records


def dashboard_snapshot(records: list[dict[str, Any]]) -> dict[str, Any]:
    requests = [record for record in records if record.get("event") == "request_received"]
    responses = [record for record in records if record.get("event") == "response_sent"]
    failures = [record for record in records if record.get("event") == "request_failed"]

    latencies = [int(record["latency_ms"]) for record in responses if record.get("latency_ms") is not None]
    ttfts = [int(record["ttft_ms"]) for record in responses if record.get("ttft_ms") is not None]
    tool_results = [record.get("tool_success") for record in records if record.get("tool_success") is not None]
    qualities = [float(record["quality_score"]) for record in responses if record.get("quality_score") is not None]

    timestamps = [timestamp for record in requests if (timestamp := _timestamp(record.get("ts"))) is not None]
    observed_minutes = 1.0
    if len(timestamps) > 1:
        observed_minutes = max(1.0, (max(timestamps) - min(timestamps)).total_seconds() / 60)

    error_breakdown: dict[str, int] = {}
    for record in failures:
        error_type = str(record.get("error_type") or "UnknownError")
        error_breakdown[error_type] = error_breakdown.get(error_type, 0) + 1

    request_count = len(requests)
    error_rate = (len(failures) / request_count * 100) if request_count else 0.0
    retrieval_success = (
        sum(result is True for result in tool_results) / len(tool_results) * 100
        if tool_results
        else 0.0
    )

    return {
        "window_minutes": WINDOW_MINUTES,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latency": {
            "p50_ms": percentile(latencies, 50),
            "p95_ms": percentile(latencies, 95),
            "p99_ms": percentile(latencies, 99),
            "ttft_p95_ms": percentile(ttfts, 95),
            "threshold_ms": 3000,
        },
        "traffic": {
            "requests": request_count,
            "requests_per_minute": round(request_count / observed_minutes, 2),
            "threshold_per_minute": 1,
        },
        "errors": {
            "error_rate_pct": round(error_rate, 2),
            "breakdown": error_breakdown,
            "retrieval_success_pct": round(retrieval_success, 2),
            "error_threshold_pct": 2,
            "retrieval_threshold_pct": 90,
        },
        "cost": {
            "total_usd": round(sum(float(record.get("cost_usd") or 0) for record in responses), 6),
            "threshold_usd": 2.5,
        },
        "tokens": {
            "input_total": sum(int(record.get("tokens_in") or 0) for record in responses),
            "output_total": sum(int(record.get("tokens_out") or 0) for record in responses),
            "threshold_total": 50000,
        },
        "quality": {
            "average": round(mean(qualities), 3) if qualities else 0.0,
            "threshold": 0.75,
        },
    }


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="refresh" content="30">
  <title>Day 13 LLMOps Dashboard</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, Segoe UI, sans-serif; }
    body { margin: 0; background: #07111f; color: #e5eefc; }
    main { max-width: 1180px; margin: auto; padding: 28px; }
    header { display: flex; justify-content: space-between; align-items: end; gap: 16px; }
    h1 { margin: 0; font-size: 28px; }
    .subtle { color: #91a4c2; font-size: 13px; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 22px; }
    .panel { background: #0d1b2d; border: 1px solid #203653; border-radius: 14px; padding: 18px; min-height: 170px; }
    .panel h2 { margin: 0 0 14px; font-size: 16px; color: #b9cff3; }
    .value { font-size: 32px; font-weight: 750; letter-spacing: -1px; }
    .row { display: flex; justify-content: space-between; margin-top: 10px; color: #bed0e9; }
    .threshold { margin-top: 16px; padding-top: 10px; border-top: 1px dashed #36506f; color: #8da4c3; font-size: 12px; }
    .good { border-left: 5px solid #34d399; }
    .bad { border-left: 5px solid #fb7185; }
    @media (max-width: 850px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
<main>
  <header>
    <div><h1>K4-L3A · Monitoring & LLMOps</h1><div class="subtle">Source: data/logs.jsonl</div></div>
    <div class="subtle" id="status">60-minute window · refresh 30s</div>
  </header>
  <section class="grid">
    <article class="panel" id="latency"><h2>Latency & TTFT</h2><div class="value" id="p95">—</div><div class="row"><span>P50 / P99</span><span id="p50p99">—</span></div><div class="row"><span>TTFT P95</span><span id="ttft">—</span></div><div class="threshold">SLO: P95 ≤ 3000 ms</div></article>
    <article class="panel" id="traffic"><h2>Request Traffic</h2><div class="value" id="requestCount">—</div><div class="row"><span>Rate</span><span id="requestRate">—</span></div><div class="threshold">Expected: ≥ 1 request/min</div></article>
    <article class="panel" id="errors"><h2>Errors & Retrieval</h2><div class="value" id="errorRate">—</div><div class="row"><span>Retrieval success</span><span id="retrieval">—</span></div><div class="row"><span>Breakdown</span><span id="breakdown">—</span></div><div class="threshold">Error ≤ 2% · Retrieval ≥ 90%</div></article>
    <article class="panel" id="cost"><h2>Cost</h2><div class="value" id="totalCost">—</div><div class="row"><span>Window</span><span>60 min</span></div><div class="threshold">Budget: ≤ $2.50</div></article>
    <article class="panel" id="tokens"><h2>Input / Output Tokens</h2><div class="value" id="tokenTotal">—</div><div class="row"><span>Input</span><span id="tokenIn">—</span></div><div class="row"><span>Output</span><span id="tokenOut">—</span></div><div class="threshold">Guardrail: ≤ 50,000 total tokens</div></article>
    <article class="panel" id="quality"><h2>Quality Proxy</h2><div class="value" id="qualityAvg">—</div><div class="row"><span>Scale</span><span>0–1 score</span></div><div class="threshold">Target: average ≥ 0.75</div></article>
  </section>
</main>
<script>
const text = (id, value) => document.getElementById(id).textContent = value;
const state = (id, ok) => document.getElementById(id).classList.add(ok ? 'good' : 'bad');
fetch('/dashboard-data').then(r => r.json()).then(d => {
  text('p95', `${d.latency.p95_ms} ms P95`); text('p50p99', `${d.latency.p50_ms} / ${d.latency.p99_ms} ms`); text('ttft', `${d.latency.ttft_p95_ms} ms`);
  text('requestCount', `${d.traffic.requests} requests`); text('requestRate', `${d.traffic.requests_per_minute} req/min`);
  text('errorRate', `${d.errors.error_rate_pct}%`); text('retrieval', `${d.errors.retrieval_success_pct}%`); text('breakdown', JSON.stringify(d.errors.breakdown));
  text('totalCost', `$${d.cost.total_usd.toFixed(6)}`);
  const total = d.tokens.input_total + d.tokens.output_total; text('tokenTotal', `${total} tokens`); text('tokenIn', d.tokens.input_total); text('tokenOut', d.tokens.output_total);
  text('qualityAvg', d.quality.average.toFixed(3)); text('status', `60-minute window · refreshed ${new Date(d.generated_at).toLocaleTimeString()}`);
  state('latency', d.latency.p95_ms <= d.latency.threshold_ms); state('traffic', d.traffic.requests_per_minute >= d.traffic.threshold_per_minute);
  state('errors', d.errors.error_rate_pct <= d.errors.error_threshold_pct && d.errors.retrieval_success_pct >= d.errors.retrieval_threshold_pct);
  state('cost', d.cost.total_usd <= d.cost.threshold_usd); state('tokens', total <= d.tokens.threshold_total); state('quality', d.quality.average >= d.quality.threshold);
}).catch(() => text('status', 'Unable to load dashboard data'));
</script>
</body>
</html>"""
