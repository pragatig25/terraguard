"""Networking posture invariants — security groups, ingress, public exposure.

CIS AWS 4.1 / 4.2 / 4.3, 5.1. These assert *deltas* against the baseline:
a PR fails only if it introduces a NEW networking regression.
"""

from __future__ import annotations

import pytest

from regression._helpers import (
    OPEN_INGRESS_RULES,
    OPEN_RDP_RULES,
    OPEN_SSH_RULES,
    SG_DESCRIPTION_RULES,
    format_violation_message,
    regressions_matching,
)


@pytest.mark.critical
def test_no_new_open_ingress_from_internet(regressions):
    """No security group may newly open ingress from 0.0.0.0/0 on guarded ports."""
    violations = regressions_matching(regressions, OPEN_INGRESS_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.critical
def test_no_new_ssh_exposed(regressions):
    """SSH (22) must not be newly exposed to the internet (CIS 4.1)."""
    violations = regressions_matching(regressions, OPEN_SSH_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.critical
def test_no_new_rdp_exposed(regressions):
    """RDP (3389) must not be newly exposed to the internet (CIS 4.2)."""
    violations = regressions_matching(regressions, OPEN_RDP_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.medium
def test_no_new_undescribed_security_group_rules(regressions):
    """New security group rules should carry descriptions (CIS 4.3)."""
    violations = regressions_matching(regressions, SG_DESCRIPTION_RULES)
    assert not violations, format_violation_message(violations)
