"""Baseline load/save, finding deduplication, and regression diffing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import structlog

from scanner.models import Baseline, ScanResult, SecurityFinding

log = structlog.get_logger(__name__)

BASELINE_PATH = Path("baseline/latest.json")


def deduplicate(findings: Iterable[SecurityFinding]) -> list[SecurityFinding]:
    """Collapse findings flagged by multiple scanners for the same issue.

    Dedup identity is (resource_type, resource_name, rule_id). When two findings
    collide we keep the one with the richer message and merge benchmark controls.
    """
    by_key: dict[str, SecurityFinding] = {}
    for f in findings:
        existing = by_key.get(f.dedup_key)
        if existing is None:
            by_key[f.dedup_key] = f.model_copy(deep=True)
            continue
        # Merge benchmark controls (union, stable order).
        merged = list(dict.fromkeys(existing.benchmark_controls + f.benchmark_controls))
        existing.benchmark_controls = merged
        # Keep the longer (more detailed) message.
        if len(f.message) > len(existing.message):
            existing.message = f.message
        # Promote to the more severe rating.
        if f.severity.weight > existing.severity.weight:
            existing.severity = f.severity
        existing.scanner = "combined"
    result = sorted(
        by_key.values(),
        key=lambda x: (-x.severity.weight, x.resource_type, x.resource_name),
    )
    log.info("deduplicated", before=len(by_key), after=len(result))
    return result


def load_baseline(path: str | Path = BASELINE_PATH) -> Baseline | None:
    """Load a baseline snapshot. Returns None if missing or empty (first run)."""
    p = Path(path)
    if not p.exists():
        log.info("baseline_missing", path=str(p))
        return None
    raw = p.read_text(encoding="utf-8").strip()
    if not raw or raw == "{}":
        log.info("baseline_empty", path=str(p))
        return None
    try:
        return Baseline.model_validate_json(raw)
    except Exception as exc:  # noqa: BLE001 — first-run / malformed baseline tolerated
        log.warning("baseline_parse_failed", error=str(exc))
        return None


def save_baseline(scan: ScanResult, path: str | Path = BASELINE_PATH) -> Baseline:
    baseline = Baseline.from_scan(scan)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(baseline.model_dump_json(indent=2), encoding="utf-8")
    log.info("baseline_saved", path=str(p), score=baseline.posture_score)
    return baseline


def mark_regressions(
    current: list[SecurityFinding], baseline: Baseline | None
) -> list[SecurityFinding]:
    """Flag findings present in `current` but absent from `baseline`.

    Mutates and returns the same finding objects with `is_regression` set.
    With no baseline (first run) nothing is a regression.
    """
    baseline_keys = {f.baseline_key for f in baseline.findings} if baseline else set()
    for f in current:
        f.is_regression = bool(baseline) and f.baseline_key not in baseline_keys
    regressions = sum(1 for f in current if f.is_regression)
    log.info("regressions_marked", total=len(current), regressions=regressions)
    return current


def score_delta(current: ScanResult, baseline: Baseline | None) -> float:
    """current_score - baseline_score. Negative = regression introduced."""
    if baseline is None:
        return 0.0
    return round(current.posture_score - baseline.posture_score, 1)
