"""Typer CLI application."""

from __future__ import annotations

import asyncio
import math
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from markdown_frontmatterer.config import Settings
from markdown_frontmatterer.frontmatter_io import has_frontmatter
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
    name="mdh",
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
    skip_existing: bool = False,
    files: list[Path] | None = None,
) -> BatchResult:
    """Run the async processor with a Rich progress bar."""
    if files is None:
        files = scan_markdown_files(root)

    if skip_existing:
        before = len(files)
        files = [f for f in files if not has_frontmatter(f)]
        skipped = before - len(files)
        if skipped:
            console.print(t("skipped_existing", count=skipped))

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
    skip_existing: Annotated[
        bool,
        typer.Option("--skip-existing", "-s", help=t("opt_skip_existing")),
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
        skip_existing=skip_existing,
        files=files,
    )

    _print_summary(result, root)


@app.command("query", help=t("cmd_query_help"))
def query(
    path: Annotated[
        Path,
        typer.Argument(help=t("arg_query_path")),
    ],
    prompt: Annotated[
        Optional[str],
        typer.Argument(help=t("arg_query_prompt")),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option("--model", "-m", help=t("opt_model")),
    ] = None,
    max_docs: Annotated[
        Optional[int],
        typer.Option("--max-docs", help=t("opt_max_docs")),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help=t("opt_output")),
    ] = None,
    no_save: Annotated[
        bool,
        typer.Option("--no-save", help=t("opt_no_save")),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help=t("opt_yes")),
    ] = False,
) -> None:
    """Query and analyse a document collection using frontmatter metadata."""
    from markdown_frontmatterer.query import QueryResult, run_query, save_query_result
    from markdown_frontmatterer.scanner import scan_markdown_files as scan

    if not path.exists():
        console.print(f"[red]{t('err_not_found', path=path)}[/red]")
        raise typer.Exit(code=1)
    if not path.is_dir():
        console.print(f"[red]{t('err_not_dir', path=path)}[/red]")
        raise typer.Exit(code=1)

    settings = Settings()
    if not settings.llm_api_key:
        console.print(f"[red]{t('err_no_api_key')}[/red]")
        raise typer.Exit(code=1)

    effective_model = model or settings.llm_model

    # Quick file count
    files = scan(path)
    if not files:
        console.print(f"[yellow]{t('query_no_files')}[/yellow]")
        raise typer.Exit()

    console.print(t("query_found_files", count=len(files), root=path))
    console.print(f"[dim]{t('query_api_calls_note')}[/dim]")

    if not yes:
        answer = console.input(f"{t('confirm_proceed')} ")
        if answer.strip().lower() not in ("", "y", "yes"):
            console.print(f"[yellow]{t('cancelled')}[/yellow]")
            raise typer.Exit()

    result: QueryResult | None = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task_id = progress.add_task(t("query_building_catalog"), total=3)

        phase_count = 0

        def on_progress(phase: str) -> None:
            nonlocal phase_count
            phase_count += 1
            progress.advance(task_id)
            if phase == "catalog_done":
                progress.update(task_id, description=t("query_selecting_docs"))
            elif phase == "selection_done":
                progress.update(task_id, description=t("query_analyzing", count="..."))
            elif phase == "analysis_done":
                progress.update(task_id, description=t("query_done"))

        result = asyncio.run(
            run_query(
                path,
                settings,
                prompt,
                model=effective_model,
                max_docs=max_docs,
                progress_callback=on_progress,
            )
        )

    # ── Display result ───────────────────────────────────────
    console.print()
    console.print(Panel(Markdown(result.answer), title=t("query_result_title"), border_style="green"))

    if result.sources:
        source_table = Table(title=t("query_sources_title"))
        source_table.add_column(t("col_file"), style="cyan")
        source_table.add_column("Title")
        source_table.add_column(t("query_col_relevance"))
        for s in result.sources:
            source_table.add_row(s["path"], s["title"], s["relevance"])
        console.print(source_table)

    console.print(
        f"\n[dim]{t('query_stats', total=result.total_files_scanned, with_fm=result.files_with_frontmatter, read=result.files_read_in_full, cat_tokens=result.catalog_tokens_est, analysis_tokens=result.analysis_tokens_est)}[/dim]"
    )

    # ── Save result ──────────────────────────────────────────
    if not no_save:
        saved = save_query_result(
            result, path, prompt, effective_model, output_path=output
        )
        console.print(f"\n[green]{t('query_saved', path=saved)}[/green]")


