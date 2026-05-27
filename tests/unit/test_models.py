"""Unit tests for scanner models, scoring, and hashing."""

import pytest

from scanner.models import (
    Baseline,
    ScanResult,
    SecurityFinding,
    Severity,
    posture_score,
    severity_counts,
)


def _finding(
    rule="CKV_AWS_24", sev=Severity.CRITICAL, name="app", rtype="aws_security_group"
):
    return SecurityFinding(
        rule_id=rule,
        severity=sev,
        resource_type=rtype,
        resource_name=name,
        message="msg",
    )


@pytest.mark.unit
def test_severity_weights_ordered():
    assert Severity.CRITICAL.weight > Severity.HIGH.weight > Severity.MEDIUM.weight
    assert Severity.LOW.weight == 1
    assert Severity.INFO.weight == 0


@pytest.mark.unit
def test_posture_score_clamped():
    findings = [_finding(sev=Severity.CRITICAL) for _ in range(10)]  # 200 penalty
    assert posture_score(findings) == 0.0
    assert posture_score([]) == 100.0


@pytest.mark.unit
def test_posture_score_formula():
    findings = [
        _finding(sev=Severity.CRITICAL),  # 20
        _finding(sev=Severity.HIGH),  # 10
        _finding(sev=Severity.MEDIUM),  # 3
        _finding(sev=Severity.LOW),  # 1
    ]
    assert posture_score(findings) == 100 - 34


@pytest.mark.unit
def test_dedup_and_baseline_keys():
    f = _finding()
    assert f.dedup_key == "aws_security_group::app::CKV_AWS_24"
    assert f.baseline_key == "CKV_AWS_24::app"


@pytest.mark.unit
def test_scan_result_computed_fields():
    f1 = _finding(sev=Severity.CRITICAL)
    f1.is_regression = True
    sr = ScanResult(run_id="x", findings=[f1, _finding(sev=Severity.LOW, name="b")])
    assert sr.regression_count == 1
    assert sr.finding_counts["CRITICAL"] == 1
    assert sr.posture_score == 100 - 21


@pytest.mark.unit
def test_findings_hash_is_order_independent():
    a = ScanResult(run_id="a", findings=[_finding(name="x"), _finding(name="y")])
    b = ScanResult(run_id="b", findings=[_finding(name="y"), _finding(name="x")])
    assert a.findings_hash() == b.findings_hash()


@pytest.mark.unit
def test_baseline_from_scan_roundtrip():
    sr = ScanResult(run_id="x", git_sha="abc", findings=[_finding()])
    bl = Baseline.from_scan(sr)
    assert bl.posture_score == sr.posture_score
    assert bl.findings_hash == sr.findings_hash()
    restored = Baseline.model_validate_json(bl.model_dump_json())
    assert restored.git_sha == "abc"


@pytest.mark.unit
def test_severity_counts_complete():
    counts = severity_counts([_finding(sev=Severity.HIGH)])
    assert counts == {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 0, "LOW": 0, "INFO": 0}
