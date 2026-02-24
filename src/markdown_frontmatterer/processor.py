"""Orchestrator: scan → analyze → merge → save pipeline."""

from __future__ import annotations

import asyncio
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field

from markdown_frontmatterer.config import Settings
from markdown_frontmatterer.frontmatter_io import load_frontmatter, merge_frontmatter, save_frontmatter
from markdown_frontmatterer.llm import LLMClient
from markdown_frontmatterer.models import Frontmatter
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


async def process_file(
    path: Path,
    client: LLMClient,
    *,
    force: bool = False,
    dry_run: bool = False,
    model: str | None = None,
) -> ProcessResult:
    """Process a single Markdown file: analyze → merge → save."""
    try:
        existing_meta, body = load_frontmatter(path)
        generated = await client.analyze(body, model=model)

        # Set timestamps
        if not generated.created_at:
            generated.created_at = resolve_created_at(path)
        generated.updated_at = datetime.now(timezone.utc)

        merged = merge_frontmatter(existing_meta, generated, force=force)

        if not dry_run:
            save_frontmatter(path, merged, body)

        return ProcessResult(path=path, success=True)
    except Exception as exc:
        logger.error("Failed to process %s: %s", path, exc)
        return ProcessResult(path=path, success=False, error=str(exc))


async def process_directory(
    root: str | Path,
    settings: Settings,
    *,
    force: bool = False,
    dry_run: bool = False,
    model: str | None = None,
    progress_callback: object | None = None,
) -> BatchResult:
    """Process all Markdown files in a directory."""
    files = scan_markdown_files(root)
    batch = BatchResult()

    async with LLMClient(settings) as client:
        tasks = [
            process_file(path, client, force=force, dry_run=dry_run, model=model)
            for path in files
        ]

        for coro in asyncio.as_completed(tasks):
            result = await coro
            batch.results.append(result)
            if progress_callback and callable(progress_callback):
                progress_callback(result)

    return batch
