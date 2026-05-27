"""Pydantic schemas for run metrics and the dashboard data contract.

`DashboardData` is the exact JSON shape the static dashboard fetches, so this
module is the single source of truth shared by the publisher and the demo
data generator.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

EventType = Literal["pr", "merge", "scheduled"]


class RunMetrics(BaseModel):
    run_id: str
    timestamp: datetime
    git_sha: str = ""
    branch: str = ""
    pr_number: Optional[int] = None
    event_type: EventType = "pr"
    posture_score_before: float = 100.0
    posture_score_after: float = 100.0
    score_delta: float = 0.0
    regressions_introduced: int = 0
    regressions_by_severity: dict[str, int] = Field(default_factory=dict)
    benchmarks_violated: list[str] = Field(default_factory=list)
    auto_fix_pr_opened: bool = False
    auto_fix_pr_url: Optional[str] = None
    scanner_findings: dict[str, int] = Field(default_factory=dict)
    duration_seconds: float = 0.0


class TrendPoint(BaseModel):
    date: str  # YYYY-MM-DD
    score: float
    pr_number: Optional[int] = None
    delta: float = 0.0
    is_regression: bool = False


class ControlCount(BaseModel):
    control: str
    count: int


class HeatmapCell(BaseModel):
    date: str  # YYYY-MM-DD
    count: int
    worst_severity: Optional[str] = None


class DashboardData(BaseModel):
    last_updated: datetime
    demo: bool = Field(default=False, alias="_demo")
    runs: list[RunMetrics] = Field(default_factory=list)
    current_posture_score: float = 100.0
    posture_trend: list[TrendPoint] = Field(default_factory=list)
    top_violated_controls: list[ControlCount] = Field(default_factory=list)
    regression_heatmap: list[HeatmapCell] = Field(default_factory=list)
    total_regressions_30d: int = 0
    total_auto_fixes_30d: int = 0
    mean_time_to_remediate_hours: float = 0.0
    controls_tested: int = 0
    controls_total: int = 0

    model_config = {"populate_by_name": True}
