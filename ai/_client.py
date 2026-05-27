"""Shared Anthropic client helpers for the TerraGuard AI layer.

Notes on model behavior (verified against the Anthropic API):
- The default model is Claude Haiku 4.5 (`claude-haiku-4-5`) — cheap and fast,
  appropriate for high-volume per-finding triage. Haiku accepts `temperature`.
- The system prompt is sent with `cache_control` so repeated calls within a run
  reuse the cached prefix (prompt caching), cutting token cost on multi-finding PRs.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import structlog

from scanner import config

log = structlog.get_logger(__name__)

_PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
# Low temperature for deterministic-ish security analysis (Haiku supports it).
TRIAGE_TEMPERATURE = 0.2
MAX_TOKENS = 1024


@lru_cache(maxsize=8)
def load_prompt(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def get_client():
    """Return an Anthropic client, or None if no API key is configured."""
    if not config.ANTHROPIC_API_KEY:
        log.warning("anthropic_no_key")
        return None
    import anthropic

    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def cached_system(text: str) -> list[dict]:
    """System prompt block with prompt-cache control on the static prefix."""
    return [
        {
            "type": "text",
            "text": text,
            "cache_control": {"type": "ephemeral"},
        }
    ]
