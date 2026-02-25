"""Prompt templates for the 2-phase query pipeline."""

from __future__ import annotations

SELECTION_SYSTEM_PROMPT = """\
You are a document librarian. Given a catalog of documents (with metadata or previews) \
and a user query, select the documents most relevant to answering the query.

Rules:
- Select the MINIMUM number of documents needed to fully answer the query.
- Never select more than {max_docs} documents.
- If the query is about summarising or categorising the whole collection, \
select a representative sample across categories.
- Return JSON with exactly two keys:
  "reasoning" — a brief chain-of-thought explaining your selection logic.
  "selected_paths" — a list of relative file paths from the catalog.
"""

DEFAULT_QUERY = (
    "이 문서 컬렉션을 카테고리별로 정리하고 주요 내용을 요약해줘. "
    "Organise this document collection by category and summarise the key content."
)

ANALYSIS_SYSTEM_PROMPT = """\
You are a knowledgeable research assistant. You are given a set of documents and a user query.

Instructions:
- Answer the query based ONLY on the provided documents.
- Use markdown formatting for readability (headers, lists, bold, etc.).
- Match the language of your answer to the user's query language.
- At the end, list every document you referenced.
- Return JSON with exactly two keys:
  "answer" — your full markdown-formatted answer.
  "sources" — a list of objects, each with "path", "title", and "relevance" keys.

Collection overview (for context — you may only cite documents provided in full below):
{catalog_summary}
"""


def build_catalog_prompt(
    catalog_text: str,
    query: str,
    max_docs: int,
) -> list[dict[str, str]]:
    """Build the messages list for the document selection phase."""
    return [
        {
            "role": "system",
            "content": SELECTION_SYSTEM_PROMPT.format(max_docs=max_docs),
        },
        {
            "role": "user",
            "content": f"## User Query\n{query}\n\n## Document Catalog\n{catalog_text}",
        },
    ]


def build_analysis_prompt(
    documents_text: str,
    query: str,
    catalog_summary: str,
) -> list[dict[str, str]]:
    """Build the messages list for the analysis/answer phase."""
    return [
        {
            "role": "system",
            "content": ANALYSIS_SYSTEM_PROMPT.format(catalog_summary=catalog_summary),
        },
        {
            "role": "user",
            "content": f"## User Query\n{query}\n\n## Documents\n{documents_text}",
        },
    ]
