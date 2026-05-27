"""Unit tests for metrics collection and aggregation."""

from datetime import datetime, timedelta, timezone

import pytest

from metrics.collector import aggregate_dashboard, build_run_metrics
from metrics.schema import RunMetrics
from scanner.models import Baseline, ScanResult, SecurityFinding, Severity


def _run(
    days_ago, score, regressions=0, sev=None, controls=None, auto=False, event="pr"
):
    return RunMetrics(
        run_id=f"r{days_ago}",
        timestamp=datetime.now(timezone.utc) - timedelta(days=days_ago),
        posture_score_before=score + (5 if regressions else 0),
        posture_score_after=score,
        score_delta=-5.0 if regressions else 1.0,
        regressions_introduced=regressions,
        regressions_by_severity={sev: regressions} if sev else {},
        benchmarks_violated=controls or [],
        auto_fix_pr_opened=auto,
        event_type=event,
    )


@pytest.mark.unit
def test_build_run_metrics_from_scan():
    f = SecurityFinding(
        rule_id="CKV_AWS_24",
        severity=Severity.CRITICAL,
        resource_type="aws_security_group",
        resource_name="app",
        message="m",
        benchmark_controls=["CIS 4.1"],
        is_regression=True,
    )
    scan = ScanResult(run_id="x", findings=[f], scanner_counts={"checkov": 1})
    baseline = Baseline(posture_score=95.0)
    rm = build_run_metrics(scan, baseline, event_type="pr")
    assert rm.regressions_introduced == 1
    assert rm.regressions_by_severity == {"CRITICAL": 1}
    assert rm.benchmarks_violated == ["CIS 4.1"]
    assert rm.score_delta == round(scan.posture_score - 95.0, 1)
    assert rm.scanner_findings == {"checkov": 1}


@pytest.mark.unit
def test_aggregate_dashboard_current_prefers_merge():
    runs = [
        _run(5, 70.0, event="pr"),
        _run(1, 88.0, event="merge"),
    ]
    d = aggregate_dashboard(runs)
    assert d.current_posture_score == 88.0


@pytest.mark.unit
def test_aggregate_dashboard_30d_window_and_heatmap():
    runs = [
        _run(2, 80.0, regressions=2, sev="HIGH", controls=["CIS 4.1"], auto=True),
        _run(
            40, 60.0, regressions=1, sev="CRITICAL", controls=["CIS 2.1.1"]
        ),  # outside 30d
    ]
    d = aggregate_dashboard(runs)
    assert d.total_regressions_30d == 2  # the 40-day-old one excluded
    assert d.total_auto_fixes_30d == 1
    assert any(c.count == 2 for c in d.regression_heatmap)
    assert d.top_violated_controls[0].control == "CIS 4.1"


@pytest.mark.unit
def test_aggregate_empty():
    d = aggregate_dashboard([])
    assert d.current_posture_score == 100.0
    assert d.posture_trend == []
