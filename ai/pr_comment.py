"""Format and post the rich TerraGuard PR comment.

All free text is sanitized to strip IPs, CIDRs, ARNs, and account IDs before it
is posted, even though demo data contains none — defense in depth for real use.
"""

from __future__ import annotations

import sys

import structlog

from ai.sanitize import safe_resource_name, sanitize
from scanner import config
from scanner.models import ScanResult, SecurityFinding, Severity

log = structlog.get_logger(__name__)

_SEV_EMOJI = {
    Severity.CRITICAL: "🔴",
    Severity.HIGH: "🟠",
    Severity.MEDIUM: "🟡",
    Severity.LOW: "🟢",
    Severity.INFO: "⚪",
}


def format_comment(
    result: ScanResult,
    score_delta: float,
    baseline_score: float,
    auto_fix_pr_url: str | None = None,
) -> str:
    regressions = [f for f in result.findings if f.is_regression]
    delta_icon = "⚠️" if score_delta < 0 else "✅"

    lines = [
        "## 🛡️ TerraGuard Security Report",
        "",
        f"**Posture Score**: {baseline_score:.1f} → {result.posture_score:.1f} "
        f"({score_delta:+.1f}) {delta_icon}",
        "",
    ]

    if not regressions:
        lines += [
            "✅ **No new security regressions detected.** Posture is maintained "
            "relative to the `main` baseline.",
        ]
    else:
        lines += [f"### Regressions Detected ({len(regressions)})", ""]
        lines += [
            "| Severity | Resource | Rule | Benchmark | Auto-Fix |",
            "|---|---|---|---|---|",
        ]
        for f in sorted(regressions, key=lambda x: -x.severity.weight):
            emoji = _SEV_EMOJI[f.severity]
            resource = safe_resource_name(f"{f.resource_type}.{f.resource_name}")
            benchmark = ", ".join(f.benchmark_controls) or "—"
            autofix = "✅" if f.auto_remediable else "—"
            lines.append(
                f"| {emoji} {f.severity.value} | `{resource}` | "
                f"`{f.rule_id}` | {benchmark} | {autofix} |"
            )
        lines.append("")

        if auto_fix_pr_url:
            lines += [f"**Auto-Fix PR**: {auto_fix_pr_url} has been opened.", ""]

        ai_analysis = _ai_details(regressions)
        if ai_analysis:
            lines += [
                "<details>",
                "<summary>View AI Analysis</summary>",
                "",
                ai_analysis,
                "</details>",
                "",
            ]

    critical = [f for f in regressions if f.severity == Severity.CRITICAL]
    if critical:
        lines += [
            "",
            f"> ⛔ **{len(critical)} CRITICAL regression(s)** — this gate blocks merge "
            "until resolved.",
        ]

    lines += [
        "",
        "---",
        f"*TerraGuard · [View Dashboard]({config.DASHBOARD_URL}) · "
        f"[Docs](https://github.com/{config.REPO})*",
    ]
    return "\n".join(lines)


def _ai_details(regressions: list[SecurityFinding]) -> str:
    blocks = []
    for f in regressions:
        if not f.plain_english:
            continue
        resource = safe_resource_name(f"{f.resource_type}.{f.resource_name}")
        detail = sanitize(f.plain_english)
        if f.blast_radius:
            detail += f" Blast radius: {sanitize(f.blast_radius)}"
        blocks.append(f"**{resource}**: {detail}")
    return "\n\n".join(blocks)


def post_comment(body: str, pr_number: int) -> None:
    """Post (or update) the TerraGuard comment on a PR via PyGithub."""
    if not config.GITHUB_TOKEN:
        log.warning("pr_comment_no_token")
        return
    from github import Github

    gh = Github(config.GITHUB_TOKEN)
    repo = gh.get_repo(config.REPO)
    pr = repo.get_issue(pr_number)

    marker = "## 🛡️ TerraGuard Security Report"
    for comment in pr.get_comments():
        if marker in comment.body:
            comment.edit(body)
            log.info("pr_comment_updated", pr=pr_number)
            return
    pr.create_comment(body)
    log.info("pr_comment_posted", pr=pr_number)


def main() -> int:
    config.configure_logging()
    try:
        result = ScanResult.model_validate_json(
            open(config.CURRENT_RESULTS, encoding="utf-8").read()
        )
    except FileNotFoundError:
        log.warning("pr_comment_no_results")
        return 0

    from scanner.baseline import load_baseline, score_delta

    baseline = load_baseline(config.BASELINE_PATH)
    baseline_score = baseline.posture_score if baseline else result.posture_score
    delta = score_delta(result, baseline)

    body = format_comment(result, delta, baseline_score)
    pr = config.pr_number()
    if pr is not None:
        post_comment(body, pr)
    else:
        log.info("pr_comment_no_pr_number", preview=body[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
