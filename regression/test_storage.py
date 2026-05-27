"""S3 storage posture invariants — encryption, public access, versioning.

CIS AWS 2.1.1 / 2.1.2 / 3.7.
"""

from __future__ import annotations

import pytest

from regression._helpers import (
    S3_ENCRYPTION_RULES,
    S3_LOGGING_RULES,
    S3_PUBLIC_RULES,
    S3_VERSIONING_RULES,
    format_violation_message,
    regressions_matching,
)


@pytest.mark.critical
def test_no_new_public_s3_buckets(regressions):
    """No S3 bucket may newly become publicly accessible (CIS 2.1.2)."""
    violations = regressions_matching(regressions, S3_PUBLIC_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.high
def test_no_new_unencrypted_s3_buckets(regressions):
    """S3 server-side encryption must not be newly removed (CIS 2.1.1)."""
    violations = regressions_matching(regressions, S3_ENCRYPTION_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.medium
def test_no_new_unversioned_s3_buckets(regressions):
    """S3 versioning must not be newly disabled (CIS 2.1.2)."""
    violations = regressions_matching(regressions, S3_VERSIONING_RULES)
    assert not violations, format_violation_message(violations)


@pytest.mark.medium
def test_no_new_buckets_without_access_logging(regressions):
    """New buckets should have access logging enabled (CIS 3.7)."""
    violations = regressions_matching(regressions, S3_LOGGING_RULES)
    assert not violations, format_violation_message(violations)
