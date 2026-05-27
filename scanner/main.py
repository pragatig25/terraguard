"""TerraGuard scan orchestrator.

Runs Checkov + tfsec + Trivy over the Terraform directory, deduplicates,
diffs against the baseline, and writes a ScanResult JSON.

Usage:
    python -m scanner.main                  # PR scan → OUTPUT_PATH
    python -m scanner.main --baseline-capture   # write baseline/latest.json
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

import structlog

from scanner import config
from scanner.baseline import (
    deduplicate,
    load_baseline,
    mark_regressions,
    save_baseline,
    score_delta,
)
from scanner.checkov_runner import run_checkov
from scanner.models import ScanResult
from scanner.tfsec_runner import run_tfsec
from scanner.trivy_runner import run_trivy

log = structlog.get_logger(__name__)


def scan(directory: str) -> ScanResult:
    """Scan a Terraform directory.

    Checkov (restricted to the governed CIS/NIST control set in .checkov.yaml)
    is the authoritative engine: its findings drive the posture score,
    regression diff, and PR gate. tfsec + Trivy also run for breadth — their
    raw counts are recorded in `scanner_counts` but they do not affect scoring,
    which keeps the score coherent and reproducible across tool versions.
    """
    checkov_findings = run_checkov(directory)
    tfsec_findings = run_tfsec(directory)
    trivy_findings = run_trivy(directory)

    governed = deduplicate(checkov_findings)

    scanner_counts = {
        "checkov": len(checkov_findings),
        "tfsec": len(tfsec_findings),
        "trivy": len(trivy_findings),
    }
    log.info("scanner_counts", **scanner_counts)

    return ScanResult(
        run_id=str(uuid.uuid4())[:8],
        git_sha=config.GIT_SHA,
        branch=config.BRANCH,
        pr_number=config.pr_number(),
        findings=governed,
        scanner="combined",
        scanner_counts=scanner_counts,
    )


def main(argv: list[str] | None = None) -> int:
    config.configure_logging()
    parser = argparse.ArgumentParser(description="TerraGuard scanner")
    parser.add_argument(
        "--baseline-capture",
        action="store_true",
        help="Write the scan result as the new baseline (run on main).",
    )
    parser.add_argument("--dir", default=config.SCAN_DIR, help="Terraform directory")
    args = parser.parse_args(argv)

    result = scan(args.dir)

    if args.baseline_capture:
        save_baseline(result)
        log.info("baseline_capture_done", score=result.posture_score)
        return 0

    baseline = load_baseline(config.BASELINE_PATH)
    mark_regressions(result.findings, baseline)
    delta = score_delta(result, baseline)

    out = Path(config.OUTPUT_PATH)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    log.info(
        "scan_complete",
        output=str(out),
        posture_score=result.posture_score,
        score_delta=delta,
        findings=len(result.findings),
        regressions=result.regression_count,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
