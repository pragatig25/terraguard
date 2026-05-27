"""Persist run history and the recomputed dashboard data to docs/data/.

The dashboard is served from `docs/` via GitHub Pages (artifact deploy). This
module owns the data files the dashboard fetches:

- docs/data/metrics.json   — raw run history (last 90 days)
- docs/data/dashboard.json — pre-aggregated LIVE dashboard data
- docs/data/demo.json       — synthetic demo data (written only by the demo generator)

The workflow is responsible for committing + pushing these files; this module
only reads and writes them so it stays easy to run and test locally.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog

from metrics.collector import aggregate_dashboard
from metrics.schema import DashboardData, RunMetrics

log = structlog.get_logger(__name__)

DATA_DIR = Path("docs/data")
METRICS_FILE = DATA_DIR / "metrics.json"
DASHBOARD_FILE = DATA_DIR / "dashboard.json"


def load_history(path: Path = METRICS_FILE) -> list[RunMetrics]:
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    import json

    data = json.loads(raw)
    runs = data.get("runs", data) if isinstance(data, dict) else data
    return [RunMetrics.model_validate(r) for r in runs]


def trim_history(runs: list[RunMetrics], days: int = 90) -> list[RunMetrics]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    kept = [r for r in runs if _aware(r.timestamp) >= cutoff]
    return sorted(kept, key=lambda r: r.timestamp)


def publish(metrics: RunMetrics, data_dir: Path = DATA_DIR) -> DashboardData:
    """Append `metrics` to history, recompute aggregates, write both files."""
    data_dir.mkdir(parents=True, exist_ok=True)
    metrics_file = data_dir / "metrics.json"
    dashboard_file = data_dir / "dashboard.json"

    history = load_history(metrics_file)
    history.append(metrics)
    history = trim_history(history)

    metrics_file.write_text(
        DashboardData(
            last_updated=datetime.now(timezone.utc), runs=history
        ).model_dump_json(indent=2, by_alias=True, include={"last_updated", "runs"}),
        encoding="utf-8",
    )

    dashboard = aggregate_dashboard(history, demo=False)
    dashboard_file.write_text(
        dashboard.model_dump_json(indent=2, by_alias=True), encoding="utf-8"
    )
    log.info(
        "metrics_published",
        runs=len(history),
        current_score=dashboard.current_posture_score,
        metrics_file=str(metrics_file),
    )
    return dashboard


def _aware(ts: datetime) -> datetime:
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
