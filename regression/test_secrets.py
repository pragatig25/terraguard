"""Secrets management posture invariants — KMS encryption, rotation.

CIS AWS 1.20; NIST IA-5.
"""

from __future__ import annotations

import pytest

from regression._helpers import (
    SECRETS_KMS_RULES,
    SECRETS_ROTATION_RULES,
    format_violation_message,
    regressions_matching,
)


@pytest.mark.high
def test_secrets_kms_encryption_not_removed(regressions):
    """Secrets Manager / sensitive resources must stay KMS-encrypted (CIS 1.20)."""
    violations = regressions_matching(regressions, SECRETS_KMS_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.medium
def test_secret_rotation_not_disabled(regressions):
    """Secret automatic rotation must not be newly disabled."""
    violations = regressions_matching(regressions, SECRETS_ROTATION_RULES)
    assert not violations, format_violation_message(violations)
