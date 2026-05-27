"""Extract a raw Terraform resource block from .tf files by (type, name).

Uses brace matching on the raw text so the returned block preserves the author's
exact formatting — important for minimal-diff remediations.
"""

from __future__ import annotations

import re
from pathlib import Path

_RESOURCE_RE = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{')


def find_resource_block(
    resource_type: str, resource_name: str, search_dir: str
) -> tuple[str, str] | None:
    """Return (file_path, block_text) for the first matching resource, else None."""
    for tf_file in sorted(Path(search_dir).rglob("*.tf")):
        text = tf_file.read_text(encoding="utf-8")
        for match in _RESOURCE_RE.finditer(text):
            if match.group(1) == resource_type and match.group(2) == resource_name:
                block = _extract_braced(text, match.start())
                if block is not None:
                    return str(tf_file), block
    return None


def _extract_braced(text: str, start: int) -> str | None:
    """Given the index of `resource`, return the full block including braces."""
    brace_open = text.find("{", start)
    if brace_open == -1:
        return None
    depth = 0
    for i in range(brace_open, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None
