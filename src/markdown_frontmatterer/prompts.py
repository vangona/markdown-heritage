"""LLM prompt templates for frontmatter generation."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are a document metadata analyst. Given a Markdown document, extract structured metadata and return it as JSON.

You MUST return a JSON object with exactly these fields:
{
  "title": "Document title (infer from heading or content)",
  "tags": ["keyword1", "keyword2"],
  "category": "one of: technology, personal, work, research, creative, reference, other",
  "doc_type": "one of: journal, note, wiki, meeting_notes, reference, tutorial, essay, log",
  "summary": "1-2 sentence summary of the document",
  "entities": [{"name": "Entity Name", "type": "person|organization|technology|place|event|other"}],
  "related_topics": ["topic1", "topic2"]
}

Rules:
- tags: lowercase, hyphenated (e.g. "web-scraping"), 3-7 tags
- category: choose the single best fit
- doc_type: choose the single best fit
- title, summary, entities, related_topics: use the same language as the document
- summary: concise, 1-2 sentences
- entities: extract notable people, organizations, technologies, places mentioned
- related_topics: broader themes this document relates to, 2-5 topics
- Return ONLY valid JSON, no markdown fences, no extra text
"""


def build_user_prompt(content: str, *, max_chars: int = 12_000) -> str:
    """Build the user message with truncated document content."""
    truncated = content[:max_chars]
    if len(content) > max_chars:
        truncated += "\n\n[... truncated ...]"
    return f"Analyze the following Markdown document and extract metadata:\n\n{truncated}"
