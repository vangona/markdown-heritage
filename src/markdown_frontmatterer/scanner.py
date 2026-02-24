"""Recursive Markdown file scanner."""

from __future__ import annotations

from pathlib import Path


def scan_markdown_files(root: str | Path) -> list[Path]:
    """Recursively find all .md files under *root*, sorted by path."""
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"Directory not found: {root}")
    return sorted(root.rglob("*.md"))
