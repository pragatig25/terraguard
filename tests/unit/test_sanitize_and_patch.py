"""Unit tests for PR-comment sanitization and patch generation."""

import pytest

from ai.sanitize import safe_resource_name, sanitize
from autopr.patch_generator import apply_patch_to_text, generate_patch


@pytest.mark.unit
def test_sanitize_redacts_identifiers():
    text = "SG opened to 203.0.113.5/32 on arn:aws:iam::123456789012:role/admin"
    out = sanitize(text)
    assert "203.0.113.5" not in out
    assert "123456789012" not in out
    assert "arn:aws:***" in out
    assert "<redacted-cidr>" in out


@pytest.mark.unit
def test_safe_resource_name_preserves_clean_names():
    assert safe_resource_name("aws_security_group.app") == "aws_security_group.app"


@pytest.mark.unit
def test_safe_resource_name_truncates_identifier_names():
    out = safe_resource_name("aws_s3_bucket.assets1234567890abcdefghhh")
    assert out.startswith("aws_s3_bucket.")
    assert out.endswith("…")


@pytest.mark.unit
def test_generate_and_apply_patch():
    original = 'resource "aws_x" "y" {\n  cidr = "0.0.0.0/0"\n}'
    fixed = 'resource "aws_x" "y" {\n  cidr = "10.0.0.0/8"\n}'
    patch = generate_patch("CKV_AWS_24", "aws_x.y", "net.tf", original, fixed)
    assert patch is not None
    assert "0.0.0.0/0" in patch.diff_text and "10.0.0.0/8" in patch.diff_text

    content = "before\n" + original + "\nafter"
    new = apply_patch_to_text(content, patch)
    assert "10.0.0.0/8" in new
    assert "0.0.0.0/0" not in new


@pytest.mark.unit
def test_generate_patch_noop_returns_none():
    block = 'resource "aws_x" "y" {}'
    assert generate_patch("R", "aws_x.y", "f.tf", block, block) is None


@pytest.mark.unit
def test_apply_patch_missing_block_raises():
    patch = generate_patch("R", "aws_x.y", "f.tf", "AAA", "BBB")
    with pytest.raises(ValueError):
        apply_patch_to_text("no match here", patch)
