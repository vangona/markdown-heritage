"""Minimal i18n module — dict-based translations for en/ko."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

_LANG = os.environ.get("MDFM_LANG", "en")

MESSAGES: dict[str, dict[str, str]] = {
    # ── app / command descriptions ──────────────────────────────
    "app_help": {
        "en": "AI-powered YAML frontmatter generator for Markdown files.",
        "ko": "AI 기반 마크다운 YAML frontmatter 자동 생성 CLI 도구.",
    },
    "cmd_process_help": {
        "en": "Process Markdown files and generate YAML frontmatter using AI.",
        "ko": "마크다운 파일을 처리하고 AI를 사용하여 YAML frontmatter를 생성합니다.",
    },
    # ── arguments / options ─────────────────────────────────────
    "arg_path": {
        "en": "Markdown file or directory to process.",
        "ko": "처리할 마크다운 파일 또는 디렉터리.",
    },
    "opt_force": {
        "en": "Overwrite existing frontmatter fields.",
        "ko": "기존 frontmatter 필드를 덮어씁니다.",
    },
    "opt_dry_run": {
        "en": "Preview without modifying files.",
        "ko": "파일을 수정하지 않고 미리보기만 합니다.",
    },
    "opt_concurrency": {
        "en": "Max concurrent LLM requests.",
        "ko": "최대 동시 LLM 요청 수.",
    },
    "opt_model": {
        "en": "LLM model to use.",
        "ko": "사용할 LLM 모델.",
    },
    "opt_lang": {
        "en": "Language for CLI output (en/ko).",
        "ko": "CLI 출력 언어 (en/ko).",
    },
    # ── runtime messages ────────────────────────────────────────
    "no_files_found": {
        "en": "No .md files found.",
        "ko": ".md 파일을 찾을 수 없습니다.",
    },
    "found_files": {
        "en": "Found [bold]{count}[/bold] Markdown file(s) in [cyan]{root}[/cyan]",
        "ko": "[cyan]{root}[/cyan] 에서 마크다운 파일 [bold]{count}[/bold]개를 찾았습니다",
    },
    "dry_run_notice": {
        "en": "Dry-run mode: no files will be modified.",
        "ko": "드라이런 모드: 파일을 수정하지 않습니다.",
    },
    "processing": {
        "en": "Processing files...",
        "ko": "파일 처리 중...",
    },
    # ── result table ────────────────────────────────────────────
    "table_title": {
        "en": "Results",
        "ko": "결과",
    },
    "col_file": {
        "en": "File",
        "ko": "파일",
    },
    "col_status": {
        "en": "Status",
        "ko": "상태",
    },
    "col_error": {
        "en": "Error",
        "ko": "오류",
    },
    "status_ok": {
        "en": "OK",
        "ko": "성공",
    },
    "status_fail": {
        "en": "FAIL",
        "ko": "실패",
    },
    "summary": {
        "en": "{succeeded} succeeded, {failed} failed",
        "ko": "{succeeded}개 성공, {failed}개 실패",
    },
    # ── cost estimate / confirmation ─────────────────────────────
    "estimate_header": {
        "en": "Estimate",
        "ko": "예측 정보",
    },
    "estimate_files": {
        "en": "Files: {count}",
        "ko": "파일 수: {count}개",
    },
    "estimate_api_calls": {
        "en": "API calls: {count}",
        "ko": "API 호출 수: {count}회",
    },
    "estimate_tokens": {
        "en": "Est. tokens: ~{total:,} (in: ~{input:,} / out: ~{output:,})",
        "ko": "예상 토큰: ~{total:,} (입력: ~{input:,} / 출력: ~{output:,})",
    },
    "estimate_cost": {
        "en": "Est. cost: ~${cost:.4f} ({model})",
        "ko": "예상 비용: ~${cost:.4f} ({model})",
    },
    "estimate_cost_unknown": {
        "en": "Est. cost: unknown (model not in pricing table)",
        "ko": "예상 비용: 알 수 없음 (가격표에 없는 모델)",
    },
    "estimate_time": {
        "en": "Est. time: ~{seconds}s (concurrency: {concurrency})",
        "ko": "예상 시간: ~{seconds}초 (concurrency: {concurrency})",
    },
    "confirm_proceed": {
        "en": "Proceed? [Y/n]",
        "ko": "계속 진행하시겠습니까? [Y/n]",
    },
    "cancelled": {
        "en": "Cancelled.",
        "ko": "취소되었습니다.",
    },
    "opt_yes": {
        "en": "Skip confirmation prompt.",
        "ko": "확인 프롬프트를 건너뜁니다.",
    },
    # ── errors ──────────────────────────────────────────────────
    "err_not_dir": {
        "en": "Error: {path} is not a directory.",
        "ko": "오류: {path} 은(는) 디렉터리가 아닙니다.",
    },
    "err_not_md": {
        "en": "Error: {path} is not a .md file.",
        "ko": "오류: {path} 은(는) .md 파일이 아닙니다.",
    },
    "err_not_found": {
        "en": "Error: {path} does not exist.",
        "ko": "오류: {path} 을(를) 찾을 수 없습니다.",
    },
    "err_no_api_key": {
        "en": "Error: LLM_API_KEY is not set. Check your .env file.",
        "ko": "오류: LLM_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.",
    },
}


def set_lang(lang: str) -> None:
    """Override the active language at runtime."""
    global _LANG  # noqa: PLW0603
    _LANG = lang


def t(key: str, **kwargs: object) -> str:
    """Return the translated string for *key* in the current language.

    Any ``{placeholder}`` in the message is filled via ``str.format(**kwargs)``.
    Falls back to English when a translation is missing.
    """
    msg = MESSAGES.get(key, {})
    text = msg.get(_LANG) or msg.get("en", key)
    return text.format(**kwargs) if kwargs else text
