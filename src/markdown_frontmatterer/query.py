"""Query orchestrator — 2-phase LLM pipeline for document analysis."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from markdown_frontmatterer.config import Settings
from markdown_frontmatterer.frontmatter_io import load_frontmatter
from markdown_frontmatterer.llm import LLMClient
from markdown_frontmatterer.query_models import DocumentSelection, QueryAnswer
from markdown_frontmatterer.query_prompts import (
    DEFAULT_QUERY,
    build_analysis_prompt,
    build_catalog_prompt,
)
from markdown_frontmatterer.scanner import scan_markdown_files

logger = logging.getLogger(__name__)

# ── Token budget constants ───────────────────────────────────────
CHARS_PER_TOKEN = 4
PREVIEW_CHARS = 500
MAX_CATALOG_TOKENS = 30_000
MAX_ANALYSIS_TOKENS = 80_000
SAFETY_MARGIN = 0.7
MIN_DOCS = 3
MAX_DOCS = 20


# ── Data structures ─────────────────────────────────────────────

@dataclass
class CatalogEntry:
    path: Path
    relative_path: str
    has_frontmatter: bool
    title: str = ""
    tags: list[str] = field(default_factory=list)
    category: str = ""
    doc_type: str = ""
    summary: str = ""
    entities: list[dict[str, str]] = field(default_factory=list)
    related_topics: list[str] = field(default_factory=list)
    preview: str = ""
    file_size: int = 0

    def to_catalog_text(self) -> str:
        """Compact text representation for the LLM catalog."""
        lines = [f"### {self.relative_path}"]
        if self.title:
            lines.append(f"- title: {self.title}")
        if self.tags:
            lines.append(f"- tags: {', '.join(self.tags)}")
        if self.category:
            lines.append(f"- category: {self.category}")
        if self.doc_type:
            lines.append(f"- doc_type: {self.doc_type}")
        if self.summary:
            lines.append(f"- summary: {self.summary}")
        if self.entities:
            names = [f"{e['name']} ({e['type']})" for e in self.entities]
            lines.append(f"- entities: {', '.join(names)}")
        if self.related_topics:
            lines.append(f"- related_topics: {', '.join(self.related_topics)}")
        if self.preview:
            lines.append(f"- preview: {self.preview[:200]}...")
        return "\n".join(lines)


@dataclass
class QueryResult:
    answer: str
    sources: list[dict[str, str]]
    total_files_scanned: int
    files_with_frontmatter: int
    files_read_in_full: int
    catalog_tokens_est: int
    analysis_tokens_est: int


# ── Core functions ───────────────────────────────────────────────

def build_catalog(root: Path, files: list[Path]) -> list[CatalogEntry]:
    """Build a metadata catalog from markdown files (no LLM calls)."""
    catalog: list[CatalogEntry] = []
    for f in files:
        try:
            metadata, body = load_frontmatter(f)
        except Exception:
            logger.warning("Failed to read %s, skipping", f)
            continue

        relative = str(f.relative_to(root))
        has_fm = bool(metadata)

        entry = CatalogEntry(
            path=f,
            relative_path=relative,
            has_frontmatter=has_fm,
            file_size=f.stat().st_size,
        )

        if has_fm:
            entry.title = metadata.get("title", "")
            entry.tags = metadata.get("tags", []) or []
            entry.category = metadata.get("category", "")
            entry.doc_type = metadata.get("doc_type", "")
            entry.summary = metadata.get("summary", "")
            raw_entities = metadata.get("entities", []) or []
            entry.entities = [
                {"name": e.get("name", ""), "type": e.get("type", "")}
                for e in raw_entities
                if isinstance(e, dict)
            ]
            entry.related_topics = metadata.get("related_topics", []) or []
        else:
            entry.preview = body[:PREVIEW_CHARS].strip()

        catalog.append(entry)

    return catalog


def format_catalog(catalog: list[CatalogEntry], max_tokens: int = MAX_CATALOG_TOKENS) -> str:
    """Format the catalog as text, prioritising entries with frontmatter."""
    # Frontmatter entries first, preview-only entries last
    sorted_entries = sorted(catalog, key=lambda e: (not e.has_frontmatter, e.relative_path))

    parts: list[str] = []
    total_chars = 0
    max_chars = max_tokens * CHARS_PER_TOKEN
    included = 0

    for entry in sorted_entries:
        text = entry.to_catalog_text()
        entry_chars = len(text)
        if total_chars + entry_chars > max_chars:
            remaining = len(sorted_entries) - included
            parts.append(f"\n... and {remaining} more documents (catalog truncated)")
            break
        parts.append(text)
        total_chars += entry_chars
        included += 1

    return "\n\n".join(parts)


def format_catalog_summary(catalog: list[CatalogEntry]) -> str:
    """Generate a statistical summary of the collection."""
    total = len(catalog)
    with_fm = sum(1 for e in catalog if e.has_frontmatter)

    cat_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    for e in catalog:
        if e.category:
            cat_counts[e.category] += 1
        if e.doc_type:
            type_counts[e.doc_type] += 1

    lines = [
        f"Total documents: {total} ({with_fm} with frontmatter, {total - with_fm} without)",
    ]
    if cat_counts:
        dist = ", ".join(f"{k}: {v}" for k, v in cat_counts.most_common())
        lines.append(f"Categories: {dist}")
    if type_counts:
        dist = ", ".join(f"{k}: {v}" for k, v in type_counts.most_common())
        lines.append(f"Document types: {dist}")

    return "\n".join(lines)


def estimate_max_docs(catalog: list[CatalogEntry], user_max: int | None = None) -> int:
    """Estimate how many full documents fit in the analysis token budget."""
    if user_max is not None:
        return max(1, min(user_max, len(catalog)))

    if not catalog:
        return MIN_DOCS

    avg_size = sum(e.file_size for e in catalog) / len(catalog)
    avg_tokens = avg_size / CHARS_PER_TOKEN

    if avg_tokens < 1:
        return MAX_DOCS

    overhead = 2000  # system prompt + query + catalog summary
    available = (MAX_ANALYSIS_TOKENS - overhead) * SAFETY_MARGIN
    estimated = int(available / avg_tokens)

    return max(MIN_DOCS, min(estimated, MAX_DOCS))


async def run_query(
    root: Path,
    settings: Settings,
    query: str | None = None,
    *,
    model: str | None = None,
    max_docs: int | None = None,
    progress_callback: object | None = None,
) -> QueryResult:
    """Execute the full query pipeline: catalog → select → analyse."""
    query = query or DEFAULT_QUERY

    # Phase 1: scan and build catalog
    files = scan_markdown_files(root)
    if not files:
        raise ValueError("No markdown files found")

    catalog = build_catalog(root, files)
    if not catalog:
        raise ValueError("Could not read any markdown files")

    if progress_callback:
        progress_callback("catalog_done")  # type: ignore[operator]

    catalog_text = format_catalog(catalog)
    catalog_tokens_est = len(catalog_text) // CHARS_PER_TOKEN
    catalog_summary = format_catalog_summary(catalog)

    effective_max = estimate_max_docs(catalog, max_docs)

    async with LLMClient(settings) as llm:
        # Phase 2a: document selection
        selection_messages = build_catalog_prompt(catalog_text, query, effective_max)
        selection: DocumentSelection = await llm.chat(
            selection_messages,
            model=model,
            response_model=DocumentSelection,
            max_tokens=16_384,
        )

        if progress_callback:
            progress_callback("selection_done")  # type: ignore[operator]

        # Resolve selected paths
        path_map = {e.relative_path: e for e in catalog}
        selected_entries: list[CatalogEntry] = []
        for p in selection.selected_paths:
            if p in path_map:
                selected_entries.append(path_map[p])
            else:
                logger.warning("LLM selected non-existent path: %s, skipping", p)

        # Fallback: if nothing selected, use top entries from catalog
        if not selected_entries:
            logger.warning("No valid documents selected, using first %d entries", effective_max)
            selected_entries = catalog[:effective_max]

        # Read full content of selected documents
        doc_parts: list[str] = []
        for entry in selected_entries:
            try:
                metadata, body = load_frontmatter(entry.path)
                doc_parts.append(
                    f"### {entry.relative_path}\n"
                    f"(title: {entry.title or 'untitled'})\n\n"
                    f"{body}"
                )
            except Exception:
                logger.warning("Failed to read selected document %s", entry.relative_path)

        documents_text = "\n\n---\n\n".join(doc_parts)
        analysis_tokens_est = len(documents_text) // CHARS_PER_TOKEN

        # Phase 2b: analysis
        analysis_messages = build_analysis_prompt(documents_text, query, catalog_summary)
        answer: QueryAnswer = await llm.chat(
            analysis_messages,
            model=model,
            response_model=QueryAnswer,
            max_tokens=16_384,
        )

        if progress_callback:
            progress_callback("analysis_done")  # type: ignore[operator]

    return QueryResult(
        answer=answer.answer,
        sources=[s.model_dump() for s in answer.sources],
        total_files_scanned=len(files),
        files_with_frontmatter=sum(1 for e in catalog if e.has_frontmatter),
        files_read_in_full=len(selected_entries),
        catalog_tokens_est=catalog_tokens_est,
        analysis_tokens_est=analysis_tokens_est,
    )


def save_query_result(
    result: QueryResult,
    root: Path,
    query: str | None,
    model: str,
    *,
    output_path: Path | None = None,
) -> Path:
    """Save the query result as a markdown file with frontmatter."""
    if output_path is None:
        result_dir = Path("result")
        result_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = result_dir / f"mdh-query-{timestamp}.md"
    else:
        dest = output_path

    now = datetime.now(timezone.utc).isoformat()

    fm_lines = [
        "---",
        f'query: "{(query or DEFAULT_QUERY).replace(chr(34), chr(39))}"',
        f"generated_at: {now}",
        f"total_scanned: {result.total_files_scanned}",
        f"files_read: {result.files_read_in_full}",
        f"model: {model}",
        "---",
        "",
    ]

    body_lines = [result.answer]

    if result.sources:
        body_lines.append("")
        body_lines.append("---")
        body_lines.append("")
        body_lines.append("### References")
        body_lines.append("")
        body_lines.append("| File | Title | Relevance |")
        body_lines.append("|------|-------|-----------|")
        for s in result.sources:
            body_lines.append(f"| {s['path']} | {s['title']} | {s['relevance']} |")

    content = "\n".join(fm_lines) + "\n".join(body_lines) + "\n"
    dest.write_text(content, encoding="utf-8")
    return dest
