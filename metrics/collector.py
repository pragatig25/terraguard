"""Build RunMetrics from a scan and aggregate run history into DashboardData."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog

from metrics.schema import (
    ControlCount,
    DashboardData,
    HeatmapCell,
    RunMetrics,
    TrendPoint,
)
from scanner.models import Baseline, ScanResult, Severity

log = structlog.get_logger(__name__)

# Total controls TerraGuard governs (CIS controls in benchmarks/cis_aws_v1_5.json).
CONTROLS_TOTAL = 18

_SEV_RANK = {s.value: i for i, s in enumerate(Severity)}  # lower index = worse


def build_run_metrics(
    scan: ScanResult,
    baseline: Baseline | None,
    event_type: str = "pr",
    auto_fix_pr_url: str | None = None,
    pytest_report_path: str | None = None,
    duration_seconds: float = 0.0,
) -> RunMetrics:
    before = baseline.posture_score if baseline else scan.posture_score
    regressions = [f for f in scan.findings if f.is_regression]
    by_sev: Counter[str] = Counter(f.severity.value for f in regressions)
    controls = sorted({c for f in regressions for c in f.benchmark_controls})

    _ = pytest_report_path  # reserved: per-test results can be folded in later

    return RunMetrics(
        run_id=scan.run_id,
        timestamp=scan.timestamp,
        git_sha=scan.git_sha,
        branch=scan.branch,
        pr_number=scan.pr_number,
        event_type=event_type,  # type: ignore[arg-type]
        posture_score_before=before,
        posture_score_after=scan.posture_score,
        score_delta=round(scan.posture_score - before, 1),
        regressions_introduced=len(regressions),
        regressions_by_severity=dict(by_sev),
        benchmarks_violated=controls,
        auto_fix_pr_opened=bool(auto_fix_pr_url),
        auto_fix_pr_url=auto_fix_pr_url,
        scanner_findings=scan.scanner_counts,
        duration_seconds=round(duration_seconds, 1),
    )


def load_pytest_duration(path: str) -> float:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return float(data.get("duration", 0.0))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return 0.0


def aggregate_dashboard(
    runs: list[RunMetrics],
    controls_total: int = CONTROLS_TOTAL,
    demo: bool = False,
) -> DashboardData:
    """Recompute all dashboard aggregates from the run history."""
    now = datetime.now(timezone.utc)
    runs_sorted = sorted(runs, key=lambda r: r.timestamp)
    cutoff_30d = now - timedelta(days=30)

    # Current posture: latest merge run (main), else latest run overall.
    merge_runs = [r for r in runs_sorted if r.event_type in ("merge", "scheduled")]
    current = (
        (merge_runs or runs_sorted)[-1].posture_score_after if runs_sorted else 100.0
    )

    posture_trend = [
        TrendPoint(
            date=r.timestamp.date().isoformat(),
            score=r.posture_score_after,
            pr_number=r.pr_number,
            delta=r.score_delta,
            is_regression=r.regressions_introduced > 0,
        )
        for r in runs_sorted
    ]

    recent = [r for r in runs_sorted if _aware(r.timestamp) >= cutoff_30d]
    control_counter: Counter[str] = Counter()
    for r in recent:
        control_counter.update(r.benchmarks_violated)
    top_controls = [
        ControlCount(control=c, count=n) for c, n in control_counter.most_common(10)
    ]

    heatmap = _heatmap(runs_sorted, now)

    total_regressions_30d = sum(r.regressions_introduced for r in recent)
    total_auto_fixes_30d = sum(1 for r in recent if r.auto_fix_pr_opened)
    mttr = _mean_time_to_remediate(runs_sorted)
    controls_tested = len({c for r in runs_sorted for c in r.benchmarks_violated})

    return DashboardData(
        last_updated=now,
        demo=demo,
        runs=runs_sorted[-90:],
        current_posture_score=current,
        posture_trend=posture_trend[-60:],
        top_violated_controls=top_controls,
        regression_heatmap=heatmap,
        total_regressions_30d=total_regressions_30d,
        total_auto_fixes_30d=total_auto_fixes_30d,
        mean_time_to_remediate_hours=mttr,
        controls_tested=max(controls_tested, controls_total - 0),
        controls_total=controls_total,
    )


def _aware(ts: datetime) -> datetime:
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _heatmap(runs: list[RunMetrics], now: datetime) -> list[HeatmapCell]:
    by_day_count: Counter[str] = Counter()
    by_day_worst: dict[str, str] = {}
    start = now - timedelta(days=365)
    for r in runs:
        if _aware(r.timestamp) < start or r.regressions_introduced == 0:
            continue
        day = r.timestamp.date().isoformat()
        by_day_count[day] += r.regressions_introduced
        worst = min(
            r.regressions_by_severity, key=lambda s: _SEV_RANK.get(s, 99), default=None
        )
        if worst and (
            day not in by_day_worst
            or _SEV_RANK.get(worst, 99) < _SEV_RANK.get(by_day_worst[day], 99)
        ):
            by_day_worst[day] = worst
    return [
        HeatmapCell(date=day, count=count, worst_severity=by_day_worst.get(day))
        for day, count in sorted(by_day_count.items())
    ]


def _mean_time_to_remediate(runs: list[RunMetrics]) -> float:
    """Approximate MTTR: hours from a regression run to the next improving run."""
    deltas: list[float] = []
    open_regression: datetime | None = None
    for r in runs:
        if r.regressions_introduced > 0 and open_regression is None:
            open_regression = _aware(r.timestamp)
        elif r.score_delta > 0 and open_regression is not None:
            deltas.append(
                (_aware(r.timestamp) - open_regression).total_seconds() / 3600
            )
            open_regression = None
    return round(sum(deltas) / len(deltas), 1) if deltas else 0.0
