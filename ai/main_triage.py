"""Entry point: AI-triage the regressions in the current scan result.

Loads the scan result, runs Claude triage over the regression findings, and
writes the enriched result back to the same path so downstream steps (auto-PR,
PR comment, metrics) see the AI fields. Degrades to a no-op without an API key.
"""

from __future__ import annotations

import sys
from pathlib import Path

import structlog

from ai.triage import triage_regressions
from scanner import config
from scanner.models import ScanResult

log = structlog.get_logger(__name__)


def main() -> int:
    config.configure_logging()
    path = Path(config.CURRENT_RESULTS)
    if not path.exists():
        log.warning("triage_no_results", path=str(path))
        return 0

    result = ScanResult.model_validate_json(path.read_text(encoding="utf-8"))
    regressions = [f for f in result.findings if f.is_regression]
    if not regressions:
        log.info("triage_nothing_to_do")
        return 0

    triage_regressions(regressions)
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    log.info("triage_complete", regressions=len(regressions), output=str(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
