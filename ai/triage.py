"""Claude-powered triage of security regressions.

For each regression finding, Claude explains the regression, assesses blast
radius, confirms benchmark mapping, scores exploitability, and flags whether the
finding is auto-remediable. Structured output is forced via a tool call and
validated client-side against the SecurityFinding fields.
"""

from __future__ import annotations

import json

import structlog

from ai._client import (
    MAX_TOKENS,
    TRIAGE_TEMPERATURE,
    cached_system,
    get_client,
    load_prompt,
)
from scanner import config
from scanner.hcl_blocks import find_resource_block
from scanner.models import SecurityFinding

log = structlog.get_logger(__name__)

TRIAGE_TOOL = {
    "name": "report_triage",
    "description": "Report the structured triage analysis for one security regression.",
    "input_schema": {
        "type": "object",
        "properties": {
            "plain_english": {
                "type": "string",
                "description": "One sentence explaining what regressed and why it matters.",
            },
            "blast_radius": {
                "type": "string",
                "description": "What else is affected if this is exploited.",
            },
            "benchmark_controls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Confirmed CIS/NIST control IDs, e.g. ['CIS 4.1', 'NIST AC-3'].",
            },
            "exploitability_score": {
                "type": "integer",
                "description": "Exploitability from 1 (hard) to 10 (trivial).",
            },
            "auto_remediable": {
                "type": "boolean",
                "description": "Whether a minimal Terraform fix can resolve this safely.",
            },
            "fix_description": {
                "type": "string",
                "description": "One sentence describing the fix.",
            },
            "severity_justification": {
                "type": "string",
                "description": "Why the severity level is correct.",
            },
        },
        "required": [
            "plain_english",
            "blast_radius",
            "benchmark_controls",
            "exploitability_score",
            "auto_remediable",
            "fix_description",
        ],
    },
}


def _resource_context(finding: SecurityFinding) -> str:
    found = find_resource_block(
        finding.resource_type, finding.resource_name, config.SCAN_DIR
    )
    if found is None:
        return "(resource block not found in scanned directory)"
    _, block = found
    return block


def triage_finding(finding: SecurityFinding) -> SecurityFinding:
    """Enrich a single finding in place via Claude. No-op if no client."""
    client = get_client()
    if client is None:
        return finding

    user = load_prompt("triage_user.txt").format(
        rule_id=finding.rule_id,
        scanner=finding.scanner,
        severity=finding.severity.value,
        benchmark_controls=", ".join(finding.benchmark_controls) or "none mapped",
        resource_type=finding.resource_type,
        resource_name=finding.resource_name,
        message=finding.message,
        resource_context=_resource_context(finding),
    )

    try:
        resp = client.messages.create(
            model=config.MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TRIAGE_TEMPERATURE,
            system=cached_system(load_prompt("triage_system.txt")),
            tools=[TRIAGE_TOOL],
            tool_choice={"type": "tool", "name": "report_triage"},
            messages=[{"role": "user", "content": user}],
        )
    except Exception as exc:  # noqa: BLE001 — triage is best-effort, never blocks
        log.warning("triage_api_error", rule=finding.rule_id, error=str(exc))
        return finding

    data = _extract_tool_input(resp)
    if data is None:
        log.warning("triage_no_tool_use", rule=finding.rule_id)
        return finding

    finding.plain_english = data.get("plain_english")
    finding.blast_radius = data.get("blast_radius")
    score = data.get("exploitability_score")
    if isinstance(score, int):
        finding.exploitability_score = max(1, min(10, score))
    finding.auto_remediable = bool(data.get("auto_remediable"))
    finding.remediation = data.get("fix_description")
    if data.get("benchmark_controls"):
        merged = list(
            dict.fromkeys(finding.benchmark_controls + data["benchmark_controls"])
        )
        finding.benchmark_controls = merged

    log.info(
        "triaged",
        rule=finding.rule_id,
        exploitability=finding.exploitability_score,
        auto_remediable=finding.auto_remediable,
    )
    return finding


def triage_regressions(regressions: list[SecurityFinding]) -> list[SecurityFinding]:
    """Triage every regression finding. Findings are mutated in place."""
    for f in regressions:
        triage_finding(f)
    return regressions


def _extract_tool_input(resp) -> dict | None:
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use":
            inp = block.input
            return inp if isinstance(inp, dict) else json.loads(inp)
    return None
