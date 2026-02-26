"""LLM prompt templates for frontmatter generation."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

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


VISION_SYSTEM_PROMPT = """\
You are a document metadata analyst. Given a Markdown document and its associated images, extract structured metadata and return it as JSON.

You MUST return a JSON object with exactly these fields:
{
  "title": "Document title (infer from heading, content, or images)",
  "tags": ["keyword1", "keyword2"],
  "category": "one of: technology, personal, work, research, creative, reference, other",
  "doc_type": "one of: journal, note, wiki, meeting_notes, reference, tutorial, essay, log",
  "summary": "1-2 sentence summary incorporating both text and image content",
  "entities": [{"name": "Entity Name", "type": "person|organization|technology|place|event|other"}],
  "related_topics": ["topic1", "topic2"],
  "image_description": "Concise visual description of the key image content"
}

Rules:
- tags: lowercase, hyphenated (e.g. "web-scraping"), 3-7 tags. Include visual elements from images (e.g. "sunset", "portrait", "food")
- category: choose the single best fit
- doc_type: choose the single best fit
- title, summary, entities, related_topics, image_description: use the same language as the document
- summary: concise, 1-2 sentences. Reflect both text and image content
- entities: extract notable people, organizations, technologies, places from text AND images
- related_topics: broader themes this document relates to, 2-5 topics
- image_description: describe the main visual elements, scene, mood, and notable objects in the images. 1-2 sentences
- Return ONLY valid JSON, no markdown fences, no extra text
"""


def _encode_image(path: Path) -> tuple[str, str]:
    """Return (base64_data, mime_type) for a local image file."""
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        mime = "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return data, mime


def build_vision_user_content(
    content: str,
    image_paths: list[Path],
    *,
    max_chars: int = 12_000,
    detail: str = "low",
) -> list[dict]:
    """Build multimodal user content array with text + base64 image_url entries."""
    truncated = content[:max_chars]
    if len(content) > max_chars:
        truncated += "\n\n[... truncated ...]"

    parts: list[dict] = [
        {
            "type": "text",
            "text": f"Analyze the following Markdown document and its images, then extract metadata:\n\n{truncated}",
        },
    ]

    for img_path in image_paths:
        b64_data, mime = _encode_image(img_path)
        parts.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime};base64,{b64_data}",
                "detail": detail,
            },
        })

    return parts
