"""Loads benchmarks/mapping.json and maps scanner rule IDs to CIS/NIST controls."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from scanner.models import Severity

_MAPPING_PATH = Path(__file__).resolve().parent.parent / "benchmarks" / "mapping.json"


@lru_cache(maxsize=1)
def _mapping() -> dict[str, dict]:
    with open(_MAPPING_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def benchmark_controls(rule_id: str) -> list[str]:
    """Return ['CIS 4.1', 'NIST AC-3', ...] for a known rule, else []."""
    entry = _mapping().get(rule_id)
    if not entry:
        return []
    controls = [f"CIS {c}" for c in entry.get("cis_controls", [])]
    controls += [f"NIST {c}" for c in entry.get("nist_controls", [])]
    return controls


def mapped_severity(rule_id: str, fallback: Severity) -> Severity:
    """Prefer the curated severity from mapping.json; else use the scanner's."""
    entry = _mapping().get(rule_id)
    if entry and entry.get("severity"):
        try:
            return Severity(entry["severity"])
        except ValueError:
            return fallback
    return fallback


def is_auto_remediable(rule_id: str) -> bool:
    entry = _mapping().get(rule_id)
    return bool(entry and entry.get("auto_remediable"))


def known_rules() -> set[str]:
    return set(_mapping().keys())
