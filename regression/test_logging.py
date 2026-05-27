"""Audit/logging posture invariants — CloudTrail, VPC flow logs, log encryption.

CIS AWS 3.1 / 3.8 / 5.2.
"""

from __future__ import annotations

import pytest

from regression._helpers import (
    CLOUDTRAIL_RULES,
    LOG_ENCRYPTION_RULES,
    VPC_FLOW_LOG_RULES,
    format_violation_message,
    regressions_matching,
)


@pytest.mark.high
def test_cloudtrail_not_disabled(regressions):
    """CloudTrail validation / multi-region must not be newly disabled (CIS 3.1)."""
    violations = regressions_matching(regressions, CLOUDTRAIL_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.high
def test_vpc_flow_logs_not_disabled(regressions):
    """VPC flow logging must not be newly disabled (CIS 5.2)."""
    violations = regressions_matching(regressions, VPC_FLOW_LOG_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.medium
def test_log_encryption_not_removed(regressions):
    """Log group / CloudTrail KMS encryption must not be newly removed (CIS 3.8)."""
    violations = regressions_matching(regressions, LOG_ENCRYPTION_RULES)
    assert not violations, format_violation_message(violations)
