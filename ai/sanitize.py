"""Redaction helpers — never leak IPs, CIDRs, ARNs, or account IDs in comments."""

from __future__ import annotations

import re

_IPV4_CIDR = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?\b")
_ARN = re.compile(r"arn:aws[\w-]*:[^\s\"']+")
_ACCOUNT_ID = re.compile(r"\b\d{12}\b")


def sanitize(text: str) -> str:
    """Redact network/account identifiers from free text bound for a PR comment."""
    if not text:
        return text
    text = _ARN.sub("arn:aws:***", text)
    text = _IPV4_CIDR.sub("<redacted-cidr>", text)
    text = _ACCOUNT_ID.sub("<account-id>", text)
    return text


# A resource name "looks sensitive" if it embeds a long digit run (account id,
# timestamp) — those get truncated; ordinary names like "app" are left intact.
_SENSITIVE_NAME = re.compile(r"\d{6,}")


def safe_resource_name(address: str, limit: int = 24) -> str:
    """Truncate only the resource *name* when it appears to embed identifiers.

    `address` is a Terraform address like `aws_s3_bucket.assets`; the type prefix
    is always preserved, the name is truncated only when it looks sensitive.
    """
    if "." not in address:
        return address
    rtype, _, name = address.partition(".")
    if _SENSITIVE_NAME.search(name) and len(name) > limit:
        name = name[:limit] + "…"
    return f"{rtype}.{name}"
