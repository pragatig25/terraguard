"""Centralized environment configuration for TerraGuard runtime."""

from __future__ import annotations

import logging
import os

import structlog
from dotenv import load_dotenv

load_dotenv()

# --- Paths (overridable via env; defaults match the workflow) ---
SCAN_DIR = os.getenv("TERRAGUARD_SCAN_DIR", "examples/terraform")
BASELINE_PATH = os.getenv("TERRAGUARD_BASELINE", "baseline/latest.json")
OUTPUT_PATH = os.getenv("TERRAGUARD_OUTPUT", "/tmp/terraguard_results.json")
CURRENT_RESULTS = os.getenv("TERRAGUARD_CURRENT_RESULTS", OUTPUT_PATH)
PLAN_JSON = os.getenv("TERRAGUARD_PLAN_JSON", "")
PYTEST_REPORT = os.getenv("PYTEST_REPORT", "/tmp/pytest_report.json")

# --- GitHub / CI context ---
REPO = os.getenv(
    "TERRAGUARD_REPO", os.getenv("GITHUB_REPOSITORY", "pragatig25/terraguard")
)
GIT_SHA = os.getenv("GIT_SHA", os.getenv("GITHUB_SHA", ""))
BRANCH = os.getenv("BRANCH", os.getenv("GITHUB_HEAD_REF", ""))
PR_NUMBER_RAW = os.getenv("PR_NUMBER", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# --- AI ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("TERRAGUARD_MODEL", "claude-haiku-4-5")

# --- Feature flags ---
ENABLE_AUTO_FIX_PR = os.getenv("ENABLE_AUTO_FIX_PR", "true").lower() != "false"
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "https://pragatig25.github.io/terraguard/")


def pr_number() -> int | None:
    try:
        return int(PR_NUMBER_RAW) if PR_NUMBER_RAW else None
    except ValueError:
        return None


def configure_logging() -> None:
    """JSON structured logs to stderr; never use print() in modules."""
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
    )
