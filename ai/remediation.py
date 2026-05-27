"""Claude-powered Terraform fix generation for auto-remediable findings."""

from __future__ import annotations

import structlog

from ai._client import MAX_TOKENS, cached_system, get_client, load_prompt
from scanner import config
from scanner.hcl_blocks import find_resource_block
from scanner.models import SecurityFinding

log = structlog.get_logger(__name__)


def generate_fix(finding: SecurityFinding) -> tuple[str, str, str] | None:
    """Return (file_path, original_block, fixed_block) or None if not fixable.

    Returns None when there is no client, the resource block can't be located,
    or Claude does not produce a usable HCL block.
    """
    client = get_client()
    if client is None:
        return None

    found = find_resource_block(
        finding.resource_type, finding.resource_name, config.SCAN_DIR
    )
    if found is None:
        log.warning("remediation_block_not_found", rule=finding.rule_id)
        return None
    file_path, original_block = found

    user = load_prompt("remediation_user.txt").format(
        rule_id=finding.rule_id,
        benchmark_controls=", ".join(finding.benchmark_controls) or "n/a",
        message=finding.message,
        fix_description=finding.remediation or "Resolve the flagged security issue.",
        file_path=file_path,
        original_block=original_block,
    )

    try:
        resp = client.messages.create(
            model=config.MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.0,
            system=cached_system(load_prompt("remediation_system.txt")),
            messages=[{"role": "user", "content": user}],
        )
    except Exception as exc:  # noqa: BLE001 — remediation is best-effort
        log.warning("remediation_api_error", rule=finding.rule_id, error=str(exc))
        return None

    fixed_block = _text(resp)
    fixed_block = _strip_fences(fixed_block)
    if not fixed_block or "resource" not in fixed_block:
        log.warning("remediation_unusable", rule=finding.rule_id)
        return None

    log.info("remediation_generated", rule=finding.rule_id, file=file_path)
    return file_path, original_block, fixed_block


def _text(resp) -> str:
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()


def _strip_fences(text: str) -> str:
    """Remove ```hcl / ``` fences if the model added them despite instructions."""
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
