# 🛡️ TerraGuard

**Catch Terraform AWS security regressions before they ship.**

TerraGuard is an end-to-end security regression pipeline for Terraform. On every
pull request it scans the plan, compares findings against the `main` baseline to
detect *regressions* (not just absolute findings), runs pytest security
invariants, uses the Claude API to triage and remediate, opens auto-fix PRs, and
publishes a posture dashboard to GitHub Pages — all inside GitHub Actions, with
no AWS credentials and no external infrastructure.

🔗 **Live dashboard:** https://pragatig25.github.io/terraguard/
📦 **Repo:** https://github.com/pragatig25/terraguard

---

## What it does

| Stage | Detail |
|---|---|
| **Scan** | Checkov (authoritative, CIS/NIST-mapped) + tfsec + Trivy run statically (`terraform init -backend=false`) — no AWS access. |
| **Baseline diff** | Findings are diffed against `baseline/latest.json` (captured on `main`) to isolate *new* regressions. |
| **Posture score** | `100 − (20·crit + 10·high + 3·med + 1·low)`, clamped to `[0,100]`. |
| **Regression tests** | `pytest` security invariants per domain (networking, IAM, storage, compute, database, logging, secrets). `critical` markers block merge; `high` warn. |
| **AI triage** | Claude Haiku 4.5 explains each regression, scores exploitability, confirms CIS/NIST mapping, and flags auto-remediable findings (structured tool-use output). |
| **Auto-fix PR** | For auto-remediable findings, Claude generates a minimal HCL fix and a PR is opened against the contributor's branch. |
| **PR comment** | A rich posture report (score delta, regressions, benchmarks) is posted on the PR. All output is sanitized of IPs/CIDRs/ARNs/account IDs. |
| **Dashboard** | Real run metrics publish to `docs/data/` and deploy to GitHub Pages. A public **DEMO** mode shows synthetic data only. |

## Architecture

```
scanner/     Plan parsing, scanner wrappers, dedup, posture scoring, PR gate
regression/  pytest security-invariant suite (markers: critical / high / medium)
ai/          Claude triage + remediation + PR comment (Haiku 4.5, prompt-cached)
autopr/      Unified-diff patch generation + PR creation (PyGithub)
metrics/     RunMetrics + DashboardData schema, aggregation, publishing
benchmarks/  CIS AWS v1.5 + NIST 800-53 control data and rule→control mapping
demo/        Synthetic demo-data generator (DEMO mode)
docs/        Static GitHub Pages dashboard (no framework, no build step)
examples/    Example Terraform infrastructure (the scan target)
```

### Design note: why Checkov is authoritative

All three scanners run, but Checkov — restricted to a documented CIS/NIST-mapped
control set (`.checkov.yaml` + `benchmarks/mapping.json`) — is the engine that
drives the posture score, regression diff, and PR gate. tfsec and Trivy add
breadth (their raw counts are recorded in `scanner_counts`) but don't affect the
score. This keeps the score coherent and reproducible across tool versions
instead of swinging with each scanner's full, overlapping rule catalog.

## Local development

```bash
# Python 3.12 via uv (system Python may be too old)
uv venv --python 3.12 .venv
VIRTUAL_ENV=.venv uv pip install -r requirements-dev.txt
export PATH="$PWD/.venv/bin:$PATH"   # put checkov/pytest on PATH

# Capture a baseline from the example infra, then scan
python -m scanner.main --baseline-capture
python -m scanner.main

# Run the regression suite
pytest regression/ -m "critical or high" -v

# Unit tests
pytest tests/unit -v

# Regenerate demo data + preview the dashboard
python demo/generate_demo_data.py
python -m http.server --directory docs 8000   # → http://localhost:8000
```

Set `ANTHROPIC_API_KEY` (and optionally `GITHUB_TOKEN`) in a local `.env` to
exercise the AI triage / remediation / PR steps. Without a key, those steps
degrade to safe no-ops.

## GitHub Actions setup

Workflows:

- **`security-regression.yml`** — runs on PRs touching `*.tf`: scan → tests →
  triage → auto-fix PR → comment → gate.
- **`baseline-capture.yml`** — on push to `main`: updates the baseline and
  publishes a real LIVE dashboard data point.
- **`dashboard-deploy.yml`** — deploys `docs/` to GitHub Pages on `docs/**` change.
- **`demo-data-refresh.yml`** — nightly synthetic demo-data refresh.

### Secrets (Settings → Secrets and variables → Actions → Secrets)

| Secret | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes (for AI) | Claude API key for triage + remediation |
| `GITHUB_TOKEN` | Auto | Provided by Actions; used for PR creation/comments |

### Variables (Settings → Secrets and variables → Actions → Variables)

| Variable | Required | Description |
|---|---|---|
| `DASHBOARD_URL` | No | Full dashboard URL used in PR comments |
| `ENABLE_AUTO_FIX_PR` | No | Set to `false` to disable auto-fix PRs |
| `CUSTOM_DOMAIN` | No | Custom domain for GitHub Pages |

### Enable GitHub Pages

Settings → Pages → Source: **GitHub Actions**. The first `dashboard-deploy` run
(push to `main` or manual dispatch) publishes the site.

## Custom domain setup

1. In your DNS provider add a `CNAME` record: `terraguard` → `pragatig25.github.io`.
2. In repo Settings → Variables → Actions, set `CUSTOM_DOMAIN` = `terraguard.yourdomain.com`.
3. In repo Settings → Pages, set the custom domain and enable **Enforce HTTPS**.
4. Re-run the `dashboard-deploy` workflow.

## Security (public repo)

This repo is safe to keep public. All workflows are hardened against abuse:

| Protection | Where | What it does |
|---|---|---|
| **Fork PR blocked** | `security-regression.yml` | Job-level `if` checks `head.repo.full_name == github.repository` — fork PRs are silently skipped, so strangers cannot burn API credits or compute |
| **API key gated** | AI triage + auto-fix steps | Steps only run when `ANTHROPIC_API_KEY` secret is present; fork PRs never see secrets |
| **`workflow_dispatch` owner-only** | All 4 workflows | `github.actor == github.repository_owner` guard on manual triggers |
| **Push to `main` protected** | `baseline-capture.yml` | Only collaborators with write access can push to `main` |
| **No real AWS credentials** | Entire pipeline | Scans run `terraform init -backend=false` — purely static analysis |
| **PR comment sanitization** | `ai/pr_comment.py` | IPs, CIDRs, ARNs, and account IDs are stripped before posting |

### Recommended repo settings

After making the repo public, configure these in **Settings → Actions → General**:

1. **Fork pull request workflows** → "Require approval for first-time contributors"
2. **Workflow permissions** → "Read repository contents and packages permissions" (least privilege)
3. **Allow GitHub Actions to create and approve pull requests** → enabled (for auto-fix PRs)

## Demo mode & public safety

The public dashboard defaults to **DEMO** mode and renders only synthetic data
(`docs/data/demo.json`, flagged `"_demo": true`): fictional resource names, the
AWS documentation account id `123456789012`, and RFC 1918 ranges only. No real
AWS credentials, state, or scan results are ever exposed. PR comments are
additionally sanitized of IPs, CIDRs, ARNs, and account IDs.

## Try the regression demo

A branch that opens SSH to `0.0.0.0/0` and removes S3 encryption drops the
posture score 95 → 65, trips two regression tests (one CRITICAL, one HIGH),
and the gate blocks merge. See `examples/terraform/` and open a PR to watch the
pipeline run for real.

---

*Built with Checkov, tfsec, Trivy, pytest, Pydantic, and the Claude API.*
