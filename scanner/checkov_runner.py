"""Wrap Checkov: run it on a Terraform directory and normalize findings."""

from __future__ import annotations

import json
import subprocess

import structlog

from scanner.benchmark_map import (
    benchmark_controls,
    is_auto_remediable,
    mapped_severity,
)
from scanner.models import SecurityFinding, Severity

log = structlog.get_logger(__name__)

# Checkov severity strings → our Severity enum.
_CHECKOV_SEVERITY = {
    "CRITICAL": Severity.CRITICAL,
    "HIGH": Severity.HIGH,
    "MEDIUM": Severity.MEDIUM,
    "LOW": Severity.LOW,
    "INFO": Severity.INFO,
}


def run_checkov(
    directory: str, config_file: str | None = ".checkov.yaml"
) -> list[SecurityFinding]:
    """Run Checkov over `directory` and return failed checks as findings."""
    cmd = ["checkov", "-d", directory, "--output", "json", "--compact"]
    if config_file:
        cmd += ["--config-file", config_file]

    log.info("checkov_run", cmd=" ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # Checkov exits non-zero when it finds failures; that is expected.
    if not proc.stdout.strip():
        log.warning("checkov_no_output", stderr=proc.stderr[:500])
        return []

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        log.error("checkov_bad_json", head=proc.stdout[:300])
        return []

    return parse_checkov_output(data)


def parse_checkov_output(data: dict | list) -> list[SecurityFinding]:
    """Parse Checkov JSON (single dict or list of framework results)."""
    blocks = data if isinstance(data, list) else [data]
    findings: list[SecurityFinding] = []

    for block in blocks:
        results = (block.get("results") or {}) if isinstance(block, dict) else {}
        for check in results.get("failed_checks", []):
            rule_id = check.get("check_id", "")
            resource = check.get("resource", "")
            resource_type = resource.split(".")[0] if "." in resource else resource
            resource_name = resource.split(".")[-1] if "." in resource else resource
            scanner_sev = _CHECKOV_SEVERITY.get(
                (check.get("severity") or "MEDIUM").upper(), Severity.MEDIUM
            )
            line_range = _line_range(check.get("file_line_range"))

            findings.append(
                SecurityFinding(
                    rule_id=rule_id,
                    severity=mapped_severity(rule_id, scanner_sev),
                    resource_type=resource_type,
                    resource_name=resource_name,
                    message=check.get("check_name", ""),
                    file_path=check.get("file_path"),
                    line_range=line_range,
                    scanner="checkov",
                    benchmark_controls=benchmark_controls(rule_id),
                    auto_remediable=is_auto_remediable(rule_id),
                )
            )

    log.info("checkov_parsed", findings=len(findings))
    return findings


def _line_range(raw: object) -> tuple[int, int] | None:
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        try:
            return int(raw[0]), int(raw[1])
        except (TypeError, ValueError):
            return None
    return None
