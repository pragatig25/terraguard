"""Shared rule-id sets and formatting helpers for the regression suite."""

from __future__ import annotations

from scanner.models import SecurityFinding

# --- Networking (CIS 4.x / 5.x) ---
OPEN_SSH_RULES = {"CKV_AWS_24"}
OPEN_RDP_RULES = {"CKV_AWS_25"}
OPEN_INGRESS_RULES = OPEN_SSH_RULES | OPEN_RDP_RULES | {"CKV_AWS_260"}
SG_DESCRIPTION_RULES = {"CKV_AWS_23"}

# --- IAM (CIS 1.x) ---
IAM_WILDCARD_RULES = {"CKV_AWS_355", "CKV2_AWS_56"}
IAM_ADMIN_RULES = {"CKV_AWS_274"}
IAM_ATTACHMENT_RULES = {"CKV_AWS_40"}

# --- Storage (CIS 2.1.x / 3.7) ---
S3_ENCRYPTION_RULES = {"CKV_AWS_19", "CKV_AWS_145"}
S3_PUBLIC_RULES = {"CKV_AWS_20", "CKV_AWS_57", "CKV2_AWS_6"}
S3_VERSIONING_RULES = {"CKV_AWS_21"}
S3_LOGGING_RULES = {"CKV_AWS_18"}

# --- Compute (CIS 2.2.1 / 5.6) ---
EBS_ENCRYPTION_RULES = {"CKV_AWS_8", "CKV_AWS_189"}
IMDSV2_RULES = {"CKV_AWS_79"}

# --- Database (CIS 2.3.x) ---
RDS_ENCRYPTION_RULES = {"CKV_AWS_16"}
RDS_PUBLIC_RULES = {"CKV_AWS_17"}
RDS_MULTIAZ_RULES = {"CKV_AWS_157"}
RDS_LOGGING_RULES = {"CKV_AWS_129"}

# --- Logging (CIS 3.x / 5.2) ---
CLOUDTRAIL_RULES = {"CKV_AWS_36", "CKV_AWS_67"}
VPC_FLOW_LOG_RULES = {"CKV2_AWS_35"}
LOG_ENCRYPTION_RULES = {"CKV_AWS_119"}

# --- Secrets (CIS 1.20) ---
SECRETS_KMS_RULES = {"CKV_AWS_57", "CKV_AWS_149"}
SECRETS_ROTATION_RULES = {"CKV2_AWS_57"}


def regressions_matching(
    regressions: list[SecurityFinding], rule_ids: set[str]
) -> list[SecurityFinding]:
    return [f for f in regressions if f.rule_id in rule_ids]


def format_violation_message(violations: list[SecurityFinding]) -> str:
    """Human-readable assertion message listing each new regression."""
    if not violations:
        return "No violations."
    lines = [f"{len(violations)} new security regression(s) introduced:"]
    for f in violations:
        controls = ", ".join(f.benchmark_controls) or "—"
        lines.append(
            f"  [{f.severity.value}] {f.rule_id} on "
            f"{f.resource_type}.{f.resource_name} "
            f"({controls}) — {f.message}"
        )
    return "\n".join(lines)
