"""Unit tests for scanner output parsers."""

import pytest

from scanner.checkov_runner import parse_checkov_output
from scanner.models import Severity
from scanner.plan_parser import (
    extract_security_relevant_changes,
    parse_plan_dict,
)
from scanner.tfsec_runner import parse_tfsec_output
from scanner.trivy_runner import parse_trivy_output


@pytest.mark.unit
def test_parse_checkov_output_maps_benchmarks():
    data = {
        "results": {
            "failed_checks": [
                {
                    "check_id": "CKV_AWS_24",
                    "check_name": "Ensure no SG allows 0.0.0.0/0 to 22",
                    "resource": "aws_security_group.app",
                    "severity": "HIGH",
                    "file_path": "/networking.tf",
                    "file_line_range": [10, 18],
                }
            ]
        }
    }
    findings = parse_checkov_output(data)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "CKV_AWS_24"
    # Mapping.json severity (CRITICAL) overrides the scanner's HIGH.
    assert f.severity == Severity.CRITICAL
    assert "CIS 4.1" in f.benchmark_controls
    assert f.line_range == (10, 18)
    assert f.scanner == "checkov"


@pytest.mark.unit
def test_parse_checkov_list_form():
    data = [{"results": {"failed_checks": []}}]
    assert parse_checkov_output(data) == []


@pytest.mark.unit
def test_parse_tfsec_output():
    data = {
        "results": [
            {
                "long_id": "aws-vpc-no-public-ingress-sgr",
                "severity": "CRITICAL",
                "description": "Security group rule allows ingress from public internet",
                "resource": "aws_security_group.web",
                "location": {"filename": "net.tf", "start_line": 5, "end_line": 9},
            }
        ]
    }
    findings = parse_tfsec_output(data)
    assert findings[0].resource_type == "aws_security_group"
    assert findings[0].resource_name == "web"
    assert findings[0].severity == Severity.CRITICAL
    assert findings[0].scanner == "tfsec"


@pytest.mark.unit
def test_parse_trivy_output():
    data = {
        "Results": [
            {
                "Target": "main.tf",
                "Misconfigurations": [
                    {
                        "ID": "AVD-AWS-0086",
                        "Severity": "HIGH",
                        "Title": "S3 bucket public",
                        "CauseMetadata": {
                            "Resource": "aws_s3_bucket.assets",
                            "StartLine": 1,
                            "EndLine": 3,
                        },
                    }
                ],
            }
        ]
    }
    findings = parse_trivy_output(data)
    assert findings[0].rule_id == "AVD-AWS-0086"
    assert findings[0].resource_name == "assets"
    assert findings[0].scanner == "trivy"


@pytest.mark.unit
def test_plan_parser_filters_security_relevant():
    plan = parse_plan_dict(
        {
            "format_version": "1.2",
            "resource_changes": [
                {
                    "address": "aws_security_group.app",
                    "type": "aws_security_group",
                    "name": "app",
                    "change": {"actions": ["update"], "before": {}, "after": {}},
                },
                {
                    "address": "random_pet.name",
                    "type": "random_pet",
                    "name": "name",
                    "change": {"actions": ["create"]},
                },
                {
                    "address": "aws_vpc.main",
                    "type": "aws_vpc",
                    "name": "main",
                    "change": {"actions": ["no-op"]},
                },
            ],
            "variables": {"db_password": {"value": "secret"}, "region": {"value": "x"}},
        }
    )
    # Variable names captured, values never stored.
    assert plan.variable_names == ["db_password", "region"]
    relevant = extract_security_relevant_changes(plan)
    addresses = {rc.address for rc in relevant}
    assert "aws_security_group.app" in addresses
    assert "random_pet.name" not in addresses  # not security-relevant
    assert "aws_vpc.main" not in addresses  # no-op excluded
