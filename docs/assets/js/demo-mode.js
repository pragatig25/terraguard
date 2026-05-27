/* TerraGuard demo/live mode toggle + data loading. Defaults to DEMO (safe). */
(function () {
  "use strict";

  const DEMO_URL = "./data/demo.json";
  const LIVE_URL = "./data/dashboard.json";

  let isDemo = true;

  async function load() {
    const url = isDemo ? DEMO_URL : LIVE_URL;
    try {
      const res = await fetch(url + "?t=" + Date.now());
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      window.TG.render(data);
    } catch (err) {
      if (!isDemo) {
        // LIVE data not present (no pipeline runs yet) — guide the user.
        renderEmptyLive();
      } else {
        console.error("Failed to load demo data", err);
      }
    }
  }

  function renderEmptyLive() {
    document.getElementById("hero-score").textContent = "—";
    document.getElementById("hero-trend").textContent = "awaiting first pipeline run";
    document.getElementById("hero-trend").className = "trend";
    ["m-reg", "m-fix", "m-ctrl", "m-mttr"].forEach((id) => {
      document.getElementById(id).textContent = "—";
    });
    document.getElementById("runs-body").innerHTML =
      '<tr><td class="muted" colspan="6">No live runs yet. Merge a PR to populate this dashboard.</td></tr>';
  }

  function setMode(demo) {
    isDemo = demo;
    document.getElementById("btn-demo").classList.toggle("active", demo);
    document.getElementById("btn-live").classList.toggle("active", !demo);
    document.getElementById("mode-banner").style.display = demo ? "none" : "block";
    document.getElementById("safety-note").textContent = demo
      ? "Demo mode: synthetic data only · No real AWS credentials used"
      : "Live mode: real pipeline runs from this repository";
    load();
  }

  window.TG = window.TG || {};
  window.TG.setMode = setMode;

  document.addEventListener("DOMContentLoaded", () => setMode(true));
  window.addEventListener("resize", () => {
    // Redraw the timeline on resize (it is width-responsive).
    load();
  });
})();
