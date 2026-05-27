"""Generate 90 days of realistic synthetic metrics for the public demo.

Demo safety (never real infrastructure):
- Fictional resource names only (aws_s3_bucket.example, aws_iam_role.demo_role)
- Only the AWS documentation example account id 123456789012
- Only RFC 1918 private CIDR ranges
- Output carries `_demo: true` so the dashboard shows the demo banner

Output: docs/data/demo.json (DashboardData schema — identical contract to LIVE).
Reproducible via a fixed RNG seed (stdlib random; unrelated to the Anthropic API).
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow `python demo/generate_demo_data.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from metrics.collector import CONTROLS_TOTAL, aggregate_dashboard
from metrics.schema import RunMetrics

SEED = 4242
OUTPUT = Path("docs/data/demo.json")

# Controls weighted toward IAM + networking (the usual real-world offenders).
WEIGHTED_CONTROLS = [
    ("CIS 4.1", ["NIST AC-3", "NIST SC-7"], "CRITICAL", 5),
    ("CIS 4.2", ["NIST AC-3", "NIST SC-7"], "CRITICAL", 3),
    ("CIS 1.16", ["NIST AC-6"], "HIGH", 5),
    ("CIS 2.1.1", ["NIST SC-28"], "HIGH", 4),
    ("CIS 2.1.2", ["NIST AC-3"], "CRITICAL", 3),
    ("CIS 2.3.1", ["NIST SC-28"], "HIGH", 2),
    ("CIS 5.2", ["NIST AU-2"], "MEDIUM", 3),
    ("CIS 2.2.1", ["NIST SC-28"], "MEDIUM", 2),
    ("CIS 5.6", ["NIST AC-6"], "HIGH", 2),
    ("CIS 3.1", ["NIST AU-2"], "MEDIUM", 1),
]

DEMO_RESOURCES = [
    "aws_s3_bucket.example",
    "aws_iam_role.demo_role",
    "aws_security_group.web",
    "aws_db_instance.demo",
    "aws_instance.api",
    "aws_vpc.demo",
]

_SEV_WEIGHT = {"CRITICAL": 20, "HIGH": 10, "MEDIUM": 3, "LOW": 1}


def _weighted_controls() -> list:
    pool: list = []
    for control, nist, sev, weight in WEIGHTED_CONTROLS:
        pool += [(control, nist, sev)] * weight
    return pool


def generate(rng: random.Random) -> list[RunMetrics]:
    pool = _weighted_controls()
    runs: list[RunMetrics] = []
    score = 78.0
    now = datetime.now(timezone.utc)
    run_seq = 0

    for day_offset in range(90, -1, -1):
        day = now - timedelta(days=day_offset)
        weekday = day.weekday()  # 0=Mon
        # More PRs Mon-Thu, quiet weekends.
        base_prs = {0: 3, 1: 3, 2: 3, 3: 2, 4: 1, 5: 0, 6: 0}[weekday]
        pr_count = max(0, base_prs + rng.choice([-1, 0, 0, 1]))

        for _ in range(pr_count):
            run_seq += 1
            ts = day.replace(
                hour=rng.randint(9, 18), minute=rng.randint(0, 59), second=0
            )
            # ~22% of PRs introduce a regression.
            has_regression = rng.random() < 0.22
            before = round(score, 1)

            if has_regression:
                control, nist, sev = rng.choice(pool)
                penalty = _SEV_WEIGHT[sev] * rng.choice([1, 1, 1, 2])
                score = max(58.0, score - penalty * 0.5)
                auto_fixed = rng.random() < 0.75
                runs.append(
                    RunMetrics(
                        run_id=f"demo{run_seq:04d}",
                        timestamp=ts,
                        git_sha=f"{rng.randrange(16**7):07x}",
                        branch=f"feat/demo-{run_seq}",
                        pr_number=100 + run_seq,
                        event_type="pr",
                        posture_score_before=before,
                        posture_score_after=round(score, 1),
                        score_delta=round(score - before, 1),
                        regressions_introduced=1,
                        regressions_by_severity={sev: 1},
                        benchmarks_violated=[control, *nist],
                        auto_fix_pr_opened=auto_fixed,
                        auto_fix_pr_url=(
                            f"https://github.com/pragatig25/terraguard/pull/{200 + run_seq}"
                            if auto_fixed
                            else None
                        ),
                        scanner_findings={
                            "checkov": rng.randint(3, 9),
                            "tfsec": rng.randint(2, 6),
                            "trivy": rng.randint(4, 11),
                        },
                        duration_seconds=round(rng.uniform(45, 140), 1),
                    )
                )
                # Auto-fix improves posture a few hours later.
                if auto_fixed:
                    fix_ts = ts + timedelta(hours=rng.uniform(2, 6))
                    score = min(92.0, score + penalty * 0.55)
                    run_seq += 1
                    runs.append(
                        RunMetrics(
                            run_id=f"demo{run_seq:04d}",
                            timestamp=fix_ts,
                            git_sha=f"{rng.randrange(16**7):07x}",
                            branch="main",
                            pr_number=None,
                            event_type="merge",
                            posture_score_before=round(score - penalty * 0.6, 1),
                            posture_score_after=round(score, 1),
                            score_delta=round(penalty * 0.6, 1),
                            regressions_introduced=0,
                            regressions_by_severity={},
                            benchmarks_violated=[],
                            auto_fix_pr_opened=False,
                            scanner_findings={
                                "checkov": rng.randint(2, 5),
                                "tfsec": rng.randint(1, 4),
                                "trivy": rng.randint(3, 7),
                            },
                            duration_seconds=round(rng.uniform(40, 90), 1),
                        )
                    )
            else:
                # Clean PR: gradual improvement toward 92.
                score = min(92.0, score + rng.uniform(0.1, 0.7))
                runs.append(
                    RunMetrics(
                        run_id=f"demo{run_seq:04d}",
                        timestamp=ts,
                        git_sha=f"{rng.randrange(16**7):07x}",
                        branch=f"feat/demo-{run_seq}",
                        pr_number=100 + run_seq,
                        event_type="pr",
                        posture_score_before=before,
                        posture_score_after=round(score, 1),
                        score_delta=round(score - before, 1),
                        regressions_introduced=0,
                        regressions_by_severity={},
                        benchmarks_violated=[],
                        auto_fix_pr_opened=False,
                        scanner_findings={
                            "checkov": rng.randint(1, 4),
                            "tfsec": rng.randint(0, 3),
                            "trivy": rng.randint(2, 6),
                        },
                        duration_seconds=round(rng.uniform(40, 100), 1),
                    )
                )

    # Close on a clean main-branch merge so the hero reads healthy.
    final_before = round(score, 1)
    score = max(score, 88.0)
    run_seq += 1
    runs.append(
        RunMetrics(
            run_id=f"demo{run_seq:04d}",
            timestamp=now,
            git_sha=f"{rng.randrange(16**7):07x}",
            branch="main",
            pr_number=None,
            event_type="merge",
            posture_score_before=final_before,
            posture_score_after=round(score, 1),
            score_delta=round(score - final_before, 1),
            regressions_introduced=0,
            regressions_by_severity={},
            benchmarks_violated=[],
            auto_fix_pr_opened=False,
            scanner_findings={"checkov": 2, "tfsec": 1, "trivy": 3},
            duration_seconds=round(rng.uniform(40, 80), 1),
        )
    )
    return runs


def main() -> None:
    rng = random.Random(SEED)
    runs = generate(rng)
    dashboard = aggregate_dashboard(runs, controls_total=CONTROLS_TOTAL, demo=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        dashboard.model_dump_json(indent=2, by_alias=True), encoding="utf-8"
    )
    print(
        f"Wrote {OUTPUT} — {len(dashboard.runs)} runs, "
        f"current score {dashboard.current_posture_score}, "
        f"{dashboard.total_regressions_30d} regressions/30d, "
        f"{dashboard.total_auto_fixes_30d} auto-fixes/30d"
    )


if __name__ == "__main__":
    main()
