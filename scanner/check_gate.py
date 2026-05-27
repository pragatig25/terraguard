"""PR gate: exit non-zero if any CRITICAL regression was introduced.

This is the step that actually blocks a PR merge. HIGH/MEDIUM/LOW regressions
warn (via the PR comment) but do not fail the build.
"""

from __future__ import annotations

import sys

import structlog

from scanner import config
from scanner.models import ScanResult, Severity

log = structlog.get_logger(__name__)


def main() -> int:
    config.configure_logging()
    try:
        result = ScanResult.model_validate_json(
            open(config.CURRENT_RESULTS, encoding="utf-8").read()
        )
    except FileNotFoundError:
        log.warning("gate_no_results", path=config.CURRENT_RESULTS)
        return 0

    critical_regressions = [
        f
        for f in result.findings
        if f.is_regression and f.severity == Severity.CRITICAL
    ]

    if critical_regressions:
        for f in critical_regressions:
            log.error(
                "critical_regression",
                rule=f.rule_id,
                resource=f"{f.resource_type}.{f.resource_name}",
            )
        log.error("gate_failed", count=len(critical_regressions))
        return 1

    log.info("gate_passed", posture_score=result.posture_score)
    return 0


if __name__ == "__main__":
    sys.exit(main())
