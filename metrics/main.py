"""Entry point: collect this run's metrics and publish dashboard data.

Run after scan + triage + auto-PR. Reads the scan result, baseline, pytest
report, and any auto-fix PR URL, then writes docs/data/{metrics,dashboard}.json.
The workflow commits these files (push/merge events only).
"""

from __future__ import annotations

import sys
from pathlib import Path

import structlog

from metrics.collector import build_run_metrics, load_pytest_duration
from metrics.publisher import publish
from scanner import config
from scanner.baseline import load_baseline
from scanner.models import ScanResult

log = structlog.get_logger(__name__)

AUTOFIX_URL_PATH = "/tmp/terraguard_autofix_url"


def _event_type() -> str:
    if config.pr_number() is not None:
        return "pr"
    if config.BRANCH in ("", "main"):
        return "merge"
    return "scheduled"


def main() -> int:
    config.configure_logging()
    path = Path(config.CURRENT_RESULTS)
    if not path.exists():
        log.warning("metrics_no_results", path=str(path))
        return 0

    scan = ScanResult.model_validate_json(path.read_text(encoding="utf-8"))
    baseline = load_baseline(config.BASELINE_PATH)

    autofix_url = None
    if Path(AUTOFIX_URL_PATH).exists():
        autofix_url = Path(AUTOFIX_URL_PATH).read_text(encoding="utf-8").strip() or None

    metrics = build_run_metrics(
        scan=scan,
        baseline=baseline,
        event_type=_event_type(),
        auto_fix_pr_url=autofix_url,
        pytest_report_path=config.PYTEST_REPORT,
        duration_seconds=load_pytest_duration(config.PYTEST_REPORT),
    )
    publish(metrics)
    log.info(
        "metrics_done",
        event_type=metrics.event_type,
        score=metrics.posture_score_after,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
