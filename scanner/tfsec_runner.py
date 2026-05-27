"""Wrap tfsec CLI: run it on a Terraform directory and normalize findings."""

from __future__ import annotations

import json
import subprocess

import structlog

from scanner.benchmark_map import benchmark_controls, mapped_severity
from scanner.models import SecurityFinding, Severity

log = structlog.get_logger(__name__)

_TFSEC_SEVERITY = {
    "CRITICAL": Severity.CRITICAL,
    "HIGH": Severity.HIGH,
    "MEDIUM": Severity.MEDIUM,
    "LOW": Severity.LOW,
}


def run_tfsec(directory: str) -> list[SecurityFinding]:
    cmd = ["tfsec", directory, "--format", "json", "--no-color", "--soft-fail"]
    log.info("tfsec_run", cmd=" ".join(cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        log.warning("tfsec_not_installed")
        return []

    if not proc.stdout.strip():
        log.warning("tfsec_no_output", stderr=proc.stderr[:500])
        return []

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        log.error("tfsec_bad_json", head=proc.stdout[:300])
        return []

    return parse_tfsec_output(data)


def parse_tfsec_output(data: dict) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    for result in data.get("results", []) or []:
        rule_id = result.get("long_id") or result.get("rule_id", "")
        resource = result.get("resource", "")
        resource_type = resource.split(".")[0] if "." in resource else resource
        resource_name = resource.split(".")[-1] if "." in resource else resource
        scanner_sev = _TFSEC_SEVERITY.get(
            (result.get("severity") or "MEDIUM").upper(), Severity.MEDIUM
        )
        location = result.get("location", {}) or {}
        start = location.get("start_line")
        end = location.get("end_line")
        line_range = (int(start), int(end)) if start and end else None

        findings.append(
            SecurityFinding(
                rule_id=rule_id,
                severity=mapped_severity(rule_id, scanner_sev),
                resource_type=resource_type,
                resource_name=resource_name,
                message=result.get("description", ""),
                file_path=location.get("filename"),
                line_range=line_range,
                scanner="tfsec",
                benchmark_controls=benchmark_controls(rule_id),
            )
        )

    log.info("tfsec_parsed", findings=len(findings))
    return findings
