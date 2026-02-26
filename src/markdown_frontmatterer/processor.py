"""Orchestrator: scan → analyze → merge → save pipeline."""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from markdown_frontmatterer.config import Settings
from markdown_frontmatterer.frontmatter_io import load_frontmatter, merge_frontmatter, save_frontmatter
from markdown_frontmatterer.llm import LLMClient
from markdown_frontmatterer.scanner import scan_markdown_files

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    path: Path
    success: bool
    error: str = ""


@dataclass
class BatchResult:
    results: list[ProcessResult] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.success)


def _git_created_at(path: Path) -> datetime | None:
    """Try to get the first commit date for a file from git log."""
    try:
        result = subprocess.run(
            ["git", "log", "--diff-filter=A", "--follow", "--format=%aI", "--", str(path)],
            capture_output=True,
            text=True,
            cwd=path.parent,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().splitlines()
            # Last line = earliest commit (first time file appeared)
            return datetime.fromisoformat(lines[-1])
    except (subprocess.TimeoutExpired, OSError, ValueError):
        pass
    return None


def _file_created_at(path: Path) -> datetime:
    """Fallback: file birth time (macOS) or mtime."""
    stat = path.stat()
    ts = getattr(stat, "st_birthtime", None) or stat.st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def resolve_created_at(path: Path) -> datetime:
    """Resolve created_at: git log → file birth time → now."""
    return _git_created_at(path) or _file_created_at(path)


_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_MD_IMAGE_RE = re.compile(r"!\[.*?\]\(([^)]+)\)")
_MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB per image (API limit is 20MB per image)


def _find_local_images(md_path: Path, meta: dict[str, Any]) -> list[Path]:
    """Find local image files referenced by a markdown document.

    Looks in:
    1. frontmatter ``media_files`` array (from ``mdh collect`` output)
    2. Markdown ``![alt](path)`` patterns in the file body
    """
    base_dir = md_path.parent
    candidates: list[str] = []

    # 1) media_files from frontmatter (collect output)
    media_files = meta.get("media_files")
    if isinstance(media_files, list):
        candidates.extend(str(f) for f in media_files)

    # 2) Markdown image references in body
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    candidates.extend(_MD_IMAGE_RE.findall(text))

    # Resolve and filter
    seen: set[Path] = set()
    result: list[Path] = []
    for raw in candidates:
        raw = raw.strip()
        if raw.startswith(("http://", "https://")):
            continue
        p = Path(raw)
        if not p.is_absolute():
            p = base_dir / p
        p = p.resolve()
        if p.suffix.lower() in _IMAGE_EXTENSIONS and p.is_file() and p not in seen:
            if p.stat().st_size > _MAX_IMAGE_BYTES:
                logger.warning("Skipping oversized image (%d MB): %s", p.stat().st_size // (1024 * 1024), p)
                continue
            seen.add(p)
            result.append(p)

    return result


async def process_file(
    path: Path,
    client: LLMClient,
    *,
    force: bool = False,
    dry_run: bool = False,
    model: str | None = None,
    vision: bool = False,
    vision_detail: str = "low",
) -> ProcessResult:
    """Process a single Markdown file: analyze → merge → save."""
    try:
        existing_meta, body = load_frontmatter(path)

        if vision:
            image_paths = _find_local_images(path, existing_meta)
            if image_paths:
                generated = await client.analyze_with_vision(
                    body, image_paths, model=model, detail=vision_detail,
                )
            else:
                logger.info("No local images found for %s, using text-only analysis", path)
                generated = await client.analyze(body, model=model)
        else:
            generated = await client.analyze(body, model=model)

        # Set timestamps
        if not generated.created_at:
            generated.created_at = resolve_created_at(path)
        generated.updated_at = datetime.now(timezone.utc)

        merged = merge_frontmatter(existing_meta, generated, force=force)

        if not dry_run:
            save_frontmatter(path, merged, body)

        return ProcessResult(path=path, success=True)
    except ValueError as exc:
        logger.error("Validation failed for %s after retries: %s", path, exc)
        return ProcessResult(path=path, success=False, error=str(exc))
    except RuntimeError as exc:
        logger.error("HTTP request failed for %s after retries: %s", path, exc)
        return ProcessResult(path=path, success=False, error=str(exc))
    except Exception as exc:
        logger.error("Unexpected error processing %s: %s", path, exc)
        return ProcessResult(path=path, success=False, error=str(exc))


async def process_directory(
    root: str | Path,
    settings: Settings,
    *,
    force: bool = False,
    dry_run: bool = False,
    model: str | None = None,
    progress_callback: object | None = None,
    files: list[Path] | None = None,
    vision: bool = False,
    vision_detail: str = "low",
) -> BatchResult:
    """Process Markdown files. Uses *files* if given, otherwise scans *root*."""
    if files is None:
        files = scan_markdown_files(root)
    batch = BatchResult()

    async with LLMClient(settings) as client:
        tasks = [
            process_file(
                path, client,
                force=force, dry_run=dry_run, model=model,
                vision=vision, vision_detail=vision_detail,
            )
            for path in files
        ]

        for coro in asyncio.as_completed(tasks):
            result = await coro
            batch.results.append(result)
            if progress_callback and callable(progress_callback):
                progress_callback(result)

    return batch
