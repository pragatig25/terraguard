"""RDS database posture invariants — public access, encryption, Multi-AZ.

CIS AWS 2.3.1 / 2.3.2 / 2.3.3.
"""

from __future__ import annotations

import pytest

from regression._helpers import (
    RDS_ENCRYPTION_RULES,
    RDS_LOGGING_RULES,
    RDS_MULTIAZ_RULES,
    RDS_PUBLIC_RULES,
    format_violation_message,
    regressions_matching,
)


@pytest.mark.critical
def test_no_new_public_rds(regressions):
    """RDS instances must not become publicly accessible (CIS 2.3.3)."""
    violations = regressions_matching(regressions, RDS_PUBLIC_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.high
def test_no_new_unencrypted_rds(regressions):
    """RDS storage encryption must not be newly disabled (CIS 2.3.1)."""
    violations = regressions_matching(regressions, RDS_ENCRYPTION_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.medium
def test_no_new_single_az_rds(regressions):
    """RDS Multi-AZ must not be newly disabled (CIS 2.3.2)."""
    violations = regressions_matching(regressions, RDS_MULTIAZ_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.medium
def test_no_new_rds_without_logging(regressions):
    """RDS log exports must not be newly removed."""
    violations = regressions_matching(regressions, RDS_LOGGING_RULES)
    assert not violations, format_violation_message(violations)
