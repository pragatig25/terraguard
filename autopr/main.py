"""Entry point: generate fixes for auto-remediable regressions and open a PR.

Reads the AI-triaged scan result, generates Terraform fixes for findings flagged
`auto_remediable`, and opens a single auto-fix PR targeting the contributor's
branch. Writes the resulting PR URL to /tmp/terraguard_autofix_url for the
metrics + PR-comment steps. Best-effort: never fails the pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

import structlog

from ai.remediation import generate_fix
from autopr.patch_generator import FilePatch, generate_patch
from autopr.pr_creator import create_fix_pr
from scanner import config
from scanner.models import ScanResult

log = structlog.get_logger(__name__)

AUTOFIX_URL_PATH = "/tmp/terraguard_autofix_url"


def main() -> int:
    config.configure_logging()
    path = Path(config.CURRENT_RESULTS)
    if not path.exists():
        log.warning("autopr_no_results")
        return 0

    result = ScanResult.model_validate_json(path.read_text(encoding="utf-8"))
    candidates = [f for f in result.findings if f.is_regression and f.auto_remediable]
    if not candidates:
        log.info("autopr_no_candidates")
        return 0

    patches: list[FilePatch] = []
    for finding in candidates:
        fix = generate_fix(finding)
        if fix is None:
            continue
        file_path, original_block, fixed_block = fix
        patch = generate_patch(
            rule_id=finding.rule_id,
            resource=f"{finding.resource_type}.{finding.resource_name}",
            file_path=file_path,
            original_block=original_block,
            fixed_block=fixed_block,
        )
        if patch is not None:
            patches.append(patch)

    pr_number = config.pr_number()
    if pr_number is None or not config.BRANCH:
        log.info("autopr_no_pr_context", patches=len(patches))
        return 0

    url = create_fix_pr(
        base_branch=config.BRANCH,
        patches=patches,
        findings=candidates,
        original_pr_number=pr_number,
    )
    if url:
        Path(AUTOFIX_URL_PATH).write_text(url, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
