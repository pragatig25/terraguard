"""Pydantic v2 models for TerraGuard findings, plans, and scan results."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, computed_field

ScannerName = Literal["checkov", "tfsec", "trivy", "combined"]


class Severity(str, Enum):
    """Finding severity ordered high-to-low for sorting and scoring."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

    @property
    def weight(self) -> int:
        return {
            Severity.CRITICAL: 20,
            Severity.HIGH: 10,
            Severity.MEDIUM: 3,
            Severity.LOW: 1,
            Severity.INFO: 0,
        }[self]


class ResourceChange(BaseModel):
    """A single resource change extracted from a Terraform plan."""

    address: str
    resource_type: str
    name: str
    actions: list[str] = Field(default_factory=list)
    before: Optional[dict] = None
    after: Optional[dict] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_create(self) -> bool:
        return "create" in self.actions

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_update(self) -> bool:
        return "update" in self.actions


class TerraformPlan(BaseModel):
    """Structured view of a `terraform show -json` document."""

    format_version: Optional[str] = None
    terraform_version: Optional[str] = None
    resource_changes: list[ResourceChange] = Field(default_factory=list)
    # Variable names only — values are never stored or logged.
    variable_names: list[str] = Field(default_factory=list)

    def change_for(self, address: str) -> Optional[ResourceChange]:
        for rc in self.resource_changes:
            if rc.address == address:
                return rc
        return None


class SecurityFinding(BaseModel):
    """A normalized security finding produced by any scanner."""

    rule_id: str
    severity: Severity
    resource_type: str
    resource_name: str
    message: str
    file_path: Optional[str] = None
    line_range: Optional[tuple[int, int]] = None
    scanner: ScannerName = "combined"
    is_regression: bool = False
    benchmark_controls: list[str] = Field(default_factory=list)
    remediation: Optional[str] = None
    # AI-enriched fields (set by ai.triage).
    plain_english: Optional[str] = None
    blast_radius: Optional[str] = None
    exploitability_score: Optional[int] = None
    auto_remediable: Optional[bool] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def dedup_key(self) -> str:
        """Identity used to dedup across scanners and diff against a baseline."""
        return f"{self.resource_type}::{self.resource_name}::{self.rule_id}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def baseline_key(self) -> str:
        """Looser identity used for baseline regression diffing."""
        return f"{self.rule_id}::{self.resource_name}"


def posture_score(findings: list[SecurityFinding]) -> float:
    """Compute a 0-100 posture score from a list of findings.

    score = 100 - sum(weight per finding), clamped to [0, 100].
    """
    penalty = sum(f.severity.weight for f in findings)
    return float(max(0, min(100, 100 - penalty)))


def severity_counts(findings: list[SecurityFinding]) -> dict[str, int]:
    counts = {s.value: 0 for s in Severity}
    for f in findings:
        counts[f.severity.value] += 1
    return counts


class ScanResult(BaseModel):
    """The full result of one scan run, persisted to JSON."""

    run_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    git_sha: str = ""
    branch: str = ""
    pr_number: Optional[int] = None
    findings: list[SecurityFinding] = Field(default_factory=list)
    scanner: ScannerName = "combined"
    # Raw finding counts per tool (breadth), e.g. {"checkov": 5, "trivy": 9}.
    scanner_counts: dict[str, int] = Field(default_factory=dict)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def posture_score(self) -> float:
        return posture_score(self.findings)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def regression_count(self) -> int:
        return sum(1 for f in self.findings if f.is_regression)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def finding_counts(self) -> dict[str, int]:
        return severity_counts(self.findings)

    def findings_hash(self) -> str:
        """Deterministic hash of sorted rule_id::resource keys."""
        keys = sorted(f.baseline_key for f in self.findings)
        return hashlib.sha256("|".join(keys).encode()).hexdigest()


class Baseline(BaseModel):
    """Snapshot of main-branch posture, committed to baseline/latest.json."""

    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    git_sha: str = ""
    posture_score: float = 100.0
    finding_counts: dict[str, int] = Field(default_factory=dict)
    findings_hash: str = ""
    findings: list[SecurityFinding] = Field(default_factory=list)

    @classmethod
    def from_scan(cls, scan: ScanResult) -> "Baseline":
        return cls(
            git_sha=scan.git_sha,
            posture_score=scan.posture_score,
            finding_counts=scan.finding_counts,
            findings_hash=scan.findings_hash(),
            findings=scan.findings,
        )