@app.command("collect", help=t("cmd_collect_help"))
def collect(
    target: Annotated[
        str,
        typer.Argument(help=t("arg_collect_target")),
    ],
    browser: Annotated[
        bool,
        typer.Option("--browser", "-b", help=t("opt_browser")),
    ] = False,
    login: Annotated[
        Optional[str],
        typer.Option("--login", "-l", help=t("opt_login")),
    ] = None,
    password: Annotated[
        Optional[str],
        typer.Option("--password", "-p", help=t("opt_password")),
    ] = None,
    session: Annotated[
        Optional[str],
        typer.Option("--session", help=t("opt_session")),
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help=t("opt_output")),
    ] = Path("./collected"),
    stories: Annotated[
        bool,
        typer.Option("--stories", help=t("opt_stories")),
    ] = False,
    highlights: Annotated[
        bool,
        typer.Option("--highlights", help=t("opt_highlights")),
    ] = False,
    reels: Annotated[
        bool,
        typer.Option("--reels/--no-reels", help=t("opt_reels")),
    ] = True,
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-n", help=t("opt_limit")),
    ] = None,
    delay: Annotated[
        float,
        typer.Option("--delay", "-d", help=t("opt_delay")),
    ] = 5.0,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help=t("opt_yes")),
    ] = False,
) -> None:
    """Collect Instagram profile data and save as Markdown."""
    from markdown_frontmatterer.collect_writer import write_all
    from markdown_frontmatterer.collector import run_collect

    username = target.lstrip("@")

    # Warn if no auth method specified
    if not browser and not login:
        console.print(t("collect_no_login_warning"))

    # Warn about unstable login method
    if login and not browser:
        console.print(t("collect_login_deprecated"))

    # Build confirmation message
    extras = ""
    if reels:
        extras += ", reels"
    if stories:
        extras += ", stories"
    if highlights:
        extras += ", highlights"
    if limit:
        extras += f", limit {limit}"

    console.print(t("collect_confirm", target=username, extras=extras, output=output))

    if not yes:
        answer = console.input(f"{t('confirm_proceed')} ")
        if answer.strip().lower() not in ("", "y", "yes"):
            console.print(f"[yellow]{t('cancelled')}[/yellow]")
            raise typer.Exit()

    # Run collection with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(t("collect_starting", target=username), total=None)

        def on_progress(phase: str) -> None:
            if phase == "profile_done":
                progress.update(task, description=t("collect_fetching_posts"))
            elif phase.startswith("post:"):
                progress.update(task, description=t("collect_fetching_posts"))
            elif phase.startswith("reel:"):
                progress.update(task, description=t("collect_fetching_reels"))
            elif phase.startswith("story:"):
                progress.update(task, description=t("collect_fetching_stories"))
            elif phase.startswith("highlight:"):
                progress.update(task, description=t("collect_fetching_highlights"))
            elif phase == "collection_done":
                progress.update(task, description=t("collect_writing"))

        try:
            result = run_collect(
                target,
                login_user=login,
                password=password,
                session_file=session,
                browser=browser,
                output_dir=output,
                include_stories=stories,
                include_highlights=highlights,
                include_reels=reels,
                limit=limit,
                delay=delay,
                progress_callback=on_progress,
            )
        except PermissionError:
            progress.stop()
            console.print(t("collect_private_error", username=username))
            raise typer.Exit(code=1)
        except Exception as exc:
            progress.stop()
            console.print(t("collect_error", error=str(exc)))
            raise typer.Exit(code=1)

        # Show profile info
        progress.update(task, description=t("collect_writing"))
        p = result.profile
        progress.stop()

    console.print(t("collect_profile_info",
        username=p.username, full_name=p.full_name,
        posts=p.media_count, followers=p.followers,
    ))

    # Warn about partial results
    if result.errors:
        console.print(t("collect_partial_warning"))
        console.print(t("collect_errors_detail", errors="; ".join(result.errors)))

    # Check if we have anything to write
    has_content = result.posts or result.reels or result.stories or result.highlights
    if not has_content:
        console.print(t("collect_partial_warning"))
        # Still write profile + index even with no posts
        console.print("[dim]Writing profile only...[/dim]")

    # Write files
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        write_task = progress.add_task(t("collect_writing"), total=None)
        counts = write_all(result, output, delay=min(delay, 1.0))
        progress.update(write_task, description=t("collect_done"))

    # Summary
    border = "green" if not result.errors else "yellow"
    console.print(Panel(
        t("collect_summary",
            posts=counts["posts"],
            reels=counts["reels"],
            stories=counts["stories"],
            highlights=counts["highlights"],
            media=counts["media"],
        ),
        title=t("collect_done"),
        border_style=border,
    ))

    save_path = output / f"@{username}"
    console.print(f"[green]{t('collect_saved_to', path=save_path)}[/green]")
