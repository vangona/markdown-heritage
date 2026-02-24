"""Tests for Pydantic model validators (BeforeValidator enum coercion)."""

from __future__ import annotations

import pytest

from markdown_frontmatterer.models import Frontmatter


class TestDocTypeCoercion:
    def test_valid_value_passes_through(self) -> None:
        fm = Frontmatter(doc_type="tutorial")
        assert fm.doc_type == "tutorial"

    @pytest.mark.parametrize(
        ("alias", "expected"),
        [
            ("guide", "tutorial"),
            ("how-to", "tutorial"),
            ("blog", "essay"),
            ("article", "essay"),
            ("diary", "journal"),
            ("memo", "note"),
            ("meeting", "meeting_notes"),
            ("documentation", "wiki"),
        ],
    )
    def test_alias_corrected(self, alias: str, expected: str) -> None:
        fm = Frontmatter(doc_type=alias)
        assert fm.doc_type == expected

    def test_unknown_value_falls_back_to_note(self) -> None:
        fm = Frontmatter(doc_type="completely_unknown")
        assert fm.doc_type == "note"

    def test_whitespace_and_casing_normalized(self) -> None:
        fm = Frontmatter(doc_type=" Tutorial ")
        assert fm.doc_type == "tutorial"


class TestCategoryCoercion:
    def test_valid_value_passes_through(self) -> None:
        fm = Frontmatter(category="technology")
        assert fm.category == "technology"

    @pytest.mark.parametrize(
        ("alias", "expected"),
        [
            ("tech", "technology"),
            ("dev", "technology"),
            ("science", "research"),
            ("business", "work"),
            ("life", "personal"),
            ("art", "creative"),
        ],
    )
    def test_alias_corrected(self, alias: str, expected: str) -> None:
        fm = Frontmatter(category=alias)
        assert fm.category == expected

    def test_unknown_value_falls_back_to_other(self) -> None:
        fm = Frontmatter(category="nonexistent")
        assert fm.category == "other"


class TestModelValidateJson:
    def test_coercion_works_via_json(self) -> None:
        raw = '{"doc_type": "guide", "category": "tech"}'
        fm = Frontmatter.model_validate_json(raw)
        assert fm.doc_type == "tutorial"
        assert fm.category == "technology"
