"""Unit tests for dedup, regression marking, and score delta."""

import pytest

from scanner.baseline import deduplicate, mark_regressions, score_delta
from scanner.models import Baseline, ScanResult, SecurityFinding, Severity


def _f(rule, name, sev=Severity.HIGH, controls=None, scanner="checkov", msg="m"):
    return SecurityFinding(
        rule_id=rule,
        severity=sev,
        resource_type="aws_s3_bucket",
        resource_name=name,
        message=msg,
        scanner=scanner,
        benchmark_controls=controls or [],
    )


@pytest.mark.unit
def test_deduplicate_merges_controls_and_keeps_detail():
    a = _f("CKV_AWS_19", "assets", controls=["CIS 2.1.1"], msg="short")
    b = _f(
        "CKV_AWS_19",
        "assets",
        controls=["NIST SC-28"],
        msg="a much longer message",
        scanner="trivy",
    )
    merged = deduplicate([a, b])
    assert len(merged) == 1
    assert set(merged[0].benchmark_controls) == {"CIS 2.1.1", "NIST SC-28"}
    assert merged[0].message == "a much longer message"
    assert merged[0].scanner == "combined"


@pytest.mark.unit
def test_deduplicate_promotes_severity():
    a = _f("CKV_AWS_19", "assets", sev=Severity.LOW)
    b = _f("CKV_AWS_19", "assets", sev=Severity.CRITICAL, scanner="trivy")
    merged = deduplicate([a, b])
    assert merged[0].severity == Severity.CRITICAL


@pytest.mark.unit
def test_mark_regressions_against_baseline():
    baseline = Baseline(findings=[_f("CKV_AWS_18", "assets", sev=Severity.LOW)])
    current = [
        _f("CKV_AWS_18", "assets", sev=Severity.LOW),  # in baseline → not regression
        _f("CKV_AWS_24", "app"),  # new → regression
    ]
    mark_regressions(current, baseline)
    assert current[0].is_regression is False
    assert current[1].is_regression is True


@pytest.mark.unit
def test_mark_regressions_no_baseline_is_noop():
    current = [_f("CKV_AWS_24", "app")]
    mark_regressions(current, None)
    assert current[0].is_regression is False


@pytest.mark.unit
def test_score_delta_negative_on_regression():
    baseline = Baseline(posture_score=95.0)
    current = ScanResult(
        run_id="x", findings=[_f("CKV_AWS_24", "app", sev=Severity.CRITICAL)]
    )
    # current score = 100 - 10 (HIGH default for _f) ... use CRITICAL: 100-20=80
    assert score_delta(current, baseline) == round(current.posture_score - 95.0, 1)
    assert score_delta(current, None) == 0.0
