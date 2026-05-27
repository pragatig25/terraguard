"""EC2/EBS compute posture invariants — IMDSv2, volume encryption.

CIS AWS 2.2.1 / 5.6.
"""

from __future__ import annotations

import pytest

from regression._helpers import (
    EBS_ENCRYPTION_RULES,
    IMDSV2_RULES,
    format_violation_message,
    regressions_matching,
)


@pytest.mark.high
def test_no_new_imdsv1_instances(regressions):
    """EC2 instances must continue to require IMDSv2 (CIS 5.6)."""
    violations = regressions_matching(regressions, IMDSV2_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.high
def test_no_new_unencrypted_ebs(regressions):
    """EBS volumes / root devices must not be newly unencrypted (CIS 2.2.1)."""
    violations = regressions_matching(regressions, EBS_ENCRYPTION_RULES)
    assert not violations, format_violation_message(violations)
