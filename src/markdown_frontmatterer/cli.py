"""Typer CLI application."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from markdown_frontmatterer.config import Settings
from markdown_frontmatterer.processor import process_directory, BatchResult
from markdown_frontmatterer.scanner import scan_markdown_files

app = typer.Typer(
    name="mdfm",
    help="AI-powered YAML frontmatter generator for Markdown files.",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def _callback() -> None:
    """AI-powered YAML frontmatter generator for Markdown files."""


def _run_with_progress(
    root: Path,
    settings: Settings,
    *,
    force: bool,
    dry_run: bool,
    model: str | None,
) -> BatchResult:
    """Run the async processor with a Rich progress bar."""
    files = scan_markdown_files(root)
    total = len(files)

    if total == 0:
        console.print("[yellow]No .md files found.[/yellow]")
        raise typer.Exit()

    console.print(f"Found [bold]{total}[/bold] Markdown file(s) in [cyan]{root}[/cyan]")
    if dry_run:
        console.print("[yellow]Dry-run mode: no files will be modified.[/yellow]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processing files...", total=total)

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
            )
        )

    return result


def _print_summary(result: BatchResult, root: Path) -> None:
    """Print a summary table of processing results."""
    table = Table(title="Results")
    table.add_column("File", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Error", style="red")

    for r in sorted(result.results, key=lambda r: r.path):
        rel = r.path.relative_to(root) if r.path.is_relative_to(root) else r.path
        status = "[green]OK[/green]" if r.success else "[red]FAIL[/red]"
        table.add_row(str(rel), status, r.error[:60] if r.error else "")

    console.print(table)
    console.print(
        f"\n[bold green]{result.succeeded} succeeded[/bold green], "
        f"[bold red]{result.failed} failed[/bold red]"
    )


@app.command("process")
def process(
    directory: Annotated[
        Path,
        typer.Argument(help="Directory containing Markdown files to process."),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing frontmatter fields."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Preview without modifying files."),
    ] = False,
    concurrency: Annotated[
        int,
        typer.Option("--concurrency", "-c", help="Max concurrent LLM requests."),
    ] = 5,
    model: Annotated[
        Optional[str],
        typer.Option("--model", "-m", help="LLM model to use."),
    ] = None,
) -> None:
    """Process Markdown files and generate YAML frontmatter using AI."""
    if not directory.is_dir():
        console.print(f"[red]Error: {directory} is not a directory.[/red]")
        raise typer.Exit(code=1)

    settings = Settings(concurrency=concurrency)

    if not settings.llm_api_key:
        console.print("[red]Error: LLM_API_KEY is not set. Check your .env file.[/red]")
        raise typer.Exit(code=1)

    result = _run_with_progress(
        directory,
        settings,
        force=force,
        dry_run=dry_run,
        model=model or settings.llm_model,
    )

    _print_summary(result, directory)
