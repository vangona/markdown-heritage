"""Typer CLI application."""

from __future__ import annotations

import asyncio
import math
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from markdown_frontmatterer.config import Settings
from markdown_frontmatterer.i18n import set_lang, t
from markdown_frontmatterer.processor import process_directory, BatchResult
from markdown_frontmatterer.scanner import scan_markdown_files

# ── Model pricing ($/1M tokens): (input, output) ────────────
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # Google Gemini
    "google/gemini-flash-1.5": (0.075, 0.30),
    "google/gemini-2.0-flash-lite": (0.075, 0.30),
    "google/gemini-flash-2.0": (0.10, 0.40),
    "google/gemini-2.0-flash-001": (0.10, 0.40),
    "google/gemini-2.5-flash-lite": (0.10, 0.40),
    "google/gemini-2.5-flash": (0.30, 2.50),
    "google/gemini-2.5-pro": (1.25, 10.00),
    "google/gemini-3-flash": (0.50, 3.00),
    "google/gemini-3-pro": (2.00, 12.00),
    "google/gemini-3.1-flash": (0.50, 3.00),
    "google/gemini-3.1-pro": (2.00, 12.00),
    # OpenAI
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4.1-mini": (0.12, 0.48),
    "openai/gpt-4o": (4.00, 12.00),
    "openai/gpt-4.1": (4.00, 12.00),
    # Anthropic
    "anthropic/claude-haiku-4.5": (0.80, 4.00),
    "anthropic/claude-3.5-sonnet": (3.00, 15.00),
    "anthropic/claude-sonnet-4": (3.00, 15.00),
    "anthropic/claude-sonnet-4.6": (3.00, 15.00),
    "anthropic/claude-opus-4.5": (15.00, 75.00),
    "anthropic/claude-opus-4.6": (15.00, 75.00),
}

SYSTEM_PROMPT_TOKENS = 180
OUTPUT_TOKENS_PER_FILE = 300
CHARS_PER_TOKEN = 4
AVG_RESPONSE_SECONDS = 3

app = typer.Typer(
    name="mdfm",
    help=t("app_help"),
    no_args_is_help=True,
)
console = Console()


def _lang_callback(value: str) -> str:
    """Eager callback — sets i18n language before any command runs."""
    set_lang(value)
    return value


@app.callback()
def _callback(
    lang: Annotated[
        str,
        typer.Option(
            "--lang",
            help=t("opt_lang"),
            is_eager=True,
            callback=_lang_callback,
        ),
    ] = "en",
) -> None:
    """AI-powered YAML frontmatter generator for Markdown files."""


def _estimate(
    files: list[Path],
    max_content_chars: int,
    concurrency: int,
    model: str,
) -> dict:
    """Build a cost/time estimate dict from the scanned file list."""
    total_input = 0
    for f in files:
        file_chars = min(f.stat().st_size, max_content_chars)
        total_input += SYSTEM_PROMPT_TOKENS + file_chars // CHARS_PER_TOKEN

    total_output = len(files) * OUTPUT_TOKENS_PER_FILE
    total_tokens = total_input + total_output

    pricing = MODEL_PRICING.get(model)
    cost: float | None = None
    if pricing:
        cost = (total_input * pricing[0] + total_output * pricing[1]) / 1_000_000

    est_seconds = math.ceil(len(files) / concurrency) * AVG_RESPONSE_SECONDS

    return {
        "file_count": len(files),
        "total_input": total_input,
        "total_output": total_output,
        "total_tokens": total_tokens,
        "cost": cost,
        "model": model,
        "seconds": est_seconds,
        "concurrency": concurrency,
    }


def _show_estimate(est: dict) -> None:
    """Render the estimate as a Rich panel."""
    lines = [
        t("estimate_files", count=est["file_count"]),
        t("estimate_api_calls", count=est["file_count"]),
        t("estimate_tokens", total=est["total_tokens"], input=est["total_input"], output=est["total_output"]),
    ]
    if est["cost"] is not None:
        lines.append(t("estimate_cost", cost=est["cost"], model=est["model"]))
    else:
        lines.append(t("estimate_cost_unknown"))
    lines.append(t("estimate_time", seconds=est["seconds"], concurrency=est["concurrency"]))

    console.print(Panel("\n".join(lines), title=t("estimate_header"), border_style="cyan"))


