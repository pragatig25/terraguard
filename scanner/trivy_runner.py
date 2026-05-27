"""Wrap Trivy (IaC config mode): run it on a Terraform directory."""

from __future__ import annotations

import json
import subprocess

import structlog

from scanner.benchmark_map import benchmark_controls, mapped_severity
from scanner.models import SecurityFinding, Severity

log = structlog.get_logger(__name__)

_TRIVY_SEVERITY = {
    "CRITICAL": Severity.CRITICAL,
    "HIGH": Severity.HIGH,
    "MEDIUM": Severity.MEDIUM,
    "LOW": Severity.LOW,
    "UNKNOWN": Severity.INFO,
}


def run_trivy(directory: str) -> list[SecurityFinding]:
    cmd = ["trivy", "config", directory, "--format", "json", "--exit-code", "0"]
    log.info("trivy_run", cmd=" ".join(cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        log.warning("trivy_not_installed")
        return []

    if not proc.stdout.strip():
        log.warning("trivy_no_output", stderr=proc.stderr[:500])
        return []

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        log.error("trivy_bad_json", head=proc.stdout[:300])
        return []

    return parse_trivy_output(data)


def parse_trivy_output(data: dict) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    for target in data.get("Results", []) or []:
        target_path = target.get("Target", "")
        for mis in target.get("Misconfigurations", []) or []:
            rule_id = mis.get("ID", "")
            scanner_sev = _TRIVY_SEVERITY.get(
                (mis.get("Severity") or "MEDIUM").upper(), Severity.MEDIUM
            )
            cause = mis.get("CauseMetadata", {}) or {}
            resource = cause.get("Resource", "") or ""
            resource_type = (
                resource.split(".")[0] if "." in resource else (resource or "unknown")
            )
            resource_name = (
                resource.split(".")[-1] if "." in resource else (resource or "unknown")
            )
            start = cause.get("StartLine")
            end = cause.get("EndLine")
            line_range = (int(start), int(end)) if start and end else None

            findings.append(
                SecurityFinding(
                    rule_id=rule_id,
                    severity=mapped_severity(rule_id, scanner_sev),
                    resource_type=resource_type,
                    resource_name=resource_name,
                    message=mis.get("Title", "") or mis.get("Description", ""),
                    file_path=target_path,
                    line_range=line_range,
                    scanner="trivy",
                    benchmark_controls=benchmark_controls(rule_id),
                )
            )

    log.info("trivy_parsed", findings=len(findings))
    return findings
