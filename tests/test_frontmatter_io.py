"""Tests for frontmatter_io module."""

from __future__ import annotations

from pathlib import Path

from markdown_frontmatterer.frontmatter_io import (
    load_frontmatter,
    merge_frontmatter,
    save_frontmatter,
)
from markdown_frontmatterer.models import Entity, Frontmatter


def test_load_no_frontmatter(tmp_md: Path) -> None:
    meta, body = load_frontmatter(tmp_md / "sample_no_frontmatter.md")
    assert meta == {}
    assert "비동기 프로그래밍" in body


def test_load_with_frontmatter(tmp_md: Path) -> None:
    meta, body = load_frontmatter(tmp_md / "sample_with_frontmatter.md")
    assert meta["title"] == "기존 제목"
    assert meta["tags"] == ["python", "tutorial"]
    assert "기존 문서" in body


def test_merge_default_keeps_existing() -> None:
    existing = {"title": "원래 제목", "tags": ["python"]}
    generated = Frontmatter(
        title="AI가 생성한 제목",
        tags=["python", "async"],
        category="technology",
        summary="테스트 요약",
    )
    result = merge_frontmatter(existing, generated)
    assert result["title"] == "원래 제목"
    assert result["tags"] == ["python"]
    assert result["category"] == "technology"
    assert result["summary"] == "테스트 요약"


def test_merge_force_overwrites() -> None:
    existing = {"title": "원래 제목", "tags": ["python"], "created_at": "2024-01-01T00:00:00"}
    generated = Frontmatter(
        title="AI가 생성한 제목",
        tags=["python", "async"],
        category="technology",
    )
    result = merge_frontmatter(existing, generated, force=True)
    assert result["title"] == "AI가 생성한 제목"
    assert result["tags"] == ["python", "async"]
    # created_at preserved even with force
    assert result["created_at"] == "2024-01-01T00:00:00"


def test_merge_strips_empty_values() -> None:
    generated = Frontmatter(title="제목", summary="")
    result = merge_frontmatter({}, generated)
    assert "summary" not in result
    assert result["title"] == "제목"


def test_save_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "test.md"
    meta = {"title": "Test", "tags": ["a", "b"]}
    body = "# Hello\n\nContent here."
    save_frontmatter(path, meta, body)

    loaded_meta, loaded_body = load_frontmatter(path)
    assert loaded_meta["title"] == "Test"
    assert loaded_meta["tags"] == ["a", "b"]
    assert "Content here." in loaded_body
