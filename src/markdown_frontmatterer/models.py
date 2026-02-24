"""Pydantic models for frontmatter schema."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Category = Literal[
    "technology", "personal", "work", "research", "creative", "reference", "other"
]
DocType = Literal[
    "journal", "note", "wiki", "meeting_notes", "reference", "tutorial", "essay", "log"
]


class Entity(BaseModel):
    name: str
    type: str


class Frontmatter(BaseModel):
    title: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    category: Category = "other"
    doc_type: DocType = "note"
    summary: str = ""
    entities: list[Entity] = Field(default_factory=list)
    related_topics: list[str] = Field(default_factory=list)
