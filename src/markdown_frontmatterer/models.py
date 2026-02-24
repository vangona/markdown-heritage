"""Pydantic models for frontmatter schema."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, BeforeValidator, Field


Category = Literal[
    "technology", "personal", "work", "research", "creative", "reference", "other"
]
DocType = Literal[
    "journal", "note", "wiki", "meeting_notes", "reference", "tutorial", "essay", "log"
]

_DOC_TYPE_ALIASES: dict[str, str] = {
    "guide": "tutorial",
    "how-to": "tutorial",
    "howto": "tutorial",
    "blog": "essay",
    "article": "essay",
    "post": "essay",
    "diary": "journal",
    "memo": "note",
    "meeting": "meeting_notes",
    "minutes": "meeting_notes",
    "documentation": "wiki",
    "docs": "wiki",
    "doc": "wiki",
    "ref": "reference",
    "changelog": "log",
    "history": "log",
}

_CATEGORY_ALIASES: dict[str, str] = {
    "tech": "technology",
    "dev": "technology",
    "development": "technology",
    "programming": "technology",
    "science": "research",
    "academic": "research",
    "study": "research",
    "business": "work",
    "career": "work",
    "professional": "work",
    "life": "personal",
    "diary": "personal",
    "art": "creative",
    "writing": "creative",
    "design": "creative",
    "ref": "reference",
    "docs": "reference",
}

_VALID_DOC_TYPES: set[str] = set(get_args(DocType))
_VALID_CATEGORIES: set[str] = set(get_args(Category))


def _coerce_doc_type(v: object) -> str:
    if not isinstance(v, str):
        return "note"
    v = v.strip().lower().replace(" ", "_")
    if v in _VALID_DOC_TYPES:
        return v
    return _DOC_TYPE_ALIASES.get(v, "note")


def _coerce_category(v: object) -> str:
    if not isinstance(v, str):
        return "other"
    v = v.strip().lower().replace(" ", "_")
    if v in _VALID_CATEGORIES:
        return v
    return _CATEGORY_ALIASES.get(v, "other")


class Entity(BaseModel):
    name: str
    type: str


class Frontmatter(BaseModel):
    title: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    category: Annotated[Category, BeforeValidator(_coerce_category)] = "other"
    doc_type: Annotated[DocType, BeforeValidator(_coerce_doc_type)] = "note"
    summary: str = ""
    entities: list[Entity] = Field(default_factory=list)
    related_topics: list[str] = Field(default_factory=list)