def _run_with_progress(
    root: Path,
    settings: Settings,
    *,
    force: bool,
    dry_run: bool,
    model: str | None,
    yes: bool,
    files: list[Path] | None = None,
) -> BatchResult:
    """Run the async processor with a Rich progress bar."""
    if files is None:
        files = scan_markdown_files(root)
    total = len(files)

    if total == 0:
        console.print(f"[yellow]{t('no_files_found')}[/yellow]")
        raise typer.Exit()

    console.print(t("found_files", count=total, root=root))
    if dry_run:
        console.print(f"[yellow]{t('dry_run_notice')}[/yellow]")

    # ── Cost estimate + confirmation ─────────────────────────
    est = _estimate(files, settings.llm_max_content_chars, settings.concurrency, model or settings.llm_model)
    _show_estimate(est)

    if not dry_run and not yes:
        answer = console.input(f"{t('confirm_proceed')} ")
        if answer.strip().lower() not in ("", "y", "yes"):
            console.print(f"[yellow]{t('cancelled')}[/yellow]")
            raise typer.Exit()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(t("processing"), total=total)

        def on_progress(_result):
            progress.advance(task)

        result = asyncio.run(
            process_directory(
                root,
                settings,
                force=force,
                dry_run=dry_run,
                model=model,
                progress_callback=on_progress,
                files=files,
            )
        )

    return result


def _print_summary(result: BatchResult, root: Path) -> None:
    """Print a summary table of processing results."""
    table = Table(title=t("table_title"))
    table.add_column(t("col_file"), style="cyan")
    table.add_column(t("col_status"), justify="center")
    table.add_column(t("col_error"), style="red")

    for r in sorted(result.results, key=lambda r: r.path):
        rel = r.path.relative_to(root) if r.path.is_relative_to(root) else r.path
        status = (
            f"[green]{t('status_ok')}[/green]"
            if r.success
            else f"[red]{t('status_fail')}[/red]"
        )
        table.add_row(str(rel), status, r.error[:60] if r.error else "")

    console.print(table)
    console.print(
        f"\n[bold green]{t('summary', succeeded=result.succeeded, failed=result.failed)}[/bold green]"
    )


@app.command("process", help=t("cmd_process_help"))
def process(
    path: Annotated[
        Path,
        typer.Argument(help=t("arg_path")),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help=t("opt_force")),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help=t("opt_dry_run")),
    ] = False,
    concurrency: Annotated[
        int,
        typer.Option("--concurrency", "-c", help=t("opt_concurrency")),
    ] = 5,
    model: Annotated[
        Optional[str],
        typer.Option("--model", "-m", help=t("opt_model")),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help=t("opt_yes")),
    ] = False,
) -> None:
    """Process Markdown files and generate YAML frontmatter using AI."""
    if not path.exists():
        console.print(f"[red]{t('err_not_found', path=path)}[/red]")
        raise typer.Exit(code=1)

    # Single file mode
    if path.is_file():
        if path.suffix.lower() != ".md":
            console.print(f"[red]{t('err_not_md', path=path)}[/red]")
            raise typer.Exit(code=1)
        root = path.parent
        files: list[Path] | None = [path]
    else:
        root = path
        files = None  # let _run_with_progress scan

    settings = Settings(concurrency=concurrency)

    if not settings.llm_api_key:
        console.print(f"[red]{t('err_no_api_key')}[/red]")
        raise typer.Exit(code=1)

    result = _run_with_progress(
        root,
        settings,
        force=force,
        dry_run=dry_run,
        model=model or settings.llm_model,
        yes=yes,
        files=files,
    )

    _print_summary(result, root)
