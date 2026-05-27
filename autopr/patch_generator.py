"""Generate unified-diff patches for auto-remediable findings."""

from __future__ import annotations

import difflib

from pydantic import BaseModel


class FilePatch(BaseModel):
    file_path: str
    original: str
    fixed: str
    diff_text: str
    rule_id: str
    resource: str


def generate_patch(
    rule_id: str,
    resource: str,
    file_path: str,
    original_block: str,
    fixed_block: str,
) -> FilePatch | None:
    """Build a FilePatch. Returns None if the fix is a no-op."""
    if original_block.strip() == fixed_block.strip():
        return None

    diff = difflib.unified_diff(
        original_block.splitlines(keepends=True),
        fixed_block.splitlines(keepends=True),
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="\n",
    )
    return FilePatch(
        file_path=file_path,
        original=original_block,
        fixed=fixed_block,
        diff_text="".join(diff),
        rule_id=rule_id,
        resource=resource,
    )


def apply_patch_to_text(content: str, patch: FilePatch) -> str:
    """Replace the original block with the fixed block in file content."""
    if patch.original not in content:
        raise ValueError(
            f"original block for {patch.rule_id} not found in {patch.file_path}"
        )
    return content.replace(patch.original, patch.fixed, 1)
