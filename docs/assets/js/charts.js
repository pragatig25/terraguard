/* TerraGuard charts — Canvas-based gauge, timeline, and heatmap (warm theme). */
(function () {
  "use strict";

  function scoreColor(s) {
    if (s >= 90) return "#3F7D5B";
    if (s >= 70) return "#5A8FA8";
    if (s >= 50) return "#C9960A";
    return "#B23A36";
  }

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
    const start = Math.PI * 0.75, end = Math.PI * 2.25;
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
      ctx.beginPath();
      ctx.lineWidth = 12;
      ctx.lineCap = "round";
      ctx.strokeStyle = "#E7DFD1";
      ctx.arc(cx, cy, r, start, end);
      ctx.stroke();
      const a = start + (end - start) * (cur / 100);
      const grad = ctx.createLinearGradient(0, 0, size, size);
      grad.addColorStop(0, color);
      grad.addColorStop(1, "#C15F3C");
      ctx.beginPath();
      ctx.strokeStyle = grad;
      ctx.shadowColor = color;
      ctx.shadowBlur = 8;
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

    const zones = [
      [90, 100, "rgba(63,125,91,0.06)"],
      [70, 90, "rgba(90,143,168,0.06)"],
      [50, 70, "rgba(201,150,10,0.06)"],
      [40, 50, "rgba(178,58,54,0.06)"],
    ];
    zones.forEach(([lo, hi, c]) => {
      ctx.fillStyle = c;
      ctx.fillRect(padL, yFor(hi), plotW, yFor(lo) - yFor(hi));
    });

    ctx.fillStyle = "#6F6A60";
    ctx.font = "11px ui-monospace, SFMono-Regular, Menlo, monospace";
    [40, 60, 80, 100].forEach((v) => {
      const y = yFor(v);
      ctx.strokeStyle = "#E7DFD1";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(W - padR, y);
      ctx.stroke();
      ctx.fillText(String(v), 12, y + 3);
    });

    if (!trend.length) return;

    const pts = trend.map((p, i) => [xFor(i), yFor(p.score)]);
    const t0 = performance.now();
    const dur = 800;
    function frame(now) {
      const prog = Math.min(1, (now - t0) / dur);
      const shown = Math.max(2, Math.floor(pts.length * prog));
      ctx.clearRect(0, 0, W, H);
      zones.forEach(([lo, hi, c]) => { ctx.fillStyle = c; ctx.fillRect(padL, yFor(hi), plotW, yFor(lo) - yFor(hi)); });
      ctx.fillStyle = "#6F6A60";
      [40, 60, 80, 100].forEach((v) => {
        const y = yFor(v);
        ctx.strokeStyle = "#E7DFD1";
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
        ctx.fillText(String(v), 12, y + 3);
      });
      const seg = pts.slice(0, shown);
      const grad = ctx.createLinearGradient(0, padT, 0, H);
      grad.addColorStop(0, "rgba(193,95,60,0.18)");
      grad.addColorStop(1, "rgba(193,95,60,0.0)");
      ctx.beginPath();
      ctx.moveTo(seg[0][0], H - padB);
      seg.forEach(([x, y]) => ctx.lineTo(x, y));
      ctx.lineTo(seg[seg.length - 1][0], H - padB);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.beginPath();
      seg.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.strokeStyle = "#C15F3C";
      ctx.lineWidth = 2;
      ctx.stroke();
      trend.slice(0, shown).forEach((p, i) => {
        if (p.is_regression) {
          ctx.beginPath();
          ctx.arc(xFor(i), yFor(p.score), 3.5, 0, Math.PI * 2);
          ctx.fillStyle = "#B8762E";
          ctx.fill();
        }
      });
      if (prog < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function drawHeatmap(container, cells) {
    container.innerHTML = "";
    const byDate = {};
    cells.forEach((c) => (byDate[c.date] = c));
    const today = new Date();
    const sevColor = { CRITICAL: "#B23A36", HIGH: "#B8762E", MEDIUM: "#C9960A", LOW: "#3F7D5B" };

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
        const base = sevColor[hit.worst_severity] || "#C15F3C";
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
