"""Read, merge, and write YAML frontmatter for Markdown files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter

from markdown_frontmatterer.models import Frontmatter


def has_frontmatter(path: Path) -> bool:
    """Return True if the file already contains YAML frontmatter."""
    post = frontmatter.load(str(path))
    return bool(post.metadata)


def load_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    """Return (existing metadata dict, body content) from a Markdown file."""
    post = frontmatter.load(str(path))
    return dict(post.metadata), post.content


def merge_frontmatter(
    existing: dict[str, Any],
    generated: Frontmatter,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Merge *generated* frontmatter into *existing*.

    - Default: keep existing values, fill in missing fields only.
    - force=True: overwrite all fields except ``created_at``.
    """
    new = generated.model_dump(mode="json")

    if force:
        merged = {**existing, **new}
        # Always preserve original created_at
        if "created_at" in existing and existing["created_at"]:
            merged["created_at"] = existing["created_at"]
    else:
        merged = {**new, **existing}

    # Remove None / empty-string fields to keep the frontmatter clean
    return {k: v for k, v in merged.items() if v is not None and v != ""}


def save_frontmatter(path: Path, metadata: dict[str, Any], body: str) -> None:
    """Write *metadata* as YAML frontmatter + *body* back to *path*."""
    post = frontmatter.Post(body, **metadata)
    path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
