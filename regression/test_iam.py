"""IAM posture invariants — wildcards, AdministratorAccess, attachment hygiene.

CIS AWS 1.16; NIST AC-6 (least privilege).
"""

from __future__ import annotations

import pytest

from regression._helpers import (
    IAM_ADMIN_RULES,
    IAM_ATTACHMENT_RULES,
    IAM_WILDCARD_RULES,
    format_violation_message,
    regressions_matching,
)


@pytest.mark.critical
def test_no_new_wildcard_iam_permissions(regressions):
    """No new IAM policy may grant wildcard (*) actions/resources (CIS 1.16)."""
    violations = regressions_matching(regressions, IAM_WILDCARD_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.high
def test_no_new_admin_access_roles(regressions):
    """No new role may attach AdministratorAccess (least privilege)."""
    violations = regressions_matching(regressions, IAM_ADMIN_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.medium
def test_no_new_user_attached_policies(regressions):
    """Policies should attach to groups/roles, not users (CIS 1.16)."""
    violations = regressions_matching(regressions, IAM_ATTACHMENT_RULES)
    assert not violations, format_violation_message(violations)
