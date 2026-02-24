# markdown-frontmatterer

마크다운 파일에 AI 기반 YAML frontmatter를 자동 생성하는 CLI 도구.

일기, 노트, 위키, 회의록 등 다양한 마크다운 기록을 스캔하여 제목, 태그, 카테고리, 요약, 엔티티, 관련 주제 등의 메타데이터를 생성한다. 향후 의미 기반 + 키워드 기반 검색의 기반 데이터로 활용할 수 있다.

## 설치

### 1. 저장소 클론 및 가상환경 생성

```bash
git clone <repo-url>
cd markdown-frontmatterer

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. 패키지 설치

```bash
# 기본 설치
pip install -e .

# 개발 의존성 포함 (pytest, ruff 등)
pip install -e ".[dev]"
```

> 반드시 가상환경 안에서 설치해야 시스템 패키지와의 충돌을 피할 수 있다.

### 3. 설치 확인

```bash
mdfm --help
```

## 설정

### .env 파일 생성

```bash
cp .env.example .env
```

`.env` 파일을 열고 API 키와 설정을 입력한다:

```env
# 필수 — LLM API 키
LLM_API_KEY=your-api-key-here

# 선택 — API 엔드포인트 (기본: OpenRouter)
LLM_BASE_URL=https://openrouter.ai/api/v1

# 선택 — 사용할 모델 (기본: google/gemini-flash-1.5)
LLM_MODEL=google/gemini-flash-1.5
```

### 환경변수 설정 전체 목록

| 환경변수 | 기본값 | 설명 |
|----------|--------|------|
| `LLM_API_KEY` | (없음, 필수) | LLM API 인증 키 |
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` | OpenAI 호환 API 엔드포인트 |
| `LLM_MODEL` | `google/gemini-flash-1.5` | 사용할 LLM 모델명 |
| `LLM_MAX_CONTENT_CHARS` | `12000` | LLM에 전송할 문서 최대 글자 수 |
| `CONCURRENCY` | `5` | 동시 LLM 요청 수 |
| `MAX_RETRIES` | `3` | 429 에러 시 재시도 횟수 |

`.env` 파일 대신 환경변수로 직접 설정해도 된다:

```bash
export LLM_API_KEY=your-api-key-here
mdfm process ./my-notes
```

### LLM 제공자별 설정 예시

**OpenRouter** (기본):
```env
LLM_API_KEY=sk-or-v1-xxxx
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=google/gemini-flash-1.5
```

**OpenAI**:
```env
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

**Ollama** (로컬):
```env
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.2
```

OpenAI 호환 API라면 `LLM_BASE_URL`만 변경하면 된다.

## 사용법

가상환경이 활성화된 상태에서 실행한다:

```bash
source .venv/bin/activate
```

### 기본 실행

```bash
# 기존 frontmatter 유지, 빈 필드만 추가
mdfm process ./my-notes
```

### 미리보기 (dry-run)

```bash
# 파일을 수정하지 않고 결과만 확인
mdfm process ./my-notes --dry-run
mdfm process ./my-notes -n          # 단축 옵션
```

### 강제 덮어쓰기

```bash
# 모든 필드를 LLM 결과로 덮어쓰기 (created_at은 항상 보존)
mdfm process ./my-notes --force
mdfm process ./my-notes -f
```

### 동시 요청 수 조절

```bash
# 동시에 10개 파일을 병렬 처리
mdfm process ./my-notes --concurrency 10
mdfm process ./my-notes -c 10
```

### 모델 지정

```bash
# .env 설정을 무시하고 특정 모델 사용
mdfm process ./my-notes --model "openai/gpt-4o-mini"
mdfm process ./my-notes -m "openai/gpt-4o-mini"
```

### 옵션 조합

```bash
# 미리보기 + 다른 모델
mdfm process ./my-notes -n -m "openai/gpt-4o-mini"

# 강제 덮어쓰기 + 높은 동시성
mdfm process ./my-notes -f -c 20
```

### CLI 옵션 요약

| 옵션 | 단축 | 기본값 | 설명 |
|------|------|--------|------|
| `--force` | `-f` | off | 기존 frontmatter 필드를 덮어쓰기 |
| `--dry-run` | `-n` | off | 파일 수정 없이 미리보기 |
| `--concurrency` | `-c` | 5 | 동시 LLM 요청 수 |
| `--model` | `-m` | .env 설정값 | 사용할 LLM 모델 |

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
| `title` | 문서 제목 | 본문에서 추론 |
| `created_at` | 최초 생성 시점 | git log / 파일 생성시간 |
| `updated_at` | 마지막 처리 시점 | 실행 시 현재 시간 |
| `tags` | 키워드 태그 | 소문자, 하이픈 구분, 3-7개 |
| `category` | 문서 분류 | `technology`, `personal`, `work`, `research`, `creative`, `reference`, `other` |
| `doc_type` | 문서 유형 | `journal`, `note`, `wiki`, `meeting_notes`, `reference`, `tutorial`, `essay`, `log` |
| `summary` | 1-2문장 요약 | 문서 언어와 동일 |
| `entities` | 주요 개체 | `type`: `person`, `organization`, `technology`, `place`, `event`, `other` |
| `related_topics` | 관련 주제 | 넓은 범위의 테마, 2-5개 |

## Merge 동작

| 모드 | 동작 |
|------|------|
| 기본 (merge) | 기존 frontmatter 필드 유지, 없는 필드만 추가 |
| `--force` | 모든 필드 덮어쓰기 (`created_at` 제외) |

`created_at`은 `--force`여도 기존 값을 보존한다 (최초 생성 시점 유지).

## Timestamp 결정 우선순위

- `created_at`: git log 첫 커밋 날짜 → 파일 생성시간(macOS birth time) → 현재시간
- `updated_at`: 처리 시점의 현재 시간

## 테스트

```bash
source .venv/bin/activate
pytest -v
```

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

## 기술 스택

- **CLI**: Typer + Rich (progress bar, 결과 테이블)
- **LLM 호출**: httpx async + Semaphore 동시성 제어 + exponential backoff 재시도
- **Frontmatter 처리**: python-frontmatter
- **설정**: pydantic-settings (.env 자동 로드)
- **검증**: Pydantic v2 (Literal 타입으로 category/doc_type 값 제한)
