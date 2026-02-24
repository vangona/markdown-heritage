"""Tests for scanner module."""

from __future__ import annotations

from pathlib import Path

import pytest

from markdown_frontmatterer.scanner import scan_markdown_files


def test_scan_finds_md_files(tmp_md: Path) -> None:
    files = scan_markdown_files(tmp_md)
    names = {f.name for f in files}
    assert "sample_no_frontmatter.md" in names
    assert "sample_with_frontmatter.md" in names
    assert "sample_journal.md" in names


def test_scan_recursive(tmp_path: Path) -> None:
    sub = tmp_path / "sub" / "deep"
    sub.mkdir(parents=True)
    (sub / "nested.md").write_text("# Nested")
    (tmp_path / "top.md").write_text("# Top")

    files = scan_markdown_files(tmp_path)
    names = [f.name for f in files]
    assert "top.md" in names
    assert "nested.md" in names


def test_scan_nonexistent_dir() -> None:
    with pytest.raises(FileNotFoundError):
        scan_markdown_files("/nonexistent/path")
