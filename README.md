# markdown-frontmatterer

마크다운 파일에 AI 기반 YAML frontmatter를 자동 생성하는 CLI 도구.

일기, 노트, 위키, 회의록 등 다양한 마크다운 기록을 스캔하여 제목, 태그, 카테고리, 요약, 엔티티, 관련 주제 등의 메타데이터를 생성한다. 향후 의미 기반 + 키워드 기반 검색의 기반 데이터로 활용할 수 있다.

## 생성되는 Frontmatter

```yaml
---
title: "문서 제목"
created_at: 2024-01-15T09:00:00
updated_at: 2026-02-24T14:30:00
tags: [python, async, web-scraping]
category: technology
doc_type: note
summary: "이 문서는 ~에 대해 설명한다"
entities:
  - name: "FastAPI"
    type: "technology"
  - name: "김철수"
    type: "person"
related_topics: [web-development, api-design]
---
```

| 필드 | 설명 | 가능한 값 |
|------|------|-----------|
| `category` | 문서 분류 | `technology`, `personal`, `work`, `research`, `creative`, `reference`, `other` |
| `doc_type` | 문서 유형 | `journal`, `note`, `wiki`, `meeting_notes`, `reference`, `tutorial`, `essay`, `log` |
| `entities` | 언급된 주요 개체 | `type`: `person`, `organization`, `technology`, `place`, `event`, `other` |

## 설치

```bash
pip install -e .

# 개발 의존성 포함
pip install -e ".[dev]"
```

## 설정

`.env.example`을 `.env`로 복사하고 API 키를 설정한다:

```bash
cp .env.example .env
```

```env
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=google/gemini-flash-1.5
```

OpenAI 호환 API라면 `LLM_BASE_URL`만 변경하면 된다 (OpenRouter, Ollama, vLLM 등).

## 사용법

```bash
# 기본 사용 — 기존 frontmatter 유지, 빈 필드만 추가
mdfm process ./my-notes

# 미리보기 (파일 수정 없음)
mdfm process ./my-notes --dry-run

# 강제 덮어쓰기 (created_at은 항상 보존)
mdfm process ./my-notes --force

# 동시 요청 수 조절
mdfm process ./my-notes --concurrency 10

# 모델 지정
mdfm process ./my-notes --model "google/gemini-flash-1.5"
```

## Merge 동작

| 모드 | 동작 |
|------|------|
| 기본 (merge) | 기존 frontmatter 필드 유지, 없는 필드만 추가 |
| `--force` | 모든 필드 덮어쓰기 (`created_at` 제외) |

`created_at`은 `--force`여도 기존 값을 보존한다 (최초 생성 시점 유지).

## Timestamp 결정 우선순위

`created_at`: git log 첫 커밋 날짜 → 파일 생성시간 → 현재시간

`updated_at`: 처리 시점의 현재 시간

## 프로젝트 구조

```
src/markdown_frontmatterer/
├── cli.py              # Typer CLI (mdfm process 커맨드)
├── config.py           # pydantic-settings 환경 설정
├── models.py           # Frontmatter/Entity Pydantic 모델
├── scanner.py          # .md 파일 재귀 탐색
├── frontmatter_io.py   # frontmatter 읽기/병합/쓰기
├── llm.py              # OpenAI 호환 async LLM 클라이언트
├── prompts.py          # LLM 프롬프트 템플릿
└── processor.py        # 오케스트레이터 (스캔→분석→병합→저장)
```

## 테스트

```bash
pytest
```

## 기술 스택

- **CLI**: Typer + Rich (progress bar, 결과 테이블)
- **LLM 호출**: httpx async + Semaphore 동시성 제어 + exponential backoff 재시도
- **Frontmatter 처리**: python-frontmatter
- **설정**: pydantic-settings (.env 자동 로드)
- **검증**: Pydantic v2 (Literal 타입으로 category/doc_type 값 제한)
