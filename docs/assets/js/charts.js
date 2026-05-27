/* TerraGuard charts — Canvas-based gauge, timeline, and heatmap. No dependencies. */
(function () {
  "use strict";

  function scoreColor(s) {
    if (s >= 90) return "#00C896";
    if (s >= 70) return "#7CB9E8";
    if (s >= 50) return "#FFD700";
    return "#FF4444";
  }

  // Radial gauge with a count-up animation.
  function drawGauge(canvas, target) {
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const size = 220;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = size + "px";
    canvas.style.height = size + "px";
    ctx.scale(dpr, dpr);
    const cx = size / 2, cy = size / 2, r = 88;
    const start = Math.PI * 0.75, end = Math.PI * 2.25; // 270° arc
    const color = scoreColor(target);
    const scoreEl = document.getElementById("hero-score");

    let cur = 0;
    const t0 = performance.now();
    const dur = 1200;
    function frame(now) {
      const p = Math.min(1, (now - t0) / dur);
      const ease = 1 - Math.pow(1 - p, 3);
      cur = target * ease;
      ctx.clearRect(0, 0, size, size);
      // track
      ctx.beginPath();
      ctx.lineWidth = 12;
      ctx.lineCap = "round";
      ctx.strokeStyle = "rgba(255,255,255,0.06)";
      ctx.arc(cx, cy, r, start, end);
      ctx.stroke();
      // value arc
      const a = start + (end - start) * (cur / 100);
      const grad = ctx.createLinearGradient(0, 0, size, size);
      grad.addColorStop(0, color);
      grad.addColorStop(1, "#E8602C");
      ctx.beginPath();
      ctx.strokeStyle = grad;
      ctx.shadowColor = color;
      ctx.shadowBlur = 12;
      ctx.arc(cx, cy, r, start, a);
      ctx.stroke();
      ctx.shadowBlur = 0;
      if (scoreEl) {
        scoreEl.textContent = cur.toFixed(1);
        scoreEl.style.color = color;
      }
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  // Posture timeline line chart with colored zones + regression dots.
  function drawTimeline(canvas, trend) {
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const W = canvas.clientWidth || 1000;
    const H = 280;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, W, H);

    const padL = 40, padR = 16, padT = 16, padB = 28;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const yMin = 40, yMax = 100;
    const xFor = (i) => padL + (trend.length <= 1 ? 0 : (i / (trend.length - 1)) * plotW);
    const yFor = (v) => padT + (1 - (v - yMin) / (yMax - yMin)) * plotH;

    // zone bands
    const zones = [
      [90, 100, "rgba(0,200,150,0.06)"],
      [70, 90, "rgba(124,185,232,0.05)"],
      [50, 70, "rgba(255,215,0,0.05)"],
      [40, 50, "rgba(255,68,68,0.05)"],
    ];
    zones.forEach(([lo, hi, c]) => {
      ctx.fillStyle = c;
      ctx.fillRect(padL, yFor(hi), plotW, yFor(lo) - yFor(hi));
    });

    // y gridlines
    ctx.fillStyle = "#71717a";
    ctx.font = "11px 'DM Mono', monospace";
    [40, 60, 80, 100].forEach((v) => {
      const y = yFor(v);
      ctx.strokeStyle = "rgba(255,255,255,0.05)";
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(W - padR, y);
      ctx.stroke();
      ctx.fillText(String(v), 12, y + 3);
    });

    if (!trend.length) return;

    // area fill + line, drawn left-to-right
    const pts = trend.map((p, i) => [xFor(i), yFor(p.score)]);
    const t0 = performance.now();
    const dur = 800;
    function frame(now) {
      const prog = Math.min(1, (now - t0) / dur);
      const shown = Math.max(2, Math.floor(pts.length * prog));
      ctx.clearRect(0, 0, W, H);
      zones.forEach(([lo, hi, c]) => { ctx.fillStyle = c; ctx.fillRect(padL, yFor(hi), plotW, yFor(lo) - yFor(hi)); });
      ctx.fillStyle = "#71717a";
      [40, 60, 80, 100].forEach((v) => {
        const y = yFor(v);
        ctx.strokeStyle = "rgba(255,255,255,0.05)";
        ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
        ctx.fillText(String(v), 12, y + 3);
      });
      const seg = pts.slice(0, shown);
      // area
      const grad = ctx.createLinearGradient(0, padT, 0, H);
      grad.addColorStop(0, "rgba(232,96,44,0.28)");
      grad.addColorStop(1, "rgba(232,96,44,0.0)");
      ctx.beginPath();
      ctx.moveTo(seg[0][0], H - padB);
      seg.forEach(([x, y]) => ctx.lineTo(x, y));
      ctx.lineTo(seg[seg.length - 1][0], H - padB);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();
      // line
      ctx.beginPath();
      seg.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.strokeStyle = "#E8602C";
      ctx.lineWidth = 2;
      ctx.stroke();
      // regression dots
      trend.slice(0, shown).forEach((p, i) => {
        if (p.is_regression) {
          ctx.beginPath();
          ctx.arc(xFor(i), yFor(p.score), 3.5, 0, Math.PI * 2);
          ctx.fillStyle = "#FF8C00";
          ctx.fill();
        }
      });
      if (prog < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  // GitHub-style contribution heatmap (52 weeks x 7 days).
  function drawHeatmap(container, cells) {
    container.innerHTML = "";
    const byDate = {};
    cells.forEach((c) => (byDate[c.date] = c));
    const today = new Date();
    const sevColor = { CRITICAL: "#FF4444", HIGH: "#FF8C00", MEDIUM: "#FFD700", LOW: "#4CAF50" };

    // Build 53 weeks back, aligned to weeks.
    const days = [];
    for (let i = 364; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      days.push(d);
    }
    let week = document.createElement("div");
    week.className = "hm-week";
    days.forEach((d, idx) => {
      const iso = d.toISOString().slice(0, 10);
      const cell = document.createElement("div");
      cell.className = "hm-cell";
      const hit = byDate[iso];
      if (hit && hit.count > 0) {
        const base = sevColor[hit.worst_severity] || "#E8602C";
        const op = Math.min(1, 0.35 + hit.count * 0.22);
        cell.style.background = hexAlpha(base, op);
        cell.title = `${iso}: ${hit.count} regression(s)` + (hit.worst_severity ? ` · worst ${hit.worst_severity}` : "");
      } else {
        cell.title = `${iso}: no regressions`;
      }
      week.appendChild(cell);
      if (d.getDay() === 6 || idx === days.length - 1) {
        container.appendChild(week);
        week = document.createElement("div");
        week.className = "hm-week";
      }
    });
  }

  function hexAlpha(hex, a) {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  }

  window.TGCharts = { drawGauge, drawTimeline, drawHeatmap, scoreColor };
})();
