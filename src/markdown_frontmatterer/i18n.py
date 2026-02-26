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
    "opt_skip_existing": {
        "en": "Skip files that already have frontmatter.",
        "ko": "이미 frontmatter가 있는 파일을 건너뜁니다.",
    },
    "skipped_existing": {
        "en": "Skipped [bold]{count}[/bold] file(s) with existing frontmatter",
        "ko": "이미 frontmatter가 있는 파일 [bold]{count}[/bold]개를 건너뛰었습니다",
    },
    # ── vision options ──────────────────────────────────────────
    "opt_vision": {
        "en": "Include images in AI analysis (multimodal).",
        "ko": "AI 분석에 이미지를 포함합니다 (멀티모달).",
    },
    "opt_vision_detail": {
        "en": "Image analysis detail level (low/high/auto).",
        "ko": "이미지 분석 상세 수준 (low/high/auto).",
    },
    "estimate_images": {
        "en": "Images: {count} (in {files} files, detail={detail})",
        "ko": "이미지: {count}개 ({files}개 파일, detail={detail})",
    },
    "vision_no_images": {
        "en": "--vision enabled but no local images found, using text-only analysis.",
        "ko": "--vision이 활성화되었지만 로컬 이미지가 없어 텍스트 전용 분석을 사용합니다.",
    },
    # ── query command ────────────────────────────────────────────
    "cmd_query_help": {
        "en": "Query and analyse a document collection using frontmatter metadata.",
        "ko": "frontmatter 메타데이터를 활용하여 문서 컬렉션을 조회/분석합니다.",
    },
    "arg_query_path": {
        "en": "Directory of Markdown files to query.",
        "ko": "조회할 마크다운 파일 디렉터리.",
    },
    "arg_query_prompt": {
        "en": "Question or instruction for the AI.",
        "ko": "AI에게 보낼 질문 또는 지시.",
    },
    "opt_max_docs": {
        "en": "Max documents to read in full.",
        "ko": "전체 읽기할 최대 문서 수.",
    },
    "opt_output": {
        "en": "Output file path for the result.",
        "ko": "결과 저장 파일 경로.",
    },
    "opt_no_save": {
        "en": "Don't save result to file.",
        "ko": "결과를 파일에 저장하지 않습니다.",
    },
    "query_scanning": {
        "en": "Scanning markdown files...",
        "ko": "마크다운 파일 스캔 중...",
    },
    "query_api_calls_note": {
        "en": "This will make 2 API calls (select + analyse).",
        "ko": "API 호출 2회 (선별 + 분석) 를 수행합니다.",
    },
    "query_building_catalog": {
        "en": "Building document catalog...",
        "ko": "문서 카탈로그 구축 중...",
    },
    "query_selecting_docs": {
        "en": "AI is selecting relevant documents...",
        "ko": "AI가 관련 문서를 선별하는 중...",
    },
    "query_analyzing": {
        "en": "Analysing {count} selected documents...",
        "ko": "선별된 {count}개 문서 분석 중...",
    },
    "query_done": {
        "en": "Query complete.",
        "ko": "조회 완료.",
    },
    "query_result_title": {
        "en": "Analysis Result",
        "ko": "분석 결과",
    },
    "query_sources_title": {
        "en": "References",
        "ko": "참조 문서",
    },
    "query_col_relevance": {
        "en": "Relevance",
        "ko": "관련성",
    },
    "query_stats": {
        "en": "Scanned {total} files | {with_fm} with frontmatter | Read {read} in full | ~{cat_tokens:,} catalog tokens | ~{analysis_tokens:,} analysis tokens",
        "ko": "총 {total}개 스캔 | frontmatter {with_fm}개 | 전체 읽기 {read}개 | 카탈로그 ~{cat_tokens:,} 토큰 | 분석 ~{analysis_tokens:,} 토큰",
    },
    "query_saved": {
        "en": "Saved to: {path}",
        "ko": "저장됨: {path}",
    },
    "query_found_files": {
        "en": "Found [bold]{count}[/bold] Markdown file(s) in [cyan]{root}[/cyan]",
        "ko": "[cyan]{root}[/cyan] 에서 마크다운 파일 [bold]{count}[/bold]개를 찾았습니다",
    },
    "query_no_files": {
        "en": "No .md files found in the directory.",
        "ko": "디렉터리에서 .md 파일을 찾을 수 없습니다.",
    },
    # ── collect command ──────────────────────────────────────────
    "cmd_collect_help": {
        "en": "Collect Instagram profile data and save as Markdown.",
        "ko": "Instagram 프로필 데이터를 수집하여 마크다운으로 저장합니다.",
    },
    "arg_collect_target": {
        "en": "Instagram username (@username or username).",
        "ko": "Instagram 사용자명 (@username 또는 username).",
    },
    "opt_browser": {
        "en": "Open a browser to log in to Instagram (Playwright).",
        "ko": "브라우저를 열어 Instagram 로그인 (Playwright).",
    },
    "opt_login": {
        "en": "Instagram account for login.",
        "ko": "로그인에 사용할 Instagram 계정.",
    },
    "opt_password": {
        "en": "Password (omit for interactive input).",
        "ko": "비밀번호 (생략 시 대화형 입력).",
    },
    "opt_session": {
        "en": "Session file path.",
        "ko": "세션 파일 경로.",
    },
    "opt_stories": {
        "en": "Collect stories (requires login + following).",
        "ko": "스토리 수집 (로그인+팔로잉 필요).",
    },
    "opt_highlights": {
        "en": "Collect highlights (requires login).",
        "ko": "하이라이트 수집 (로그인 필요).",
    },
    "opt_reels": {
        "en": "Collect reels.",
        "ko": "릴스 수집.",
    },
    "opt_limit": {
        "en": "Max number of posts to collect.",
        "ko": "최대 게시글 수.",
    },
    "opt_delay": {
        "en": "Delay between requests in seconds.",
        "ko": "요청 간 대기 시간(초).",
    },
    "collect_starting": {
        "en": "Collecting @{target}...",
        "ko": "@{target} 수집 시작...",
    },
    "collect_no_login_warning": {
        "en": "[yellow]Warning: No --login or --browser specified. Most data requires authentication.[/yellow]",
        "ko": "[yellow]경고: --login 또는 --browser가 지정되지 않았습니다. 대부분의 데이터는 인증이 필요합니다.[/yellow]",
    },
    "collect_browser_login_prompt": {
        "en": "Log in to Instagram in the browser, then press Enter here...",
        "ko": "브라우저에서 Instagram에 로그인한 후 여기서 Enter를 누르세요...",
    },
    "collect_browser_already_logged_in": {
        "en": "Existing login session found.",
        "ko": "기존 로그인 세션 발견.",
    },
    "collect_session_expired": {
        "en": "[yellow]Session expired. Use --browser to re-authenticate from your browser.[/yellow]",
        "ko": "[yellow]세션이 만료되었습니다. --browser 옵션으로 브라우저에서 재인증하세요.[/yellow]",
    },
    "collect_login_deprecated": {
        "en": "[yellow]Warning: --login/--password authentication is unstable (instaloader issue). Prefer --browser.[/yellow]",
        "ko": "[yellow]경고: --login/--password 인증이 불안정합니다 (instaloader 이슈). --browser 사용을 권장합니다.[/yellow]",
    },
    "collect_confirm": {
        "en": "Collect @{target}'s profile (posts{extras})?\nOutput: {output}",
        "ko": "@{target}의 프로필을 수집합니다 (게시글{extras}).\n출력: {output}",
    },
    "collect_authenticating": {
        "en": "Authenticating as @{login}...",
        "ko": "@{login}으로 인증 중...",
    },
    "collect_fetching_profile": {
        "en": "Fetching profile...",
        "ko": "프로필 가져오는 중...",
    },
    "collect_profile_info": {
        "en": "@{username} — {full_name} | {posts} posts | {followers:,} followers",
        "ko": "@{username} — {full_name} | 게시글 {posts}개 | 팔로워 {followers:,}명",
    },
    "collect_private_error": {
        "en": "[red]Error: @{username} is a private account and you are not following them.[/red]",
        "ko": "[red]오류: @{username}은(는) 비공개 계정이며 팔로우하고 있지 않습니다.[/red]",
    },
    "collect_fetching_posts": {
        "en": "Fetching posts...",
        "ko": "게시글 수집 중...",
    },
    "collect_fetching_reels": {
        "en": "Fetching reels...",
        "ko": "릴스 수집 중...",
    },
    "collect_fetching_stories": {
        "en": "Fetching stories...",
        "ko": "스토리 수집 중...",
    },
    "collect_fetching_highlights": {
        "en": "Fetching highlights...",
        "ko": "하이라이트 수집 중...",
    },
    "collect_writing": {
        "en": "Writing markdown & downloading media...",
        "ko": "마크다운 작성 및 미디어 다운로드 중...",
    },
    "collect_done": {
        "en": "Collection complete!",
        "ko": "수집 완료!",
    },
    "collect_summary": {
        "en": "{posts} posts, {reels} reels, {stories} stories, {highlights} highlight items, {media} media files",
        "ko": "게시글 {posts}개, 릴스 {reels}개, 스토리 {stories}개, 하이라이트 {highlights}개, 미디어 {media}개",
    },
    "collect_saved_to": {
        "en": "Saved to: {path}",
        "ko": "저장됨: {path}",
    },
    "collect_error": {
        "en": "[red]Error during collection: {error}[/red]",
        "ko": "[red]수집 중 오류 발생: {error}[/red]",
    },
    "collect_partial_warning": {
        "en": "[yellow]Warning: Some data could not be collected (rate limiting). Saving partial results.[/yellow]",
        "ko": "[yellow]경고: 일부 데이터를 수집하지 못했습니다 (속도 제한). 수집된 부분만 저장합니다.[/yellow]",
    },
    "collect_errors_detail": {
        "en": "[dim]Errors: {errors}[/dim]",
        "ko": "[dim]오류 내역: {errors}[/dim]",
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
