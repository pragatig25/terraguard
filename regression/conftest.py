"""Pytest fixtures for the TerraGuard regression suite.

These are *posture* tests, not unit tests: they assert that a PR does not
introduce new security regressions relative to the main-branch baseline.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scanner.baseline import load_baseline, mark_regressions
from scanner.models import Baseline, ScanResult, SecurityFinding


@pytest.fixture(scope="session")
def current() -> ScanResult:
    """Current scan result written by `scanner.main`."""
    path = os.getenv("TERRAGUARD_CURRENT_RESULTS", "/tmp/terraguard_results.json")
    if not Path(path).exists():
        pytest.skip(f"No current scan results at {path}")
    return ScanResult.model_validate_json(Path(path).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def baseline() -> Baseline:
    """Main-branch baseline. Skips regression tests entirely on first run."""
    path = os.getenv("TERRAGUARD_BASELINE", "baseline/latest.json")
    bl = load_baseline(path)
    if bl is None:
        pytest.skip("No baseline found — first run, nothing to regress against")
    return bl


@pytest.fixture(scope="session")
def regressions(current: ScanResult, baseline: Baseline) -> list[SecurityFinding]:
    """Findings present in `current` but absent from the baseline."""
    mark_regressions(current.findings, baseline)
    return [f for f in current.findings if f.is_regression]
