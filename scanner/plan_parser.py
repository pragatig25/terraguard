"""Parse `terraform show -json` output into structured TerraformPlan objects.

Variable *values* are never read or logged — only names — to avoid leaking
secrets that may be passed as Terraform variables.
"""

from __future__ import annotations

import json

import structlog

from scanner.models import ResourceChange, TerraformPlan

log = structlog.get_logger(__name__)

# Resource type prefixes considered security-relevant for triage filtering.
SECURITY_RELEVANT_PREFIXES: tuple[str, ...] = (
    "aws_security_group",
    "aws_iam_",
    "aws_s3_",
    "aws_rds_",
    "aws_db_",
    "aws_kms_",
    "aws_cloudtrail",
    "aws_vpc",
    "aws_subnet",
    "aws_network_acl",
    "aws_flow_log",
    "aws_ec2_",
    "aws_instance",
    "aws_ebs_",
)


def parse_plan_file(plan_json_path: str) -> TerraformPlan:
    """Load a `terraform show -json` file into a TerraformPlan."""
    with open(plan_json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return parse_plan_dict(data)


def parse_plan_dict(data: dict) -> TerraformPlan:
    changes: list[ResourceChange] = []
    for rc in data.get("resource_changes", []):
        change = rc.get("change", {}) or {}
        changes.append(
            ResourceChange(
                address=rc.get("address", ""),
                resource_type=rc.get("type", ""),
                name=rc.get("name", ""),
                actions=change.get("actions", []) or [],
                before=change.get("before"),
                after=change.get("after"),
            )
        )

    variable_names = sorted((data.get("variables") or {}).keys())

    plan = TerraformPlan(
        format_version=data.get("format_version"),
        terraform_version=data.get("terraform_version"),
        resource_changes=changes,
        variable_names=variable_names,
    )
    log.info(
        "parsed_plan",
        resource_changes=len(plan.resource_changes),
        variables=len(plan.variable_names),
    )
    return plan


def extract_resource_changes(plan: TerraformPlan) -> list[ResourceChange]:
    return list(plan.resource_changes)


def extract_security_relevant_changes(plan: TerraformPlan) -> list[ResourceChange]:
    """Filter to resource types that matter for security posture."""
    return [
        rc
        for rc in plan.resource_changes
        if rc.resource_type.startswith(SECURITY_RELEVANT_PREFIXES)
        # 'no-op' changes never alter posture.
        and rc.actions != ["no-op"]
    ]
