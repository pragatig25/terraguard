/* TerraGuard dashboard renderer — maps DashboardData JSON into the DOM. */
(function () {
  "use strict";

  // CIS AWS Foundations v1.5 controls TerraGuard governs (mirrors
  // benchmarks/cis_aws_v1_5.json — embedded so the dashboard stays static).
  const CIS_CONTROLS = [
    ["1.16", "IAM policies on groups/roles"],
    ["1.20", "Secrets encrypted & rotated"],
    ["2.1.1", "S3 server-side encryption"],
    ["2.1.2", "S3 public access blocked"],
    ["2.2.1", "EBS volume encryption"],
    ["2.3.1", "RDS encryption at rest"],
    ["2.3.2", "RDS Multi-AZ"],
    ["2.3.3", "RDS not public"],
    ["3.1", "CloudTrail enabled"],
    ["3.8", "CloudTrail KMS encryption"],
    ["4.1", "No SSH from 0.0.0.0/0"],
    ["4.2", "No RDP from 0.0.0.0/0"],
    ["4.3", "Default SG restricts traffic"],
    ["5.2", "VPC flow logging"],
    ["5.6", "EC2 requires IMDSv2"],
  ];

  function relTime(iso) {
    const d = new Date(iso);
    const mins = Math.round((Date.now() - d.getTime()) / 60000);
    if (mins < 60) return `${Math.max(1, mins)}m ago`;
    const hrs = Math.round(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.round(hrs / 24);
    return `${days}d ago`;
  }

  function staggerCards() {
    document.querySelectorAll(".card").forEach((c, i) => {
      setTimeout(() => c.classList.add("in"), 80 + i * 60);
    });
  }

  function render(data) {
    const C = window.TGCharts;

    // Hero
    C.drawGauge(document.getElementById("gauge"), data.current_posture_score || 0);
    const trend = data.posture_trend || [];
    const trendEl = document.getElementById("hero-trend");
    let weekDelta = 0;
    if (trend.length > 1) {
      const recent = trend[trend.length - 1].score;
      const prior = trend[Math.max(0, trend.length - 8)].score;
      weekDelta = recent - prior;
    }
    trendEl.textContent = (weekDelta >= 0 ? "↑ +" : "↓ ") + weekDelta.toFixed(1) + " from last week";
    trendEl.className = "trend " + (weekDelta >= 0 ? "up" : "down");
    document.getElementById("hero-when").textContent = data.last_updated ? relTime(data.last_updated) : "—";

    // Metrics
    document.getElementById("m-reg").textContent = data.total_regressions_30d ?? 0;
    document.getElementById("m-fix").textContent = data.total_auto_fixes_30d ?? 0;
    const autoRate = data.total_regressions_30d
      ? Math.round((data.total_auto_fixes_30d / data.total_regressions_30d) * 100)
      : 0;
    document.getElementById("m-fix-sub").textContent = `${autoRate}% auto-rate`;
    document.getElementById("m-ctrl").textContent = `${data.controls_tested ?? 0}/${data.controls_total ?? 0}`;
    document.getElementById("m-mttr").textContent = (data.mean_time_to_remediate_hours ?? 0).toFixed(1);
    staggerCards();

    // Timeline + heatmap
    C.drawTimeline(document.getElementById("timeline"), trend);
    C.drawHeatmap(document.getElementById("heatmap"), data.regression_heatmap || []);

    // Benchmark coverage
    const violated = new Set((data.top_violated_controls || []).map((c) => c.control));
    const cisBody = document.getElementById("cis-body");
    cisBody.innerHTML = CIS_CONTROLS.map(([id, desc]) => {
      const warn = violated.has("CIS " + id);
      const pill = warn
        ? '<span class="pill warn">⚠ Warn</span>'
        : '<span class="pill pass">✓ Pass</span>';
      return `<tr><td class="mono">${id}</td><td>${desc}</td><td>${pill}</td></tr>`;
    }).join("");

    const topBody = document.getElementById("top-body");
    const tops = data.top_violated_controls || [];
    topBody.innerHTML = tops.length
      ? tops.map((c) => `<tr><td class="mono">${c.control}</td><td class="mono">${c.count}</td></tr>`).join("")
      : '<tr><td class="muted" colspan="2">No violations in the last 30 days</td></tr>';

    // Recent runs (last 10, newest first)
    const runs = (data.runs || []).slice(-10).reverse();
    const runsBody = document.getElementById("runs-body");
    runsBody.innerHTML = runs.map((r) => {
      const color = C.scoreColor(r.posture_score_after);
      const badge = `<span class="score-badge" style="color:${color};border-color:${color}55;background:${color}14">${r.posture_score_after.toFixed(1)}</span>`;
      const delta = r.score_delta === 0
        ? '<span class="muted">+0.0</span>'
        : (r.score_delta > 0
            ? `<span style="color:var(--status-pass)">+${r.score_delta.toFixed(1)}</span>`
            : `<span style="color:var(--status-high)">${r.score_delta.toFixed(1)} ⚠</span>`);
      const reg = r.regressions_introduced > 0
        ? `${r.regressions_introduced} ${Object.keys(r.regressions_by_severity || {}).join(", ")}`
        : '<span class="muted">0</span>';
      const fix = r.auto_fix_pr_opened
        ? (r.auto_fix_pr_url ? `<a href="${r.auto_fix_pr_url}" target="_blank" rel="noopener" style="color:var(--status-pass)">✓ PR</a>` : "✓")
        : '<span class="muted">—</span>';
      return `<tr><td>${relTime(r.timestamp)}</td><td class="mono">${r.branch || "—"}</td><td>${badge}</td><td class="mono">${delta}</td><td>${reg}</td><td>${fix}</td></tr>`;
    }).join("");
  }

  window.TG = window.TG || {};
  window.TG.render = render;
})();
